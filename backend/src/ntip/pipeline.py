"""The processing pipeline: source event -> incident -> assessment -> store.

Each step appends everything it produced, plus the audit events describing
it, in one atomic batch. Parsing or assessment failures never lose the input
and never produce a low priority: the source event is stored and the incident
gets a ``processing_failed`` assessment that demands urgent human review
(design v1.2, sections 5.3 and 7.5).
"""

import logging
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum

from ntip.ml.contract import InferenceMessage, InferenceRequest, ModelOutput
from ntip.ml.extractors import ModelExtractor
from ntip.ml.fusion import fuse
from ntip.ml.verify import verify
from ntip.parser.parser import PARSER_ID, PARSER_VERSION, parse
from ntip.schema.advisory import Assessment, AssessmentStatus
from ntip.schema.audit import Actor, ActorKind, AuditEvent, AuditEventType
from ntip.schema.base import SchemaModel, sha256_digest
from ntip.schema.canonical import Incident, InferenceMode
from ntip.schema.review import HumanReview, ReviewDecision
from ntip.schema.source import SourceEvent, SourceType
from ntip.store import (
    ConcurrentModification,
    EventStore,
    Expectation,
    IdempotencyClaim,
    Record,
    UnknownIncident,
)
from ntip.triage.engine import ENGINE_ID, ENGINE_VERSION, assess, failed_assessment
from ntip.triage.ruleset import DEFAULT_RULESET, load_ruleset

log = logging.getLogger(__name__)

PIPELINE_ACTOR = Actor(kind=ActorKind.SERVICE, actor_id="pipeline")
# Retries when another message for the same incident was written concurrently.
MAX_ATTEMPTS = 20


class IdempotencyConflict(Exception):
    """The idempotency key was already used for a different request."""


class IncidentState(StrEnum):
    """Review state machine (design v1.2, section 11.3)."""

    AWAITING_REVIEW = "awaiting_review"
    REVIEWED = "reviewed"
    PROCESSING_FAILED = "processing_failed"
    CLOSED = "closed"


def _now() -> datetime:
    return datetime.now(UTC)


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex}"


