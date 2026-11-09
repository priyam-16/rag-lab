"""Run a config against the gold set and save comparable results.

Two modes:
  retrieval-only  no LLM calls, free, seconds: hit@k, doc-hit@k, MRR (+ CIs), retrieval latency
  full            + generation and LLM judge: faithfulness, correctness, refusal accuracy,
                  false-refusal rate, end-to-end latency, cost per query
"""

from __future__ import annotations

import json
import logging
import re
import subprocess
import time
from datetime import UTC, datetime
from pathlib import Path

from raglab.config import REPO_ROOT, Config
from raglab.evals.gold import GoldItem, describe
from raglab.evals.judge import is_refusal, judge_answer
from raglab.evals.metrics import (
    bootstrap_ci,
    doc_hit_at_k,
    hit_at_k,
    percentile,
    reciprocal_rank,
)

log = logging.getLogger(__name__)


def with_retries(fn, max_retries: int = 5, base_delay: float = 2.0):
    """Retry on provider rate limits with exponential backoff (2, 4, 8 ... s, capped at 30)."""
    for attempt in range(max_retries + 1):
        try:
            return fn()
        except Exception as e:  # noqa: BLE001 - match by name to avoid importing provider SDKs
            is_rate_limit = "RateLimit" in type(e).__name__ or "429" in str(e)
            if not is_rate_limit or attempt == max_retries:
                raise
            delay = min(base_delay * 2**attempt, 30)
            log.warning("rate limited, retrying in %.0fs (%d/%d)", delay, attempt + 1, max_retries)
            time.sleep(delay)


def _git_commit() -> str | None:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=5,
        )
        return out.stdout.strip() or None
    except Exception:  # noqa: BLE001 - not a git checkout (e.g. Docker image)
        return None


def _slug(s: str) -> str:
    return re.sub(r"[^a-zA-Z0-9.-]+", "-", s).strip("-")


def _p(values: list[float], q: float) -> float | None:
    return round(percentile(values, q), 1) if values else None


def evaluate(
    cfg: Config,
    gold: list[GoldItem],
    *,
    retrieval_only: bool = False,
    model: str | None = None,
    judge_model: str | None = None,
    limit: int | None = None,
    pipeline=None,
    completion_fn=None,
) -> dict:
    """Score `cfg` on `gold`. `pipeline` / `completion_fn` let tests inject fakes."""
    from raglab.pipeline import RAGPipeline

    items = gold[:limit] if limit is not None else gold
    gen_model = model or cfg.generation.model
    j_model = judge_model or cfg.evaluation.judge_model
    own_pipeline = pipeline is None
    pipe = pipeline or RAGPipeline(cfg)

    rows = []
    try:
        for i, item in enumerate(items, start=1):
            row: dict = {"id": item.id, "type": item.type.value, "question": item.question}
            # One failing question must not lose the whole run: record the error and continue.
            try:
                _score_item(row, item, pipe, retrieval_only, gen_model, j_model, cfg, completion_fn)
            except Exception as e:  # noqa: BLE001
                row["error"] = f"{type(e).__name__}: {e}"[:500]
                log.warning("question %s failed: %s", item.id, row["error"])
            rows.append(row)
            if i % 10 == 0 or i == len(items):
                log.info("evaluated %d/%d", i, len(items))
    finally:
        if own_pipeline:
            pipe.close()

    return {
        "meta": {
            "config": cfg.name,
            "config_body": cfg.model_dump(),
            "mode": "retrieval-only" if retrieval_only else "full",
            "generator_model": None if retrieval_only else gen_model,
            "judge_model": None if retrieval_only else j_model,
            "top_k": cfg.retrieval.top_k,
            "limit": limit,
            "git_commit": _git_commit(),
            "timestamp": datetime.now(UTC).isoformat(timespec="seconds"),
            "gold": describe(items),
        },
        "summary": summarise(rows, cfg.evaluation.n_bootstrap, retrieval_only),
        "items": rows,
    }


def _score_item(row, item, pipe, retrieval_only, gen_model, j_model, cfg, completion_fn) -> None:
    retries = cfg.evaluation.max_retries
    t0 = time.perf_counter()
    retrieved = pipe.retrieve(item.question)
    row["retrieve_ms"] = round((time.perf_counter() - t0) * 1000, 1)
    row["retrieved"] = [
        {
            "chunk_id": rc.chunk.chunk_id,
            "doc_id": rc.chunk.doc_id,
            "page": rc.chunk.page,
            "score": round(rc.score, 4),
        }
        for rc in retrieved
    ]
    if item.answerable:
        row["hit"] = hit_at_k(retrieved, item.doc_id, item.pages)
        row["doc_hit"] = doc_hit_at_k(retrieved, item.doc_id)
        row["rr"] = reciprocal_rank(retrieved, item.doc_id, item.pages)
    if retrieval_only:
        return

    t1 = time.perf_counter()
    text, usage, cost, _ = with_retries(
        lambda: pipe.generator.generate(item.question, retrieved, gen_model), retries
    )
    text = text or ""
    row["generate_ms"] = round((time.perf_counter() - t1) * 1000, 1)
    row["answer"] = text
    row["usage"] = usage
    row["cost_usd"] = cost
    row["refused"] = refused = is_refusal(text)
    if not item.answerable:
        return  # scored by refusal_accuracy: answering an unanswerable question = failure
    if refused:
        row["correctness"] = 0.0  # refused although the answer exists
        return
    verdict, _j_usage, j_cost = with_retries(
        lambda: judge_answer(
            item.question,
            item.answer,
            text,
            retrieved,
            j_model,
            cfg.evaluation.judge_max_tokens,
            completion_fn,
        ),
        retries,
    )
    row["faithfulness"] = verdict.faithfulness
    row["correctness"] = verdict.correctness
    row["judge_reason"] = verdict.reason
    row["judge_cost_usd"] = j_cost


