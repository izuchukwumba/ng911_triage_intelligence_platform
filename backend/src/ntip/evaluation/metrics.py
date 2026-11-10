"""Metrics with uncertainty (design v1.2, sections 3A.8 and 10.5).

Small, dependency-free implementations: counts, rates with percentile
bootstrap confidence intervals, and confusion matrices. Every rate is
reported with its numerator and denominator.
"""

import random
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Any

BOOTSTRAP_RESAMPLES = 2000


@dataclass(frozen=True)
class Rate:
    numerator: int
    denominator: int
    ci_low: float | None
    ci_high: float | None

    @property
    def value(self) -> float | None:
        return self.numerator / self.denominator if self.denominator else None

    def as_dict(self) -> dict[str, Any]:
        return {
            "value": None if self.value is None else round(self.value, 4),
            "numerator": self.numerator,
            "denominator": self.denominator,
            "ci95": None
            if self.ci_low is None
            else [round(self.ci_low, 4), round(self.ci_high or 0, 4)],
        }


def rate(outcomes: Sequence[bool], *, seed: int) -> Rate:
    """Share of True outcomes, with a 95% percentile bootstrap interval."""
    n = len(outcomes)
    k = sum(outcomes)
    if n == 0:
        return Rate(0, 0, None, None)
    rng = random.Random(seed)
    samples = sorted(sum(rng.choices(outcomes, k=n)) / n for _ in range(BOOTSTRAP_RESAMPLES))
    return Rate(
        k,
        n,
        samples[int(0.025 * BOOTSTRAP_RESAMPLES)],
        samples[int(0.975 * BOOTSTRAP_RESAMPLES) - 1],
    )


@dataclass(frozen=True)
class PRF:
    tp: int
    fp: int
    fn: int

    @property
    def precision(self) -> float | None:
        return self.tp / (self.tp + self.fp) if self.tp + self.fp else None

    @property
    def recall(self) -> float | None:
        return self.tp / (self.tp + self.fn) if self.tp + self.fn else None

    @property
    def f1(self) -> float | None:
        p, r = self.precision, self.recall
        return (
            2 * p * r / (p + r) if p and r else (0.0 if p is not None and r is not None else None)
        )

    def as_dict(self) -> dict[str, float | int | None]:
        def r4(x: float | None) -> float | None:
            return None if x is None else round(x, 4)

        return {"tp": self.tp, "fp": self.fp, "fn": self.fn, "precision": r4(self.precision),
                "recall": r4(self.recall), "f1": r4(self.f1)}  # fmt: skip


def confusion(pairs: Sequence[tuple[str, str]], labels: Sequence[str]) -> dict[str, dict[str, int]]:
    """matrix[expected][predicted] = count."""
    matrix = {e: dict.fromkeys(labels, 0) for e in labels}
    for expected, predicted in pairs:
        matrix.setdefault(expected, dict.fromkeys(labels, 0))
        matrix[expected][predicted] = matrix[expected].get(predicted, 0) + 1
    return matrix


def bootstrap_metric(
    items: Sequence[object], metric: Callable[[Sequence[object]], float | None], *, seed: int
) -> tuple[float | None, float | None]:
    """95% percentile interval for an arbitrary metric over resampled items."""
    if not items:
        return None, None
    rng = random.Random(seed)
    values = sorted(
        v
        for v in (metric(rng.choices(items, k=len(items))) for _ in range(BOOTSTRAP_RESAMPLES))
        if v is not None
    )
    if not values:
        return None, None
    return values[int(0.025 * len(values))], values[int(0.975 * len(values)) - 1]
