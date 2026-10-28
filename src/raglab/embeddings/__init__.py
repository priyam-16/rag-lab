"""Embedding providers behind one interface: embed_documents / embed_query / dim."""

from __future__ import annotations

import hashlib
import logging
import math
from typing import Protocol

from raglab.config import EmbeddingCfg

log = logging.getLogger(__name__)


class Embedder(Protocol):
    dim: int

    def embed_documents(self, texts: list[str]) -> list[list[float]]: ...
    def embed_query(self, text: str) -> list[float]: ...


class FastEmbedEmbedder:
    """Local ONNX embeddings (no torch, no API key). Downloads the model once."""

    def __init__(self, model: str):
        from fastembed import TextEmbedding

        self._m = TextEmbedding(model_name=model)
        self.dim = len(next(iter(self._m.embed(["probe"]))))

    def embed_documents(self, texts):
        return [v.tolist() for v in self._m.embed(texts, batch_size=64)]

    def embed_query(self, text):
        return next(iter(self._m.query_embed(text))).tolist()


class LiteLLMEmbedder:
    """Hosted embeddings via LiteLLM (e.g. text-embedding-3-small)."""

    def __init__(self, model: str):
        self.model = model
        self.dim = len(self.embed_query("probe"))

    def embed_documents(self, texts):
        import litellm

        out = []
        for i in range(0, len(texts), 128):
            resp = litellm.embedding(model=self.model, input=texts[i : i + 128])
            out.extend(d["embedding"] for d in resp.data)
            if len(texts) > 128:
                log.info("      embedded %d/%d", len(out), len(texts))
        return out

    def embed_query(self, text):
        return self.embed_documents([text])[0]


class HashEmbedder:
    """Deterministic bag-of-words hashing embedder. For tests/offline only — not semantic."""

    def __init__(self, dim: int = 256):
        self.dim = dim

    def _vec(self, text: str) -> list[float]:
        v = [0.0] * self.dim
        for tok in text.lower().split():
            h = int(hashlib.md5(tok.encode()).hexdigest(), 16)
            v[h % self.dim] += 1.0
        n = math.sqrt(sum(x * x for x in v)) or 1.0
        return [x / n for x in v]

    def embed_documents(self, texts):
        return [self._vec(t) for t in texts]

    def embed_query(self, text):
        return self._vec(text)


def get_embedder(cfg: EmbeddingCfg) -> Embedder:
    if cfg.provider == "fastembed":
        return FastEmbedEmbedder(cfg.model)
    if cfg.provider == "litellm":
        return LiteLLMEmbedder(cfg.model)
    if cfg.provider == "hash":
        return HashEmbedder()
    raise ValueError(f"Unknown embedding provider: {cfg.provider}")
