# RAG Lab — notes for Claude

Portfolio project: modular RAG over financial/regulatory PDFs with benchmarked techniques.

## Conventions
- Core pipeline is plain Python under `src/raglab/` — no LangChain/LlamaIndex backbone.
  LangGraph only for the agentic-RAG layer.
- Every technique is a swappable component selected by YAML config in `configs/`.
  One experiment = one config file. Never hard-code a choice that should be benchmarked.
- All LLM and hosted-embedding calls go through LiteLLM so providers are one string apart.
- Record timings, token usage and cost for every answer — the benchmark depends on it.
- `tests/` must run offline (hash embedder + in-memory Qdrant). Keep them green.
- Secrets live only in `.env` (gitignored). PDFs in `data/raw/` are never committed.
- Owner is learning Next.js: explain frontend code clearly when writing it.
