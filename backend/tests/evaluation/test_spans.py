"""Evidence-span and cue-status metrics."""

from typing import Any

from ntip.evaluation.dataset import EvalCase
from ntip.evaluation.runner import evaluate_case, rule_codes, rules_baseline, score
from ntip.evaluation.spans import Mention, gold_mentions, score_spans

MESSAGE = "My father is not breathing and there is no fire. We are at 9 Pine Road."


def _span(text: str) -> dict[str, Any]:
    start = MESSAGE.index(text)
    return {"message": 0, "start": start, "end": start + len(text), "text": text}


def _case(annotations: list[dict[str, Any]] | None) -> EvalCase:
    labels: dict[str, Any] = {
        "domain": "ems",
        "severity": "critical",
        "priority": "P0",
        "location": "present",
    }
    if annotations is None:
        labels["cues"] = ["NOT_BREATHING"]
    else:
        labels["cue_annotations"] = annotations
    return EvalCase.model_validate(
        {
            "case_id": "c1",
            "split": "dev",
            "family": "f",
            "label_source": "generator",
            "messages": [MESSAGE],
            "labels": labels,
        }
    )


GOLD = [
    {"code": "NOT_BREATHING", "status": "affirmed", "evidence": _span("is not breathing")},
    {"code": "FIRE_REPORTED", "status": "negated", "evidence": _span("no fire")},
]


def test_cases_without_spans_are_not_scored() -> None:
    assert gold_mentions(_case(None)) is None
    assert score_spans([(_case(None), [])], {"NOT_BREATHING"}, seed=1) is None


def test_exact_overlap_and_status() -> None:
    start = MESSAGE.index("not breathing")
    predicted = [
        # Overlaps but is shorter than the label: overlap, not exact.
        Mention("NOT_BREATHING", "affirmed", 0, start, start + len("not breathing")),
        # Exact span, wrong status.
        Mention(
            "FIRE_REPORTED",
            "affirmed",
            0,
            MESSAGE.index("no fire"),
            MESSAGE.index("no fire") + len("no fire"),
        ),
        # Not in the labels at all.
        Mention("SMOKE_REPORTED", "affirmed", 0, 0, 2),
    ]
    result = score_spans(
        [(_case(GOLD), predicted)], {"NOT_BREATHING", "FIRE_REPORTED", "SMOKE_REPORTED"}, seed=1
    )
    assert result is not None
    assert (result["gold_mentions"], result["predicted_mentions"]) == (2, 3)
    assert result["span_exact"]["tp"] == 1 and result["span_exact"]["recall"] == 0.5
    assert result["span_overlap"]["tp"] == 2 and result["span_overlap"]["recall"] == 1.0
    assert result["span_overlap"]["precision"] == round(2 / 3, 4)
    assert result["status_accuracy"]["numerator"] == 1
    assert result["status_confusion"]["negated"]["affirmed"] == 1


def test_codes_outside_the_evaluated_set_are_ignored() -> None:
    result = score_spans([(_case(GOLD), [])], {"NOT_BREATHING"}, seed=1)
    assert result is not None and result["gold_mentions"] == 1


def test_the_rules_are_scored_end_to_end() -> None:
    relevant = rule_codes()
    result = evaluate_case(_case(GOLD), rules_baseline(), relevant)
    statuses = {m.code: m.status for m in result.mentions}
    assert statuses["NOT_BREATHING"] == "affirmed"
    assert statuses["FIRE_REPORTED"] == "negated"
    metrics = score([result], seed=1, critical=set())
    assert metrics["spans"]["span_overlap"]["recall"] == 1.0
    assert metrics["spans"]["status_accuracy"]["value"] == 1.0
    # Author-labelled cases without spans get no span section.
    plain = score([evaluate_case(_case(None), rules_baseline(), relevant)], seed=1, critical=set())
    assert "spans" not in plain
