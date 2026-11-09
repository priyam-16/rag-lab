# 001 — Tasks

- [x] 1. Persist chunks to JSONL at ingest (+ `corpus.processed_dir` config field)
- [x] 2. Gold-set schema + loader with validation (`src/raglab/evals/gold.py`) + tests
- [x] 3. Retrieval metrics: hit@k, doc-hit@k, MRR (`evals/metrics.py`) + tests
- [x] 4. `raglab draft-gold` command (LLM drafts from sampled chunks) + test with fake LLM
- [ ] 5. Human review of ~40 drafted questions → `evals/gold_set.jsonl`   ← owner
- [x] 6. LLM judge (faithfulness, correctness, refusal) with robust JSON parsing + tests
- [x] 7. `raglab evaluate` runner: retrieval-only + full modes, retries, result JSON + tests
- [ ] 8. Run baseline; commit `results/baseline__*.json`; add LEARNING.md row
- [x] 9. `uv run poe test` green; update run-eval skill status line

Added beyond spec: bootstrap 95% CIs on every metric; `--fail-under-hit` regression gate (CI runs it on a synthetic corpus); false-refusal rate; hit@k by question type.
