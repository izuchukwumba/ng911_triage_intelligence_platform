"""Adjudication: disagreement sheet and adjudicated dataset records."""

import csv
import json
from pathlib import Path
from typing import Any

import pytest

from ntip.evaluation.adjudication import _disputed, apply, main, summary, write_sheet
from ntip.evaluation.annotation import LABEL_COLUMNS, Round, WorkbookError, sample
from ntip.evaluation.dataset import LabelSource, load_dataset

MESSAGES = {
    "c-1": "My father is not breathing. We are at 9 Pine Road.",
    "c-2": "There is smoke in the hallway.",
    "c-3": "Mi esposo no respira.",
}


@pytest.fixture
def root(tmp_path: Path) -> Path:
    rows = [
        {
            "case_id": cid,
            "split": "dev",
            "family": f"f{i}",
            "label_source": "author",
            "messages": [text],
            "labels": {
                "domain": "ems",
                "severity": "critical",
                "priority": "P0",
                "cues": [],
                "location": "present",
            },
        }
        for i, (cid, text) in enumerate(MESSAGES.items())
    ]
    (tmp_path / "curated.jsonl").write_text("\n".join(json.dumps(r) for r in rows) + "\n", "utf-8")
    return tmp_path


@pytest.fixture
def round_(root: Path) -> Round:
    return sample("R1", 5, include_all=[root / "curated.jsonl"])


def _labels(severity: str, priority: str, cue: str | None = None) -> dict[str, Any]:
    labels: dict[str, Any] = {
        "domain": "ems",
        "severity": severity,
        "priority": priority,
        "location": "present",
        "cues": [],
        "absent_cues": [],
    }
    if cue:
        start = MESSAGES["c-1"].index("not breathing")
        labels["cues"] = [cue]
        labels["cue_annotations"] = [
            {
                "code": cue,
                "status": "affirmed",
                "evidence": {
                    "message": 0,
                    "start": start,
                    "end": start + 13,
                    "text": "not breathing",
                },
            }
        ]
    return labels


def _records(round_: Round) -> dict[str, dict[str, dict[str, Any]]]:
    number = {c.case_id: c.case_number for c in round_.cases}
    a1 = {
        "c-1": _labels("critical", "P0", "NOT_BREATHING"),
        "c-2": _labels("elevated", "P2"),
        "c-3": None,  # skipped for language
    }
    a2 = {
        "c-1": _labels("critical", "P0", "NOT_BREATHING"),  # agrees
        "c-2": _labels("standard", "P3"),  # disagrees
        "c-3": None,
    }

    def records(name: str, labels: dict[str, Any]) -> dict[str, dict[str, Any]]:
        return {
            number[cid]: {
                "case_number": number[cid],
                "annotator": name,
                "case_id": cid,
                "skipped": lab is None,
                "labels": lab,
                "practitioner": {},
            }
            for cid, lab in labels.items()
        }

    return {"A1": records("A1", a1), "A2": records("A2", a2)}


def _decide(path: Path, rows: list[tuple[str, str, str]]) -> Path:
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["case_number", "decision", "reason"])
        writer.writerows(rows)
    return path


def test_only_disagreements_go_on_the_sheet(round_: Round, root: Path) -> None:
    records = _records(round_)
    number = {c.case_id: c.case_number for c in round_.cases}
    assert _disputed(records) == [number["c-2"]]
    assert write_sheet(round_, records, root / "sheet.csv", root) == 1
    sheet = (root / "sheet.csv").read_text("utf-8-sig")
    assert "There is smoke in the hallway." in sheet
    assert "ems / elevated (P2)" in sheet and "ems / standard (P3)" in sheet
    assert "c-2" not in sheet  # still blinded


def test_apply_takes_agreement_and_decisions(round_: Round, root: Path) -> None:
    records = _records(round_)
    number = {c.case_id: c.case_number for c in round_.cases}
    decisions = _decide(root / "d.csv", [(number["c-2"], "A1", "smoke inside; elevated")])
    cases, left_out = apply(round_, records, decisions, None, root)
    by_id = {c.case_id: c for c in cases}
    assert set(by_id) == {"c-1", "c-2"} and left_out == [number["c-3"]]
    assert all(c.label_source is LabelSource.ADJUDICATED for c in cases)
    assert by_id["c-2"].labels.severity == "elevated"
    assert by_id["c-2"].notes == "adjudicated in round R1: A1 (smoke inside, elevated)"
    assert "; " not in by_id["c-2"].notes  # would start a report slice
    assert by_id["c-1"].labels.cue_annotations is not None
    assert by_id["c-1"].family == "f0" and by_id["c-1"].split.value == "dev"


def test_own_labels_come_from_the_adjudicators_sheet(round_: Round, root: Path) -> None:
    records = _records(round_)
    number = {c.case_id: c.case_number for c in round_.cases}
    decisions = _decide(root / "d.csv", [(number["c-2"], "own", "neither fits")])
    with (root / "adj.csv").open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, LABEL_COLUMNS)
        writer.writeheader()
        writer.writerow(
            {
                "case_number": number["c-2"],
                "annotator": "ADJ",
                "domain": "fire",
                "severity": "elevated",
                "location": "missing",
                "cue_code": "SMOKE_REPORTED",
                "cue_status": "affirmed",
                "evidence": "smoke",
            }
        )
    cases, _ = apply(round_, records, decisions, root / "adj.csv", root)
    c2 = next(c for c in cases if c.case_id == "c-2")
    assert c2.labels.domain == "fire" and c2.labels.cues == ["SMOKE_REPORTED"]


def test_every_dispute_needs_a_valid_decision_and_reason(round_: Round, root: Path) -> None:
    records = _records(round_)
    number = {c.case_id: c.case_number for c in round_.cases}
    for rows, message in [
        ([], "no decision"),
        ([(number["c-2"], "A1", "")], "needs a reason"),
        ([(number["c-2"], "A9", "x")], "must be one of"),
        ([(number["c-2"], "own", "x")], "has no ADJ labels"),
        ([(number["c-2"], "A1", "x"), (number["c-1"], "A2", "y")], "not disputed"),
    ]:
        with pytest.raises(WorkbookError, match=message):
            apply(round_, records, _decide(root / "d.csv", rows), None, root)


def test_summary_is_readable() -> None:
    text = summary(_labels("critical", "P0", "NOT_BREATHING"))
    assert text.startswith("ems / critical (P0)")
    assert "NOT_BREATHING affirmed “not breathing”" in text
    assert summary(None) == "skipped (language)"


def test_command_line_writes_a_loadable_dataset(
    round_: Round, root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("ntip.evaluation.adjudication._repo_root", lambda: root)
    (root / "R1.json").write_text(round_.to_json(), "utf-8")
    imported = []
    for name, cases in _records(round_).items():
        path = root / f"{name}.jsonl"
        path.write_text("".join(json.dumps(r) + "\n" for r in cases.values()), "utf-8")
        imported += ["--imported", str(path)]
    number = {c.case_id: c.case_number for c in round_.cases}
    common = ["--round", str(root / "R1.json"), *imported]
    assert main(["sheet", *common, "--out", str(root / "sheet.csv")]) == 0
    decisions = _decide(root / "d.csv", [(number["c-2"], "A2", "no injury")])
    out = root / "adjudicated.jsonl"
    assert main(["apply", *common, "--decisions", str(decisions), "--out", str(out)]) == 0
    assert len(load_dataset(out).cases) == 2
