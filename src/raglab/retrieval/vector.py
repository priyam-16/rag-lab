"""Baseline retriever: dense vector search only.
Next arms: BM25, hybrid (RRF fusion), reranker, query rewriting, HyDE."""

from __future__ import annotations

from raglab.embeddings import Embedder
from raglab.models import RetrievedChunk
from raglab.store.qdrant_store import QdrantStore


class VectorRetriever:
    def __init__(self, embedder: Embedder, store: QdrantStore):
        self.embedder = embedder
        self.store = store

    def retrieve(self, query: str, top_k: int) -> list[RetrievedChunk]:
        return self.store.search(self.embedder.embed_query(query), top_k)
