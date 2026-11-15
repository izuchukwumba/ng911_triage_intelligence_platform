"""Paired statistics: McNemar's exact test and paired bootstrap differences."""

import pytest

from ntip.evaluation.paired import CaseCounts, compare_pair, mcnemar, paired_differences


def counts(*, tp=1, fp=0, fn=0, p0=False, missed=False, exact=True, under=False, over=False):
    return CaseCounts(
        tp=tp, fp=fp, fn=fn,
        critical_found=0 if missed else int(p0), critical_labelled=int(p0),
        p0_labelled=p0, p0_missed=missed, priority_exact=exact, under=under, over=over,
    )  # fmt: skip


class TestMcNemar:
    def test_exact_p_value_matches_the_binomial(self):
        # 9 cases where a is right and b wrong, 1 the other way: p = 2 * (1 + 10) / 2**10.
        a = [True] * 9 + [False] + [True] * 5
        b = [False] * 9 + [True] + [True] * 5
        result = mcnemar(a, b)
        assert result["a_right_b_wrong"] == 9
        assert result["b_right_a_wrong"] == 1
        assert result["both_right"] == 5
        assert result["p_value"] == pytest.approx(22 / 1024, abs=1e-6)

    def test_no_discordant_cases_gives_p_one(self):
        assert mcnemar([True, False], [True, False])["p_value"] == 1.0

    def test_balanced_split_is_capped_at_one(self):
        assert mcnemar([True, False], [False, True])["p_value"] == 1.0

    def test_is_symmetric(self):
        a, b = [True, True, True, False], [False, False, True, True]
        assert mcnemar(a, b)["p_value"] == mcnemar(b, a)["p_value"]

    def test_lengths_must_match(self):
        with pytest.raises(ValueError):
            mcnemar([True], [True, False])


class TestPairedDifferences:
    def test_identical_systems_differ_by_zero(self):
        cases = [counts(), counts(fp=1, exact=False, over=True), counts(p0=True)] * 5
        out = paired_differences(cases, cases, seed=1)
        for stat in out.values():
            assert stat["difference"] == 0
            assert stat["ci95"] == [0, 0]

    def test_difference_and_interval(self):
        a = [counts(exact=True)] * 20
        b = [counts(exact=False, under=True)] * 10 + [counts(exact=True)] * 10
        out = paired_differences(a, b, seed=7)["priority_exact"]
        assert (out["a"], out["b"], out["difference"]) == (1.0, 0.5, 0.5)
        low, high = out["ci95"]
        assert 0 < low <= 0.5 <= high <= 1

    def test_f1_from_totals(self):
        a = [counts(tp=2, fp=0, fn=0)] * 4
        b = [counts(tp=1, fp=1, fn=1)] * 4
        out = paired_differences(a, b, seed=3)["cue_micro_f1"]
        assert out["a"] == 1.0
        assert out["b"] == 0.5
        assert out["difference"] == 0.5

    def test_critical_undertriage_only_counts_p0_cases(self):
        a = [counts(p0=True), counts(p0=True), counts()]
        b = [counts(p0=True, missed=True), counts(p0=True), counts()]
        out = paired_differences(a, b, seed=3)["critical_undertriage"]
        assert (out["a"], out["b"], out["difference"]) == (0.0, 0.5, -0.5)

    def test_same_seed_same_interval(self):
        a = [counts(), counts(exact=False)] * 10
        b = [counts(exact=False), counts()] * 5 + [counts()] * 10
        assert paired_differences(a, b, seed=5) == paired_differences(a, b, seed=5)


def test_compare_pair_runs_mcnemar_on_p0_cases_only():
    a = [counts(p0=True), counts(p0=True), counts(exact=False)]
    b = [counts(p0=True, missed=True), counts(p0=True), counts()]
    result = compare_pair(a, b, seed=1)
    p0 = result["mcnemar"]["critical_calls_given_p0"]
    assert p0["cases"] == 2
    assert (p0["a_right_b_wrong"], p0["b_right_a_wrong"]) == (1, 0)
    exact = result["mcnemar"]["priority_exact"]
    assert exact["cases"] == 3
    assert (exact["a_right_b_wrong"], exact["b_right_a_wrong"]) == (0, 1)
    assert set(result["differences"]) == {
        "cue_micro_f1", "critical_cue_sensitivity", "critical_undertriage",
        "priority_exact", "undertriage", "overtriage",
    }  # fmt: skip