@dataclass
class Pipeline:
    store: EventStore
    ruleset_name: str = DEFAULT_RULESET
    clock: Callable[[], datetime] = _now
    new_id: Callable[[str], str] = _new_id
    # Test hook: replaces the parser, e.g. to simulate a crash.
    parser: Callable[..., Incident] = field(default=parse)
    # How model output is used (design v1.2, section 3A.3). The rules baseline
    # always runs; a model can only add to it, and never blocks it.
    inference_mode: InferenceMode = InferenceMode.RULES_ONLY
    extractor: ModelExtractor | None = None

    # ------------------------------------------------------------------ ingest

    def ingest(
        self,
        text: str,
        *,
        incident_id: str | None = None,
        source_type: SourceType = SourceType.SYNTHETIC_TRANSCRIPT,
        idempotency_key: str | None = None,
        correlation_id: str | None = None,
        new_incident_id: str | None = None,
    ) -> "IngestResult":
        """Accept a new message, either opening an incident or adding to one.

        ``new_incident_id`` names a new incident (used by the interop gateway
        so an external incident always maps to the same platform incident).
        """
        correlation_id = correlation_id or self.new_id("req")
        request_digest = sha256_digest(f"{incident_id or ''}\n{source_type}\n{text}")

        if idempotency_key is not None:
            claim = self.store.idempotency_claim(idempotency_key)
            if claim is not None:
                if claim.request_digest != request_digest:
                    raise IdempotencyConflict(idempotency_key)
                return self._replayed(claim.incident_id)

        if incident_id is not None and not self.store.source_events(incident_id):
            raise UnknownIncident(incident_id)
        incident_id = incident_id or new_incident_id or self.new_id("inc")

        # Optimistic concurrency: derive from the conversation as read, and
        # write only if no other message arrived meanwhile; otherwise re-read
        # and derive again, so the stored result always covers every message.
        for _ in range(MAX_ATTEMPTS):
            previous = self.store.source_events(incident_id)
            now = self.clock()
            source = SourceEvent.from_text(
                source_event_id=self.new_id("evt"),
                incident_id=incident_id,
                received_at=now,
                text=text,
                source_type=source_type,
                supersedes=previous[-1].source_event_id if previous else None,
            )
            records: list[Record] = []
            if idempotency_key is not None:
                records.append(
                    IdempotencyClaim(
                        key=idempotency_key,
                        request_digest=request_digest,
                        incident_id=incident_id,
                        claimed_at=now,
                    )
                )
            records += [source, self._audit(AuditEventType.SOURCE_RECEIVED, source, correlation_id)]
            incident, assessment, derived = self._process([*previous, source], correlation_id)
            try:
                self.store.append(records + derived, expect=Expectation(incident_id, len(previous)))
            except ConcurrentModification:
                continue
            return IngestResult(incident_id, source.source_event_id, incident, assessment, False)
        raise ConcurrentModification(f"{incident_id}: gave up after {MAX_ATTEMPTS} attempts")

    def _process(
        self, sources: list[SourceEvent], correlation_id: str
    ) -> tuple[Incident | None, Assessment, list[Record]]:
        """Parse and assess; returns the records to append after the source."""
        incident_id = sources[0].incident_id
        now = self.clock()
        assessment_id = self.new_id("assess")
        try:
            incident, model_records = self._with_model(
                self.parser(sources, derived_at=now), sources
            )
            assessment = assess(
                incident,
                assessment_id=assessment_id,
                assessed_at=now,
                ruleset=load_ruleset(self.ruleset_name),
            )
        except Exception as err:  # any failure must surface as needs-review, never as low priority
            log.exception("processing failed for incident %s", incident_id)
            failed = failed_assessment(
                incident_id=incident_id,
                assessment_id=assessment_id,
                assessed_at=now,
                reason=f"{type(err).__name__} during processing",
                ruleset_version=self.ruleset_name,
            )
            # Nothing partially derived is kept; the source event is stored regardless.
            return (
                None,
                failed,
                [
                    failed,
                    self._audit(AuditEventType.PROCESSING_FAILED, failed, correlation_id),
                ],
            )
        return (
            incident,
            assessment,
            [
                incident,
                self._audit(AuditEventType.INCIDENT_PARSED, incident, correlation_id),
                *model_records,
                assessment,
                self._audit(AuditEventType.TRIAGE_ASSESSED, assessment, correlation_id),
            ],
        )

    def _with_model(
        self, rules: Incident, sources: list[SourceEvent]
    ) -> tuple[Incident, list[Record]]:
        """Apply the inference mode. A model problem never fails processing."""
        mode = self.inference_mode
        if mode is InferenceMode.RULES_ONLY:
            return fuse(rules, mode), []
        if self.extractor is None:
            return fuse(rules, mode, failure="no model configured"), []

        request = InferenceRequest(
            request_id=self.new_id("infer"),
            incident_id=rules.incident_id,
            messages=[
                InferenceMessage(source_event_id=s.source_event_id, text=s.text) for s in sources
            ],
            language_hint=rules.language,
        )
        model_id, model_version = self.extractor.model_id, self.extractor.model_version
        try:
            response = self.extractor.infer(request)
            verified = verify(response, {s.source_event_id: s.text for s in sources})
            fused = fuse(
                rules,
                mode,
                verified=verified,
                abstained_codes=[a.code for a in response.abstentions],
                model_id=model_id,
                model_version=model_version,
            )
            error = None
        except Exception as err:  # the model is optional; fall back to the rules
            log.warning("inference failed for %s: %s", rules.incident_id, err)
            response, error = None, f"{type(err).__name__}: {err}"[:500]
            fused = fuse(rules, mode, failure=error, model_id=model_id, model_version=model_version)
        output = ModelOutput(
            output_id=self.new_id("mo"),
            incident_id=rules.incident_id,
            recorded_at=self.clock(),
            mode=mode,
            request=request,
            response=response,
            error=error,
        )
        return fused, [output]

    def _replayed(self, incident_id: str) -> "IngestResult":
        sources = self.store.source_events(incident_id)
        versions = self.store.incident_versions(incident_id)
        return IngestResult(
            incident_id,
            sources[-1].source_event_id,
            versions[-1] if versions else None,
            self.store.assessments(incident_id)[-1],
            True,
        )

    # ------------------------------------------------------------------ review

    def review(
        self,
        incident_id: str,
        *,
        assessment_id: str,
        reviewer_id: str,
        decision: ReviewDecision,
        reason: str | None = None,
        override_priority: str | None = None,
        corrected_classification: dict[str, object] | None = None,
        correlation_id: str | None = None,
    ) -> HumanReview:
        """Record a human decision. The assessment itself is never modified."""
        assessment = self.store.assessment(assessment_id)
        if assessment is None or assessment.incident_id != incident_id:
            raise UnknownIncident(f"{incident_id}/{assessment_id}")
        review = HumanReview.model_validate(
            {
                "review_id": self.new_id("rev"),
                "incident_id": incident_id,
                "assessment_id": assessment_id,
                "reviewer_id": reviewer_id,
                "reviewed_at": self.clock(),
                "decision": decision,
                "reason": reason,
                "override_priority": override_priority,
                "corrected_classification": corrected_classification,
            }
        )
        event = {
            ReviewDecision.OVERRIDE_PRIORITY: AuditEventType.TRIAGE_OVERRIDDEN,
            ReviewDecision.CLOSE: AuditEventType.INCIDENT_CLOSED,
        }.get(decision, AuditEventType.INCIDENT_REVIEWED)
        actor = Actor(kind=ActorKind.OPERATOR, actor_id=reviewer_id)
        self.store.append(
            [review, self._audit(event, review, correlation_id or self.new_id("req"), actor)]
        )
        return review

    # ------------------------------------------------------------------ views

    def view(self, incident_id: str) -> "IncidentView":
        sources = self.store.source_events(incident_id)
        if not sources:
            raise UnknownIncident(incident_id)
        versions = self.store.incident_versions(incident_id)
        assessments = self.store.assessments(incident_id)
        reviews = self.store.reviews(incident_id)
        return IncidentView.project(sources, versions, assessments, reviews)

    # ------------------------------------------------------------------ helpers

    def _audit(
        self,
        event_type: AuditEventType,
        subject: SchemaModel,
        correlation_id: str,
        actor: Actor = PIPELINE_ACTOR,
    ) -> AuditEvent:
        subject_id, version = _subject(subject)
        return AuditEvent(
            event_id=self.new_id("ae"),
            incident_id=getattr(subject, "incident_id"),  # noqa: B009
            occurred_at=self.clock(),
            event_type=event_type,
            actor=actor,
            component_version=version,
            correlation_id=correlation_id,
            subject_id=subject_id,
            subject_digest=sha256_digest(subject.model_dump_json()),
        )


