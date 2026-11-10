"""Human-review replay (design v1.2, section 10.2, mode 4).

Puts each machine assessment that a person reviewed next to what that person
decided: confirmed it, overrode its priority (up or down), corrected the
classification, escalated it, or only added a note. Nothing here changes any
record, and an operator's decision is reported as a human judgement, never as
ground truth: it is not used to score or retrain anything automatically.
"""

from collections import Counter
from enum import StrEnum

from pydantic import BaseModel, ConfigDict

from ntip.schema.review import HumanReview, ReviewDecision
from ntip.store import EventStore

NOTE = (
    "Operator decisions are human judgements recorded for review. They are not ground "
    "truth and are never used to score or retrain a model automatically (design v1.2, 10.2)."
)


class Agreement(StrEnum):
    CONFIRMED = "confirmed"
    RAISED = "raised"  # the operator made it more urgent
    LOWERED = "lowered"  # the operator made it less urgent
    OVERRIDE_SAME = "override_same"  # an override to the machine's own priority
    RECLASSIFIED = "reclassified"
    ESCALATED = "escalated"
    CLOSED = "closed"
    NOTED = "noted"  # a note only: no judgement on the output


class _Out(BaseModel):
    model_config = ConfigDict(json_schema_serialization_defaults_required=True)


class ReviewedCase(_Out):
    incident_id: str
    assessment_id: str
    ruleset_version: str
    machine_priority: str | None
    machine_severity: str
    machine_reasons: list[str]
    decision: str
    human_priority: str | None
    corrected_domain: str | None
    reason: str | None
    reviewer_id: str
    agreement: Agreement


class ReviewComparison(_Out):
    note: str
    reviewed_assessments: int
    by_agreement: dict[str, int]
    cases: list[ReviewedCase]


def _rank(priority: str | None) -> int:
    return int(priority[1]) if priority else -1


def _agreement(machine: str | None, review: HumanReview) -> Agreement:
    match review.decision:
        case ReviewDecision.CONFIRM:
            return Agreement.CONFIRMED
        case ReviewDecision.OVERRIDE_PRIORITY:
            human = review.override_priority.value if review.override_priority else None
            if _rank(human) < _rank(machine):
                return Agreement.RAISED
            if _rank(human) > _rank(machine):
                return Agreement.LOWERED
            return Agreement.OVERRIDE_SAME
        case ReviewDecision.CORRECT_CLASSIFICATION:
            return Agreement.RECLASSIFIED
        case ReviewDecision.ESCALATE:
            return Agreement.ESCALATED
        case ReviewDecision.CLOSE:
            return Agreement.CLOSED
        case _:
            return Agreement.NOTED


def compare_reviews(store: EventStore, *, tenant_id: str, limit: int = 1000) -> ReviewComparison:
    """The latest decision on every reviewed assessment of one tenant, newest first."""
    _, incidents = store.list_incidents(limit=limit, offset=0, tenant_id=tenant_id)
    cases: list[ReviewedCase] = []
    for summary in incidents:
        latest: dict[str, HumanReview] = {}
        for review in store.reviews(summary.incident_id):
            # A note says nothing about the output; any other decision wins.
            current = latest.get(review.assessment_id)
            if current is None or review.decision is not ReviewDecision.NOTE:
                latest[review.assessment_id] = review
        for assessment_id, review in latest.items():
            assessment = store.assessment(assessment_id)
            if assessment is None:
                continue
            machine = assessment.advisory_priority.value if assessment.advisory_priority else None
            cases.append(
                ReviewedCase(
                    incident_id=summary.incident_id,
                    assessment_id=assessment_id,
                    ruleset_version=assessment.ruleset_version,
                    machine_priority=machine,
                    machine_severity=assessment.severity_band.value,
                    machine_reasons=[r.reason_code for r in assessment.reasons],
                    decision=review.decision.value,
                    human_priority=review.override_priority.value
                    if review.override_priority
                    else None,
                    corrected_domain=(
                        review.corrected_classification.domain.value
                        if review.corrected_classification
                        else None
                    ),
                    reason=review.reason,
                    reviewer_id=review.reviewer_id,
                    agreement=_agreement(machine, review),
                )
            )
    counts = Counter(c.agreement.value for c in cases)
    return ReviewComparison(
        note=NOTE,
        reviewed_assessments=len(cases),
        by_agreement={a.value: counts.get(a.value, 0) for a in Agreement},
        cases=cases,
    )
