# Architecture

Two flows share one config file (`configs/*.yaml`) that decides every swappable choice.
Entry point for everything: the `raglab` CLI (`src/raglab/cli.py`).

> Legend: items marked *(planned)* are on the roadmap, not built yet.

## Flow 1 — building the index (`raglab ingest`)

```mermaid
flowchart TD
    A["1. Download PDFs<br/><code>raglab download</code>"] --> R[("data/raw/*.pdf")]
    R --> B["2. Parse into pages<br/><code>ingest/parse.py</code>"]
    B --> C["3. Split into chunks<br/><code>chunking/</code>"]
    C --> D["4. Embed chunks<br/><code>embeddings/</code>"]
    D --> E["5. Store vectors<br/><code>store/qdrant_store.py</code>"]
    C --> J[("data/processed/chunks.jsonl<br/>for BM25 (planned)")]
    E --> Q[("Qdrant index<br/>data/qdrant or Qdrant Cloud")]
```

| Step | File | What happens |
|---|---|---|
| 1 | `raglab download` (`ingest/download.py`) | Reads `data/sources.yaml`, downloads public PDFs into `data/raw/`, lists any to save manually. |
| 2 | `src/raglab/ingest/parse.py` | PyMuPDF extracts text page by page; each page keeps `doc_id`, `title`, `page` for citations. |
| 3 | `src/raglab/chunking/` | Cuts pages into overlapping windows, preferring paragraph/sentence breaks. |
| 4 | `src/raglab/embeddings/` | Turns each chunk into a vector (OpenAI `text-embedding-3-small` via LiteLLM by default, or local `bge-small`). |
| 5 | `src/raglab/store/qdrant_store.py` | Writes vectors + chunk text + page into Qdrant. Duplicate PDFs are skipped by content hash. |

## Flow 2 — answering a question (`raglab ask` or `POST /ask`)

```mermaid
flowchart TD
    U1["<code>raglab ask</code><br/>terminal"] --> P
    U2["<code>api/main.py</code><br/>POST /ask"] --> P
    W["Next.js UI (planned)<br/><code>web/</code>"] --> U2
    P["RAGPipeline.ask()<br/><code>pipeline.py</code>"] --> RT
    RT{"Retriever<br/><code>retrieval/</code>"} -->|vector| V[("Qdrant")]
    RT -->|bm25 planned| K[("chunks.jsonl")]
    RT -->|hybrid planned| F["RRF fusion of both"]
    F --> RR["Reranker (planned)"]
    RT --> RR
    RR --> G["Generate cited answer<br/><code>generation/generator.py</code><br/>via LiteLLM: Groq · Claude · GPT · Ollama"]
    G --> O["Answer: text, citations,<br/>timings, tokens, cost"]
```

## Flow 3 — measuring (`raglab evaluate`, planned — spec 001)

```mermaid
flowchart LR
    GS[("evals/gold_set.jsonl")] --> EV["raglab evaluate"]
    CFG["configs/*.yaml"] --> EV
    EV --> RM["Retrieval metrics<br/>hit@k, MRR"]
    EV --> JM["LLM-judge metrics<br/>faithfulness, correctness"]
    EV --> LC["Latency + cost"]
    RM & JM & LC --> RES[("results/*.json")]
    RES --> DB["Benchmark dashboard<br/>web/ → /benchmark"]
```

## Design rules
- Core pipeline is plain Python — every stage is a small class you can read in one sitting.
- One experiment = one YAML file in `configs/`. Comparisons stay honest because only one thing changes.
- Every answer records timings, tokens and cost; the benchmark is built from those records.

## Operations
- Production run model, scheduler jobs and failure table: [`runbook.md`](runbook.md), [`../infra/jobs/README.md`](../infra/jobs/README.md)
- Why the big choices were made: [`adr/`](adr/)
