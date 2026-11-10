import json
from pathlib import Path

import pytest

from ntip.evaluation.dataset import EvalCase, Split, load_dataset
from ntip.evaluation.metrics import PRF, confusion, rate
from ntip.evaluation.report import to_markdown
from ntip.evaluation.runner import REPO_ROOT, evaluate

CURATED = REPO_ROOT / "data" / "eval" / "curated.jsonl"


def write(tmp_path: Path, *cases: dict[str, object]) -> Path:
    path = tmp_path / "cases.jsonl"
    path.write_text("\n".join(json.dumps(c) for c in cases), encoding="utf-8")
    return path


def case(
    case_id: str, split: str, family: str, text: str = "Fire at 12 Oak Street."
) -> dict[str, object]:
    return {
        "case_id": case_id,
        "split": split,
        "family": family,
        "messages": [text],
        "label_source": "author",
        "labels": {"domain": "fire", "severity": "elevated", "priority": "P2",
                   "cues": ["FIRE_REPORTED"], "location": "present"},
    }  # fmt: skip


class TestDataset:
    def test_curated_dataset_is_valid_and_leak_free(self) -> None:
        dataset = load_dataset(CURATED)
        assert len(dataset.cases) >= 50
        assert {c.split for c in dataset.cases} == set(Split)
        assert all(c.synthetic for c in dataset.cases)

    def test_family_spanning_splits_is_rejected(self, tmp_path: Path) -> None:
        path = write(tmp_path, case("a", "dev", "fam"), case("b", "test", "fam"))
        with pytest.raises(ValueError, match="leakage"):
            load_dataset(path)

    def test_duplicate_ids_are_rejected(self, tmp_path: Path) -> None:
        path = write(tmp_path, case("a", "dev", "f1"), case("a", "dev", "f2"))
        with pytest.raises(ValueError, match="duplicate"):
            load_dataset(path)

    def test_cue_cannot_be_both_present_and_absent(self) -> None:
        raw = case("a", "dev", "f")
        raw["labels"]["absent_cues"] = ["FIRE_REPORTED"]  # type: ignore[index]
        with pytest.raises(ValueError, match="both present and absent"):
            EvalCase.model_validate(raw)

    def test_digest_ignores_line_endings(self, tmp_path: Path) -> None:
        lf = write(tmp_path, case("a", "dev", "f"))
        crlf = tmp_path / "crlf.jsonl"
        crlf.write_bytes(lf.read_bytes().replace(b"\n", b"\r\n"))
        assert load_dataset(lf).digest == load_dataset(crlf).digest


class TestMetrics:
    def test_rate_reports_counts_and_interval(self) -> None:
        result = rate([True, True, False, True], seed=1)
        assert (result.numerator, result.denominator, result.value) == (3, 4, 0.75)
        assert result.ci_low is not None and result.ci_high is not None
        assert 0 <= result.ci_low <= 0.75 <= result.ci_high <= 1

    def test_rate_is_reproducible_for_a_seed(self) -> None:
        outcomes = [True, False] * 10
        assert rate(outcomes, seed=7) == rate(outcomes, seed=7)

    def test_empty_rate(self) -> None:
        assert rate([], seed=1).value is None

    def test_prf(self) -> None:
        prf = PRF(tp=8, fp=2, fn=2)
        assert (prf.precision, prf.recall, prf.f1) == (0.8, 0.8, pytest.approx(0.8))

    def test_confusion(self) -> None:
        matrix = confusion([("P0", "P0"), ("P0", "P2")], ["P0", "P2"])
        assert matrix["P0"] == {"P0": 1, "P2": 1}


class TestRunner:
    def test_scores_a_correct_case(self, tmp_path: Path) -> None:
        result = evaluate(load_dataset(write(tmp_path, case("a", "dev", "f"))), [Split.DEV])
        metrics = result["metrics"]
        assert metrics["priority_exact"]["value"] == 1.0
        assert metrics["failures"] == {}

    def test_reports_failures_with_reasons(self, tmp_path: Path) -> None:
        wrong = case("a", "dev", "f", "There is no fire here at all.")
        result = evaluate(load_dataset(write(tmp_path, wrong)), [Split.DEV])
        assert "missed cues ['FIRE_REPORTED']" in result["metrics"]["failures"]["a"][0]

    def test_manifest_pins_inputs(self, tmp_path: Path) -> None:
        dataset = load_dataset(write(tmp_path, case("a", "dev", "f")))
        manifest = evaluate(dataset, [Split.DEV], seed=3)["manifest"]
        assert manifest["dataset"]["digest"] == dataset.digest
        assert manifest["ruleset"]["digest"].startswith("sha256:")
        assert manifest["seed"] == 3

    def test_evaluation_is_deterministic(self) -> None:
        dataset = load_dataset(CURATED)
        first = evaluate(dataset, [Split.DEV])["metrics"]
        assert first == evaluate(dataset, [Split.DEV])["metrics"]

    def test_markdown_report_renders(self) -> None:
        markdown = to_markdown(evaluate(load_dataset(CURATED), [Split.DEV]))
        assert "Critical-cue sensitivity" in markdown
        assert "not evidence of real-world dispatch accuracy" in markdown
