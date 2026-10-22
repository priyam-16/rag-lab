"""Core data types passed between pipeline stages."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Page:
    doc_id: str
    title: str
    page: int  # 1-based
    text: str


@dataclass
class Chunk:
    chunk_id: str
    doc_id: str
    title: str
    page: int
    text: str
    metadata: dict = field(default_factory=dict)


@dataclass
class RetrievedChunk:
    chunk: Chunk
    score: float


@dataclass
class Answer:
    question: str
    answer: str
    citations: list[RetrievedChunk]
    model: str
    timings_ms: dict[str, float]
    usage: dict[str, int]
    cost_usd: float | None
