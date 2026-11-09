"""Evaluation harness: metrics maths, CIs, gold validation, judge parsing, drafting, runner."""

import json
from types import SimpleNamespace

import pytest

from raglab.config import Config
from raglab.evals.draft import draft_gold, sample_chunks
from raglab.evals.gold import GoldItem, load_gold
from raglab.evals.judge import is_refusal, parse_verdict
from raglab.evals.metrics import (
    bootstrap_ci,
    doc_hit_at_k,
    hit_at_k,
    percentile,
    reciprocal_rank,
)
from raglab.evals.runner import evaluate, summarise, with_retries
from raglab.models import Chunk, RetrievedChunk


def rc(doc, page, score=0.5):
    return RetrievedChunk(Chunk(f"{doc}:p{page}:c0", doc, doc.title(), page, "text"), score)


# ---------- metrics ----------


def test_hit_and_mrr_by_rank():
    retrieved = [rc("a", 1), rc("b", 9), rc("b", 3)]
    assert hit_at_k(retrieved, "b", [3]) == 1.0
    assert reciprocal_rank(retrieved, "b", [3]) == pytest.approx(1 / 3)
    assert doc_hit_at_k(retrieved, "b") == 1.0


def test_miss_when_right_doc_wrong_page():
    retrieved = [rc("b", 9)]
    assert hit_at_k(retrieved, "b", [3]) == 0.0
    assert reciprocal_rank(retrieved, "b", [3]) == 0.0
    assert doc_hit_at_k(retrieved, "b") == 1.0


def test_answer_spanning_pages_counts_any_listed_page():
    assert hit_at_k([rc("a", 5)], "a", [4, 5]) == 1.0


def test_percentile_interpolates():
    assert percentile([1, 2, 3, 4], 50) == pytest.approx(2.5)
    assert percentile([7], 95) == 7


def test_bootstrap_ci_brackets_mean_and_is_deterministic():
    values = [1.0] * 80 + [0.0] * 20
    e1, e2 = bootstrap_ci(values, 500, seed=1), bootstrap_ci(values, 500, seed=1)
    assert e1.mean == pytest.approx(0.8)
    assert e1.ci_low < 0.8 < e1.ci_high
    assert (e1.ci_low, e1.ci_high) == (e2.ci_low, e2.ci_high)
    assert 0.05 < e1.ci_high - e1.ci_low < 0.25  # ~±0.08 for n=100


def test_bootstrap_ci_single_value_and_empty():
    assert bootstrap_ci([1.0]).ci_low == 1.0
    with pytest.raises(ValueError):
        bootstrap_ci([])


# ---------- gold set ----------


def _write(tmp_path, rows):
    p = tmp_path / "gold.jsonl"
    p.write_text("\n".join(json.dumps(r) for r in rows), encoding="utf-8")
    return p


def test_gold_loads_valid_items(tmp_path):
    p = _write(
        tmp_path,
        [
            {
                "id": "q1",
                "question": "What is the output floor?",
                "answer": "72.5%",
                "doc_id": "basel",
                "pages": [141],
                "type": "numeric",
            },
            {"id": "q2", "question": "What did the Fed decide in 2031?", "type": "unanswerable"},
        ],
    )
    items = load_gold(p)
    assert [i.answerable for i in items] == [True, False]


def test_gold_reports_line_numbers_for_bad_items(tmp_path):
    p = _write(
        tmp_path,
        [
            {"id": "q1", "question": "What is the output floor?", "answer": "72.5%"},  # no doc/page
            {
                "id": "q2",
                "question": "Unanswerable with a page?",
                "type": "unanswerable",
                "doc_id": "x",
                "pages": [1],
            },
        ],
    )
    with pytest.raises(ValueError) as e:
        load_gold(p)
    msg = str(e.value)
    assert "2 invalid" in msg and "line 1:" in msg and "line 2:" in msg


def test_gold_rejects_duplicate_ids(tmp_path):
    row = {"id": "q1", "question": "What is CET1?", "answer": "x", "doc_id": "d", "pages": [1]}
    with pytest.raises(ValueError, match="duplicate"):
        load_gold(_write(tmp_path, [row, row]))


def test_gold_missing_file_explains_next_step(tmp_path):
    with pytest.raises(FileNotFoundError, match="draft-gold"):
        load_gold(tmp_path / "nope.jsonl")


