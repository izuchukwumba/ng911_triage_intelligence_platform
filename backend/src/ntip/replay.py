"""Replay stored incidents against pinned or candidate rulesets."""

from collections.abc import Callable, Sequence
from datetime import datetime

from ntip.schema.advisory import Assessment, AssessmentStatus
from ntip.schema.audit import Actor, ActorKind, AuditEvent, AuditEventType
from ntip.schema.base import sha256_digest
from ntip.schema.replay import ReplayCase, ReplayOutcome, ReplayRun, ReplaySummary
from ntip.store import EventStore, Record, UnknownIncident
from ntip.triage.engine import ENGINE_VERSION, assess
from ntip.triage.ruleset import RELEASED, load_ruleset


class UnknownRuleset(ValueError):
    pass


def _outcome(assessment: Assessment) -> ReplayOutcome:
    return ReplayOutcome(
        ruleset_version=assessment.ruleset_version,
        severity_band=assessment.severity_band,
        advisory_priority=assessment.advisory_priority,
        reason_codes=[r.reason_code for r in assessment.reasons],
    )


def _rank(priority: str | None) -> int:
    return int(priority[1]) if priority else -1  # no priority (failure) ranks most urgent


def replay_incident(store: EventStore, incident_id: str, candidate: str | None) -> ReplayCase:
    assessments = store.assessments(incident_id)
    versions = store.incident_versions(incident_id)
    if not assessments:
        raise UnknownIncident(incident_id)
    stored = assessments[-1]

    def skipped(reason: str) -> ReplayCase:
        return ReplayCase(
            incident_id=incident_id,
            stored_assessment_id=stored.assessment_id,
            stored=_outcome(stored),
            reproduced=None,
            reproducible=None,
            candidate=None,
            priority_changed=None,
            candidate_lowers_priority=None,
            skipped_reason=reason,
        )

    if stored.status is AssessmentStatus.PROCESSING_FAILED or not versions:
        return skipped("stored processing failed")
    if stored.ruleset_version not in RELEASED:
        return skipped(f"ruleset {stored.ruleset_version} is not a released ruleset")

    incident = versions[-1]

    def rerun(ruleset_name: str) -> Assessment:
        # Same inputs as the stored run: the stored incident, its location
        # quality, its timestamp and id. Only the ruleset may differ.
        return assess(
            incident,
            assessment_id=stored.assessment_id,
            assessed_at=stored.assessed_at,
            ruleset=load_ruleset(ruleset_name),
            location_quality=stored.location_quality,
        )

    reproduced = rerun(stored.ruleset_version)
    candidate_outcome = _outcome(rerun(candidate)) if candidate else None
    changed = lowers = None
    if candidate_outcome is not None:
        changed = candidate_outcome.advisory_priority != stored.advisory_priority
        lowers = _rank(candidate_outcome.advisory_priority) > _rank(stored.advisory_priority)
    return ReplayCase(
        incident_id=incident_id,
        stored_assessment_id=stored.assessment_id,
        stored=_outcome(stored),
        reproduced=_outcome(reproduced),
        # Equality of the full assessment, not just the priority.
        reproducible=reproduced.model_dump_json() == stored.model_dump_json(),
        candidate=candidate_outcome,
        priority_changed=changed,
        candidate_lowers_priority=lowers,
    )


def run_replay(
    store: EventStore,
    *,
    incident_ids: Sequence[str] | None,
    candidate_ruleset: str | None,
    requested_by: str,
    clock: Callable[[], datetime],
    new_id: Callable[[str], str],
    correlation_id: str,
) -> ReplayRun:
    """Replay incidents (all when ``incident_ids`` is None) and store the run."""
    if candidate_ruleset is not None and candidate_ruleset not in RELEASED:
        raise UnknownRuleset(candidate_ruleset)
    if incident_ids is None:
        total, _ = store.list_incidents(limit=1, offset=0)
        _, page = store.list_incidents(limit=max(total, 1), offset=0)
        incident_ids = [s.incident_id for s in page]

    now = clock()
    cases = [replay_incident(store, i, candidate_ruleset) for i in incident_ids]
    run = ReplayRun(
        run_id=new_id("replay"),
        created_at=now,
        requested_by=requested_by,
        candidate_ruleset=candidate_ruleset,
        engine_version=ENGINE_VERSION,
        cases=cases,
        summary=ReplaySummary(
            incidents=len(cases),
            skipped=sum(c.skipped_reason is not None for c in cases),
            reproducible=sum(c.reproducible is True for c in cases),
            not_reproducible=sum(c.reproducible is False for c in cases),
            priority_changed=sum(c.priority_changed is True for c in cases),
            candidate_lowers_priority=sum(c.candidate_lowers_priority is True for c in cases),
        ),
    )
    digest = sha256_digest(run.model_dump_json())
    actor = Actor(kind=ActorKind.OPERATOR, actor_id=requested_by)
    events: list[Record] = [
        AuditEvent(
            event_id=new_id("ae"),
            incident_id=case.incident_id,
            occurred_at=now,
            event_type=AuditEventType.INCIDENT_REPLAYED,
            actor=actor,
            component_version=f"triage-engine-{ENGINE_VERSION}",
            correlation_id=correlation_id,
            subject_id=run.run_id,
            subject_digest=digest,
        )
        for case in cases
    ]
    store.append([run, *events])
    return run
