# RAG Lab

A modular Retrieval-Augmented Generation system for financial and regulatory documents
(Basel III, MAS notices and guidelines, bank annual reports), built to **measure** what each
RAG technique actually buys you — in answer quality, latency and cost — across Claude, GPT
and open-source models.

> Status: **v0.1 — baseline pipeline.** Evaluation harness, hybrid retrieval, reranking,
> model comparison, dashboard and deployment are next (see Roadmap).

## Why this project

Most RAG demos show that retrieval *works*. This one shows *how much each choice matters*:
every technique is a config change benchmarked against the same gold question set.

## Architecture (v0.1)

```
PDFs ──► parse (PyMuPDF) ──► chunk (fixed, per page) ──► embed (bge-small, local)
                                                              │
                                                              ▼
question ──► embed ──► Qdrant vector search (top-k) ──► LLM via LiteLLM ──► answer + [n] citations
                                                     (Groq / Claude / GPT / Ollama)
```

| Layer | Baseline choice | Swappable via |
|---|---|---|
| Parsing | PyMuPDF text | `src/raglab/ingest/` |
| Chunking | fixed 1200 chars, 200 overlap | `configs/*.yaml` → `chunking` |
| Embeddings | `BAAI/bge-small-en-v1.5` (local, free) | `embedding.provider/model` |
| Vector store | Qdrant (local disk or Qdrant Cloud) | `.env` → `QDRANT_URL` |
| Generation | Llama 3.3 70B on Groq | `generation.model` or `--model` |

## Quickstart

Needs [uv](https://docs.astral.sh/uv/) (`pip install uv`). No venv activation needed — `uv run` uses the project's `.venv` automatically.

```bash
git clone https://github.com/priyam-16/rag-lab && cd rag-lab
uv run poe setup                 # creates .venv, installs exact versions (uv.lock), git hooks
cp .env.example .env             # add OPENAI_API_KEY (embeddings) + GROQ_API_KEY (answers)

uv run raglab download           # fetch public PDFs; lists any to save manually
uv run raglab ingest             # parse -> chunk -> embed -> index
uv run raglab ask "What is the output floor under the Basel III reforms?"
uv run raglab serve --reload     # API at http://localhost:8000/docs

uv run poe test                  # lint + offline unit tests (no keys needed)
uv run poe                       # list every task
```

The old `python scripts/*.py` entry points still work (they call the same CLI).
**Bring your own documents:** drop PDFs into `data/raw/` and re-run `raglab ingest`.

## Repository guide

| Path | What's there |
|---|---|
| `src/raglab/` | Pipeline code; `cli.py` is the `raglab` command |
| `configs/` | One YAML per experiment (`prod.example.yaml` for servers) |
| `docs/` | [architecture](docs/architecture.md), [ADRs](docs/adr/), [runbook](docs/runbook.md), [LEARNING](docs/LEARNING.md) |
| `specs/` | Feature specs, written before building |
| `infra/` | Dockerfile, docker-compose (Qdrant + API), scheduler job guide |
| `AGENTS.md`, `.claude/` | Instructions, skills and subagents for AI coding agents |
| `tests/unit`, `tests/integration` | Offline tests (CI) / live API tests (manual) |

## Roadmap

- [x] Baseline: parse, chunk, embed, vector search, cited answers, CLI + API
- [ ] Gold Q&A set (~100 questions) + eval harness (faithfulness, relevance, recall@k, LLM judge)
- [ ] Hybrid retrieval (BM25 + vector, RRF) and rerankers (local bge vs hosted)
- [ ] Chunking arms: recursive, semantic, parent-child, contextual retrieval
- [ ] Query transforms: rewriting, multi-query, HyDE
- [ ] Agentic RAG (LangGraph): routing, corrective retrieval, self-check
- [ ] Model benchmark: Claude, GPT, Llama/Qwen (Groq), local (Ollama) — quality × latency × cost
- [ ] Semantic cache, streaming, prompt caching
- [ ] Next.js UI + benchmark dashboard (Vercel), FastAPI backend (Render), Langfuse tracing

## Results

_Benchmark table lands here once the eval harness is in._
