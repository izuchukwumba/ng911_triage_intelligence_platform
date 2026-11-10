from datetime import UTC, datetime, timedelta

import pytest

from ntip.parser.parser import parse
from ntip.schema.audit import Actor, ActorKind, AuditEvent, AuditEventType
from ntip.schema.base import sha256_digest
from ntip.schema.review import HumanReview, ReviewDecision
from ntip.schema.source import SourceEvent
from ntip.store import DuplicateRecord, EventStore, IdempotencyClaim
from ntip.triage.engine import assess

T0 = datetime(2026, 11, 9, 12, 0, tzinfo=UTC)


def source(incident_id: str, n: int, text: str, minutes: int = 0) -> SourceEvent:
    return SourceEvent.from_text(
        source_event_id=f"{incident_id}_evt_{n}",
        incident_id=incident_id,
        received_at=T0 + timedelta(minutes=minutes),
        text=text,
    )


def audit(incident_id: str, n: int, kind: AuditEventType, subject: str) -> AuditEvent:
    return AuditEvent(
        event_id=f"{incident_id}_ae_{n}",
        incident_id=incident_id,
        occurred_at=T0,
        event_type=kind,
        actor=Actor(kind=ActorKind.SERVICE, actor_id="pipeline"),
        correlation_id="req_1",
        subject_id=subject,
        subject_digest=sha256_digest(subject),
    )


def ingest(store: EventStore, incident_id: str, text: str, minutes: int = 0) -> None:
    src = source(incident_id, 1, text, minutes)
    incident = parse([src], derived_at=src.received_at)
    assessment = assess(incident, assessment_id=f"{incident_id}_a1", assessed_at=src.received_at)
    store.append(
        [
            src,
            incident,
            assessment,
            audit(incident_id, 1, AuditEventType.SOURCE_RECEIVED, src.source_event_id),
            audit(incident_id, 2, AuditEventType.TRIAGE_ASSESSED, assessment.assessment_id),
        ]
    )


def test_round_trips_every_record_type(store: EventStore) -> None:
    ingest(store, "inc_1", "He is not breathing at 12 Oak Street.")
    review = HumanReview(
        review_id="rev_1",
        incident_id="inc_1",
        assessment_id="inc_1_a1",
        reviewer_id="op_1",
        reviewed_at=T0,
        decision=ReviewDecision.CONFIRM,
    )
    store.append([review])

    [src] = store.source_events("inc_1")
    assert src.text == "He is not breathing at 12 Oak Street."
    assert store.incident_versions("inc_1")[0].observations
    assert store.assessments("inc_1")[0].severity_band == "critical"
    assert store.assessment("inc_1_a1") == store.assessments("inc_1")[0]
    assert store.reviews("inc_1") == [review]
    assert [e.event_type for e in store.audit_events("inc_1")] == [
        "source.received",
        "triage.assessed",
    ]


def test_duplicate_identity_rejects_the_whole_batch(store: EventStore) -> None:
    ingest(store, "inc_1", "Fire at 12 Oak Street.")
    fresh = source("inc_1", 2, "It is spreading.")
    duplicate = source("inc_1", 1, "Fire at 12 Oak Street.")
    with pytest.raises(DuplicateRecord):
        store.append([fresh, duplicate])
    # Nothing from the failed batch was written.
    assert len(store.source_events("inc_1")) == 1


def test_records_come_back_in_append_order(store: EventStore) -> None:
    ingest(store, "inc_1", "Smoke at 12 Oak Street.")
    store.append([source("inc_1", 2, "Now there are flames."), source("inc_1", 3, "Trapped.")])
    assert [s.source_event_id for s in store.source_events("inc_1")] == [
        "inc_1_evt_1",
        "inc_1_evt_2",
        "inc_1_evt_3",
    ]


def test_idempotency_claims(store: EventStore) -> None:
    claim = IdempotencyClaim(
        key="req-123", request_digest=sha256_digest("body"), incident_id="inc_1", claimed_at=T0
    )
    store.append([claim])
    assert store.idempotency_claim("req-123") == claim
    assert store.idempotency_claim("other") is None
    with pytest.raises(DuplicateRecord):
        store.append([claim])


def test_list_incidents_newest_first_with_latest_assessment(store: EventStore) -> None:
    ingest(store, "inc_old", "Fire at 12 Oak Street.", minutes=0)
    ingest(store, "inc_new", "He is not breathing at 5 Elm Road.", minutes=5)
    total, page = store.list_incidents(limit=10, offset=0)
    assert total == 2
    assert [s.incident_id for s in page] == ["inc_new", "inc_old"]
    assert page[0].latest_assessment is not None
    assert page[0].latest_assessment.advisory_priority == "P0"

    total, page = store.list_incidents(limit=1, offset=1)
    assert (total, [s.incident_id for s in page]) == (2, ["inc_old"])


