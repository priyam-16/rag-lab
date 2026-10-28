# AGENTS.md

Instructions for AI coding agents (Claude Code, Codex, Cursor, ...). Keep this file SHORT:
it is loaded on every request. Procedures live in `.claude/skills/`; folder-specific notes
live in that folder's own `CLAUDE.md`.

## What this is
RAG Lab: modular RAG over financial/regulatory PDFs. Every technique is benchmarked
(quality, latency, cost) against a fixed gold question set. Portfolio + reference template.

## Map
- `src/raglab/` core pipeline: ingest/ chunking/ embeddings/ store/ retrieval/ generation/
- `src/raglab/cli.py` the `raglab` command (download, ingest, ask, serve)
- `configs/*.yaml` one file = one experiment · `api/` FastAPI · `scripts/` thin wrappers
- `specs/` feature specs · `docs/` architecture, adr/, runbook, LEARNING.md
- `tests/unit/` offline · `tests/integration/` real APIs (marker `integration`)

## Commands (always via uv; never activate a venv)
- `uv run poe test` lint + unit tests: must pass before any commit
- `uv run poe format` auto-format
- `uv run raglab ingest --config configs/<name>.yaml` / `uv run raglab ask "..."`
- `uv run poe` list all tasks

## Hard rules
- Plain Python core. No LangChain/LlamaIndex in `src/raglab/` (LangGraph only for the agentic layer).
- Never hard-code a choice that should be benchmarked: add a config field + factory option.
- All LLM / hosted-embedding calls go through LiteLLM.
- Every answer records timings, token usage and cost.
- Unit tests stay offline (HashEmbedder + in-memory Qdrant). No network, no keys.
- Never read or print `.env`; never commit secrets, PDFs, or `data/`.
- CLI commands exit 0 on success, non-zero on failure (schedulers depend on it).

## Workflow (definition of done)
1. Feature > ~1 day: write `specs/NNN-name/spec.md` first (copy `specs/000-template/`).
2. Build in small steps; add/adjust unit tests.
3. `uv run poe test` green.
4. Significant design choice: add `docs/adr/NNNN-title.md`.
5. New benchmark result: add a row + short note to `docs/LEARNING.md`.

## Owner context
Owner is learning Next.js and LangGraph: explain non-obvious code briefly in comments.
