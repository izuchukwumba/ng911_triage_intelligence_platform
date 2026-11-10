from datetime import UTC, datetime, timedelta
from itertools import count
from typing import Any

import pytest

from ntip.pipeline import IdempotencyConflict, IncidentState, Pipeline
from ntip.schema.advisory import AssessmentStatus, ReviewAction
from ntip.schema.base import sha256_digest
from ntip.schema.canonical import Incident
from ntip.schema.review import ReviewDecision
from ntip.store import InMemoryEventStore, UnknownIncident
from ntip.triage.engine import ENGINE_VERSION


def make_pipeline(**overrides: Any) -> Pipeline:
    ticks = count()
    ids = count(1)
    defaults: dict[str, Any] = {
        "store": InMemoryEventStore(),
        "clock": lambda: datetime(2026, 11, 9, 12, 0, tzinfo=UTC) + timedelta(seconds=next(ticks)),
        "new_id": lambda prefix: f"{prefix}_{next(ids)}",
    }
    return Pipeline(**{**defaults, **overrides})


class TestIngest:
    def test_stores_source_incident_assessment_and_audit_trail(self) -> None:
        pipeline = make_pipeline()
        result = pipeline.ingest("He is not breathing at 12 Oak Street.", correlation_id="req_x")

        store = pipeline.store
        assert [s.text for s in store.source_events(result.incident_id)] == [
            "He is not breathing at 12 Oak Street."
        ]
        assert len(store.incident_versions(result.incident_id)) == 1
        assert result.assessment.advisory_priority == "P0"
        events = store.audit_events(result.incident_id)
        assert [e.event_type for e in events] == [
            "source.received",
            "incident.parsed",
            "triage.assessed",
        ]
        assert {e.correlation_id for e in events} == {"req_x"}

    def test_audit_events_reference_their_subjects_by_digest(self) -> None:
        pipeline = make_pipeline()
        result = pipeline.ingest("Fire at 12 Oak Street.")
        [received, _, assessed] = pipeline.store.audit_events(result.incident_id)
        [source] = pipeline.store.source_events(result.incident_id)
        assert received.subject_digest == sha256_digest(source.model_dump_json())
        assert assessed.subject_id == result.assessment.assessment_id
        assert assessed.component_version == f"triage-engine-{ENGINE_VERSION}"

    def test_follow_up_message_reprocesses_the_whole_conversation(self) -> None:
        pipeline = make_pipeline()
        first = pipeline.ingest("There is smoke at 12 Oak Street.")
        second = pipeline.ingest("Now people are trapped inside.", incident_id=first.incident_id)

        assert second.incident_id == first.incident_id
        sources = pipeline.store.source_events(first.incident_id)
        assert sources[1].supersedes == sources[0].source_event_id
        assert first.assessment.severity_band == "elevated"
        assert second.assessment.severity_band == "critical"
        # History is kept: both assessments and both incident versions remain.
        assert len(pipeline.store.assessments(first.incident_id)) == 2
        assert len(pipeline.store.incident_versions(first.incident_id)) == 2

    def test_follow_up_for_unknown_incident_is_rejected(self) -> None:
        with pytest.raises(UnknownIncident):
            make_pipeline().ingest("Hello", incident_id="inc_missing")


class TestIdempotency:
    def test_retry_with_same_key_returns_the_original_result(self) -> None:
        pipeline = make_pipeline()
        first = pipeline.ingest("Fire at 12 Oak Street.", idempotency_key="k1")
        retry = pipeline.ingest("Fire at 12 Oak Street.", idempotency_key="k1")

        assert retry.idempotent_replay
        assert retry.incident_id == first.incident_id
        assert retry.assessment == first.assessment
        assert len(pipeline.store.source_events(first.incident_id)) == 1

    def test_same_key_with_different_body_is_a_conflict(self) -> None:
        pipeline = make_pipeline()
        pipeline.ingest("Fire at 12 Oak Street.", idempotency_key="k1")
        with pytest.raises(IdempotencyConflict):
            pipeline.ingest("Something else entirely.", idempotency_key="k1")


