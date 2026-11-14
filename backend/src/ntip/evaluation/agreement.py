"""Inter-annotator agreement (annotation protocol section 8).

Computed from the annotators' independent labels, as written by
``python -m ntip.evaluation.annotation import``, before adjudication:

    python -m ntip.evaluation.agreement imported/A1.jsonl imported/A2.jsonl --out report/

With two annotators the primary measure is Cohen's kappa; with more,
Krippendorff's alpha. Both are always reported. Every figure carries its count
and a bootstrap 95% interval (cases resampled, seed recorded), and each field
gets the protocol's pre-declared band. Cases an annotator skipped for language
are reported and left out, not counted as disagreements.
"""

import argparse
import json
import random
import re
from collections import Counter
from collections.abc import Callable, Hashable, Sequence
from pathlib import Path
from typing import Any

from ntip.evaluation.annotation import COMPONENTS, LABELLED_CODES

PRIORITY_ORDER = ("P4", "P3", "P2", "P1", "P0")
RESAMPLES = 2000
# A rating per annotator for one case; None when that annotator gave none.
Ratings = list[Hashable | None]


# --- Coefficients -----------------------------------------------------------------


def cohen_kappa(pairs: Sequence[tuple[Hashable, Hashable]]) -> float | None:
    if not pairs:
        return None
    n = len(pairs)
    observed = sum(a == b for a, b in pairs) / n
    left = Counter(a for a, _ in pairs)
    right = Counter(b for _, b in pairs)
    expected = sum(left[c] * right[c] for c in left) / (n * n)
    if expected == 1:
        return None  # both annotators used one category throughout: undefined
    return (observed - expected) / (1 - expected)


def krippendorff_alpha(
    units: Sequence[Ratings], order: Sequence[Hashable] | None = None
) -> float | None:
    """Nominal alpha, or ordinal alpha when ``order`` ranks the categories."""
    coincidence: dict[tuple[Hashable, Hashable], float] = {}
    for unit in units:
        values = [v for v in unit if v is not None]
        m = len(values)
        if m < 2:
            continue
        for i, a in enumerate(values):
            for j, b in enumerate(values):
                if i != j:
                    coincidence[(a, b)] = coincidence.get((a, b), 0.0) + 1 / (m - 1)
    totals: dict[Hashable, float] = {}
    for (a, _), weight in coincidence.items():
        totals[a] = totals.get(a, 0.0) + weight
    n = sum(totals.values())
    if n <= 1:
        return None
    if order is None:

        def distance(a: Hashable, b: Hashable) -> float:
            return 0.0 if a == b else 1.0

    else:
        rank = {c: i for i, c in enumerate(order)}
        ranked = sorted(totals, key=lambda c: rank[c])

        def distance(a: Hashable, b: Hashable) -> float:
            lo, hi = sorted((rank[a], rank[b]))
            between = sum(totals[c] for c in ranked if lo <= rank[c] <= hi)
            return (between - (totals[a] + totals[b]) / 2) ** 2

    observed = sum(w * distance(a, b) for (a, b), w in coincidence.items()) / n
    expected = sum(totals[a] * totals[b] * distance(a, b) for a in totals for b in totals) / (
        n * (n - 1)
    )
    if expected == 0:
        return None
    return 1 - observed / expected


def _tokens(text: str) -> list[str]:
    return re.findall(r"\w+", text.lower())


def token_f1(a: str, b: str) -> float:
    left, right = Counter(_tokens(a)), Counter(_tokens(b))
    common = sum((left & right).values())
    if common == 0:
        return 0.0
    precision, recall = common / sum(right.values()), common / sum(left.values())
    return 2 * precision * recall / (precision + recall)


def band(value: float | None) -> str:
    """The protocol's pre-declared interpretation (section 8)."""
    if value is None:
        return "undefined"
    if value >= 0.8:
        return "reference"
    if value >= 0.6:
        return "use, report agreement"
    return "not used; revise rubric"


