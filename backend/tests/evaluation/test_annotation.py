"""Annotation rounds: sampling, blinded export and validated import."""

import csv
import json
from pathlib import Path

import pytest

from ntip.evaluation.annotation import (
    LABEL_COLUMNS,
    Round,
    WorkbookError,
    annotator_order,
    export,
    main,
    read_workbook,
    sample,
)


def _case(case_id: str, family: str, message: str, split: str = "dev") -> dict[str, object]:
    return {
        "case_id": case_id,
        "split": split,
        "family": family,
        "label_source": "author",
        "messages": [message],
        "labels": {
            "domain": "ems",
            "severity": "critical",
            "priority": "P0",
            "cues": ["NOT_BREATHING"],
            "location": "present",
        },
    }


@pytest.fixture
def root(tmp_path: Path) -> Path:
    curated = [
        _case("c-1", "f1", "My father is not breathing. We are at 9 Pine Road."),
        _case("c-2", "f2", "He wasn't breathing earlier but he is awake now, 12 Oak Street."),
        _case("c-3", "f3", "Mi esposo no respira."),
    ]
    generated = [
        _case(f"g-{i}", f"fam{i % 3}", f"Call number {i}, nobody is hurt.") for i in range(9)
    ]
    for name, cases in (("curated.jsonl", curated), ("generated.jsonl", generated)):
        (tmp_path / name).write_text("\n".join(json.dumps(c) for c in cases) + "\n", "utf-8")
    return tmp_path


@pytest.fixture
def round_(root: Path) -> Round:
    return sample(
        "R1",
        7,
        include_all=[root / "curated.jsonl"],
        exclude=["c-3"],
        stratified=[root / "generated.jsonl"],
        per_family=2,
    )


def test_sample_takes_every_listed_case_and_a_stratified_draw(round_: Round, root: Path) -> None:
    ids = [(c.dataset, c.case_id) for c in round_.cases]
    assert ("curated.jsonl", "c-1") in ids and ("curated.jsonl", "c-3") not in ids
    generated = [i for d, i in ids if d == "generated.jsonl"]
    assert len(generated) == 6  # 2 from each of 3 families
    numbers = [c.case_number for c in round_.cases]
    assert len(set(numbers)) == len(numbers) and all(len(n) == 4 for n in numbers)
    again = sample(
        "R1",
        7,
        include_all=[root / "curated.jsonl"],
        exclude=["c-3"],
        stratified=[root / "generated.jsonl"],
        per_family=2,
    )
    assert again == round_
    assert Round.load(_write(root / "R1.json", round_.to_json())) == round_


def _write(path: Path, text: str) -> Path:
    path.write_text(text, "utf-8")
    return path


def test_export_is_blinded_and_shuffled_per_annotator(round_: Round, root: Path) -> None:
    export(round_, ["A1", "A2"], root / "out", root)
    sheet = (root / "out" / "A1-cases.csv").read_text("utf-8-sig")
    assert "c-1" not in sheet and "f1" not in sheet and "NOT_BREATHING" not in sheet
    assert "My father is not breathing." in sheet
    assert annotator_order(round_, "A1") != annotator_order(round_, "A2")
    with (root / "out" / "A2-labels.csv").open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    assert [r["case_number"] for r in rows] == [
        c.case_number for c in annotator_order(round_, "A2")
    ]
    assert {r["annotator"] for r in rows} == {"A2"}


def _fill(path: Path, round_: Round, rows_for: dict[str, list[dict[str, str]]]) -> None:
    """Write a label sheet: given rows for some cases, a plain no-cue row for the rest."""
    default = {"domain": "other", "severity": "low", "location": "missing"}
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, LABEL_COLUMNS)
        writer.writeheader()
        for rc in round_.cases:
            for row in rows_for.get(rc.case_id, [default]):
                writer.writerow({"case_number": rc.case_number, "annotator": "A1", **row})


def _number(round_: Round, case_id: str) -> str:
    return next(c.case_number for c in round_.cases if c.case_id == case_id)


