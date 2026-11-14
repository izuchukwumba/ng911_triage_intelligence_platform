"""Blinded annotation rounds (annotation protocol sections 4 and 7; ML layer design 4.4).

The coordinator runs three steps:

    # 1. Fix the cases and their neutral case numbers (the round file is the key:
    #    it maps case numbers to case ids, so only the coordinator keeps it).
    python -m ntip.evaluation.annotation sample --round R1 --seed 7 \\
        --all ../data/eval/curated.jsonl --exclude fx-001 \\
        --stratified ../data/eval/generated-2.1.0-seed42.jsonl --per-family 3 \\
        --out rounds/R1.json

    # 2. One blinded workbook per annotator: the messages only, in a different
    #    order for each annotator, and a label sheet to fill in.
    python -m ntip.evaluation.annotation export --round rounds/R1.json \\
        --annotator A1 --annotator A2 --out rounds/R1

    # 3. Read the returned label sheets: every row is validated and every quoted
    #    piece of evidence must occur verbatim in the case's messages.
    python -m ntip.evaluation.annotation import --round rounds/R1.json \\
        --workbook rounds/R1/A1-labels.csv --workbook rounds/R1/A2-labels.csv \\
        --out rounds/R1/imported

Workbooks are CSV (UTF-8 with a byte-order mark, so spreadsheet programs open
them correctly). Nothing in a workbook names a case id, family, split, label
or platform output.
"""

import argparse
import csv
import json
import random
import sys
from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from ntip.evaluation.dataset import (
    CaseLabels,
    CaseUncertainty,
    CueAnnotation,
    CueStatus,
    EvalCase,
    LocationComponents,
    TextSpan,
    load_dataset,
)
from ntip.parser.lexicon import OBSERVATION_CUES

ROUND_FORMAT = "ntip-annotation-round/1"
# Codes in the labelling guide's table; the caller-state codes are not labelled.
LABELLED_CODES = frozenset(OBSERVATION_CUES) - {
    "CALLER_HIGH_DISTRESS",
    "CALLER_LOCATION_UNKNOWN",
    "POSSIBLE_PRANK",
}
PRIORITY_FOR_SEVERITY = {
    "critical": "P0",
    "high": "P1",
    "elevated": "P2",
    "standard": "P3",
    "low": "P4",
    "undetermined": "P2",
}
COMPONENTS = ("house_number", "street", "unit", "intersection", "landmark", "locality")
CASE_COLUMNS = (
    "domain",
    "severity",
    "location",
    *COMPONENTS,
    "victim_count",
    "case_uncertainty",
    "practitioner_priority",
    "realism",
    "rubric_concern",
    "comment",
)
LABEL_COLUMNS = ("case_number", "annotator", "cue_code", "cue_status", "evidence", *CASE_COLUMNS)
SKIPPED_LANGUAGE = "skipped_language"
PRACTITIONER_FIELDS = ("practitioner_priority", "realism", "rubric_concern", "comment")


# --- Round file ---------------------------------------------------------------


@dataclass(frozen=True)
class RoundCase:
    case_number: str
    dataset: str
    case_id: str


@dataclass(frozen=True)
class Round:
    name: str
    seed: int
    datasets: dict[str, str]  # path -> digest
    cases: list[RoundCase]

    def to_json(self) -> str:
        return (
            json.dumps(
                {
                    "format": ROUND_FORMAT,
                    "round": self.name,
                    "seed": self.seed,
                    "datasets": self.datasets,
                    "cases": [vars(c) for c in self.cases],
                },
                indent=2,
                ensure_ascii=False,
            )
            + "\n"
        )

    @classmethod
    def load(cls, path: Path) -> "Round":
        data = json.loads(path.read_text("utf-8"))
        if data.get("format") != ROUND_FORMAT:
            raise ValueError(f"{path} is not an annotation round file")
        return cls(
            name=data["round"],
            seed=data["seed"],
            datasets=data["datasets"],
            cases=[RoundCase(**c) for c in data["cases"]],
        )

    def resolve(self, root: Path) -> dict[str, EvalCase]:
        """The round's cases by case number; refuses a dataset that has changed."""
        by_dataset: dict[str, dict[str, EvalCase]] = {}
        for path, digest in self.datasets.items():
            dataset = load_dataset(root / path)
            if dataset.digest != digest:
                raise ValueError(
                    f"{path} has changed since the round was sampled ({dataset.digest} != {digest})"
                )
            by_dataset[path] = {c.case_id: c for c in dataset.cases}
        return {c.case_number: by_dataset[c.dataset][c.case_id] for c in self.cases}


