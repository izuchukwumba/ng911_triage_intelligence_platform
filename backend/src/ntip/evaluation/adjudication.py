"""Adjudication: from independent labels to reference labels (annotation protocol 5 and 9).

After agreement is computed, the adjudicator decides every case where the
annotators differ:

    # 1. A sheet of the disagreements only: messages and each annotator's labels.
    python -m ntip.evaluation.adjudication sheet --round R1.json \\
        --imported imported/A1.jsonl --imported imported/A2.jsonl --out R1-adjudication.csv

    # 2. The adjudicator fills in `decision` (an annotator's name, or "own") and
    #    a one-sentence `reason` for every row. For "own", they label the case
    #    themselves in a label sheet with annotator ADJ (same columns as the
    #    annotators' sheets; only those cases).

    # 3. Dataset records with label_source "adjudicated".
    python -m ntip.evaluation.adjudication apply --round R1.json \\
        --imported imported/A1.jsonl --imported imported/A2.jsonl \\
        --decisions R1-adjudication.csv --own ADJ-labels.csv --out adjudicated-R1.jsonl

A case on which every annotator gave the same labels needs no decision. A case
every annotator skipped for language is left out and listed. Each record keeps
its source case id, split and family, so the family split rules still hold,
and its notes say how the label was reached.
"""

import argparse
import csv
import json
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from ntip.evaluation.annotation import Round, WorkbookError, read_workbook
from ntip.evaluation.dataset import CaseLabels, EvalCase, LabelSource, dump_case

OWN = "own"
ADJUDICATOR = "ADJ"


def _load(paths: Sequence[Path]) -> dict[str, dict[str, dict[str, Any]]]:
    """records[annotator][case_number]"""
    out: dict[str, dict[str, dict[str, Any]]] = {}
    for path in paths:
        rows = [json.loads(x) for x in path.read_text("utf-8").splitlines() if x.strip()]
        if rows:
            out[rows[0]["annotator"]] = {r["case_number"]: r for r in rows}
    if len(out) < 2:
        raise ValueError("adjudication needs the imported labels of at least two annotators")
    numbers = [set(cases) for cases in out.values()]
    if any(n != numbers[0] for n in numbers):
        raise ValueError("annotators labelled different cases; import the same round")
    return out


def summary(labels: dict[str, Any] | None) -> str:
    """One annotator's labels for a case, readable in a spreadsheet cell."""
    if labels is None:
        return "skipped (language)"
    cues = "; ".join(
        f"{a['code']} {a['status']}" + (f" “{a['evidence']['text']}”" if a.get("evidence") else "")
        for a in labels.get("cue_annotations") or []
    )
    parts = [
        f"{labels['domain']} / {labels['severity']} ({labels['priority']})",
        f"location {labels['location']}",
        f"cues: {cues or 'none'}",
    ]
    if labels.get("victim_count") is not None:
        parts.append(f"victims {labels['victim_count']}")
    components = labels.get("location_components") or {}
    if components:
        parts.append(", ".join(f"{k} “{v['text']}”" for k, v in sorted(components.items())))
    if labels.get("case_uncertainty"):
        parts.append(labels["case_uncertainty"])
    return " | ".join(parts)


def _disputed(records: dict[str, dict[str, dict[str, Any]]]) -> list[str]:
    names = sorted(records)
    numbers = sorted(records[names[0]])
    return [
        n
        for n in numbers
        if len({json.dumps(records[a][n]["labels"], sort_keys=True) for a in names}) > 1
    ]


def write_sheet(
    round_: Round, records: dict[str, dict[str, dict[str, Any]]], out: Path, root: Path
) -> int:
    cases = round_.resolve(root)
    names = sorted(records)
    disputed = _disputed(records)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["case_number", "messages", *names, "decision", "reason"])
        for n in disputed:
            messages = "\n".join(cases[n].messages)
            writer.writerow(
                [n, messages, *(summary(records[a][n]["labels"]) for a in names), "", ""]
            )
    return len(disputed)


