"""Paired comparisons between two systems on the same cases (ML layer design 8.3).

Two systems run on the same cases are compared case by case, not as two
independent samples:

- **McNemar's exact test** for a yes/no outcome per case (a critical call
  given P0, a priority exactly right). Only the discordant cases count: those
  where one system is right and the other is not. The two-sided p-value is
  the exact binomial probability of a split at least that uneven, with
  p = 0.5.
- **Paired bootstrap intervals** for the difference in a rate or in micro
  F1. Cases are resampled with replacement, the *same* resample for both
  systems, and the difference is recomputed each time; the 95% interval is
  the 2.5th and 97.5th percentiles.

Both work on per-case counts (``CaseCounts``). Every statistic is a function
of the counts' totals, so each bootstrap resample only sums numbers and
stays fast on thousands of cases.
"""

import math
import random
from collections.abc import Callable, Sequence
from dataclasses import astuple, dataclass, fields
from typing import Any

from ntip.evaluation.metrics import BOOTSTRAP_RESAMPLES


@dataclass(frozen=True)
class CaseCounts:
    """What one system got right or wrong on one case."""

    tp: int  # cues found and labelled
    fp: int  # cues found but not labelled
    fn: int  # cues labelled but not found
    critical_found: int  # labelled critical cues found
    critical_labelled: int
    p0_labelled: bool  # the case's labelled priority is P0
    p0_missed: bool  # labelled P0 but not given P0
    priority_exact: bool
    under: bool  # the system's priority is lower than the label's
    over: bool  # the system's priority is higher than the label's


_NAMES = tuple(f.name for f in fields(CaseCounts))
Totals = dict[str, int]
Statistic = Callable[[Totals], float | None]


def _ratio(num: str, den: str) -> Statistic:
    return lambda t: t[num] / t[den] if t[den] else None


def _f1(t: Totals) -> float | None:
    if t["tp"] + t["fp"] == 0 or t["tp"] + t["fn"] == 0:
        return None
    return 2 * t["tp"] / (2 * t["tp"] + t["fp"] + t["fn"])


STATISTICS: dict[str, Statistic] = {
    "cue_micro_f1": _f1,
    "critical_cue_sensitivity": _ratio("critical_found", "critical_labelled"),
    "critical_undertriage": _ratio("p0_missed", "p0_labelled"),
    "priority_exact": _ratio("priority_exact", "cases"),
    "undertriage": _ratio("under", "cases"),
    "overtriage": _ratio("over", "cases"),
}


def _rows(cases: Sequence[CaseCounts]) -> list[tuple[int, ...]]:
    return [tuple(int(v) for v in astuple(c)) for c in cases]


def _totals(rows: Sequence[tuple[int, ...]], idx: Sequence[int] | None = None) -> Totals:
    picked = rows if idx is None else [rows[i] for i in idx]
    sums = [sum(col) for col in zip(*picked, strict=True)] if picked else [0] * len(_NAMES)
    return {"cases": len(picked), **dict(zip(_NAMES, sums, strict=True))}


def mcnemar(a: Sequence[bool], b: Sequence[bool]) -> dict[str, Any]:
    """Exact two-sided McNemar test; ``a`` and ``b`` are per-case "right" outcomes."""
    if len(a) != len(b):
        raise ValueError("paired outcomes must have the same length")
    pairs = list(zip(a, b, strict=True))
    a_only = sum(x and not y for x, y in pairs)
    b_only = sum(y and not x for x, y in pairs)
    n = a_only + b_only
    k = min(a_only, b_only)
    p = 1.0 if n == 0 else min(1.0, 2 * sum(math.comb(n, i) for i in range(k + 1)) / 2**n)
    return {
        "cases": len(pairs),
        "a_right_b_wrong": a_only,
        "b_right_a_wrong": b_only,
        "both_right": sum(x and y for x, y in pairs),
        "both_wrong": sum(not x and not y for x, y in pairs),
        "p_value": round(p, 6),
    }


def _r4(x: float | None) -> float | None:
    return None if x is None else round(x, 4)


def paired_differences(
    a: Sequence[CaseCounts], b: Sequence[CaseCounts], *, seed: int
) -> dict[str, dict[str, Any]]:
    """For every statistic, ``a - b`` with a 95% paired bootstrap interval."""
    if len(a) != len(b):
        raise ValueError("paired cases must have the same length")
    ra, rb = _rows(a), _rows(b)
    ta, tb = _totals(ra), _totals(rb)
    rng = random.Random(seed)
    n = len(ra)
    diffs: dict[str, list[float]] = {name: [] for name in STATISTICS}
    for _ in range(BOOTSTRAP_RESAMPLES if n else 0):
        idx = [rng.randrange(n) for _ in range(n)]
        sa, sb = _totals(ra, idx), _totals(rb, idx)
        for name, statistic in STATISTICS.items():
            x, y = statistic(sa), statistic(sb)
            if x is not None and y is not None:
                diffs[name].append(x - y)
    out: dict[str, dict[str, Any]] = {}
    for name, statistic in STATISTICS.items():
        x, y = statistic(ta), statistic(tb)
        d = sorted(diffs[name])
        out[name] = {
            "a": _r4(x),
            "b": _r4(y),
            "difference": None if x is None or y is None else round(x - y, 4),
            "ci95": [round(d[int(0.025 * len(d))], 4), round(d[int(0.975 * len(d)) - 1], 4)]
            if d
            else None,
        }
    return out


def compare_pair(a: Sequence[CaseCounts], b: Sequence[CaseCounts], *, seed: int) -> dict[str, Any]:
    """Every paired statistic for system ``a`` against system ``b`` on the same cases."""
    p0 = [i for i, c in enumerate(a) if c.p0_labelled]
    return {
        "mcnemar": {
            "critical_calls_given_p0": mcnemar(
                [not a[i].p0_missed for i in p0], [not b[i].p0_missed for i in p0]
            ),
            "priority_exact": mcnemar([c.priority_exact for c in a], [c.priority_exact for c in b]),
        },
        "differences": paired_differences(a, b, seed=seed),
    }
