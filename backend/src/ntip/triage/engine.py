"""Assess an incident: severity, review actions and research priority.

Severity is decided only by what was reported, through the versioned
ruleset. Everything else — location quality, uncertain or second-hand cues,
contradictions, possible pranks, weak classification — adds *review actions*
for a human and never lowers severity (design v1.2, sections 3A.6, 7.1, 7.5;
DDL-011).
"""

from collections import defaultdict
from datetime import datetime

from ntip.location import assess_location
from ntip.schema.advisory import (
    Assessment,
    AssessmentStatus,
    LocationQuality,
    LocationQualityStatus,
    ReviewAction,
    RuleFiring,
    SeverityBand,
)
from ntip.schema.base import FactStatus
from ntip.schema.canonical import (
    Extractor,
    ExtractorKind,
    Incident,
    IncidentDomain,
    Polarity,
    Temporality,
)
from ntip.triage.ruleset import SEVERITY_ORDER, Ruleset, load_ruleset

ENGINE_ID = "triage-engine"
ENGINE_VERSION = "1.1.0"
ASSESSOR = Extractor(kind=ExtractorKind.RULE, extractor_id=ENGINE_ID, version=ENGINE_VERSION)

# Review policies live in code and are versioned with the engine. Their ids
# appear in Assessment.reasons next to the ruleset's severity rules.
POLICY_UNCERTAIN_SERIOUS_CUE = "P-REVIEW-001"
POLICY_CONFLICT = "P-REVIEW-002"
POLICY_POSSIBLE_PRANK = "P-REVIEW-003"
POLICY_WEAK_CLASSIFICATION = "P-REVIEW-004"
POLICY_LOCATION = "P-REVIEW-005"

_SERIOUS = {SeverityBand.HIGH, SeverityBand.CRITICAL}


def _rank(band: SeverityBand) -> int:
    return SEVERITY_ORDER.index(band)


def _policy(rule_id: str, reason_code: str, **refs: list[str]) -> RuleFiring:
    return RuleFiring(rule_id=rule_id, rule_version=ENGINE_VERSION, reason_code=reason_code, **refs)


