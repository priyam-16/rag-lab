"""Live tests against real providers. Skipped unless the needed key is set.

Run explicitly (costs a fraction of a cent):  uv run poe integration
"""

import os

import pytest

pytestmark = pytest.mark.integration


@pytest.mark.skipif(not os.getenv("OPENAI_API_KEY"), reason="OPENAI_API_KEY not set")
def test_openai_embedding_roundtrip():
    from raglab.embeddings import LiteLLMEmbedder

    emb = LiteLLMEmbedder("text-embedding-3-small")
    assert emb.dim == 1536
    assert len(emb.embed_documents(["capital adequacy", "output floor"])) == 2


@pytest.mark.skipif(not os.getenv("GROQ_API_KEY"), reason="GROQ_API_KEY not set")
def test_groq_generation_roundtrip():
    from raglab.config import GenerationCfg
    from raglab.generation.generator import Generator
    from raglab.models import Chunk, RetrievedChunk

    ctx = [RetrievedChunk(Chunk("c1", "d", "Doc", 1, "The output floor is 72.5%."), 0.9)]
    text, usage, _cost, _model = Generator(
        GenerationCfg(model="groq/openai/gpt-oss-120b", max_tokens=2000)
    ).generate("What is the output floor?", ctx)
    assert "72.5" in text
    assert usage["prompt_tokens"] > 0
