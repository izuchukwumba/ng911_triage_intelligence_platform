"""Run a system over labelled cases and score it.

The system under test is any callable from messages to (Incident, Assessment).
The rules baseline B0 is the default; ML extractors plug in the same way.
"""

import platform
import subprocess
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ntip.evaluation.dataset import Dataset, EvalCase, Split
from ntip.evaluation.metrics import PRF, bootstrap_metric, confusion, rate
from ntip.evaluation.spans import Mention, predicted_mentions, score_spans
from ntip.parser.parser import PARSER_ID, PARSER_VERSION, parse
from ntip.schema.advisory import Assessment, SeverityBand
from ntip.schema.base import SCHEMA_VERSION, FactStatus, sha256_digest
from ntip.schema.canonical import ConflictKind, Incident, Polarity, Temporality
from ntip.schema.source import SourceEvent
from ntip.triage.engine import ENGINE_ID, ENGINE_VERSION, assess
from ntip.triage.ruleset import DEFAULT_RULESET, load_ruleset, ruleset_digest

REPO_ROOT = Path(__file__).resolve().parents[4]
FIXED_TIME = datetime(2026, 1, 1, tzinfo=UTC)  # evaluation must not depend on the clock

System = Callable[[list[str]], tuple[Incident, Assessment]]


def rules_baseline(ruleset_name: str = DEFAULT_RULESET) -> System:
    """B0: the deterministic rules parser and triage engine."""
    ruleset = load_ruleset(ruleset_name)

    def run(messages: list[str]) -> tuple[Incident, Assessment]:
        sources = [
            SourceEvent.from_text(
                source_event_id=f"evt_{i}", incident_id="eval", received_at=FIXED_TIME, text=m
            )
            for i, m in enumerate(messages, 1)
        ]
        incident = parse(sources, derived_at=FIXED_TIME)
        return incident, assess(
            incident, assessment_id="eval", assessed_at=FIXED_TIME, ruleset=ruleset
        )

    return run


def rule_codes(ruleset_name: str = DEFAULT_RULESET) -> set[str]:
    return {code for rule in load_ruleset(ruleset_name).rules for code in rule.all_of}


def critical_codes(ruleset_name: str = DEFAULT_RULESET) -> set[str]:
    return {
        code
        for rule in load_ruleset(ruleset_name).rules
        if rule.severity is SeverityBand.CRITICAL and len(rule.all_of) == 1
        for code in rule.all_of
    }


@dataclass
class CaseResult:
    case: EvalCase
    predicted_cues: set[str]
    predicted_domain: str
    predicted_severity: str
    predicted_priority: str | None
    predicted_location: str
    predicted_victims: int | str | None
    errors: list[str] = field(default_factory=list)
    # Every cue the system mentioned, with status and quoted span (for span metrics).
    mentions: list[Mention] = field(default_factory=list)
    relevant: frozenset[str] = frozenset()


def _location_status(incident: Incident) -> str:
    if any(c.kind is ConflictKind.LOCATION_MISMATCH for c in incident.conflicts):
        return "conflicting"
    return "present" if incident.locations else "missing"


def _victims(incident: Incident) -> int | str | None:
    fact = incident.victim_count
    if fact.status is FactStatus.REPORTED:
        return fact.value
    if fact.status in {FactStatus.UNKNOWN, FactStatus.CONFLICTING}:
        return "unknown"
    return None


def _priority_rank(p: str | None) -> int:
    return int(p[1]) if p else 9


def evaluate_case(case: EvalCase, system: System, relevant: set[str]) -> CaseResult:
    incident, assessment = system(case.messages)
    live = {
        o.code
        for o in incident.observations
        if o.polarity is not Polarity.NEGATED and o.temporality is Temporality.CURRENT
    }
    result = CaseResult(
        case=case,
        predicted_cues=live & relevant,
        predicted_domain=incident.classification.domain,
        predicted_severity=assessment.severity_band,
        predicted_priority=assessment.advisory_priority,
        predicted_location=_location_status(incident),
        predicted_victims=_victims(incident),
        mentions=predicted_mentions(
            incident, [f"evt_{i}" for i in range(1, len(case.messages) + 1)]
        ),
        relevant=frozenset(relevant),
    )
    labels = case.labels
    expected = set(labels.cues)
    if missing := expected - result.predicted_cues:
        result.errors.append(f"missed cues {sorted(missing)}")
    if extra := result.predicted_cues - expected:
        result.errors.append(f"spurious cues {sorted(extra)}")
    if leaked := set(labels.absent_cues) & live:
        result.errors.append(f"denied/past cues treated as live {sorted(leaked)}")
    if result.predicted_priority != labels.priority:
        result.errors.append(f"priority {result.predicted_priority} != {labels.priority}")
    if result.predicted_domain != labels.domain:
        result.errors.append(f"domain {result.predicted_domain} != {labels.domain}")
    if result.predicted_location != labels.location:
        result.errors.append(f"location {result.predicted_location} != {labels.location}")
    if result.predicted_victims != labels.victim_count:
        result.errors.append(f"victims {result.predicted_victims!r} != {labels.victim_count!r}")
    return result