# ---------- judge ----------


def test_parse_verdict_handles_prose_and_fences():
    v = parse_verdict('Sure!\n```json\n{"faithfulness": 5, "correctness": 3, "reason": "ok"}\n```')
    assert (v.faithfulness, v.correctness) == (1.0, 0.5)


@pytest.mark.parametrize("raw", ["", "no json here", '{"faithfulness": 9}', "{not json}"])
def test_parse_verdict_never_crashes_on_bad_output(raw):
    v = parse_verdict(raw)
    assert v.faithfulness is None


def test_refusal_detection():
    assert is_refusal("I can't find this in the provided documents.")
    assert not is_refusal("The output floor is 72.5% [1].")


# ---------- retries ----------


class RateLimitError(Exception):
    pass


def test_with_retries_recovers_from_rate_limit(monkeypatch):
    monkeypatch.setattr("raglab.evals.runner.time.sleep", lambda s: None)
    calls = {"n": 0}

    def flaky():
        calls["n"] += 1
        if calls["n"] < 3:
            raise RateLimitError("429")
        return "ok"

    assert with_retries(flaky, max_retries=5) == "ok"
    assert calls["n"] == 3


def test_with_retries_does_not_retry_other_errors():
    with pytest.raises(KeyError):
        with_retries(lambda: (_ for _ in ()).throw(KeyError("x")), max_retries=5)


# ---------- runner with fakes ----------


def fake_completion(content):
    def complete(**_kw):
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=content))],
            usage=SimpleNamespace(prompt_tokens=10, completion_tokens=5),
        )

    return complete


class FakePipeline:
    """Returns fixed chunks; the 'generator' answers or refuses based on the question."""

    def __init__(self):
        self.generator = SimpleNamespace(generate=self._generate)

    def retrieve(self, q, top_k=None):
        return [rc("basel", 141, 0.8), rc("trm", 3, 0.4)]

    def _generate(self, q, chunks, model):
        if "2031" in q:
            return (
                "I can't find this in the provided documents.",
                {"prompt_tokens": 1},
                0.001,
                model,
            )
        return "The output floor is 72.5% [1].", {"prompt_tokens": 1}, 0.002, model

    def close(self):
        pass


GOLD = [
    GoldItem(
        id="q1",
        question="What is the output floor?",
        answer="72.5%",
        doc_id="basel",
        pages=[141],
        type="numeric",
    ),
    GoldItem(id="q2", question="What does TRM say on page 9?", answer="x", doc_id="trm", pages=[9]),
    GoldItem(id="q3", question="What did the Fed decide in 2031?", type="unanswerable"),
]


def test_evaluate_retrieval_only_makes_no_llm_calls():
    def boom(**_kw):
        raise AssertionError("LLM must not be called")

    res = evaluate(Config(), GOLD, retrieval_only=True, pipeline=FakePipeline(), completion_fn=boom)
    s = res["summary"]
    assert s["hit_at_k"]["mean"] == pytest.approx(0.5)  # q1 hit, q2 wrong page
    assert s["doc_hit_at_k"]["mean"] == 1.0
    assert "faithfulness" not in s
    assert res["meta"]["mode"] == "retrieval-only"


def test_evaluate_full_scores_judge_refusal_and_cost():
    judge = fake_completion('{"faithfulness": 5, "correctness": 5, "reason": "matches"}')
    res = evaluate(Config(), GOLD, pipeline=FakePipeline(), completion_fn=judge)
    s = res["summary"]
    assert s["faithfulness"]["mean"] == 1.0
    assert s["refusal_accuracy"] == 1.0  # refused the unanswerable one
    assert s["false_refusal_rate"] == 0.0
    assert s["cost_usd_per_query"] > 0
    assert res["items"][2]["refused"] is True


def test_summary_counts_wrong_refusal_as_incorrect():
    rows = [
        {
            "id": "q",
            "type": "factoid",
            "retrieve_ms": 5,
            "generate_ms": 10,
            "hit": 1.0,
            "doc_hit": 1.0,
            "rr": 1.0,
            "answer": "I can't find this in the provided documents.",
            "refused": True,
            "correctness": 0.0,
            "cost_usd": None,
        }
    ]
    s = summarise(rows)
    assert s["false_refusal_rate"] == 1.0
    assert s["correctness"]["mean"] == 0.0
    assert s["generator_cost_unknown"] == 1


