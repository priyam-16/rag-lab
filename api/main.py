"""FastAPI service. Run:  uvicorn api.main:app --reload
Docs at http://localhost:8000/docs"""

from __future__ import annotations

import os
from functools import lru_cache

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from raglab.config import load_config
from raglab.pipeline import RAGPipeline

app = FastAPI(title="RAG Lab API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "http://localhost:3000").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)


@lru_cache
def pipeline() -> RAGPipeline:
    return RAGPipeline(load_config(os.getenv("RAGLAB_CONFIG", "configs/default.yaml")))


class AskRequest(BaseModel):
    question: str = Field(min_length=3, max_length=1000)
    top_k: int | None = Field(default=None, ge=1, le=20)
    model: str | None = None


class Citation(BaseModel):
    n: int
    doc_id: str
    title: str
    page: int
    score: float
    text: str


class AskResponse(BaseModel):
    answer: str
    citations: list[Citation]
    model: str
    timings_ms: dict[str, float]
    usage: dict[str, int]
    cost_usd: float | None


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/ask", response_model=AskResponse)
def ask(req: AskRequest):
    try:
        a = pipeline().ask(req.question, req.top_k, req.model)
    except Exception as e:  # surface provider/config errors clearly
        raise HTTPException(status_code=502, detail=f"{type(e).__name__}: {e}") from e
    return AskResponse(
        answer=a.answer,
        citations=[
            Citation(
                n=i,
                doc_id=rc.chunk.doc_id,
                title=rc.chunk.title,
                page=rc.chunk.page,
                score=rc.score,
                text=rc.chunk.text,
            )
            for i, rc in enumerate(a.citations, start=1)
        ],
        model=a.model,
        timings_ms=a.timings_ms,
        usage=a.usage,
        cost_usd=a.cost_usd,
    )
