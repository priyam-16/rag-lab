# Evaluation

Every benchmark number depends on `gold_set.jsonl`. It is drafted by an LLM and **checked by a human**.

## Sunday steps (about 45 minutes)

```bash
git pull
uv run raglab ingest                 # re-run once: it now also saves chunks for drafting
uv run poe draft-gold                # ~40 drafts -> evals/gold_set.draft.jsonl  (~$0.30 with Claude)
# review the draft (below), then save the reviewed file as evals/gold_set.jsonl
uv run poe eval-retrieval            # free: hit@k, MRR with 95% confidence intervals
uv run poe eval                      # full: + answers, judge, refusal, cost   (~$0.50-1.00)
```

## How to review each draft (the part only you can do)

Open `gold_set.draft.jsonl` in VS Code next to the PDF. For each line:

1. **Open the PDF at the listed page.** Is the answer really there?
   - Yes → keep. If the answer continues onto the next page, add it: `"pages": [141, 142]`.
   - No / wrong page → fix `pages`, or delete the line.
2. **Is the reference `answer` exactly right?** Fix figures and wording to match the document.
3. **Is the question fair?** Specific, something a banker would ask, answerable from the documents.
   Vague ones ("what does this section say?") → rewrite or delete.
4. **Unanswerable items:** confirm the documents really don't answer them (search the PDFs). If they do,
   delete the item.
5. **Type:** `factoid`, `numeric`, `table` (answer sits in a table), `multi_hop`, `cross_doc`, `unanswerable`.
   Change it if wrong — scores are reported per type.
6. Delete the `notes` text or replace it with anything useful ("answer in footnote", "ambiguous").

Aim for a balanced set: every document represented, a few table and unanswerable questions.
**Write 3–5 questions yourself** that a credit/risk professional would really ask — LLM drafts are
easier than real users. Save as `evals/gold_set.jsonl` (that file is committed; drafts are not).

`raglab evaluate` validates the file and reports any bad line by number.

## Format

```json
{"id": "q001", "question": "...", "answer": "...", "doc_id": "bis_basel3_final", "pages": [141],
 "type": "numeric", "difficulty": "easy", "notes": ""}
```
Unanswerable items: no `doc_id`, no `pages`, empty `answer`.

## What the numbers mean

| Metric | Meaning |
|---|---|
| hit@k | share of questions where a top-k chunk came from the gold document **and** a gold page |
| doc_hit@k | looser: right document, any page |
| MRR | how near the top the first correct chunk is (1st = 1, 2nd = 0.5, ...) |
| faithfulness | judge: are all claims supported by the retrieved passages (catches hallucination) |
| correctness | judge: does the answer match the reference |
| refusal_accuracy | on unanswerable questions, share where it correctly said it can't find the answer |
| false_refusal_rate | on answerable questions, share where it wrongly refused |
| `[low, high]` | 95% bootstrap confidence interval. Overlapping intervals = no proven difference |

The judge defaults to Claude Sonnet (a different family from the Groq generator). Before trusting
judge scores, spot-check ~10 verdicts in the results file against your own judgement.
