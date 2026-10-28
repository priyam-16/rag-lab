---
name: add-component
description: Add a new swappable pipeline component (parser, chunker, embedder, retriever, reranker, generator) behind a config option. Use when a new technique needs code.
---

# Add a pipeline component

Components are small classes selected by a factory from the YAML config.

1. Find the stage folder in `src/raglab/` (ingest, chunking, embeddings, store, retrieval, generation).
2. Read the existing implementation and its interface first (e.g. `FixedChunker.chunk(pages)`,
   `VectorRetriever.retrieve(query, top_k)`, `Embedder.embed_documents/embed_query`). Match it exactly.
3. Add the class in its own module, e.g. `src/raglab/retrieval/bm25.py`.
4. Register it in the stage's factory (e.g. `get_chunker` in `chunking/__init__.py`) under a new
   `strategy` / `provider` string. Unknown strings must raise `ValueError`.
5. If it needs new settings, add fields with safe defaults to the matching model in `src/raglab/config.py`,
   so existing configs keep working unchanged.
6. New third-party dependency: `uv add <pkg>` (updates pyproject.toml + uv.lock).
7. Unit test in `tests/unit/test_<component>.py`: offline only (use `HashEmbedder`,
   in-memory Qdrant via `make_client(None, None, None)`, tiny `Page` fixtures).
8. `uv run poe test` must pass. Then use `add-experiment` to create the config that uses it.

Keep the component readable: the owner should understand it in one sitting.
