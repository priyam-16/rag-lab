"""Grounded answer generation with numbered citations, via LiteLLM (any provider)."""

from __future__ import annotations

from raglab.config import GenerationCfg
from raglab.models import RetrievedChunk

SYSTEM_PROMPT = """You answer questions about financial and regulatory documents.
Rules:
- Use ONLY the numbered context passages provided. Do not use outside knowledge.
- Cite every factual claim with the passage number in square brackets, e.g. [2].
- If the passages do not contain the answer, say exactly: "I can't find this in the provided documents."
- Be concise and precise. Quote figures exactly as written."""


def build_context(chunks: list[RetrievedChunk]) -> str:
    parts = []
    for i, rc in enumerate(chunks, start=1):
        c = rc.chunk
        parts.append(f"[{i}] (source: {c.title}, page {c.page})\n{c.text}")
    return "\n\n".join(parts)


class Generator:
    def __init__(self, cfg: GenerationCfg):
        self.cfg = cfg

    def generate(self, question: str, chunks: list[RetrievedChunk], model: str | None = None):
        import litellm

        model = model or self.cfg.model
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": f"Context passages:\n\n{build_context(chunks)}\n\nQuestion: {question}",
            },
        ]
        resp = litellm.completion(
            model=model,
            messages=messages,
            temperature=self.cfg.temperature,
            max_tokens=self.cfg.max_tokens,
        )
        usage = {
            "prompt_tokens": getattr(resp.usage, "prompt_tokens", 0) or 0,
            "completion_tokens": getattr(resp.usage, "completion_tokens", 0) or 0,
        }
        try:
            cost = float(litellm.completion_cost(completion_response=resp))
        except Exception:  # noqa: BLE001
            cost = None  # free-tier / unknown pricing
        return resp.choices[0].message.content, usage, cost, model
