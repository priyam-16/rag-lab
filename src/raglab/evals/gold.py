"""Gold question set: schema + loader with validation.

One JSON object per line in evals/gold_set.jsonl:
  {"id": "q001", "question": "...", "answer": "...", "doc_id": "bis_basel3_final",
   "pages": [141], "type": "numeric", "difficulty": "easy"}

`unanswerable` items have no doc_id/pages: the correct behaviour is to refuse.
"""

from __future__ import annotations

import json
from collections import Counter
from enum import StrEnum
from pathlib import Path

from pydantic import BaseModel, Field, ValidationError, model_validator


class QType(StrEnum):
    factoid = "factoid"
    numeric = "numeric"
    table = "table"
    multi_hop = "multi_hop"
    cross_doc = "cross_doc"
    unanswerable = "unanswerable"


class GoldItem(BaseModel):
    id: str
    question: str = Field(min_length=5)
    answer: str = ""  # reference answer; empty for unanswerable
    doc_id: str | None = None
    pages: list[int] = Field(default_factory=list)
    type: QType = QType.factoid
    difficulty: str = "medium"
    notes: str = ""

    @model_validator(mode="after")
    def _check_location(self) -> GoldItem:
        if self.type == QType.unanswerable:
            if self.doc_id or self.pages:
                raise ValueError("unanswerable items must not have doc_id/pages")
        else:
            if not self.doc_id or not self.pages:
                raise ValueError("answerable items need doc_id and at least one page")
            if not self.answer.strip():
                raise ValueError("answerable items need a reference answer")
        return self

    @property
    def answerable(self) -> bool:
        return self.type != QType.unanswerable


def load_gold(path: Path) -> list[GoldItem]:
    """Load and validate. Errors name the line number so a reviewer can fix the file."""
    if not path.exists():
        raise FileNotFoundError(
            f"{path} not found. Draft one with `raglab draft-gold`, review it, "
            "then save the reviewed file under this name."
        )
    items, errors, seen = [], [], set()
    for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip() or line.lstrip().startswith("//"):
            continue
        try:
            item = GoldItem.model_validate(json.loads(line))
        except (json.JSONDecodeError, ValidationError) as e:
            errors.append(f"line {n}: {e}")
            continue
        if item.id in seen:
            errors.append(f"line {n}: duplicate id {item.id}")
            continue
        seen.add(item.id)
        items.append(item)
    if errors:
        raise ValueError(f"{len(errors)} invalid gold item(s) in {path}:\n" + "\n".join(errors))
    if not items:
        raise ValueError(f"{path} contains no gold items")
    return items


def describe(items: list[GoldItem]) -> dict:
    """Mix of question types and documents — check the set is balanced before trusting scores."""
    return {
        "n": len(items),
        "by_type": dict(Counter(i.type.value for i in items)),
        "by_doc": dict(Counter(i.doc_id or "(none)" for i in items)),
    }
