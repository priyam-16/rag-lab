"""Qdrant vector store. Local on-disk mode by default; Qdrant Cloud when QDRANT_URL is set."""

from __future__ import annotations

import uuid
from pathlib import Path

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams

from raglab.models import Chunk, RetrievedChunk


def make_client(url: str | None, api_key: str | None, local_path: Path | None) -> QdrantClient:
    if url:
        return QdrantClient(url=url, api_key=api_key)
    if local_path is None:
        return QdrantClient(location=":memory:")
    local_path.mkdir(parents=True, exist_ok=True)
    return QdrantClient(path=str(local_path))


class QdrantStore:
    def __init__(self, client: QdrantClient, collection: str):
        self.client = client
        self.collection = collection

    def recreate(self, dim: int) -> None:
        if self.client.collection_exists(self.collection):
            self.client.delete_collection(self.collection)
        self.client.create_collection(
            self.collection, vectors_config=VectorParams(size=dim, distance=Distance.COSINE)
        )

    def upsert(self, chunks: list[Chunk], vectors: list[list[float]], batch: int = 256) -> None:
        points = [
            PointStruct(
                id=str(uuid.uuid5(uuid.NAMESPACE_URL, c.chunk_id)),
                vector=v,
                payload={
                    "chunk_id": c.chunk_id,
                    "doc_id": c.doc_id,
                    "title": c.title,
                    "page": c.page,
                    "text": c.text,
                    **c.metadata,
                },
            )
            for c, v in zip(chunks, vectors, strict=True)
        ]
        for i in range(0, len(points), batch):
            self.client.upsert(self.collection, points=points[i : i + batch])

    def search(self, vector: list[float], top_k: int) -> list[RetrievedChunk]:
        res = self.client.query_points(
            self.collection, query=vector, limit=top_k, with_payload=True
        )
        out = []
        for p in res.points:
            pl = dict(p.payload)
            chunk = Chunk(
                chunk_id=pl.pop("chunk_id"),
                doc_id=pl.pop("doc_id"),
                title=pl.pop("title"),
                page=pl.pop("page"),
                text=pl.pop("text"),
                metadata=pl,
            )
            out.append(RetrievedChunk(chunk=chunk, score=p.score))
        return out

    def count(self) -> int:
        return self.client.count(self.collection).count

    def close(self) -> None:
        """Release the connection / local file lock explicitly (avoids noisy __del__ at exit)."""
        self.client.close()