# --- Per-case ratings ---------------------------------------------------------------


def _load(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text("utf-8").splitlines() if line.strip()]


Extract = Callable[[dict[str, Any]], Hashable | None]


def _field(name: str) -> Extract:
    return lambda labels: labels.get(name)


def _live(code: str) -> Extract:
    return lambda labels: code in labels.get("cues", [])


def _component(name: str) -> Extract:
    def get(labels: dict[str, Any]) -> Hashable | None:
        span = (labels.get("location_components") or {}).get(name)
        return span["text"] if span else None

    return get


def _annotations(labels: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {a["code"]: a for a in labels.get("cue_annotations") or []}


class Agreement:
    def __init__(self, annotators: dict[str, list[dict[str, Any]]], seed: int) -> None:
        self.names = sorted(annotators)
        if len(self.names) < 2:
            raise ValueError("agreement needs at least two annotators")
        by_annotator = {a: {r["case_number"]: r for r in rs} for a, rs in annotators.items()}
        numbers = set.intersection(*(set(cases) for cases in by_annotator.values()))
        if any(set(cases) != numbers for cases in by_annotator.values()):
            raise ValueError("annotators labelled different cases; import the same round")
        self.skipped = {
            a: sorted(n for n, r in cases.items() if r["skipped"])
            for a, cases in by_annotator.items()
        }
        skipped_any = set().union(*self.skipped.values())
        self.cases = sorted(numbers - skipped_any)
        # labels[case][annotator]
        self.labels = {n: [by_annotator[a][n]["labels"] for a in self.names] for n in self.cases}
        self.practitioner = {
            n: [by_annotator[a][n]["practitioner"] for a in self.names] for n in self.cases
        }
        self.seed = seed

    def _ratings(self, extract: Extract) -> dict[str, Ratings]:
        return {n: [extract(lab) for lab in self.labels[n]] for n in self.cases}

    def _interval(self, statistic: Callable[[list[str]], float | None]) -> list[float | None]:
        rng = random.Random(self.seed)
        values = []
        for _ in range(RESAMPLES):
            sample = [rng.choice(self.cases) for _ in self.cases]
            value = statistic(sample)
            if value is not None:
                values.append(value)
        if len(values) < RESAMPLES * 0.9:  # mostly undefined: no honest interval
            return [None, None]
        values.sort()
        return [
            round(values[int(0.025 * len(values))], 4),
            round(values[int(0.975 * len(values)) - 1], 4),
        ]

    def categorical(
        self, extract: Extract, *, order: Sequence[Hashable] | None = None
    ) -> dict[str, Any]:
        """Kappa (two annotators), alpha and exact agreement for one field."""
        ratings = self._ratings(extract)

        def kappa(cases: list[str]) -> float | None:
            pairs = [(ratings[c][0], ratings[c][1]) for c in cases]
            return cohen_kappa([(a, b) for a, b in pairs if a is not None and b is not None])

        def alpha(cases: list[str]) -> float | None:
            return krippendorff_alpha([ratings[c] for c in cases], order)

        def exact(cases: list[str]) -> float | None:
            rated = [ratings[c] for c in cases]
            return sum(len(set(r)) == 1 for r in rated) / len(rated) if rated else None

        result: dict[str, Any] = {"cases": len(self.cases)}
        primary = "kappa" if len(self.names) == 2 else "alpha"
        measures = {"alpha": alpha, "exact": exact}
        if len(self.names) == 2:
            measures = {"kappa": kappa, **measures}
        for name, statistic in measures.items():
            value = statistic(self.cases)
            result[name] = None if value is None else round(value, 4)
            result[f"{name}_ci95"] = self._interval(statistic)
        result["primary"] = primary
        result["band"] = band(result[primary])
        return result

    def cue_codes(self) -> dict[str, Any]:
        out = {}
        for code in sorted(LABELLED_CODES):
            ratings = self._ratings(_live(code))
            either = sum(any(r) for r in ratings.values())
            if either == 0:
                continue
            out[code] = {"cases_either_reported": either, **self.categorical(_live(code))}
        return out

    def cue_status_and_evidence(self) -> dict[str, Any]:
        """Over the cues every annotator recorded for the same case."""
        shared: list[tuple[str, str]] = []
        for n in self.cases:
            recorded = [_annotations(lab) for lab in self.labels[n]]
            codes = set.intersection(*(set(r) for r in recorded))
            shared += [(n, code) for code in sorted(codes)]
        if not shared:
            return {"cues_recorded_by_all": 0}
        statuses = {
            (n, code): [_annotations(lab)[code]["status"] for lab in self.labels[n]]
            for n, code in shared
        }
        quotes = {
            (n, code): [
                (_annotations(lab)[code].get("evidence") or {}).get("text", "")
                for lab in self.labels[n]
            ]
            for n, code in shared
        }
        pairs = [(i, j) for i in range(len(self.names)) for j in range(i + 1, len(self.names))]
        f1 = [token_f1(q[i], q[j]) for q in quotes.values() for i, j in pairs]
        exact = [q[i] == q[j] for q in quotes.values() for i, j in pairs]
        status: dict[str, Any] = {"alpha": _round(krippendorff_alpha(list(statuses.values())))}
        if len(self.names) == 2:
            status["kappa"] = _round(cohen_kappa([(s[0], s[1]) for s in statuses.values()]))
        status["primary"] = "kappa" if len(self.names) == 2 else "alpha"
        status["band"] = band(status[status["primary"]])
        return {
            "cues_recorded_by_all": len(shared),
            "status": status,
            "evidence_token_f1": round(sum(f1) / len(f1), 4),
            "evidence_exact_match": round(sum(exact) / len(exact), 4),
        }

    def priority(self) -> dict[str, Any]:
        result = self.categorical(_field("priority"), order=PRIORITY_ORDER)
        rank = {p: i for i, p in enumerate(PRIORITY_ORDER)}
        within = [
            max(rank[lab["priority"]] for lab in self.labels[n])
            - min(rank[lab["priority"]] for lab in self.labels[n])
            <= 1
            for n in self.cases
        ]
        result["within_one_level"] = round(sum(within) / len(within), 4) if within else None
        return result

    def components(self) -> dict[str, Any]:
        out = {}
        for name in COMPONENTS:
            ratings = self._ratings(_component(name))
            given = [r for r in ratings.values() if any(v is not None for v in r)]
            if given:
                out[name] = {
                    "cases_either_gave": len(given),
                    "exact": round(sum(len(set(r)) == 1 for r in given) / len(given), 4),
                }
        return out

    def practitioner_vs_rubric(self) -> dict[str, Any]:
        rank = {p: i for i, p in enumerate(PRIORITY_ORDER)}
        out = {}
        for k, name in enumerate(self.names):
            given = [
                (self.practitioner[n][k]["practitioner_priority"], self.labels[n][k]["priority"])
                for n in self.cases
                if self.practitioner[n][k].get("practitioner_priority")
            ]
            out[name] = {
                "cases": len(given),
                "same": sum(p == r for p, r in given),
                "practitioner_higher": sum(rank[p] > rank[r] for p, r in given),
                "practitioner_lower": sum(rank[p] < rank[r] for p, r in given),
            }
        return out

    def report(self) -> dict[str, Any]:
        return {
            "annotators": self.names,
            "cases": len(self.cases),
            "skipped_language": self.skipped,
            "bootstrap": {"resamples": RESAMPLES, "seed": self.seed},
            "cue_codes": self.cue_codes(),
            "cue_status_and_evidence": self.cue_status_and_evidence(),
            "domain": self.categorical(_field("domain")),
            "severity": self.categorical(
                _field("severity"), order=SEVERITY_ORDER_WITH_UNDETERMINED
            ),
            "priority": self.priority(),
            "location": self.categorical(_field("location")),
            "location_components": self.components(),
            "victim_count": self.categorical(lambda lab: str(lab.get("victim_count"))),
            "practitioner_vs_rubric": self.practitioner_vs_rubric(),
        }


# "Undetermined" maps to P2 in the rubric, so it sits with "elevated" for ordinal alpha.
SEVERITY_ORDER_WITH_UNDETERMINED = (
    "low", "standard", "undetermined", "elevated", "high", "critical",
)  # fmt: skip


def _round(value: float | None) -> float | None:
    return None if value is None else round(value, 4)


# --- Report -----------------------------------------------------------------------


def _cell(field: dict[str, Any]) -> str:
    primary = field["primary"]
    value, ci = field[primary], field[f"{primary}_ci95"]
    if value is None:
        return f"{primary} undefined"
    interval = f" [{ci[0]}, {ci[1]}]" if ci[0] is not None else ""
    return f"{primary} {value}{interval}"


def to_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Inter-annotator agreement",
        "",
        f"Annotators {', '.join(report['annotators'])} · {report['cases']} cases · bootstrap "
        f"{report['bootstrap']['resamples']} resamples, seed {report['bootstrap']['seed']}. "
        "Independent labels, before adjudication (annotation protocol section 8).",
        "",
        "| Field | Agreement | Exact | Band |",
        "|---|---|---|---|",
    ]
    for name in ("domain", "severity", "priority", "location", "victim_count"):
        field = report[name]
        extra = f"; within one level {field['within_one_level']}" if name == "priority" else ""
        lines.append(f"| {name} | {_cell(field)} | {field['exact']}{extra} | {field['band']} |")
    status = report["cue_status_and_evidence"]
    if status.get("cues_recorded_by_all"):
        s = status["status"]
        lines += [
            "",
            f"**Cue status** over {status['cues_recorded_by_all']} cues every annotator recorded: "
            f"{s['primary']} {s[s['primary']]} ({s['band']}). **Evidence:** token F1 "
            f"{status['evidence_token_f1']}, exact match {status['evidence_exact_match']}.",
        ]
    lines += [
        "",
        "## Cue codes (reported live or not)",
        "",
        "| Code | Cases either reported | Agreement | Band |",
        "|---|---|---|---|",
    ]
    for code, field in report["cue_codes"].items():
        lines.append(
            f"| `{code}` | {field['cases_either_reported']} | {_cell(field)} | {field['band']} |"
        )
    if report["location_components"]:
        lines += ["", "## Location components (exact match where either gave one)", ""]
        for name, c in report["location_components"].items():
            lines.append(f"- {name}: {c['exact']} of {c['cases_either_gave']} cases")
    lines += [
        "",
        "## Practitioner priority against the rubric",
        "",
        "| Annotator | Cases | Same | Practitioner higher | Practitioner lower |",
        "|---|---|---|---|---|",
    ]
    for name, p in report["practitioner_vs_rubric"].items():
        lines.append(
            f"| {name} | {p['cases']} | {p['same']} | "
            f"{p['practitioner_higher']} | {p['practitioner_lower']} |"
        )
    skipped = {a: s for a, s in report["skipped_language"].items() if s}
    if skipped:
        lines += ["", f"Skipped for language (left out): {skipped}"]
    return "\n".join(lines) + "\n"


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("imported", type=Path, nargs="+", help="one JSONL per annotator")
    parser.add_argument("--seed", type=int, default=20261114)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    records = {}
    for path in args.imported:
        rows = _load(path)
        records[rows[0]["annotator"] if rows else path.stem] = rows
    report = Agreement(records, args.seed).report()
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "agreement.json").write_text(json.dumps(report, indent=2) + "\n", "utf-8")
    markdown = to_markdown(report)
    (args.out / "agreement.md").write_text(markdown, encoding="utf-8", newline="\n")
    print(markdown)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
