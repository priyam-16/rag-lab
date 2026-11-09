---
name: run-eval
description: Evaluate a config against the gold question set and summarise results vs the baseline. Use when asked to score, benchmark or compare configs.
---

# Run an evaluation

> Requires a reviewed gold set at `evals/gold_set.jsonl` (draft with `raglab draft-gold`).

1. Confirm the config's index exists (else `uv run raglab ingest --config <cfg>`).
2. Cheap first: retrieval-only metrics (free, fast):
   `uv run raglab evaluate --config <cfg> --retrieval-only`
3. Full run (calls generator + judge, costs money): state the expected cost first
   (questions x ~$0.01 for Claude-class models; Groq free tier ~$0), then
   `uv run raglab evaluate --config <cfg>`
4. Results land in `results/<config>__<model>.json`.
5. Summarise vs baseline as a table: hit@k, MRR, faithfulness, correctness, p50/p95 latency, cost/query.
   Call out regressions, not just wins. Note sample size; differences of 1-2 questions are noise.
6. Add the row to `docs/LEARNING.md`.
