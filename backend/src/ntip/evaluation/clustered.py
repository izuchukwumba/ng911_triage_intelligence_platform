"""Paired comparisons that respect clustering by scenario family.

Generated calls come in families: many paraphrases of one scenario. Their
errors are correlated, so a test that treats every call as independent is
over-confident. These functions treat the **family** as the unit of
resampling or of evidence:

- ``clustered_mcnemar``: Durkalski et al. (2003), a McNemar test for
  clustered matched pairs. With ``d_k`` the difference in discordant counts
  in cluster ``k`` (A right and B wrong, minus the reverse),
  ``X² = (Σ d_k)² / Σ d_k²`` on one degree of freedom. With one case per
  cluster it equals the ordinary (uncorrected) McNemar statistic.
- ``family_sign_test``: an exact two-sided sign test over the families in
  which the two systems differ.
- ``cluster_bootstrap``: 95% percentile intervals for the difference in any
  ``ntip.evaluation.paired`` statistic, resampling whole families.
"""

import math
import random
from collections.abc import Sequence
from typing import Any

from ntip.evaluation.metrics import BOOTSTRAP_RESAMPLES
from ntip.evaluation.paired import STATISTICS, CaseCounts, _rows, _totals


def _groups(families: Sequence[str]) -> list[list[int]]:
    index: dict[str, list[int]] = {}
    for i, family in enumerate(families):
        index.setdefault(family, []).append(i)
    return list(index.values())


def clustered_mcnemar(
    a: Sequence[bool], b: Sequence[bool], families: Sequence[str]
) -> dict[str, Any]:
    """Durkalski's clustered McNemar test on per-case "right" outcomes."""
    if not len(a) == len(b) == len(families):
        raise ValueError("outcomes and families must have the same length")
    diffs = []
    for members in _groups(families):
        a_only = sum(a[i] and not b[i] for i in members)
        b_only = sum(b[i] and not a[i] for i in members)
        diffs.append(a_only - b_only)
    denominator = sum(d * d for d in diffs)
    statistic = sum(diffs) ** 2 / denominator if denominator else 0.0
    return {
        "clusters": len(diffs),
        "clusters_with_discordance": sum(d != 0 for d in diffs),
        "a_right_b_wrong": sum(x and not y for x, y in zip(a, b, strict=True)),
        "b_right_a_wrong": sum(y and not x for x, y in zip(a, b, strict=True)),
        "chi_square": round(statistic, 4),
        # Survival function of chi-square with one degree of freedom.
        "p_value": float(f"{math.erfc(math.sqrt(statistic / 2)):.3g}"),
    }


def family_sign_test(a_scores: Sequence[float], b_scores: Sequence[float]) -> dict[str, Any]:
    """Exact sign test over families; ties are dropped."""
    a_better = sum(x > y for x, y in zip(a_scores, b_scores, strict=True))
    b_better = sum(y > x for x, y in zip(a_scores, b_scores, strict=True))
    n, k = a_better + b_better, min(a_better, b_better)
    p = 1.0 if n == 0 else min(1.0, 2 * sum(math.comb(n, i) for i in range(k + 1)) / 2**n)
    return {
        "families": len(a_scores),
        "a_better": a_better,
        "b_better": b_better,
        "ties": len(a_scores) - n,
        "p_value": float(f"{p:.3g}"),
    }


def cluster_bootstrap(
    a: Sequence[CaseCounts],
    b: Sequence[CaseCounts],
    families: Sequence[str],
    *,
    seed: int,
) -> dict[str, dict[str, Any]]:
    """For every paired statistic, ``a - b`` with a 95% family-resampled interval."""
    if not len(a) == len(b) == len(families):
        raise ValueError("cases and families must have the same length")
    ra, rb = _rows(a), _rows(b)
    groups = _groups(families)
    rng = random.Random(seed)
    diffs: dict[str, list[float]] = {name: [] for name in STATISTICS}
    for _ in range(BOOTSTRAP_RESAMPLES if groups else 0):
        idx = [i for _ in groups for i in groups[rng.randrange(len(groups))]]
        sa, sb = _totals(ra, idx), _totals(rb, idx)
        for name, statistic in STATISTICS.items():
            x, y = statistic(sa), statistic(sb)
            if x is not None and y is not None:
                diffs[name].append(x - y)
    ta, tb = _totals(ra), _totals(rb)
    out: dict[str, dict[str, Any]] = {}
    for name, statistic in STATISTICS.items():
        x, y = statistic(ta), statistic(tb)
        d = sorted(diffs[name])
        out[name] = {
            "difference": None if x is None or y is None else round(x - y, 4),
            "ci95": [round(d[int(0.025 * len(d))], 4), round(d[int(0.975 * len(d)) - 1], 4)]
            if d
            else None,
        }
    return out
