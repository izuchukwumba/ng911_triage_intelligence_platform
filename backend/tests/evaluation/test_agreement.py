"""Agreement measures (annotation protocol section 8)."""

import json
from pathlib import Path
from typing import Any

import pytest

from ntip.evaluation.agreement import (
    Agreement,
    band,
    cohen_kappa,
    krippendorff_alpha,
    main,
    to_markdown,
    token_f1,
)

N = None


def test_coefficients_match_published_values() -> None:
    # Krippendorff (2011), "Computing Krippendorff's alpha-reliability": 4 coders, 12 units.
    coders = [
        [1, 2, 3, 3, 2, 1, 4, 1, 2, N, N, N],
        [1, 2, 3, 3, 2, 2, 4, 1, 2, 5, N, 3],
        [N, 3, 3, 3, 2, 3, 4, 2, 2, 5, 1, N],
        [1, 2, 3, 3, 2, 4, 4, 1, 2, 5, 1, N],
    ]
    units = [list(u) for u in zip(*coders, strict=True)]
    assert krippendorff_alpha(units) == pytest.approx(0.743, abs=1e-3)
    assert krippendorff_alpha(units, order=[1, 2, 3, 4, 5]) == pytest.approx(0.815, abs=1e-3)
    pairs = [("y", "y"), ("y", "n"), ("n", "n"), ("n", "n"), ("y", "y")]
    assert cohen_kappa(pairs) == pytest.approx(0.6154, abs=1e-4)
    assert cohen_kappa([("a", "a"), ("a", "a")]) is None  # one category only: undefined


def test_token_f1_and_bands() -> None:
    assert token_f1("is not breathing", "not breathing") == pytest.approx(0.8)
    assert token_f1("x", "y") == 0.0
    assert [band(v) for v in (0.85, 0.7, 0.3, None)] == [
        "reference",
        "use, report agreement",
        "not used; revise rubric",
        "undefined",
    ]


def _record(number: str, annotator: str, **labels: Any) -> dict[str, Any]:
    practitioner = labels.pop("practitioner", None)
    skipped = labels.pop("skipped", False)
    full = {
        "domain": "ems",
        "severity": "critical",
        "priority": "P0",
        "location": "present",
        "cues": [],
        "absent_cues": [],
        **labels,
    }
    return {
        "case_number": number,
        "annotator": annotator,
        "dataset": "d.jsonl",
        "case_id": f"c{number}",
        "skipped": skipped,
        "labels": None if skipped else full,
        "practitioner": {
            "practitioner_priority": practitioner,
            "realism": None,
            "rubric_concern": None,
            "comment": None,
        },
    }


def _nb(status: str, quote: str) -> dict[str, Any]:
    live = status in ("affirmed", "uncertain")
    return {
        "cues": ["NOT_BREATHING"] if live else [],
        "absent_cues": [] if live else ["NOT_BREATHING"],
        "cue_annotations": [
            {
                "code": "NOT_BREATHING",
                "status": status,
                "evidence": {"message": 0, "start": 0, "end": len(quote), "text": quote},
            }
        ],
    }


@pytest.fixture
def two() -> dict[str, list[dict[str, Any]]]:
    a1 = [
        _record("1001", "A1", **_nb("affirmed", "is not breathing"), practitioner="P0"),
        _record(
            "1002",
            "A1",
            **_nb("historical", "wasn't breathing earlier"),
            severity="elevated",
            priority="P2",
            practitioner="P1",
        ),
        _record(
            "1003",
            "A1",
            domain="fire",
            severity="elevated",
            priority="P2",
            location="missing",
            practitioner="P3",
        ),
        _record("1004", "A1", domain="police", severity="standard", priority="P3"),
        _record("1005", "A1", skipped=True),
    ]
    a2 = [
        _record("1001", "A2", **_nb("affirmed", "not breathing")),
        _record(
            "1002",
            "A2",
            **_nb("affirmed", "wasn't breathing earlier"),
            severity="critical",
            priority="P0",
        ),
        _record(
            "1003", "A2", domain="fire", severity="elevated", priority="P2", location="missing"
        ),
        _record("1004", "A2", domain="police", severity="high", priority="P1"),
        _record("1005", "A2", domain="other", severity="low", priority="P4"),
    ]
    return {"A1": a1, "A2": a2}


def test_report_measures_each_field(two: dict[str, list[dict[str, Any]]]) -> None:
    report = Agreement(two, seed=1).report()
    assert report["cases"] == 4  # 1005 skipped by A1
    assert report["skipped_language"] == {"A1": ["1005"], "A2": []}
    assert report["domain"]["primary"] == "kappa"
    assert report["domain"]["exact"] == 1.0 and report["domain"]["band"] == "reference"
    assert report["priority"]["exact"] == 0.5
    assert report["priority"]["within_one_level"] == 0.5  # P2/P0 and P3/P1 differ by two
    nb = report["cue_codes"]["NOT_BREATHING"]
    assert nb["cases_either_reported"] == 2 and nb["exact"] == 0.75
    evidence = report["cue_status_and_evidence"]
    assert evidence["cues_recorded_by_all"] == 2
    assert evidence["evidence_exact_match"] == 0.5
    assert evidence["evidence_token_f1"] == pytest.approx((0.8 + 1.0) / 2, abs=1e-4)
    assert report["practitioner_vs_rubric"]["A1"] == {
        "cases": 3,
        "same": 1,
        "practitioner_higher": 1,
        "practitioner_lower": 1,
    }
    ci = report["severity"]["kappa_ci95"]
    assert ci == [None, None] or ci[0] <= ci[1]
    markdown = to_markdown(report)
    assert "| domain | kappa 1.0" in markdown and "`NOT_BREATHING`" in markdown


def test_three_annotators_use_alpha(two: dict[str, list[dict[str, Any]]]) -> None:
    third = [{**r, "annotator": "A3"} for r in two["A2"]]
    report = Agreement({**two, "A3": third}, seed=1).report()
    assert report["domain"]["primary"] == "alpha" and "kappa" not in report["domain"]


def test_annotators_must_label_the_same_cases(two: dict[str, list[dict[str, Any]]]) -> None:
    with pytest.raises(ValueError, match="different cases"):
        Agreement({"A1": two["A1"], "A2": two["A2"][:-1]}, seed=1)
    with pytest.raises(ValueError, match="at least two"):
        Agreement({"A1": two["A1"]}, seed=1)


def test_command_line(two: dict[str, list[dict[str, Any]]], tmp_path: Path) -> None:
    paths = []
    for name, rows in two.items():
        path = tmp_path / f"{name}.jsonl"
        path.write_text("".join(json.dumps(r) + "\n" for r in rows), "utf-8")
        paths.append(str(path))
    assert main([*paths, "--out", str(tmp_path / "out")]) == 0
    report = json.loads((tmp_path / "out" / "agreement.json").read_text("utf-8"))
    assert report["annotators"] == ["A1", "A2"]
    assert (tmp_path / "out" / "agreement.md").exists()
