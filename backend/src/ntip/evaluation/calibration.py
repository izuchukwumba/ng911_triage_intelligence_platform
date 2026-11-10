"""Calibration and selective-prediction metrics (design v1.2, section 3A.8).

Inputs are (score, outcome) pairs: a model's score that a cue is present and
whether it actually is. These answer "can the model know when not to guess?":

- Brier score: mean squared error of the scores (lower is better).
- Expected calibration error (ECE): how far scores are from observed
  frequencies, over 10 equal-width bins.
- Risk-coverage: answer only the most confident fraction of decisions and
  measure the error rate among them; AURC is the area under that curve.
"""

from collections.abc import Sequence
from typing import Any

Pair = tuple[float, bool]


def brier(pairs: Sequence[Pair]) -> float | None:
    if not pairs:
        return None
    return sum((p - float(y)) ** 2 for p, y in pairs) / len(pairs)


def expected_calibration_error(pairs: Sequence[Pair], bins: int = 10) -> float | None:
    if not pairs:
        return None
    total = 0.0
    for b in range(bins):
        lo, hi = b / bins, (b + 1) / bins
        members = [(p, y) for p, y in pairs if lo <= p < hi or (b == bins - 1 and p == 1.0)]
        if members:
            confidence = sum(p for p, _ in members) / len(members)
            frequency = sum(y for _, y in members) / len(members)
            total += abs(confidence - frequency) * len(members) / len(pairs)
    return total


def risk_coverage(pairs: Sequence[Pair], threshold: float = 0.5) -> dict[str, Any]:
    """Selective risk when answering only the most confident decisions."""
    if not pairs:
        return {"aurc": None, "risk_at": {}}
    decisions = sorted(
        ((max(p, 1 - p), (p >= threshold) != y) for p, y in pairs), key=lambda d: -d[0]
    )
    risks = []
    errors = 0
    for i, (_, wrong) in enumerate(decisions, 1):
        errors += wrong
        risks.append(errors / i)
    n = len(decisions)
    at = {f"{int(c * 100)}%": round(risks[max(1, round(c * n)) - 1], 4) for c in (0.5, 0.8, 1.0)}
    return {"aurc": round(sum(risks) / n, 4), "risk_at": at}


def summarise(pairs: Sequence[Pair]) -> dict[str, Any]:
    def r4(x: float | None) -> float | None:
        return None if x is None else round(x, 4)

    return {
        "pairs": len(pairs),
        "positives": sum(y for _, y in pairs),
        "brier": r4(brier(pairs)),
        "ece": r4(expected_calibration_error(pairs)),
        **risk_coverage(pairs),
    }