def sample(
    name: str,
    seed: int,
    *,
    include_all: Sequence[Path] = (),
    exclude: Sequence[str] = (),
    stratified: Sequence[Path] = (),
    per_family: int = 10,
) -> Round:
    """Every case of ``include_all`` (minus ``exclude``), plus up to ``per_family``
    cases of each family of ``stratified``, drawn with ``seed``."""
    rng = random.Random(seed)
    datasets: dict[str, str] = {}
    chosen: list[tuple[str, str]] = []
    for path in include_all:
        dataset = load_dataset(path)
        datasets[dataset.path] = dataset.digest
        chosen += [(dataset.path, c.case_id) for c in dataset.cases if c.case_id not in exclude]
    for path in stratified:
        dataset = load_dataset(path)
        datasets[dataset.path] = dataset.digest
        families: dict[str, list[str]] = defaultdict(list)
        for case in dataset.cases:
            if case.case_id not in exclude:
                families[case.family].append(case.case_id)
        for family in sorted(families):
            ids = families[family]
            drawn = sorted(rng.sample(ids, min(per_family, len(ids))))
            chosen += [(dataset.path, i) for i in drawn]
    if len(set(chosen)) != len(chosen):
        raise ValueError("a case was chosen twice")
    numbers = rng.sample(range(1000, 10000), len(chosen))
    cases = [RoundCase(f"{n:04d}", d, i) for n, (d, i) in zip(numbers, chosen, strict=True)]
    return Round(name, seed, datasets, sorted(cases, key=lambda c: c.case_number))


# --- Export -------------------------------------------------------------------


def annotator_order(round_: Round, annotator: str) -> list[RoundCase]:
    """A different, reproducible order for each annotator."""
    order = list(round_.cases)
    random.Random(f"{round_.seed}:{annotator}").shuffle(order)
    return order


