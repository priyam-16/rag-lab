# Evaluation

`gold_set.jsonl` holds the gold Q&A set — one JSON object per line:

```json
{"id": "q001", "question": "...", "answer": "...", "doc_id": "bis_basel3_final", "pages": [12],
 "type": "factoid", "difficulty": "easy"}
```

- `answer` — the reference answer, written from the source page.
- `doc_id` / `pages` — where the answer lives; used for retrieval recall@k.
- `type` — `factoid`, `numeric`, `multi_hop`, `cross_doc`, `table`, `unanswerable`.
  Unanswerable questions test whether the model correctly refuses.

Target: ~100 questions, balanced across documents and types. Drafted with Claude from the
actual PDFs, then reviewed by a human — every reference answer must be checked against the page.