class TestFailSafe:
    def test_parser_crash_keeps_the_source_and_demands_urgent_review(self) -> None:
        def broken_parser(*_: Any, **__: Any) -> Incident:
            raise RuntimeError("boom")

        pipeline = make_pipeline(parser=broken_parser)
        result = pipeline.ingest("He is not breathing at 12 Oak Street.")

        assert result.assessment.status is AssessmentStatus.PROCESSING_FAILED
        assert result.assessment.advisory_priority is None
        assert ReviewAction.URGENT_HUMAN_REVIEW in result.assessment.review_actions
        assert result.assessment.failure_reason == "RuntimeError during processing"
        store = pipeline.store
        assert len(store.source_events(result.incident_id)) == 1
        assert store.incident_versions(result.incident_id) == []
        assert [e.event_type for e in store.audit_events(result.incident_id)] == [
            "source.received",
            "processing.failed",
        ]
        assert pipeline.view(result.incident_id).state is IncidentState.PROCESSING_FAILED


class TestReviewAndView:
    def test_override_is_recorded_separately_and_wins_in_the_view(self) -> None:
        pipeline = make_pipeline()
        result = pipeline.ingest("I twisted my ankle at 99 Cedar Lane.")
        assert pipeline.view(result.incident_id).state is IncidentState.AWAITING_REVIEW

        pipeline.review(
            result.incident_id,
            assessment_id=result.assessment.assessment_id,
            reviewer_id="op_7",
            decision=ReviewDecision.OVERRIDE_PRIORITY,
            override_priority="P1",
            reason="Caller is elderly and alone",
        )

        view = pipeline.view(result.incident_id)
        assert view.state is IncidentState.REVIEWED
        assert view.effective_priority == "P1"
        # The machine's assessment is untouched.
        assert view.assessment == result.assessment
        assert view.assessment.advisory_priority == "P3"
        assert pipeline.store.audit_events(result.incident_id)[-1].event_type == (
            "triage.overridden"
        )
        assert pipeline.store.audit_events(result.incident_id)[-1].actor.actor_id == "op_7"

    def test_review_of_an_assessment_from_another_incident_is_rejected(self) -> None:
        pipeline = make_pipeline()
        a = pipeline.ingest("Fire at 12 Oak Street.")
        b = pipeline.ingest("Smoke at 5 Elm Road.")
        with pytest.raises(UnknownIncident):
            pipeline.review(
                a.incident_id,
                assessment_id=b.assessment.assessment_id,
                reviewer_id="op_7",
                decision=ReviewDecision.CONFIRM,
            )

    def test_new_message_reopens_review(self) -> None:
        pipeline = make_pipeline()
        result = pipeline.ingest("Smoke at 12 Oak Street.")
        pipeline.review(
            result.incident_id,
            assessment_id=result.assessment.assessment_id,
            reviewer_id="op_7",
            decision=ReviewDecision.CONFIRM,
        )
        pipeline.ingest("Now it is spreading.", incident_id=result.incident_id)
        assert pipeline.view(result.incident_id).state is IncidentState.AWAITING_REVIEW

    def test_unknown_incident(self) -> None:
        with pytest.raises(UnknownIncident):
            make_pipeline().view("inc_missing")


class TestClosure:
    def test_closing_an_incident(self) -> None:
        pipeline = make_pipeline()
        result = pipeline.ingest("I twisted my ankle at 99 Cedar Lane.")
        pipeline.review(
            result.incident_id,
            assessment_id=result.assessment.assessment_id,
            reviewer_id="op_7",
            decision=ReviewDecision.CLOSE,
        )
        assert pipeline.view(result.incident_id).state is IncidentState.CLOSED
        assert pipeline.store.audit_events(result.incident_id)[-1].event_type == "incident.closed"

    def test_a_new_message_reopens_a_closed_incident(self) -> None:
        pipeline = make_pipeline()
        result = pipeline.ingest("Smoke at 12 Oak Street.")
        pipeline.review(
            result.incident_id,
            assessment_id=result.assessment.assessment_id,
            reviewer_id="op_7",
            decision=ReviewDecision.CLOSE,
        )
        pipeline.ingest("Now people are trapped inside.", incident_id=result.incident_id)
        view = pipeline.view(result.incident_id)
        assert view.state is IncidentState.AWAITING_REVIEW
        assert view.assessment.severity_band == "critical"

    def test_a_failed_incident_can_be_closed_after_manual_handling(self) -> None:
        def broken(*_: Any, **__: Any) -> Incident:
            raise RuntimeError("boom")

        pipeline = make_pipeline(parser=broken)
        result = pipeline.ingest("anything")
        pipeline.review(
            result.incident_id,
            assessment_id=result.assessment.assessment_id,
            reviewer_id="op_7",
            decision=ReviewDecision.CLOSE,
            reason="Handled manually from the transcript",
        )
        assert pipeline.view(result.incident_id).state is IncidentState.CLOSED