def apply(
    round_: Round,
    records: dict[str, dict[str, dict[str, Any]]],
    decisions_path: Path,
    own_path: Path | None,
    root: Path,
) -> tuple[list[EvalCase], list[str]]:
    """(adjudicated cases, case numbers left out); raises WorkbookError on problems."""
    cases = round_.resolve(root)
    sources = {c.case_number: c for c in round_.cases}
    names = sorted(records)
    with decisions_path.open(encoding="utf-8-sig", newline="") as f:
        rows = list(enumerate(csv.DictReader(f), 2))
    decisions: dict[str, tuple[int, str, str]] = {}
    problems: list[str] = []
    for line, row in rows:
        number = (row.get("case_number") or "").strip()
        decisions[number] = (
            line,
            (row.get("decision") or "").strip(),
            (row.get("reason") or "").strip(),
        )
    own: dict[str, dict[str, Any]] = {}
    if own_path is not None:
        own = {r["case_number"]: r for r in read_workbook(own_path, round_, cases, partial=True)}

    adjudicated: list[EvalCase] = []
    left_out: list[str] = []
    disputed = set(_disputed(records))
    for number in sorted(records[names[0]]):
        source = sources[number]
        case = cases[number]
        labels: dict[str, Any] | None
        if number not in disputed:
            labels = records[names[0]][number]["labels"]
            note = f"adjudicated in round {round_.name}: all annotators agreed"
        elif number not in decisions:
            problems.append(f"case {number}: annotators disagree and there is no decision")
            continue
        else:
            line, decision, reason = decisions[number]
            if not reason:
                problems.append(f"line {line}: case {number} needs a reason")
                continue
            if decision in names:
                labels = records[decision][number]["labels"]
            elif decision.lower() == OWN:
                if number not in own:
                    problems.append(f"line {line}: case {number} is 'own' but has no ADJ labels")
                    continue
                labels = own[number]["labels"]
            else:
                problems.append(
                    f"line {line}: decision {decision!r} must be one of {[*names, OWN]}"
                )
                continue
            # "; " in notes starts the variant list used for report slices, so avoid it.
            note = f"adjudicated in round {round_.name}: {decision} ({reason.replace('; ', ', ')})"
        if labels is None:  # every annotator skipped it, or the chosen one did
            left_out.append(number)
            continue
        adjudicated.append(
            EvalCase(
                case_id=source.case_id,
                split=case.split,
                family=case.family,
                messages=case.messages,
                label_source=LabelSource.ADJUDICATED,
                labels=CaseLabels.model_validate(labels),
                notes=note,
            )
        )
    stale = sorted(set(decisions) - disputed - {""})
    if stale:
        problems.append(f"decisions for cases that are not disputed: {stale}")
    if problems:
        raise WorkbookError(problems)
    return sorted(adjudicated, key=lambda c: c.case_id), left_out


def _repo_root() -> Path:
    from ntip.evaluation.runner import REPO_ROOT

    return REPO_ROOT


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    commands = parser.add_subparsers(dest="command", required=True)
    s = commands.add_parser("sheet", help="list the cases the annotators disagree on")
    a = commands.add_parser("apply", help="write adjudicated dataset records")
    for p in (s, a):
        p.add_argument("--round", type=Path, required=True)
        p.add_argument("--imported", type=Path, action="append", required=True)
        p.add_argument("--out", type=Path, required=True)
    a.add_argument("--decisions", type=Path, required=True)
    a.add_argument("--own", type=Path, help="the adjudicator's own label sheet (annotator ADJ)")
    args = parser.parse_args(argv)
    round_ = Round.load(args.round)
    records = _load(args.imported)
    root = _repo_root()
    if args.command == "sheet":
        n = write_sheet(round_, records, args.out, root)
        print(f"{n} disputed cases -> {args.out}")
        return 0
    try:
        adjudicated, left_out = apply(round_, records, args.decisions, args.own, root)
    except WorkbookError as error:
        print("\n".join(error.problems), file=sys.stderr)
        print("Nothing written.", file=sys.stderr)
        return 1
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        "".join(dump_case(c) + "\n" for c in adjudicated), encoding="utf-8", newline="\n"
    )
    print(f"{len(adjudicated)} adjudicated cases -> {args.out}")
    if left_out:
        print(f"left out (skipped for language): {left_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