def export(round_: Round, annotators: Sequence[str], out: Path, root: Path) -> list[Path]:
    cases = round_.resolve(root)
    longest = max(len(c.messages) for c in cases.values())
    out.mkdir(parents=True, exist_ok=True)
    written = []
    for annotator in annotators:
        order = annotator_order(round_, annotator)
        case_sheet = out / f"{annotator}-cases.csv"
        with case_sheet.open("w", encoding="utf-8-sig", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["case_number", *(f"message_{i + 1}" for i in range(longest))])
            for rc in order:
                writer.writerow([rc.case_number, *cases[rc.case_number].messages])
        label_sheet = out / f"{annotator}-labels.csv"
        with label_sheet.open("w", encoding="utf-8-sig", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(LABEL_COLUMNS)
            for rc in order:
                writer.writerow([rc.case_number, annotator] + [""] * (len(LABEL_COLUMNS) - 2))
        written += [case_sheet, label_sheet]
    return written


# --- Import -------------------------------------------------------------------


class WorkbookError(ValueError):
    def __init__(self, problems: list[str]) -> None:
        super().__init__("\n".join(problems))
        self.problems = problems


_OPENING = "\"'" + chr(0x201C) + chr(0x2018)  # straight and curly quotes
_CLOSING = "\"'" + chr(0x201D) + chr(0x2019)


def _quote(text: str) -> str:
    """Evidence as typed, without surrounding whitespace or quotation marks."""
    text = text.strip()
    while len(text) >= 2 and text[0] in _OPENING and text[-1] in _CLOSING:
        text = text[1:-1].strip()
    return text


def _span(messages: list[str], quote: str) -> TextSpan:
    for index, message in enumerate(messages):
        if quote and quote in message:
            return TextSpan.find(messages, index, quote)
    raise ValueError(f"{quote!r} does not occur verbatim in any message")


def _case_record(
    number: str,
    annotator: str,
    source: RoundCase,
    case: EvalCase,
    rows: list[tuple[int, dict[str, str]]],
) -> tuple[dict[str, Any] | None, list[str]]:
    problems: list[str] = []
    first_line, first = rows[0]
    for line, row in rows[1:]:
        for column in CASE_COLUMNS:
            if row[column] and row[column] != first[column]:
                problems.append(
                    f"line {line}: case {number}: {column} {row[column]!r} differs from "
                    f"line {first_line} ({first[column]!r})"
                )
    practitioner: dict[str, Any] = {k: first[k] or None for k in PRACTITIONER_FIELDS}
    if practitioner["practitioner_priority"] not in (None, "P0", "P1", "P2", "P3", "P4"):
        problems.append(f"line {first_line}: practitioner_priority must be P0 to P4 or empty")
    if practitioner["realism"] is not None:
        if practitioner["realism"] not in ("1", "2", "3", "4", "5"):
            problems.append(f"line {first_line}: realism must be 1 to 5 or empty")
        else:
            practitioner["realism"] = int(practitioner["realism"])
    record: dict[str, Any] = {
        "case_number": number,
        "annotator": annotator,
        "dataset": source.dataset,
        "case_id": source.case_id,
        "skipped": first["case_uncertainty"] == SKIPPED_LANGUAGE,
        "labels": None,
        "practitioner": practitioner,
    }
    if record["skipped"]:
        return (None if problems else record), problems

    annotations: list[CueAnnotation] = []
    seen: set[str] = set()
    for line, row in rows:
        code = row["cue_code"].strip().upper()
        if not code:
            if row["cue_status"] or row["evidence"]:
                problems.append(f"line {line}: cue_status or evidence given without a cue_code")
            continue
        if code not in LABELLED_CODES:
            problems.append(f"line {line}: unknown cue_code {code!r}")
            continue
        if code in seen:
            problems.append(f"line {line}: {code} recorded twice for case {number}")
            continue
        seen.add(code)
        try:
            status = CueStatus(row["cue_status"].strip().lower())
        except ValueError:
            problems.append(f"line {line}: cue_status {row['cue_status']!r} is not a status")
            continue
        quote = _quote(row["evidence"])
        if not quote:
            problems.append(f"line {line}: {code} needs evidence (the caller's exact words)")
            continue
        try:
            span = _span(case.messages, quote)
        except ValueError as e:
            problems.append(f"line {line}: {code}: {e}")
            continue
        annotations.append(CueAnnotation(code=code, status=status, evidence=span))

    components: dict[str, TextSpan] = {}
    for name in COMPONENTS:
        if quote := _quote(first[name]):
            try:
                components[name] = _span(case.messages, quote)
            except ValueError as e:
                problems.append(f"line {first_line}: {name}: {e}")

    victims: int | str | None = first["victim_count"].strip().lower() or None
    if isinstance(victims, str) and victims != "unknown":
        if victims.isdigit() and int(victims) > 0:
            victims = int(victims)
        else:
            problems.append(f"line {first_line}: victim_count must be a number, unknown or empty")
    severity = first["severity"].strip().lower()
    uncertainty = first["case_uncertainty"].strip().lower() or None
    if uncertainty is not None and uncertainty not in {u.value for u in CaseUncertainty}:
        problems.append(f"line {first_line}: case_uncertainty {uncertainty!r} is not a value")
        uncertainty = None
    if problems:
        return None, problems
    try:
        labels = CaseLabels.model_validate(
            {
                "domain": first["domain"].strip().lower(),
                "severity": severity,
                "priority": PRIORITY_FOR_SEVERITY.get(severity, ""),
                "location": first["location"].strip().lower(),
                "victim_count": victims,
                "cue_annotations": annotations,
                "location_components": LocationComponents(**components) if components else None,
                "case_uncertainty": uncertainty,
            }
        )
    except ValidationError as e:
        fields = "; ".join(
            f"{'.'.join(str(p) for p in err['loc']) or 'labels'}: {err['msg']}"
            for err in e.errors()
        )
        return None, [f"line {first_line}: case {number}: {fields}"]
    record["labels"] = labels.model_dump(mode="json", exclude_none=True)
    return record, []


def read_workbook(path: Path, round_: Round, cases: dict[str, EvalCase]) -> list[dict[str, Any]]:
    """Validated records, one per case, in case-number order; raises WorkbookError."""
    with path.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        missing = [c for c in LABEL_COLUMNS if c not in (reader.fieldnames or [])]
        if missing:
            raise WorkbookError([f"{path.name}: missing columns {missing}"])
        rows = [(i, {k: (v or "") for k, v in row.items() if k}) for i, row in enumerate(reader, 2)]
    problems: list[str] = []
    annotators = {row["annotator"].strip() for _, row in rows if row["annotator"].strip()}
    if len(annotators) != 1:
        raise WorkbookError([f"{path.name}: expected one annotator, found {sorted(annotators)}"])
    annotator = annotators.pop()
    by_case: dict[str, list[tuple[int, dict[str, str]]]] = defaultdict(list)
    for line, row in rows:
        number = row["case_number"].strip()
        if not number and not any(row.values()):
            continue  # blank line
        if number not in cases:
            problems.append(f"line {line}: unknown case_number {number!r}")
            continue
        by_case[number].append((line, row))
    sources = {c.case_number: c for c in round_.cases}
    unlabelled = sorted(set(cases) - set(by_case))
    if unlabelled:
        problems.append(f"no rows for cases {unlabelled}")
    records = []
    for number in sorted(by_case):
        record, case_problems = _case_record(
            number, annotator, sources[number], cases[number], by_case[number]
        )
        problems += case_problems
        if record is not None:
            records.append(record)
    if problems:
        raise WorkbookError([f"{path.name}: {p}" for p in problems])
    return records


# --- Command line ---------------------------------------------------------------


def _repo_root() -> Path:
    from ntip.evaluation.runner import REPO_ROOT

    return REPO_ROOT


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    commands = parser.add_subparsers(dest="command", required=True)
    s = commands.add_parser("sample", help="fix a round's cases and case numbers")
    s.add_argument("--round", required=True, help="round name, for example R1")
    s.add_argument("--seed", type=int, required=True)
    s.add_argument("--all", type=Path, action="append", default=[], dest="include_all")
    s.add_argument("--exclude", action="append", default=[], help="a case id to leave out")
    s.add_argument("--stratified", type=Path, action="append", default=[])
    s.add_argument("--per-family", type=int, default=10)
    s.add_argument("--out", type=Path, required=True)
    e = commands.add_parser("export", help="write blinded workbooks")
    e.add_argument("--round", type=Path, required=True)
    e.add_argument("--annotator", action="append", required=True)
    e.add_argument("--out", type=Path, required=True)
    i = commands.add_parser("import", help="validate returned label sheets")
    i.add_argument("--round", type=Path, required=True)
    i.add_argument("--workbook", type=Path, action="append", required=True)
    i.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)

    root = _repo_root()
    if args.command == "sample":
        round_ = sample(
            args.round,
            args.seed,
            include_all=args.include_all,
            exclude=args.exclude,
            stratified=args.stratified,
            per_family=args.per_family,
        )
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(round_.to_json(), encoding="utf-8", newline="\n")
        print(f"{len(round_.cases)} cases -> {args.out}")
        return 0
    round_ = Round.load(args.round)
    if args.command == "export":
        for path in export(round_, args.annotator, args.out, root):
            print(path)
        return 0
    cases = round_.resolve(root)
    failed = False
    results: dict[str, list[dict[str, Any]]] = {}
    for workbook in args.workbook:
        try:
            records = read_workbook(workbook, round_, cases)
        except WorkbookError as error:
            failed = True
            print("\n".join(error.problems), file=sys.stderr)
            continue
        results[records[0]["annotator"] if records else workbook.stem] = records
    if failed:
        print("Nothing written: fix the problems above and import again.", file=sys.stderr)
        return 1
    args.out.mkdir(parents=True, exist_ok=True)
    for annotator, records in results.items():
        path = args.out / f"{annotator}.jsonl"
        path.write_text(
            "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in records),
            encoding="utf-8",
            newline="\n",
        )
        print(f"{annotator}: {len(records)} cases -> {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
