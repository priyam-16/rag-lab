"""Wires the stages together. Ingestion and query paths both live here."""

from __future__ import annotations

import logging
import time

from raglab.chunking import get_chunker
from raglab.config import REPO_ROOT, Config, Secrets
from raglab.embeddings import get_embedder
from raglab.generation.generator import Generator
from raglab.ingest.parse import load_corpus
from raglab.models import Answer
from raglab.retrieval.vector import VectorRetriever
from raglab.store.qdrant_store import QdrantStore, make_client

log = logging.getLogger(__name__)


def _store(cfg: Config) -> QdrantStore:
    s = Secrets()
    client = make_client(s.qdrant_url, s.qdrant_api_key, cfg.resolve(cfg.vector_store.local_path))
    return QdrantStore(client, cfg.vector_store.collection)


def ingest(cfg: Config) -> dict:
    t0 = time.perf_counter()
    log.info("[1/4] parsing PDFs in %s", cfg.corpus.raw_dir)
    pages = load_corpus(cfg.resolve(cfg.corpus.raw_dir), REPO_ROOT / "data" / "sources.yaml")
    if not pages:
        raise FileNotFoundError(f"No usable PDFs in {cfg.corpus.raw_dir}. Run: raglab download")

    log.info("[2/4] chunking %d pages (%s)", len(pages), cfg.chunking.strategy)
    chunks = get_chunker(cfg.chunking).chunk(pages)

    log.info("[3/4] embedding %d chunks with %s", len(chunks), cfg.embedding.model)
    t1 = time.perf_counter()
    embedder = get_embedder(cfg.embedding)
    vectors = embedder.embed_documents([c.text for c in chunks])
    log.info("      embedded in %.1fs", time.perf_counter() - t1)

    log.info("[4/4] writing to Qdrant collection '%s'", cfg.vector_store.collection)
    store = _store(cfg)
    try:
        store.recreate(embedder.dim)
        store.upsert(chunks, vectors)
    finally:
        store.close()
    return {
        "documents": len({p.doc_id for p in pages}),
        "pages": len(pages),
        "chunks": len(chunks),
        "seconds": round(time.perf_counter() - t0, 1),
    }


class RAGPipeline:
    def __init__(self, cfg: Config):
        self.cfg = cfg
        self.store = _store(cfg)
        self.retriever = VectorRetriever(get_embedder(cfg.embedding), self.store)
        self.generator = Generator(cfg.generation)

    def close(self) -> None:
        self.store.close()

    def ask(self, question: str, top_k: int | None = None, model: str | None = None) -> Answer:
        t0 = time.perf_counter()
        chunks = self.retriever.retrieve(question, top_k or self.cfg.retrieval.top_k)
        t1 = time.perf_counter()
        text, usage, cost, used_model = self.generator.generate(question, chunks, model)
        t2 = time.perf_counter()
        return Answer(
            question=question,
            answer=text,
            citations=chunks,
            model=used_model,
            timings_ms={
                "retrieve": round((t1 - t0) * 1000, 1),
                "generate": round((t2 - t1) * 1000, 1),
                "total": round((t2 - t0) * 1000, 1),
            },
            usage=usage,
            cost_usd=cost,
        )
