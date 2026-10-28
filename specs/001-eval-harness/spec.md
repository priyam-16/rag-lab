# 001 — Evaluation harness

## Problem
We can't tell whether any change helps. Cosine scores rank chunks but don't measure
whether retrieval found the right page or whether answers are correct and grounded.
Every later technique (hybrid, rerank, parsing, agentic) needs a fixed, repeatable score.

## Goal / non-goals
- Goal: one command that scores a config on a gold question set and saves comparable results.
- Goal: a cheap retrieval-only mode (no LLM calls) for fast iteration.
- Not in scope: dashboard (week 5), statistical significance tests beyond a noise note.

## Design
- **Gold set** `evals/gold_set.jsonl`, one object per line:
  `{id, question, answer, doc_id, pages[], type, difficulty}`;
  `type` in factoid | numeric | table | multi_hop | cross_doc | unanswerable.
- **Drafting** `raglab draft-gold --n 40`: samples chunks across documents (stratified),
  asks an LLM for one Q/A per chunk with its page, plus ~10% unanswerable questions.
  Writes `evals/gold_set.draft.jsonl`. A human checks every answer against the page,
  then saves as `gold_set.jsonl`. Drafts are never used for scoring.
- **Persist chunks** at ingest to `data/processed/<collection>.chunks.jsonl` (needed for drafting, later BM25).
- **Evaluate** `raglab evaluate --config <cfg> [--model M] [--judge-model J] [--retrieval-only] [--limit N]`:
  - Retrieval metrics per question: hit@k (any retrieved chunk with matching doc_id and page),
    MRR, doc-hit@k. Skipped for `unanswerable`.
  - Generation metrics (LLM judge, JSON output, temperature 0): faithfulness 1-5 (claims supported
    by retrieved passages), correctness 1-5 (vs reference answer); normalised to 0-1.
    Unanswerable: correct iff the model refuses.
  - Latency p50/p95 (retrieve, generate, total), tokens, cost per query.
  - Rate limits: retry with backoff on 429.
- **Output** `results/<config>__<model>.json`: run metadata (config body, models, git commit,
  timestamp), summary metrics, and per-question rows (retrieved chunk ids/pages, answer, judge verdicts).
- **Judge** defaults to a different model family than the generator (reduces self-preference bias);
  configurable under `evaluation.judge_model`.

## Acceptance criteria
- [ ] `raglab draft-gold` writes a valid draft file with doc_id + page per question.
- [ ] `raglab evaluate --retrieval-only` runs with zero LLM calls and prints hit@k + MRR.
- [ ] Full `raglab evaluate` writes a result JSON matching the schema above.
- [ ] Unit tests (offline): metric maths, gold-set loading/validation, judge JSON parsing
      (incl. malformed output), retrieval-only path with fake embedder.
- [ ] Baseline result for `configs/default.yaml` committed in `results/` and noted in LEARNING.md.

## Evaluation criteria
N/A (this feature creates the measuring stick). Sanity: re-running the same config gives
retrieval metrics identical and judge metrics within ±0.05.

## Risks / open questions
- LLM judges are biased and noisy: spot-check ~10 verdicts by hand on first run.
- Gold-set quality caps everything: budget ~2 hours of human review.
- Page-level hit@k is strict when the answer spans pages: allow `pages` to list several.
