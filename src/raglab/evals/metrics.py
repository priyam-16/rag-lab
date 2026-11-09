"""Retrieval metrics + bootstrap confidence intervals.

hit@k        did any of the top-k chunks come from the gold document AND a gold page?
doc_hit@k    looser: any top-k chunk from the gold document (any page)
reciprocal rank   1/rank of the first correct chunk (1st = 1, 2nd = 0.5, ...), 0 if absent; MRR = mean

Confidence intervals: resample the per-question scores with replacement many times and take the
2.5th / 97.5th percentiles of the mean. With ~100 questions, differences of a few points are noise.
"""

from __future__ import annotations

import random
from dataclasses import dataclass

from raglab.models import RetrievedChunk


def _is_correct(rc: RetrievedChunk, doc_id: str, pages: list[int]) -> bool:
    return rc.chunk.doc_id == doc_id and rc.chunk.page in pages


def hit_at_k(retrieved: list[RetrievedChunk], doc_id: str, pages: list[int]) -> float:
    return 1.0 if any(_is_correct(rc, doc_id, pages) for rc in retrieved) else 0.0


def doc_hit_at_k(retrieved: list[RetrievedChunk], doc_id: str) -> float:
    return 1.0 if any(rc.chunk.doc_id == doc_id for rc in retrieved) else 0.0


def reciprocal_rank(retrieved: list[RetrievedChunk], doc_id: str, pages: list[int]) -> float:
    for rank, rc in enumerate(retrieved, start=1):
        if _is_correct(rc, doc_id, pages):
            return 1.0 / rank
    return 0.0


def percentile(values: list[float], q: float) -> float:
    """Linear-interpolated percentile, q in [0, 100]."""
    if not values:
        raise ValueError("percentile of empty list")
    s = sorted(values)
    pos = (len(s) - 1) * q / 100
    lo, hi = int(pos), min(int(pos) + 1, len(s) - 1)
    return s[lo] + (s[hi] - s[lo]) * (pos - lo)


@dataclass
class Estimate:
    mean: float
    ci_low: float
    ci_high: float
    n: int

    def __str__(self) -> str:
        return f"{self.mean:.3f} [{self.ci_low:.3f}, {self.ci_high:.3f}] (n={self.n})"

    def as_dict(self) -> dict:
        return {
            "mean": round(self.mean, 4),
            "ci_low": round(self.ci_low, 4),
            "ci_high": round(self.ci_high, 4),
            "n": self.n,
        }


def bootstrap_ci(
    values: list[float], n_resamples: int = 1000, alpha: float = 0.05, seed: int = 0
) -> Estimate:
    """Mean with a (1 - alpha) bootstrap percentile interval. Seeded, so reruns are identical."""
    if not values:
        raise ValueError("no values to estimate")
    n = len(values)
    mean = sum(values) / n
    if n == 1 or n_resamples < 1:
        return Estimate(mean, mean, mean, n)
    rng = random.Random(seed)
    means = [sum(rng.choices(values, k=n)) / n for _ in range(n_resamples)]
    return Estimate(
        mean, percentile(means, 100 * alpha / 2), percentile(means, 100 * (1 - alpha / 2)), n
    )
