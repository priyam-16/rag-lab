# LEARNING.md

One section per stage: the concept, why we chose what we did, the numbers we got, and
interview questions with model answers. This is the interview-prep guide for the project.

## Results log
| Date | Config | hit@5 | MRR | Faithfulness | Correctness | p50 latency | Cost/query | Note |
|---|---|---|---|---|---|---|---|---|
| _pending_ | baseline | | | | | | | needs eval harness (spec 001) |

First manual run (2026-10-24, not a benchmark): Claude Sonnet answered the Basel III output-floor
question correctly with citations; retrieve 20 ms, generate 12.1 s, $0.009. Showed a duplicate PDF
was wasting 2 of 5 top-k slots (now auto-skipped at ingest).

---

## Stage 0 — Baseline RAG

**Concept.** Retrieve relevant passages first, then have the LLM answer only from them, with citations.
Ingest: parse → chunk → embed → store. Query: embed question → nearest chunks → grounded prompt → answer.

**Key ideas**
- *Chunking*: ~1,200 characters with 200 overlap, cut at paragraph/sentence breaks, per page (exact citations).
- *Embeddings*: text → vector; similar meaning → nearby vectors.
- *Cosine similarity*: `A·B / (|A||B|)`, direction only. A ranking signal, not a probability;
  not comparable across embedding models.
- *Grounded prompt*: "use only these passages, cite [n], say you can't find it otherwise".

**Interview questions**
1. *Why chunk at all? What if chunks are too big or too small?*
   Embeddings of large chunks average many topics and match poorly; tiny chunks lose context the LLM
   needs. Size is a trade-off we measure, not guess; overlap protects ideas split at a boundary.
2. *What does a 0.81 similarity score mean?*
   Only that this chunk points in a closer direction to the question than lower-scored ones. It's not a
   confidence. Whether retrieval "worked" is measured separately (hit@k against a gold set).
3. *How do you stop the model making things up?*
   Ground it: only retrieved passages in context, mandatory citations, an explicit refusal string when
   the answer is absent, temperature 0; then measure faithfulness with an evaluator rather than trusting it.

---

## Engineering — project structure (2026-10-28)

**Concept.** A project should run identically on a laptop, in CI, in Docker and under a scheduler.

**Key ideas**
- `pyproject.toml`: dependencies + tool settings + `[project.scripts]` (creates the `raglab` launcher).
- Launcher: a small file (`raglab.exe` on Windows) with the venv's Python path baked in at install time,
  so no activation is needed.
- `uv.lock`: exact versions; `uv sync --frozen` at deploy time; nothing installed at job run time.
- Exit codes 0/1 are the contract with schedulers; logs go to stdout/stderr.
- Agent setup: short AGENTS.md (always loaded), procedures in skills (loaded on demand) to keep token cost low.

**Interview questions**
1. *How would you run this pipeline in production under Control-M?*
   Build once per release (`uv sync --frozen --no-dev` from an internal mirror), then each job calls
   `/opt/raglab/.venv/bin/raglab <step> --config prod.yaml`. One job per step for restartability,
   non-concurrent ingest, secrets from the vault, failures signalled by exit code.
2. *Why not activate the environment inside the script?*
   Activation only changes a shell's PATH; by the time Python runs, the interpreter is already chosen.
   Calling the env's launcher/interpreter by absolute path is deterministic.
3. *How do you keep AI coding agents cheap and consistent across a team?*
   Short always-loaded instructions, on-demand skills for procedures, folder-scoped notes,
   deny-lists for data/lockfiles, cheaper models for exploratory subagents, and the same files
   committed so every engineer's agent behaves the same.