def _subject(subject: SchemaModel) -> tuple[str, str | None]:
    match subject:
        case SourceEvent():
            return subject.source_event_id, None
        case Incident():
            # One incident has many derived versions; the derivation time tells them apart.
            stamp = subject.derived_at.strftime("%Y%m%dT%H%M%S.%fZ")
            return f"{subject.incident_id}:{stamp}", f"{PARSER_ID}-{PARSER_VERSION}"
        case Assessment():
            return subject.assessment_id, f"{ENGINE_ID}-{ENGINE_VERSION}"
        case HumanReview():
            return subject.review_id, None
    raise TypeError(type(subject).__name__)


@dataclass(frozen=True)
class IngestResult:
    incident_id: str
    source_event_id: str
    incident: Incident | None
    assessment: Assessment
    idempotent_replay: bool


@dataclass(frozen=True)
class IncidentView:
    """Current state of an incident, projected from its append-only history."""

    incident_id: str
    sources: list[SourceEvent]
    incident: Incident | None
    assessment: Assessment
    reviews: list[HumanReview]
    state: IncidentState
    effective_priority: str | None

    @classmethod
    def project(
        cls,
        sources: list[SourceEvent],
        versions: list[Incident],
        assessments: list[Assessment],
        reviews: list[HumanReview],
    ) -> "IncidentView":
        latest = assessments[-1]
        on_latest = [r for r in reviews if r.assessment_id == latest.assessment_id]
        if on_latest and on_latest[-1].decision is ReviewDecision.CLOSE:
            state = IncidentState.CLOSED
        elif latest.status is AssessmentStatus.PROCESSING_FAILED:
            state = IncidentState.PROCESSING_FAILED
        elif on_latest:
            state = IncidentState.REVIEWED
        else:
            state = IncidentState.AWAITING_REVIEW
        overrides = [r for r in on_latest if r.override_priority is not None]
        # A human override wins over the machine; the machine output is kept.
        effective = overrides[-1].override_priority if overrides else latest.advisory_priority
        return cls(
            incident_id=sources[0].incident_id,
            sources=sources,
            incident=versions[-1] if versions else None,
            assessment=latest,
            reviews=reviews,
            state=state,
            effective_priority=effective,
        )