def summarise(rows: list[dict], n_bootstrap: int = 1000, retrieval_only: bool = False) -> dict:
    errors = [r for r in rows if "error" in r]
    ans = [r for r in rows if "hit" in r]
    out: dict = {"n_questions": len(rows), "n_answerable": len(ans), "n_errors": len(errors)}
    if ans:
        out["hit_at_k"] = bootstrap_ci([r["hit"] for r in ans], n_bootstrap).as_dict()
        out["doc_hit_at_k"] = bootstrap_ci([r["doc_hit"] for r in ans], n_bootstrap).as_dict()
        out["mrr"] = bootstrap_ci([r["rr"] for r in ans], n_bootstrap).as_dict()
        by_type: dict[str, list[float]] = {}
        for r in ans:
            by_type.setdefault(r["type"], []).append(r["hit"])
        out["hit_at_k_by_type"] = {t: round(sum(v) / len(v), 3) for t, v in by_type.items()}
    rtimes = [r["retrieve_ms"] for r in rows if "retrieve_ms" in r]
    out["retrieve_ms_p50"] = _p(rtimes, 50)
    out["retrieve_ms_p95"] = _p(rtimes, 95)
    if retrieval_only:
        return out
    done = [r for r in rows if "error" not in r and "answer" in r]  # generation completed

    faith = [r["faithfulness"] for r in done if r.get("faithfulness") is not None]
    corr = [r["correctness"] for r in done if r.get("correctness") is not None]
    if faith:
        out["faithfulness"] = bootstrap_ci(faith, n_bootstrap).as_dict()
    if corr:
        out["correctness"] = bootstrap_ci(corr, n_bootstrap).as_dict()
    # Unparseable verdicts are excluded from the means above, so report how many there were.
    out["judge_unparseable"] = sum(
        1
        for r in done
        if "judge_reason" in r and (r.get("faithfulness") is None or r.get("correctness") is None)
    )
    unans = [r for r in done if r["type"] == "unanswerable"]
    if unans:
        out["refusal_accuracy"] = round(sum(r["refused"] for r in unans) / len(unans), 3)
    ans_done = [r for r in done if "hit" in r]
    if ans_done:
        out["false_refusal_rate"] = round(sum(r["refused"] for r in ans_done) / len(ans_done), 3)
    totals = [r["retrieve_ms"] + r["generate_ms"] for r in done]
    out["total_ms_p50"] = _p(totals, 50)
    out["total_ms_p95"] = _p(totals, 95)
    # Generator and judge costs are added separately: a free generator (cost None) can still
    # have a paid judge. Questions with an unknown generator price are counted, not hidden.
    costs = [(r.get("cost_usd") or 0) + (r.get("judge_cost_usd") or 0) for r in done]
    out["cost_usd_total"] = round(sum(costs), 5) if done else None
    out["cost_usd_per_query"] = round(sum(costs) / len(done), 5) if done else None
    out["generator_cost_unknown"] = sum(1 for r in done if r.get("cost_usd") is None)
    return out


def write_results(result: dict, cfg: Config) -> Path:
    meta = result["meta"]
    model = meta["generator_model"] or "retrieval-only"
    suffix = f"__limit{meta['limit']}" if meta.get("limit") is not None else ""
    name = (
        f"{_slug(cfg.name)}__{_slug(model)}{suffix}.json"  # partial runs never overwrite full ones
    )
    path = cfg.resolve(cfg.evaluation.results_dir) / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    return path


def format_summary(result: dict) -> str:
    s, m = result["summary"], result["meta"]
    lines = [
        f"config={m['config']}  mode={m['mode']}  model={m['generator_model']}  "
        f"judge={m['judge_model']}  top_k={m['top_k']}  questions={s['n_questions']}",
        "metric                  mean    95% CI",
    ]
    for key in ("hit_at_k", "doc_hit_at_k", "mrr", "faithfulness", "correctness"):
        if key in s:
            e = s[key]
            lines.append(f"  {key:<20} {e['mean']:.3f}   [{e['ci_low']:.3f}, {e['ci_high']:.3f}]")
    for key in (
        "n_errors",
        "refusal_accuracy",
        "false_refusal_rate",
        "judge_unparseable",
        "retrieve_ms_p50",
        "retrieve_ms_p95",
        "total_ms_p50",
        "total_ms_p95",
        "cost_usd_per_query",
        "generator_cost_unknown",
    ):
        if key in s and s[key] is not None:
            lines.append(f"  {key:<20} {s[key]}")
    if "hit_at_k_by_type" in s:
        lines.append(f"  hit_at_k by type     {s['hit_at_k_by_type']}")
    return "\n".join(lines)