def test_ping(store: EventStore) -> None:
    assert store.ping()


def test_replay_runs_round_trip(store: EventStore) -> None:
    from itertools import count

    from ntip.replay import run_replay

    ingest(store, "inc_1", "He is not breathing at 12 Oak Street.")
    ids = count(1)
    run = run_replay(
        store,
        incident_ids=["inc_1"],
        candidate_ruleset="research-1.0.0",
        requested_by="analyst_1",
        clock=lambda: T0,
        new_id=lambda prefix: f"{prefix}_{next(ids)}",
        correlation_id="req_r",
    )
    assert run.summary.reproducible == 1
    assert store.replay_run(run.run_id) == run
    assert store.replay_runs(limit=10) == [run]
    assert store.audit_events("inc_1")[-1].event_type == "incident.replayed"


def test_model_outputs_round_trip(store: EventStore) -> None:
    from ntip.ml.contract import InferenceMessage, InferenceRequest, ModelOutput
    from ntip.schema.canonical import InferenceMode

    output = ModelOutput(
        output_id="mo_1",
        incident_id="inc_1",
        recorded_at=T0,
        mode=InferenceMode.ML_SHADOW,
        request=InferenceRequest(
            request_id="r1",
            incident_id="inc_1",
            messages=[InferenceMessage(source_event_id="e1", text="Fire.")],
        ),
        response=None,
        error="timeout",
    )
    store.append([output])
    assert store.model_outputs("inc_1") == [output]


def test_interop_receipts_round_trip_scoped_by_tenant(store: EventStore) -> None:
    from ntip.interop.receipts import InteropReceipt, ReceiptStatus

    def receipt(receipt_id: str, tenant: str) -> InteropReceipt:
        return InteropReceipt(
            receipt_id=receipt_id,
            received_at=T0,
            tenant_id=tenant,
            profile_id="p",
            adapter_version="a",
            schema_artifact_digest=sha256_digest("schema"),
            status=ReceiptStatus.QUARANTINED,
            payload="{}",
            payload_digest=sha256_digest("{}"),
            source_event_id="urn:x",
        )

    store.append([receipt("r1", "tenant-a"), receipt("r2", "tenant-b")])
    assert store.interop_receipt("r1") == receipt("r1", "tenant-a")
    assert [r.receipt_id for r in store.interop_receipts("tenant-a", "urn:x")] == ["r1"]


def test_expectation_rejects_a_stale_write(store: EventStore) -> None:
    from ntip.store import ConcurrentModification, Expectation

    ingest(store, "inc_1", "Smoke at 12 Oak Street.")
    first = source("inc_1", 2, "It is spreading.")
    store.append([first], expect=Expectation("inc_1", 1))
    stale = source("inc_1", 3, "People are trapped.")
    with pytest.raises(ConcurrentModification):
        store.append([stale], expect=Expectation("inc_1", 1))  # read before `first` was written
    assert len(store.source_events("inc_1")) == 2


def test_incidents_and_replay_runs_are_filtered_by_tenant(store: EventStore) -> None:
    from itertools import count

    from ntip.replay import run_replay

    ingest(store, "inc_default", "Smoke from the shed at 3 Pine Road.")
    other = SourceEvent.from_text(
        source_event_id="inc_b_evt_1",
        incident_id="inc_b",
        received_at=T0 + timedelta(minutes=1),
        text="He is not breathing at 12 Oak Street.",
        tenant_id="psap-b",
    )
    store.append([other])

    assert store.tenant_of("inc_default") == "default"
    assert store.tenant_of("inc_b") == "psap-b"
    assert store.tenant_of("inc_missing") is None
    total, page = store.list_incidents(limit=10, offset=0, tenant_id="psap-b")
    assert (total, [s.incident_id for s in page]) == (1, ["inc_b"])
    assert store.list_incidents(limit=10, offset=0)[0] == 2  # unfiltered

    ids = count(1)
    run = run_replay(
        store,
        incident_ids=None,
        candidate_ruleset=None,
        requested_by="analyst_1",
        clock=lambda: T0,
        new_id=lambda prefix: f"{prefix}_{next(ids)}",
        correlation_id="req_r",
    )
    assert [c.incident_id for c in run.cases] == ["inc_default"]
    assert store.replay_runs(limit=10, tenant_id="default") == [run]
    assert store.replay_runs(limit=10, tenant_id="psap-b") == []
