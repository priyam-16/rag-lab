"""Draft gold questions from your own indexed chunks, for HUMAN REVIEW.

The LLM writes one question + reference answer per sampled chunk (so doc_id and page are
known), plus a few unanswerable questions. Output goes to evals/gold_set.draft.jsonl and is
NEVER used for scoring: a domain expert checks every item against the PDF page, fixes or deletes
it, and saves the result as evals/gold_set.jsonl.
"""

from __future__ import annotations

import json
import logging
import random
import re
from collections import defaultdict
from pathlib import Path

from raglab.config import Config
from raglab.models import Chunk

log = logging.getLogger(__name__)

ANSWERABLE_PROMPT = """You are building an evaluation set for a question-answering system over
financial and regulatory documents. Read the passage and write ONE question that:
- a banking professional might genuinely ask,
- can be answered fully and only from this passage,
- is specific (include the concept, figure or rule it asks about), not "what does this passage say".

Document: {title} (page {page})
Passage:
\"\"\"{text}\"\"\"

Return ONLY JSON:
{{"question": "...", "answer": "<short reference answer quoting key figures exactly>",
  "type": "<factoid|numeric|table>", "difficulty": "<easy|medium|hard>"}}"""

UNANSWERABLE_PROMPT = """You are building an evaluation set for a question-answering system whose
documents are: {titles}.
Write ONE realistic question a banking professional might ask that these documents almost
certainly do NOT answer (e.g. about a different regulator, a later year, or a detail they omit).
It should sound plausible, so a weak system might be tempted to guess.

Return ONLY JSON: {{"question": "..."}}"""


def _parse_json(raw: str) -> dict | None:
    m = re.search(r"\{.*\}", raw or "", flags=re.DOTALL)
    if not m:
        return None
    try:
        return json.loads(m.group(0))
    except json.JSONDecodeError:
        return None


def sample_chunks(chunks: list[Chunk], n: int, seed: int = 0, min_chars: int = 300) -> list[Chunk]:
    """Round-robin across documents so every document is represented, random within each."""
    rng = random.Random(seed)
    by_doc: dict[str, list[Chunk]] = defaultdict(list)
    for c in chunks:
        if len(c.text) >= min_chars:
            by_doc[c.doc_id].append(c)
    for pool in by_doc.values():
        rng.shuffle(pool)
    picked, docs = [], sorted(by_doc)
    while len(picked) < n and any(by_doc.values()):
        for d in docs:
            if by_doc[d] and len(picked) < n:
                picked.append(by_doc[d].pop())
    return picked


def draft_gold(
    cfg: Config,
    chunks: list[Chunk],
    n: int = 40,
    unanswerable_frac: float = 0.1,
    model: str | None = None,
    seed: int = 0,
    completion_fn=None,
) -> list[dict]:
    import litellm

    from raglab.evals.runner import with_retries

    complete = completion_fn or litellm.completion
    model = model or cfg.evaluation.judge_model
    n_unans = max(1, round(n * unanswerable_frac)) if unanswerable_frac > 0 else 0
    picked = sample_chunks(chunks, n - n_unans, seed)

    def ask(prompt: str) -> dict | None:
        resp = with_retries(
            lambda: complete(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=500,
            ),
            cfg.evaluation.max_retries,
        )
        return _parse_json(resp.choices[0].message.content or "")

    drafts: list[dict] = []
    for c in picked:
        data = ask(ANSWERABLE_PROMPT.format(title=c.title, page=c.page, text=c.text[:3000]))
        if not data or not data.get("question"):
            log.warning("skipped chunk %s: no usable draft", c.chunk_id)
            continue
        qtype = (
            data.get("type") if data.get("type") in ("factoid", "numeric", "table") else "factoid"
        )
        drafts.append(
            {
                "id": f"d{len(drafts) + 1:03d}",
                "question": str(data["question"]).strip(),
                "answer": str(data.get("answer", "")).strip(),
                "doc_id": c.doc_id,
                "pages": [c.page],
                "type": qtype,
                "difficulty": data.get("difficulty", "medium"),
                "notes": f"DRAFT from {c.chunk_id} - check answer against the PDF page; "
                "add pages if the answer spans several",
            }
        )

    titles = ", ".join(sorted({c.title for c in chunks}))
    for _ in range(n_unans):
        data = ask(UNANSWERABLE_PROMPT.format(titles=titles))
        if data and data.get("question"):
            drafts.append(
                {
                    "id": f"d{len(drafts) + 1:03d}",
                    "question": str(data["question"]).strip(),
                    "answer": "",
                    "type": "unanswerable",
                    "difficulty": "medium",
                    "notes": "DRAFT - VERIFY the documents really do not answer this",
                }
            )
    return drafts


def write_drafts(drafts: list[dict], path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for d in drafts:
            f.write(json.dumps(d, ensure_ascii=False) + "\n")
    return path