def assess(
    incident: Incident,
    *,
    assessment_id: str,
    assessed_at: datetime,
    ruleset: Ruleset | None = None,
    location_quality: LocationQuality | None = None,
) -> Assessment:
    ruleset = ruleset or load_ruleset()
    location_quality = location_quality or assess_location(incident)

    # Cues that describe the present: affirmed or uncertain, not negated, not
    # historical or hypothetical. Second-hand reports still count.
    supporting: dict[str, list[str]] = defaultdict(list)
    certain: set[str] = set()
    # Cues reported as having happened earlier; only rules that ask for
    # historical cues look at these.
    past: dict[str, list[str]] = defaultdict(list)
    for obs in incident.observations:
        if obs.polarity is Polarity.NEGATED:
            continue
        if obs.temporality is Temporality.HISTORICAL:
            past[obs.code].append(obs.observation_id)
        if obs.temporality is not Temporality.CURRENT:
            continue
        supporting[obs.code].append(obs.observation_id)
        if obs.polarity is Polarity.AFFIRMED:
            certain.add(obs.code)

    reasons: list[RuleFiring] = []
    actions: set[ReviewAction] = set()
    severity: SeverityBand | None = None
    escalations = []

    for rule in ruleset.rules:
        cues = past if rule.temporality == "historical" else supporting
        if not all(code in cues for code in rule.all_of):
            continue
        reasons.append(
            RuleFiring(
                rule_id=rule.id,
                rule_version=rule.version,
                reason_code=rule.reason_code,
                observation_ids=[oid for code in rule.all_of for oid in cues[code]],
            )
        )
        if rule.effect == "escalate":
            escalations.append(rule)
        elif severity is None or _rank(rule.severity) > _rank(severity):
            severity = rule.severity
        # A serious cue the caller was unsure about is kept at full weight and
        # sent to a human to confirm, rather than discounted.
        uncertain = rule.temporality == "current" and not all(c in certain for c in rule.all_of)
        if rule.severity in _SERIOUS and uncertain:
            actions.add(ReviewAction.CONFIRM_CRITICAL_REPORT)
            reasons.append(
                _policy(
                    POLICY_UNCERTAIN_SERIOUS_CUE,
                    "UNCERTAIN_SERIOUS_CUE",
                    observation_ids=[oid for code in rule.all_of for oid in supporting[code]],
                )
            )

    for rule in escalations:
        if severity is None:
            severity = rule.severity
        else:
            severity = SEVERITY_ORDER[min(_rank(severity) + 1, len(SEVERITY_ORDER) - 1)]

    prank = "POSSIBLE_PRANK" in supporting
    if prank:
        # A prank cue never suppresses credible evidence. It only asks a human
        # to confirm the call is genuine, and sets the band to "low" when
        # nothing else was reported.
        actions.add(ReviewAction.CONFIRM_CLASSIFICATION)
        reasons.append(
            _policy(
                POLICY_POSSIBLE_PRANK,
                "POSSIBLE_PRANK_REPORTED",
                observation_ids=supporting["POSSIBLE_PRANK"],
            )
        )
        if severity is None:
            severity = SeverityBand.LOW

    classification = incident.classification
    if severity is None:
        severity = (
            SeverityBand.UNDETERMINED
            if classification.domain is IncidentDomain.UNKNOWN
            else SeverityBand.STANDARD
        )

    weak = (
        classification.domain is IncidentDomain.UNKNOWN
        or classification.heuristic_confidence is None
        or classification.heuristic_confidence < ruleset.confirm_classification_below
    )
    if weak or severity is SeverityBand.UNDETERMINED:
        actions.add(ReviewAction.CONFIRM_CLASSIFICATION)
        reasons.append(_policy(POLICY_WEAK_CLASSIFICATION, "CLASSIFICATION_UNCERTAIN"))

    if severity is SeverityBand.CRITICAL:
        actions.add(ReviewAction.CONFIRM_CRITICAL_REPORT)

    if incident.conflicts or incident.victim_count.status is FactStatus.CONFLICTING:
        actions.add(ReviewAction.RESOLVE_CONFLICT)
        reasons.append(
            _policy(
                POLICY_CONFLICT,
                "CONFLICTING_REPORTS",
                observation_ids=[o for c in incident.conflicts for o in c.observation_ids],
                location_ids=[loc for c in incident.conflicts for loc in c.location_ids],
            )
        )

    if location_quality.status is not LocationQualityStatus.SUFFICIENT:
        # Location quality changes the workflow, never the severity.
        actions.add(ReviewAction.VERIFY_LOCATION)
        reasons.append(
            _policy(
                POLICY_LOCATION,
                f"LOCATION_{location_quality.status.upper()}",
                location_ids=list(location_quality.conflicting_location_ids),
            )
        )

    ordered = [action for action in ReviewAction if action in actions]
    return Assessment(
        assessment_id=assessment_id,
        incident_id=incident.incident_id,
        assessed_at=assessed_at,
        assessor=ASSESSOR,
        ruleset_version=ruleset.name,
        status=AssessmentStatus.COMPLETED,
        severity_band=severity,
        location_quality=location_quality,
        advisory_priority=ruleset.priority_by_severity[severity],
        reasons=reasons,
        review_actions=ordered,
        requires_human_review=bool(ordered),
    )


def failed_assessment(
    *,
    incident_id: str,
    assessment_id: str,
    assessed_at: datetime,
    reason: str,
    ruleset_version: str = "none",
) -> Assessment:
    """The assessment recorded when parsing or scoring fails.

    It carries no priority and an undetermined severity, and demands urgent
    human review: a failure is never turned into a low-priority incident
    (design v1.2, sections 2.4 and 7.5).
    """
    return Assessment(
        assessment_id=assessment_id,
        incident_id=incident_id,
        assessed_at=assessed_at,
        assessor=ASSESSOR,
        ruleset_version=ruleset_version,
        status=AssessmentStatus.PROCESSING_FAILED,
        failure_reason=reason,
        severity_band=SeverityBand.UNDETERMINED,
        location_quality=LocationQuality(
            status=LocationQualityStatus.MISSING, missing_fields=["location"]
        ),
        advisory_priority=None,
        review_actions=[ReviewAction.URGENT_HUMAN_REVIEW, ReviewAction.VERIFY_LOCATION],
        requires_human_review=True,
    )