# ---------- drafting ----------


def test_sample_chunks_covers_every_document():
    chunks = [Chunk(f"{d}:{i}", d, d, i, "x" * 400) for d in ("a", "b", "c") for i in range(10)]
    picked = sample_chunks(chunks, 6)
    assert {c.doc_id for c in picked} == {"a", "b", "c"}
    assert len(picked) == 6


def test_draft_gold_produces_valid_items_after_review():
    chunks = [Chunk("basel:p141:c0", "basel", "Basel III", 141, "The output floor is 72.5%. " * 20)]
    responses = iter(
        [
            '{"question": "What is the output floor level?", "answer": "72.5%", "type": "numeric"}',
            '{"question": "What did MAS announce in 2031 about crypto capital?"}',
        ]
    )

    def complete(**_kw):
        return fake_completion(next(responses))()

    drafts = draft_gold(Config(), chunks, n=2, completion_fn=complete)
    assert [d["type"] for d in drafts] == ["numeric", "unanswerable"]
    assert drafts[0]["doc_id"] == "basel" and drafts[0]["pages"] == [141]
    for d in drafts:  # drafts already satisfy the gold schema
        GoldItem.model_validate(d)


# ---------- review fixes ----------


def test_judge_cost_counted_when_generator_is_free():
    rows = [
        {
            "id": "q",
            "type": "factoid",
            "retrieve_ms": 5,
            "generate_ms": 10,
            "hit": 1.0,
            "doc_hit": 1.0,
            "rr": 1.0,
            "answer": "x",
            "refused": False,
            "faithfulness": 1.0,
            "correctness": 1.0,
            "judge_reason": "ok",
            "cost_usd": None,
            "judge_cost_usd": 0.004,
        }
    ]
    s = summarise(rows)
    assert s["cost_usd_total"] == pytest.approx(0.004)
    assert s["generator_cost_unknown"] == 1


def test_one_failing_question_does_not_lose_the_run():
    class Flaky(FakePipeline):
        def _generate(self, q, chunks, model):
            if "TRM" in q:
                raise TimeoutError("provider timed out")
            return super()._generate(q, chunks, model)

    judge = fake_completion('{"faithfulness": 5, "correctness": 5, "reason": "ok"}')
    res = evaluate(Config(), GOLD, pipeline=Flaky(), completion_fn=judge)
    s = res["summary"]
    assert s["n_errors"] == 1
    assert "TimeoutError" in res["items"][1]["error"]
    assert s["hit_at_k"]["n"] == 2  # retrieval still scored for the failed question
    assert s["correctness"]["n"] == 1  # only the completed answerable question


@pytest.mark.parametrize(
    "text, refused",
    [
        ("I can’t find this in the provided documents.", True),  # curly apostrophe
        ("The text does not contain the 2019 figure, but the 2020 figure is 8% [1].", False),
        ("There is no information on 2019; the 2020 ratio is 14.1% [2].", False),
        (None, False),
    ],
)
def test_refusal_detection_edge_cases(text, refused):
    assert is_refusal(text) is refused


def test_judge_rejects_boolean_scores():
    assert parse_verdict('{"faithfulness": true, "correctness": 4}').faithfulness is None


def test_unparseable_judge_is_reported_not_hidden():
    judge = fake_completion("I think it's fine")
    res = evaluate(Config(), GOLD[:1], pipeline=FakePipeline(), completion_fn=judge)
    assert res["summary"]["judge_unparseable"] == 1
    assert "correctness" not in res["summary"]


def test_limit_zero_means_zero_questions_and_names_file_separately(tmp_path):
    from raglab.evals.runner import write_results

    cfg = Config.model_validate({"evaluation": {"results_dir": str(tmp_path)}})
    res = evaluate(cfg, GOLD, retrieval_only=True, limit=2, pipeline=FakePipeline())
    assert res["summary"]["n_questions"] == 2
    assert write_results(res, cfg).name == "baseline__retrieval-only__limit2.json"
    assert (
        evaluate(cfg, GOLD, retrieval_only=True, limit=0, pipeline=FakePipeline())["summary"][
            "n_questions"
        ]
        == 0
    )
