import json
from pathlib import Path

import pytest

from ntip.evaluation.calibration import brier, expected_calibration_error, risk_coverage, summarise


def test_brier() -> None:
    assert brier([(1.0, True), (0.0, False)]) == 0.0
    assert brier([(0.5, True), (0.5, False)]) == 0.25
    assert brier([]) is None


def test_ece_is_zero_when_scores_match_frequencies() -> None:
    pairs = [(0.25, True)] + [(0.25, False)] * 3
    assert expected_calibration_error(pairs) == pytest.approx(0.0)


def test_ece_detects_overconfidence() -> None:
    pairs = [(0.95, False)] * 10
    assert expected_calibration_error(pairs) == pytest.approx(0.95)


def test_risk_coverage_rewards_confident_correct_answers() -> None:
    # Confident decisions are right, the unsure one is wrong.
    pairs = [(0.99, True), (0.01, False), (0.55, False)]
    result = risk_coverage(pairs)
    assert result["risk_at"]["50%"] == 0.0
    assert result["risk_at"]["100%"] == pytest.approx(1 / 3, abs=1e-4)


def test_summary_counts() -> None:
    summary = summarise([(0.9, True), (0.2, False)])
    assert (summary["pairs"], summary["positives"]) == (2, 1)


def test_compare_runs_all_systems(tmp_path: Path) -> None:
    pytest.importorskip("sklearn")
    from ntip.evaluation.compare import compare, to_markdown
    from ntip.evaluation.dataset import Split, load_dataset

    case = {
        "case_id": "a", "split": "test", "family": "f", "label_source": "author",
        "messages": ["My father is not breathign. We are at 12 Oak Street."],
        "labels": {"domain": "ems", "severity": "critical", "priority": "P0",
                   "cues": ["NOT_BREATHING"], "location": "present"},
    }  # fmt: skip
    path = tmp_path / "cases.jsonl"
    path.write_text(json.dumps(case), encoding="utf-8")

    result = compare(load_dataset(path), [Split.TEST])

    systems = result["systems"]
    assert set(systems) == {"B0 rules", "B1 only", "Hybrid B0+B1", "Hybrid without abstention"}
    # The misspelling hides the cue from the rules but not from B1.
    assert systems["B0 rules"]["metrics"]["critical_undertriage"]["numerator"] == 1
    assert systems["Hybrid B0+B1"]["metrics"]["critical_undertriage"]["numerator"] == 0
    assert result["b1_calibration"]["pairs"] > 0
    assert "| Critical-cue sensitivity |" in to_markdown(result)
