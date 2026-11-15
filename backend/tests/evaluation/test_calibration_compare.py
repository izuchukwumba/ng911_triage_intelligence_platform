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


def test_compare_records_extra_models(tmp_path: Path) -> None:
    pytest.importorskip("sklearn")
    from ntip.evaluation.compare import compare, to_markdown
    from ntip.evaluation.dataset import Split, load_dataset
    from ntip.ml.extractors import RulesAsModel

    case = {
        "case_id": "a", "split": "dev", "family": "f", "label_source": "author",
        "messages": ["My father is not breathing. We are at 12 Oak Street."],
        "labels": {"domain": "ems", "severity": "critical", "priority": "P0",
                   "cues": ["NOT_BREATHING"], "location": "present"},
    }  # fmt: skip
    path = tmp_path / "cases.jsonl"
    path.write_text(json.dumps(case), encoding="utf-8")
    extra = RulesAsModel()

    result = compare(load_dataset(path), [Split.DEV], extra_models={"Extra": extra})

    assert result["manifest"]["extra_models"] == {
        "Extra": {"model_id": extra.model_id, "model_version": extra.model_version}
    }
    assert {"Extra only", "Hybrid B0+Extra"} <= set(result["systems"])
    assert f"Extra `{extra.model_version}`" in to_markdown(result)


def test_compare_pairs_every_system_with_the_rules(tmp_path: Path) -> None:
    pytest.importorskip("sklearn")
    from ntip.evaluation.compare import compare, paired_comparisons, to_markdown
    from ntip.evaluation.dataset import Split, load_dataset
    from ntip.ml.extractors import RulesAsModel

    case = {
        "case_id": "a", "split": "dev", "family": "f", "label_source": "author",
        "messages": ["My father is not breathign. We are at 12 Oak Street."],
        "labels": {"domain": "ems", "severity": "critical", "priority": "P0",
                   "cues": ["NOT_BREATHING"], "location": "present"},
    }  # fmt: skip
    path = tmp_path / "cases.jsonl"
    path.write_text(json.dumps(case), encoding="utf-8")

    result = compare(load_dataset(path), [Split.DEV], extra_models={"Extra": RulesAsModel()})

    expected = paired_comparisons(list(result["systems"]), ["Extra"])
    assert ("Hybrid B0+Extra", "Hybrid B0+B1") in expected
    assert set(result["paired"]) == {f"{a} vs {b}" for a, b in expected}
    hybrid = result["paired"]["Hybrid B0+B1 vs B0 rules"]
    # The misspelling hides the cue from the rules but not from B1: one discordant P0 call.
    p0 = hybrid["mcnemar"]["critical_calls_given_p0"]
    assert (p0["a_right_b_wrong"], p0["b_right_a_wrong"]) == (1, 0)
    assert hybrid["differences"]["critical_undertriage"]["difference"] == -1.0
    assert "## Paired comparisons" in to_markdown(result)


def test_compare_records_the_preregistration_and_run_cost(tmp_path: Path) -> None:
    pytest.importorskip("sklearn")
    from ntip.evaluation.compare import compare, to_markdown
    from ntip.evaluation.dataset import Split, load_dataset
    from ntip.ml.extractors import RulesAsModel
    from ntip.schema.base import sha256_digest

    case = {
        "case_id": "a", "split": "test", "family": "f", "label_source": "author",
        "messages": ["My father is not breathing. We are at 12 Oak Street."],
        "labels": {"domain": "ems", "severity": "critical", "priority": "P0",
                   "cues": ["NOT_BREATHING"], "location": "present"},
    }  # fmt: skip
    path = tmp_path / "cases.jsonl"
    path.write_text(json.dumps(case), encoding="utf-8")
    prereg = tmp_path / "plan.md"
    prereg.write_bytes(b"# Plan\r\nfixed before the run\r\n")

    result = compare(
        load_dataset(path), [Split.TEST], extra_models={"Extra": RulesAsModel()},
        preregistration=prereg,
    )  # fmt: skip

    record = result["manifest"]["preregistration"]
    # Line endings are normalised, so a Windows and a Linux checkout give the same digest.
    expected = sha256_digest("# Plan\nfixed before the run\n")
    assert record == {"path": "plan.md", "digest": expected}
    assert record["digest"] in to_markdown(result)
    run = result["systems"]["Hybrid B0+B1"]["run"]
    assert run["span_verification_rejections"] == 0
    assert run["p50_ms"] is not None
    assert result["systems"]["B0 rules"]["run"]["span_verification_rejections"] is None
    assert "## Run cost and verification" in to_markdown(result)


def test_the_test_split_needs_a_preregistration(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    from ntip.evaluation import compare

    argv = ["compare", "--dataset", str(tmp_path / "x.jsonl"), "--split", "test"]
    monkeypatch.setattr("sys.argv", argv)
    with pytest.raises(SystemExit):
        compare.main()
    assert "pre-registration" in capsys.readouterr().err
    # The default split is test, so leaving --split out is refused too.
    monkeypatch.setattr("sys.argv", argv[:3])
    with pytest.raises(SystemExit):
        compare.main()


def test_a_console_that_cannot_encode_the_report_does_not_fail_the_run(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    pytest.importorskip("sklearn")
    import io
    import sys

    from ntip.evaluation import compare

    case = {
        "case_id": "a", "split": "dev", "family": "f", "label_source": "author",
        "messages": ["My father is not breathing. We are at 12 Oak Street."],
        "labels": {"domain": "ems", "severity": "critical", "priority": "P0",
                   "cues": ["NOT_BREATHING"], "location": "present"},
    }  # fmt: skip
    path = tmp_path / "cases.jsonl"
    path.write_text(json.dumps(case), encoding="utf-8")
    console = io.TextIOWrapper(io.BytesIO(), encoding="cp1252")
    monkeypatch.setattr(sys, "stdout", console)
    argv = ["compare", "--dataset", str(path), "--split", "dev", "--out", str(tmp_path / "out")]
    monkeypatch.setattr("sys.argv", argv)

    assert compare.main() == 0
    assert "Δ" in (tmp_path / "out" / "compare-cases-dev.md").read_text("utf-8")
