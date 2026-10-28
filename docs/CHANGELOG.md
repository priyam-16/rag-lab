# Changelog

## 0.2.0
- Project restructure: uv + lockfile, `raglab` CLI (download/ingest/ask/serve) with scheduler-friendly
  exit codes, poe tasks, pre-commit hooks, offline CI, unit/integration test split.
- Agent setup: AGENTS.md, skills, subagents, specs workflow.
- Ingest: skips duplicate PDFs (content hash), reports text-less PDFs, logs progress per stage.
- Ops: Dockerfile, docker-compose (Qdrant + API), prod config template, scheduler job guide, runbook, ADRs.
- Default models: OpenAI `text-embedding-3-small` embeddings; Groq `openai/gpt-oss-120b` answers.

## 0.1.0
- Baseline pipeline: PyMuPDF parsing, fixed chunking, embeddings, Qdrant, cited generation via LiteLLM, FastAPI.
