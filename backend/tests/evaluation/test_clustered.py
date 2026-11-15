"""Clustered paired statistics: Durkalski's McNemar, a family sign test, a cluster bootstrap."""

import math

import pytest

from ntip.evaluation.clustered import cluster_bootstrap, clustered_mcnemar, family_sign_test
from ntip.evaluation.paired import CaseCounts


def counts(*, exact: bool = True, p0: bool = False, missed: bool = False) -> CaseCounts:
    return CaseCounts(
        tp=1, fp=0, fn=0, critical_found=0, critical_labelled=0, p0_labelled=p0,
        p0_missed=missed, priority_exact=exact, under=False, over=False,
    )  # fmt: skip


class TestClusteredMcNemar:
    def test_one_case_per_cluster_is_the_ordinary_mcnemar_statistic(self):
        # 6 vs 2 discordant pairs, each its own cluster: X² = (6 - 2)² / (6 + 2) = 2.
        a = [True] * 6 + [False] * 2 + [True] * 3
        b = [False] * 6 + [True] * 2 + [True] * 3
        result = clustered_mcnemar(a, b, [f"f{i}" for i in range(len(a))])
        assert result["chi_square"] == 2.0
        assert result["p_value"] == pytest.approx(math.erfc(1.0), rel=1e-2)

    def test_discordance_concentrated_in_one_cluster_is_weak_evidence(self):
        # 10 discordant pairs all in one family: X² = 10² / 10² = 1.
        a = [True] * 10 + [True] * 10
        b = [False] * 10 + [True] * 10
        families = ["one"] * 10 + [f"f{i}" for i in range(10)]
        result = clustered_mcnemar(a, b, families)
        assert result["chi_square"] == 1.0
        assert result["clusters_with_discordance"] == 1
        # The same discordance spread over ten families is strong evidence.
        spread = clustered_mcnemar(a, b, [f"g{i}" for i in range(20)])
        assert spread["chi_square"] == 10.0
        assert spread["p_value"] < result["p_value"]

    def test_no_discordance(self):
        result = clustered_mcnemar([True, False], [True, False], ["a", "b"])
        assert (result["chi_square"], result["p_value"]) == (0.0, 1.0)

    def test_lengths_must_match(self):
        with pytest.raises(ValueError):
            clustered_mcnemar([True], [True], ["a", "b"])


def test_family_sign_test():
    result = family_sign_test([3, 2, 1, 0, 5], [1, 2, 0, 0, 4])
    assert (result["a_better"], result["b_better"], result["ties"]) == (3, 0, 2)
    assert result["p_value"] == 0.25  # 2 * (1/2)**3


class TestClusterBootstrap:
    def test_identical_systems(self):
        cases = [counts(), counts(exact=False)] * 4
        out = cluster_bootstrap(cases, cases, list("aabbccdd"), seed=1)
        assert out["priority_exact"] == {"difference": 0.0, "ci95": [0.0, 0.0]}

    def test_clustering_widens_the_interval(self):
        # A is right on every case; B is wrong on one whole family of four.
        a = [counts()] * 16
        b = [counts(exact=False)] * 4 + [counts()] * 12
        by_case = cluster_bootstrap(a, b, [str(i) for i in range(16)], seed=3)["priority_exact"]
        by_family = cluster_bootstrap(a, b, [str(i // 4) for i in range(16)], seed=3)[
            "priority_exact"
        ]
        assert by_case["difference"] == by_family["difference"] == 0.25
        width = lambda r: r["ci95"][1] - r["ci95"][0]  # noqa: E731
        assert width(by_family) > width(by_case)


def test_posthoc_screening_ppv_falls_with_prevalence():
    from types import SimpleNamespace

    from ntip.evaluation.ml10_posthoc import _screening

    def result(gold: str, given: str) -> SimpleNamespace:
        return SimpleNamespace(
            case=SimpleNamespace(labels=SimpleNamespace(priority=gold)), predicted_priority=given
        )

    # Sensitivity 0.8 (8 of 10 P0 calls given P0), false-positive rate 0.1 (2 of 20).
    results = [result("P0", "P0")] * 8 + [result("P0", "P1")] * 2
    results += [result("P2", "P0")] * 2 + [result("P2", "P2")] * 18
    s = _screening(results)  # type: ignore[arg-type]
    assert (s["sensitivity"], s["false_positive_rate"], s["false_p0"]) == (0.8, 0.1, 2)
    # PPV = 0.8p / (0.8p + 0.1(1 - p)).
    assert s["ppv_at_prevalence"]["0.1"] == round(0.08 / (0.08 + 0.09), 4)
    assert s["ppv_at_prevalence"]["0.05"] < s["ppv_at_prevalence"]["0.35"]