def _git_commit() -> str:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "HEAD"], capture_output=True, text=True, cwd=REPO_ROOT, check=True
        )
        return out.stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def manifest(dataset: Dataset, splits: Sequence[Split], seed: int, system: str) -> dict[str, Any]:
    """Everything needed to reproduce a run (design v1.2, sections 3A.9 and 10.3)."""
    lock = REPO_ROOT / "backend" / "uv.lock"
    return {
        "system": system,
        "git_commit": _git_commit(),
        "dataset": {"path": dataset.path, "digest": dataset.digest, "splits": list(splits)},
        "parser": f"{PARSER_ID}-{PARSER_VERSION}",
        "engine": f"{ENGINE_ID}-{ENGINE_VERSION}",
        "ruleset": {"name": DEFAULT_RULESET, "digest": ruleset_digest(DEFAULT_RULESET)},
        "schema_version": SCHEMA_VERSION,
        "python": platform.python_version(),
        "lockfile_digest": (
            sha256_digest(lock.read_text("utf-8").replace("\r\n", "\n")) if lock.exists() else None
        ),
        "seed": seed,
        "bootstrap": "percentile, 2000 resamples, 95%",
    }


def _prf(results: Sequence[CaseResult], code: str | None = None) -> PRF:
    tp = fp = fn = 0
    for r in results:
        expected = set(r.case.labels.cues)
        predicted = r.predicted_cues
        if code is not None:
            expected &= {code}
            predicted = predicted & {code}
        tp += len(expected & predicted)
        fp += len(predicted - expected)
        fn += len(expected - predicted)
    return PRF(tp, fp, fn)


def score(results: Sequence[CaseResult], *, seed: int, critical: set[str]) -> dict[str, Any]:
    labels_seen = sorted({c for r in results for c in r.case.labels.cues} | {
        c for r in results for c in r.predicted_cues})  # fmt: skip

    critical_outcomes = [
        code in r.predicted_cues for r in results for code in r.case.labels.cues if code in critical
    ]
    expected_p0 = [r for r in results if r.case.labels.priority == "P0"]
    under = [
        _priority_rank(r.predicted_priority) > _priority_rank(r.case.labels.priority)
        for r in results
    ]
    over = [
        _priority_rank(r.predicted_priority) < _priority_rank(r.case.labels.priority)
        for r in results
    ]

    def micro_f1(items: Sequence[object]) -> float | None:
        return _prf([i for i in items if isinstance(i, CaseResult)]).f1

    f1_low, f1_high = bootstrap_metric(list(results), micro_f1, seed=seed)
    micro = _prf(results)

    def r(outcomes: Sequence[bool]) -> dict[str, Any]:
        return rate(outcomes, seed=seed).as_dict()

    spans = score_spans(
        [(x.case, x.mentions) for x in results],
        set().union(*(x.relevant for x in results)) if results else set(),
        seed=seed,
    )
    return {
        **({"spans": spans} if spans is not None else {}),
        "cases": len(results),
        "cue_extraction": {
            "micro": {
                **micro.as_dict(),
                "f1_ci95": [None if v is None else round(v, 4) for v in (f1_low, f1_high)],
            },
            "per_code": {code: _prf(results, code).as_dict() for code in labels_seen},
            "denied_or_past_cues_treated_as_live": sum(
                len(set(x.case.labels.absent_cues) & x.predicted_cues) for x in results
            ),
        },
        "critical_cue_sensitivity": r(critical_outcomes),
        "critical_undertriage": {
            **r([r_.predicted_priority != "P0" for r_ in expected_p0]),
            "cases": [x.case.case_id for x in expected_p0 if x.predicted_priority != "P0"],
        },
        "priority_exact": r([x.predicted_priority == x.case.labels.priority for x in results]),
        "undertriage": r(under),
        "overtriage": r(over),
        "severity_exact": r([x.predicted_severity == x.case.labels.severity for x in results]),
        "domain_accuracy": r([x.predicted_domain == x.case.labels.domain for x in results]),
        "location_accuracy": r([x.predicted_location == x.case.labels.location for x in results]),
        "victim_count_accuracy": r(
            [x.predicted_victims == x.case.labels.victim_count for x in results]
        ),
        "priority_confusion": confusion(
            [(x.case.labels.priority, x.predicted_priority or "none") for x in results],
            ["P0", "P1", "P2", "P3", "P4", "none"],
        ),
        "failures": {x.case.case_id: x.errors for x in results if x.errors},
    }


def evaluate(
    dataset: Dataset,
    splits: Sequence[Split],
    *,
    seed: int = 20261109,
    system: System | None = None,
    system_name: str = "B0-rules",
) -> dict[str, Any]:
    run = system or rules_baseline()
    relevant = rule_codes()
    results = [evaluate_case(case, run, relevant) for case in dataset.split(*splits)]
    return {
        "manifest": manifest(dataset, splits, seed, system_name),
        "metrics": score(results, seed=seed, critical=critical_codes()),
    }
