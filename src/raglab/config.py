"""Experiment config (YAML) + secrets (.env). One config file = one experiment."""

from __future__ import annotations

from pathlib import Path

import yaml
from dotenv import load_dotenv
from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(REPO_ROOT / ".env")


class Secrets(BaseSettings):
    model_config = SettingsConfigDict(env_file=REPO_ROOT / ".env", extra="ignore")

    qdrant_url: str | None = None
    qdrant_api_key: str | None = None


class CorpusCfg(BaseModel):
    raw_dir: str = "data/raw"


class ChunkingCfg(BaseModel):
    strategy: str = "fixed"
    chunk_size: int = 1200
    chunk_overlap: int = 200


class EmbeddingCfg(BaseModel):
    provider: str = "fastembed"
    model: str = "BAAI/bge-small-en-v1.5"


class VectorStoreCfg(BaseModel):
    collection: str = "raglab_baseline"
    local_path: str = "data/qdrant"


class RetrievalCfg(BaseModel):
    top_k: int = 5


class GenerationCfg(BaseModel):
    model: str = "groq/llama-3.3-70b-versatile"
    temperature: float = 0.0
    max_tokens: int = 800


class Config(BaseModel):
    name: str = "baseline"
    corpus: CorpusCfg = CorpusCfg()
    chunking: ChunkingCfg = ChunkingCfg()
    embedding: EmbeddingCfg = EmbeddingCfg()
    vector_store: VectorStoreCfg = VectorStoreCfg()
    retrieval: RetrievalCfg = RetrievalCfg()
    generation: GenerationCfg = GenerationCfg()

    def resolve(self, rel: str) -> Path:
        """Resolve a repo-relative path from the config."""
        p = Path(rel)
        return p if p.is_absolute() else REPO_ROOT / p


def load_config(path: str | Path = "configs/default.yaml") -> Config:
    p = Path(path)
    if not p.is_absolute():
        p = REPO_ROOT / p
    with open(p) as f:
        return Config.model_validate(yaml.safe_load(f) or {})
