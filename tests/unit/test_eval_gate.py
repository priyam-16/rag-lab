"""Regression gate (runs in CI): ingest a small synthetic corpus offline and require perfect
retrieval on its gold set. If a code change breaks parsing, chunking, storage or retrieval,
this fails and blocks the merge.

Offline: HashEmbedder + local Qdrant in a temp folder. The real-corpus gate is
`raglab evaluate --retrieval-only --fail-under-hit <x>` on your machine or a scheduler.
"""

import json

import pymupdf

from raglab import cli
from raglab.config import Config
from raglab.evals.gold import load_gold
from raglab.evals.runner import evaluate
from raglab.pipeline import ingest

DOCS = {
    "capital": [
        "The output floor is set at 72.5 percent of standardised risk weighted assets.",
        "Banks must hold common equity tier one capital of at least 4.5 percent.",
    ],
    "techrisk": [
        "Banks should test incident response plans for cyber attacks every year.",
        "Critical systems must have a recovery time objective of four hours.",
    ],
    "fairness": [
        "Models used for credit decisions should be explainable to affected customers.",
        "Firms should regularly review models for unintended bias against groups.",
    ],
}
GOLD = [
    ("output floor percent of standardised risk weighted assets", "capital", 1),
    ("common equity tier one capital minimum", "capital", 2),
    ("test incident response plans cyber attacks", "techrisk", 1),
    ("recovery time objective critical systems", "techrisk", 2),
    ("explainable credit decisions customers", "fairness", 1),
    ("review models unintended bias groups", "fairness", 2),
]


def _corpus(tmp_path):
    raw = tmp_path / "raw"
    raw.mkdir()
    for name, pages in DOCS.items():
        doc = pymupdf.open()
        for text in pages:
            doc.new_page().insert_text((72, 72), text)
        doc.save(raw / f"{name}.pdf")
    gold = tmp_path / "gold.jsonl"
    gold.write_text(
        "\n".join(
            json.dumps({"id": f"g{i}", "question": q, "answer": "x", "doc_id": d, "pages": [p]})
            for i, (q, d, p) in enumerate(GOLD)
        ),
        encoding="utf-8",
    )
    cfg = Config.model_validate(
        {
            "name": "gate",
            "corpus": {"raw_dir": str(raw), "processed_dir": str(tmp_path / "processed")},
            "embedding": {"provider": "hash"},
            "vector_store": {"collection": "gate", "local_path": str(tmp_path / "qdrant")},
            "retrieval": {"top_k": 1},
            "evaluation": {"results_dir": str(tmp_path / "results"), "n_bootstrap": 200},
        }
    )
    return cfg, gold


def test_retrieval_gate_on_fixture_corpus(tmp_path):
    cfg, gold = _corpus(tmp_path)
    stats = ingest(cfg)
    assert stats["documents"] == 3
    assert (tmp_path / "processed" / "gate.chunks.jsonl").exists()

    result = evaluate(cfg, load_gold(gold), retrieval_only=True)
    assert result["summary"]["hit_at_k"]["mean"] == 1.0, result["summary"]


def test_cli_fail_under_hit_returns_exit_code_1(tmp_path, monkeypatch):
    cfg, gold = _corpus(tmp_path)
    ingest(cfg)
    monkeypatch.setattr("raglab.config.load_config", lambda _p: cfg)
    ok = cli.main(["evaluate", "--gold", str(gold), "--retrieval-only", "--fail-under-hit", "0.9"])
    impossible = cli.main(
        ["evaluate", "--gold", str(gold), "--retrieval-only", "--fail-under-hit", "1.01"]
    )
    assert (ok, impossible) == (0, 1)