def test_import_resolves_evidence_and_components(round_: Round, root: Path) -> None:
    case_level = {
        "domain": "ems",
        "severity": "critical",
        "location": "present",
        "house_number": "9",
        "street": "Pine Road",
        "victim_count": "1",
        "case_uncertainty": "clear",
        "practitioner_priority": "P0",
        "realism": "4",
    }
    _fill(
        root / "A1-labels.csv",
        round_,
        {
            "c-1": [
                {
                    **case_level,
                    "cue_code": "not_breathing",
                    "cue_status": "affirmed",
                    "evidence": '"is not breathing"',
                }
            ],
            "c-2": [
                {
                    "domain": "ems",
                    "severity": "elevated",
                    "location": "present",
                    "street": "Oak Street",
                    "cue_code": "NOT_BREATHING",
                    "cue_status": "historical",
                    "evidence": "wasn't breathing earlier",
                }
            ],
        },
    )
    records = read_workbook(root / "A1-labels.csv", round_, round_.resolve(root))
    by_id = {r["case_id"]: r for r in records}
    assert len(records) == len(round_.cases)
    first = by_id["c-1"]
    assert first["labels"]["cues"] == ["NOT_BREATHING"]
    assert first["labels"]["priority"] == "P0"
    assert first["labels"]["cue_annotations"][0]["evidence"] == {
        "message": 0,
        "start": 10,
        "end": 26,
        "text": "is not breathing",
    }
    assert first["labels"]["location_components"]["street"]["text"] == "Pine Road"
    assert first["practitioner"] == {
        "practitioner_priority": "P0",
        "realism": 4,
        "rubric_concern": None,
        "comment": None,
    }
    second = by_id["c-2"]["labels"]
    assert second["cues"] == [] and second["absent_cues"] == ["NOT_BREATHING"]
    assert second["priority"] == "P2"


def test_import_reports_every_problem_with_its_line(round_: Round, root: Path) -> None:
    _fill(
        root / "A1-labels.csv",
        round_,
        {
            "c-1": [
                {
                    "domain": "ems",
                    "severity": "critical",
                    "location": "present",
                    "cue_code": "NOT_BREATHING",
                    "cue_status": "affirmed",
                    "evidence": "not breathin",
                },
                {
                    "domain": "fire",
                    "cue_code": "MADE_UP",
                    "cue_status": "affirmed",
                    "evidence": "x",
                },
            ],
            "c-2": [
                {
                    "domain": "ems",
                    "severity": "dire",
                    "location": "present",
                    "cue_code": "UNCONSCIOUS",
                    "cue_status": "awake",
                    "evidence": "awake",
                }
            ],
        },
    )
    text = (root / "A1-labels.csv").read_text("utf-8-sig")
    # Drop one case's rows entirely.
    last = round_.cases[-1].case_number
    lines = [x for x in text.splitlines() if not x.startswith(last)]
    (root / "A1-labels.csv").write_text("\n".join(lines) + "\n", "utf-8-sig")
    with pytest.raises(WorkbookError) as raised:
        read_workbook(root / "A1-labels.csv", round_, round_.resolve(root))
    problems = "\n".join(raised.value.problems)
    assert "domain 'fire' differs" in problems
    assert "unknown cue_code 'MADE_UP'" in problems
    assert "'awake' is not a status" in problems
    assert f"no rows for cases ['{last}']" in problems
    assert "A1-labels.csv: line 7: case" in problems  # spreadsheet row numbers


def test_evidence_must_be_verbatim(round_: Round, root: Path) -> None:
    _fill(
        root / "A1-labels.csv",
        round_,
        {
            "c-1": [
                {
                    "domain": "ems",
                    "severity": "critical",
                    "location": "present",
                    "cue_code": "NOT_BREATHING",
                    "cue_status": "affirmed",
                    "evidence": "is not breathin g",
                }
            ]
        },
    )
    with pytest.raises(WorkbookError, match="does not occur verbatim"):
        read_workbook(root / "A1-labels.csv", round_, round_.resolve(root))


def test_skipped_language_is_recorded_not_labelled(root: Path) -> None:
    round_ = sample("R2", 1, include_all=[root / "curated.jsonl"])
    _fill(root / "A1-labels.csv", round_, {"c-3": [{"case_uncertainty": "skipped_language"}]})
    records = read_workbook(root / "A1-labels.csv", round_, round_.resolve(root))
    skipped = next(r for r in records if r["case_id"] == "c-3")
    assert skipped["skipped"] is True and skipped["labels"] is None


def test_a_changed_dataset_is_refused(round_: Round, root: Path) -> None:
    path = root / "curated.jsonl"
    path.write_text(path.read_text("utf-8").replace("Pine Road", "Pine Rd"), "utf-8")
    with pytest.raises(ValueError, match="has changed since the round was sampled"):
        round_.resolve(root)


def test_command_line_round_trip(root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("ntip.evaluation.annotation._repo_root", lambda: root)
    round_file = root / "R1.json"
    assert (
        main(
            [
                "sample",
                "--round",
                "R1",
                "--seed",
                "3",
                "--all",
                str(root / "curated.jsonl"),
                "--out",
                str(round_file),
            ]
        )
        == 0
    )
    assert (
        main(["export", "--round", str(round_file), "--annotator", "A1", "--out", str(root / "wb")])
        == 0
    )
    round_ = Round.load(round_file)
    _fill(root / "wb" / "A1-labels.csv", round_, {})
    assert (
        main(
            [
                "import",
                "--round",
                str(round_file),
                "--workbook",
                str(root / "wb" / "A1-labels.csv"),
                "--out",
                str(root / "imp"),
            ]
        )
        == 0
    )
    lines = (root / "imp" / "A1.jsonl").read_text("utf-8").splitlines()
    assert len(lines) == 3
