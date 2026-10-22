from raglab.chunking.fixed import FixedChunker
from raglab.config import ChunkingCfg


def get_chunker(cfg: ChunkingCfg):
    if cfg.strategy == "fixed":
        return FixedChunker(cfg.chunk_size, cfg.chunk_overlap)
    raise ValueError(f"Unknown chunking strategy: {cfg.strategy}")
