"""Human-review replay: machine output next to the operator's decision (design 10.2, mode 4)."""

from fastapi.testclient import TestClient

from ntip.api import create_app
from ntip.api.settings import Settings
from ntip.pipeline import Pipeline
from ntip.review_replay import compare_reviews
from ntip.schema.review import ReviewDecision
from ntip.store import InMemoryEventStore

P0_CALL = "My father is not breathing at 12 Oak Street."
LOW_CALL = "Someone scratched my car outside 9 Birch Lane, nobody is hurt."


def review(pipeline: Pipeline, text: str, decision: ReviewDecision, **kwargs: object) -> str:
    result = pipeline.ingest(text)
    pipeline.review(result.incident_id, assessment_id=result.assessment.assessment_id,
                    reviewer_id="op_1", decision=decision, **kwargs)  # type: ignore[arg-type]  # fmt: skip
    return result.incident_id


def test_each_decision_is_shown_next_to_the_machine_output() -> None:
    store = InMemoryEventStore()
    pipeline = Pipeline(store=store)
    confirmed = review(pipeline, P0_CALL, ReviewDecision.CONFIRM)
    lowered = review(pipeline, P0_CALL, ReviewDecision.OVERRIDE_PRIORITY, override_priority="P2",
                     reason="Patient breathing on arrival of a neighbour (synthetic).")  # fmt: skip
    raised = review(pipeline, LOW_CALL, ReviewDecision.OVERRIDE_PRIORITY, override_priority="P1",
                    reason="Caller sounds injured (synthetic).")  # fmt: skip
    noted = review(pipeline, LOW_CALL, ReviewDecision.NOTE, reason="Called back, no answer.")
    pipeline.ingest(LOW_CALL)  # never reviewed: not part of the comparison

    comparison = compare_reviews(store, tenant_id="default")
    by_incident = {c.incident_id: c for c in comparison.cases}
    assert set(by_incident) == {confirmed, lowered, raised, noted}
    assert by_incident[confirmed].agreement == "confirmed"
    assert (by_incident[lowered].machine_priority, by_incident[lowered].human_priority) == ("P0", "P2")
    assert by_incident[lowered].agreement == "lowered"
    assert by_incident[lowered].reason.startswith("Patient breathing")  # type: ignore[union-attr]
    assert by_incident[raised].agreement == "raised"
    assert by_incident[noted].agreement == "noted"
    assert by_incident[confirmed].machine_reasons  # the rules that fired are shown
    assert comparison.by_agreement["lowered"] == 1
    assert "not ground truth" in comparison.note


def test_a_note_does_not_hide_an_earlier_judgement() -> None:
    store = InMemoryEventStore()
    pipeline = Pipeline(store=store)
    result = pipeline.ingest(P0_CALL)
    for decision, extra in ((ReviewDecision.CONFIRM, {}), (ReviewDecision.NOTE, {"reason": "ok"})):
        pipeline.review(result.incident_id, assessment_id=result.assessment.assessment_id,
                        reviewer_id="op_1", decision=decision, **extra)  # type: ignore[arg-type]  # fmt: skip
    [case] = compare_reviews(store, tenant_id="default").cases
    assert case.agreement == "confirmed"


def test_the_comparison_is_tenant_scoped_and_served_by_the_api() -> None:
    store = InMemoryEventStore()
    pipeline = Pipeline(store=store)
    review(pipeline, P0_CALL, ReviewDecision.CONFIRM)
    other = pipeline.ingest(P0_CALL, tenant_id="psap-b")
    pipeline.review(other.incident_id, assessment_id=other.assessment.assessment_id,
                    reviewer_id="op_2", decision=ReviewDecision.CONFIRM)  # fmt: skip
    assert compare_reviews(store, tenant_id="default").reviewed_assessments == 1

    client = TestClient(create_app(store=store, settings=Settings()))
    body = client.get("/v1/review-comparison").json()
    assert body["reviewed_assessments"] == 1
    assert body["cases"][0]["agreement"] == "confirmed"
