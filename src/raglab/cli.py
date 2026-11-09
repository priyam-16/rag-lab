"""raglab command-line interface — one command, several subcommands.

    raglab download                                   fetch the default corpus into data/raw
    raglab ingest   --config configs/default.yaml     parse -> chunk -> embed -> index
    raglab ask      "question" [--model M] [--top-k K]
    raglab draft-gold [--n 40]                         LLM drafts gold questions for human review
    raglab evaluate [--retrieval-only] [--fail-under-hit 0.8]   score a config on the gold set
    raglab serve    [--port 8000] [--reload]

pyproject.toml has `[project.scripts] raglab = "raglab.cli:main"`, so installing the
project creates a `raglab` launcher (raglab.exe on Windows) that calls main() below.

Exit codes: 0 = success, 1 = failure (schedulers such as Control-M rely on this).
"""

from __future__ import annotations

import argparse
import logging
import sys

DEFAULT_CONFIG = "configs/default.yaml"
log = logging.getLogger("raglab")


# ---------- one small function per subcommand ----------


def cmd_download(args: argparse.Namespace) -> None:
    from raglab.ingest.download import download_corpus

    missing = download_corpus()
    if missing and args.strict:
        raise RuntimeError(f"{len(missing)} document(s) must be saved manually: {missing}")


def cmd_ingest(args: argparse.Namespace) -> None:
    from raglab.config import load_config
    from raglab.pipeline import ingest

    stats = ingest(load_config(args.config))
    log.info("ingest done: %s", stats)


def cmd_ask(args: argparse.Namespace) -> None:
    from raglab.config import load_config
    from raglab.pipeline import RAGPipeline

    pipe = RAGPipeline(load_config(args.config))
    try:
        ans = pipe.ask(args.question, args.top_k, args.model)
    finally:
        pipe.close()
    print(f"\n{ans.answer}\n\nSources:")
    for i, rc in enumerate(ans.citations, start=1):
        print(f"  [{i}] {rc.chunk.title} - p.{rc.chunk.page}  (score {rc.score:.3f})")
    cost = f"${ans.cost_usd:.5f}" if ans.cost_usd is not None else "n/a"
    print(f"\nmodel={ans.model}  timings={ans.timings_ms}  tokens={ans.usage}  cost={cost}")


def cmd_draft_gold(args: argparse.Namespace) -> None:
    from raglab.config import load_config
    from raglab.evals.draft import draft_gold, write_drafts
    from raglab.pipeline import chunks_path, load_chunks

    cfg = load_config(args.config)
    drafts = draft_gold(cfg, load_chunks(chunks_path(cfg)), n=args.n, model=args.model)
    out = write_drafts(drafts, cfg.resolve(args.out))
    log.info("wrote %d draft questions to %s", len(drafts), out)
    log.info(
        "NEXT: check every item against its PDF page, fix/delete, save as %s",
        cfg.evaluation.gold_path,
    )


def cmd_evaluate(args: argparse.Namespace) -> None:
    from raglab.config import load_config
    from raglab.evals.gold import load_gold
    from raglab.evals.runner import evaluate, format_summary, write_results

    cfg = load_config(args.config)
    gold = load_gold(cfg.resolve(args.gold or cfg.evaluation.gold_path))
    result = evaluate(
        cfg,
        gold,
        retrieval_only=args.retrieval_only,
        model=args.model,
        judge_model=args.judge_model,
        limit=args.limit,
    )
    path = write_results(result, cfg)
    print(format_summary(result))
    log.info("results saved to %s", path)

    # Regression gate: fail the command (exit 1) if retrieval quality drops below the floor.
    if args.fail_under_hit is not None:
        hit = result["summary"].get("hit_at_k", {}).get("mean")
        if hit is None or hit < args.fail_under_hit:
            raise RuntimeError(f"hit@k {hit} is below the required {args.fail_under_hit}")


def cmd_serve(args: argparse.Namespace) -> None:
    import uvicorn

    from raglab.config import REPO_ROOT

    # `api/` sits next to `src/`, not inside the package. A launcher doesn't put the
    # repo folder on sys.path, so tell uvicorn where to import `api.main` from.
    uvicorn.run(
        "api.main:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        app_dir=str(REPO_ROOT),
    )


# ---------- the parser: reads the words you typed and picks a function ----------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="raglab", description="RAG Lab pipeline")
    parser.add_argument("-v", "--verbose", action="store_true", help="debug logging")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("download", help="download the default corpus into data/raw")
    p.add_argument("--strict", action="store_true", help="fail if any document needs manual save")
    p.set_defaults(func=cmd_download)

    p = sub.add_parser("ingest", help="parse, chunk, embed and index all PDFs")
    p.add_argument("--config", default=DEFAULT_CONFIG)
    p.set_defaults(func=cmd_ingest)

    p = sub.add_parser("ask", help="ask one question")
    p.add_argument("question")
    p.add_argument("--config", default=DEFAULT_CONFIG)
    p.add_argument("--model", default=None, help="override generation.model, e.g. anthropic/...")
    p.add_argument("--top-k", type=int, default=None)
    p.set_defaults(func=cmd_ask)

    p = sub.add_parser(
        "draft-gold", help="LLM-draft gold questions from indexed chunks (for review)"
    )
    p.add_argument("--config", default=DEFAULT_CONFIG)
    p.add_argument("--n", type=int, default=40, help="number of questions (~10%% unanswerable)")
    p.add_argument("--model", default=None, help="drafting model (default: evaluation.judge_model)")
    p.add_argument("--out", default="evals/gold_set.draft.jsonl")
    p.set_defaults(func=cmd_draft_gold)

    p = sub.add_parser("evaluate", help="score a config against the gold set")
    p.add_argument("--config", default=DEFAULT_CONFIG)
    p.add_argument("--gold", default=None, help="gold file (default: evaluation.gold_path)")
    p.add_argument("--retrieval-only", action="store_true", help="no LLM calls: free and fast")
    p.add_argument("--model", default=None, help="override generation.model")
    p.add_argument("--judge-model", default=None, help="override evaluation.judge_model")
    p.add_argument("--limit", type=int, default=None, help="only the first N questions")
    p.add_argument(
        "--fail-under-hit",
        type=float,
        default=None,
        help="exit 1 if hit@k is below this (regression gate for CI / schedulers)",
    )
    p.set_defaults(func=cmd_evaluate)

    p = sub.add_parser("serve", help="start the FastAPI server")
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=8000)
    p.add_argument("--reload", action="store_true", help="auto-reload on code changes (dev)")
    p.set_defaults(func=cmd_serve)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    try:
        args.func(args)
        return 0
    except KeyboardInterrupt:
        log.warning("interrupted")
        return 130
    except Exception:
        log.exception("raglab %s failed", args.command)
        return 1


if __name__ == "__main__":  # also allows: python -m raglab.cli ingest
    sys.exit(main())
