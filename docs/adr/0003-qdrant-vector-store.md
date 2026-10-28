# 0003 — Qdrant as the vector store

- Status: accepted
- Date: 2026-10-22

## Context
Need vector search with stored payload (text, doc, page), metadata filters, a free hosted
option for deployment, and something runnable fully offline for tests.

## Options considered
1. FAISS — fast library; no payload storage/filters/server; we'd build the rest.
2. pgvector — great if Postgres already exists; more setup for this project.
3. Pinecone — managed only; no local/offline mode.
4. Qdrant — in-memory (tests), local folder (dev), server/Docker/Cloud (prod) with the same client code.

## Decision
Qdrant, behind our own `QdrantStore` class (the only module that imports `qdrant_client`).

## Consequences
+ Same code in tests, laptop and prod; free cloud tier for the demo.
− Local folder mode is single-process and slow for bulk writes: dev only, never prod.
+ Swapping vendors means rewriting one file.
