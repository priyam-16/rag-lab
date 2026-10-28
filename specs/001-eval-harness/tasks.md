# 001 — Tasks

- [ ] 1. Persist chunks to JSONL at ingest (+ `corpus.processed_dir` config field)
- [ ] 2. Gold-set schema + loader with validation (`src/raglab/evals/gold.py`) + tests
- [ ] 3. Retrieval metrics: hit@k, doc-hit@k, MRR (`evals/metrics.py`) + tests
- [ ] 4. `raglab draft-gold` command (LLM drafts from sampled chunks) + test with fake LLM
- [ ] 5. Human review of ~40 drafted questions → `evals/gold_set.jsonl`   ← owner
- [ ] 6. LLM judge (faithfulness, correctness, refusal) with robust JSON parsing + tests
- [ ] 7. `raglab evaluate` runner: retrieval-only + full modes, retries, result JSON + tests
- [ ] 8. Run baseline; commit `results/baseline__*.json`; add LEARNING.md row
- [ ] 9. `uv run poe test` green; update run-eval skill status line
