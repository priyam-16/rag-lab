"""LLM-as-judge for answer quality, plus a deterministic refusal check.

The judge scores 1-5 (normalised to 0-1):
  faithfulness  every claim in the answer is supported by the retrieved passages
  correctness   the answer matches the reference answer
Judges are biased and noisy: check them against human labels before trusting them
(judge calibration, planned), and keep temperature 0.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass

from raglab.generation.generator import build_context
from raglab.models import RetrievedChunk

# Only the exact refusal sentence the generator is instructed to use (generator.SYSTEM_PROMPT),
# plus close variants. Broad phrases like "does not contain" would misclassify partial answers.
REFUSAL_MARKERS = (
    "can't find this in the provided documents",
    "cannot find this in the provided documents",
    "can not find this in the provided documents",
    "couldn't find this in the provided documents",
    "could not find this in the provided documents",
)

JUDGE_PROMPT = """You are grading an answer produced by a document question-answering system.

Question:
{question}

Reference answer (written by a domain expert):
{reference}

Retrieved passages the system was given:
{context}

System answer:
{answer}

Score two things from 1 (worst) to 5 (best):
- faithfulness: are ALL claims in the system answer supported by the retrieved passages?
  (5 = every claim supported; 1 = mostly unsupported or invented)
- correctness: does the system answer agree with the reference answer on the key facts?
  (5 = same key facts; 3 = partly; 1 = wrong or missing)

Return ONLY a JSON object, no other text:
{{"faithfulness": <1-5>, "correctness": <1-5>, "reason": "<one short sentence>"}}"""


@dataclass
class Verdict:
    faithfulness: float | None  # 0-1, None if the judge output was unusable
    correctness: float | None
    reason: str
    raw: str


def is_refusal(answer: str) -> bool:
    a = (answer or "").lower().replace("\u2019", "'")  # curly apostrophe -> straight
    return any(m in a for m in REFUSAL_MARKERS)


def _norm(score) -> float | None:
    if isinstance(score, bool):  # bool is an int subclass; "true" is not a score
        return None
    try:
        s = float(score)
    except (TypeError, ValueError):
        return None
    if not 1 <= s <= 5:
        return None
    return (s - 1) / 4  # 1 -> 0.0, 5 -> 1.0


def parse_verdict(raw: str) -> Verdict:
    """Robust to judges that wrap JSON in prose or code fences, or return garbage."""
    match = re.search(r"\{.*\}", raw or "", flags=re.DOTALL)
    if not match:
        return Verdict(None, None, "unparseable judge output", raw)
    try:
        data = json.loads(match.group(0))
    except json.JSONDecodeError:
        return Verdict(None, None, "invalid JSON from judge", raw)
    return Verdict(
        _norm(data.get("faithfulness")),
        _norm(data.get("correctness")),
        str(data.get("reason", ""))[:300],
        raw,
    )


def judge_answer(
    question: str,
    reference: str,
    answer: str,
    contexts: list[RetrievedChunk],
    model: str,
    max_tokens: int = 600,
    completion_fn=None,
) -> tuple[Verdict, dict, float | None]:
    """Returns (verdict, usage, cost). `completion_fn` lets tests inject a fake LLM."""
    import litellm

    complete = completion_fn or litellm.completion
    prompt = JUDGE_PROMPT.format(
        question=question,
        reference=reference,
        context=build_context(contexts),
        answer=answer,
    )
    resp = complete(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.0,
        max_tokens=max_tokens,
    )
    raw = resp.choices[0].message.content or ""
    usage = {
        "prompt_tokens": getattr(resp.usage, "prompt_tokens", 0) or 0,
        "completion_tokens": getattr(resp.usage, "completion_tokens", 0) or 0,
    }
    try:
        cost = float(litellm.completion_cost(completion_response=resp))
    except Exception:  # noqa: BLE001 - unknown/free pricing
        cost = None
    return parse_verdict(raw), usage, cost
