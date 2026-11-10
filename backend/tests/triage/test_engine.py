from datetime import UTC, datetime

import pytest

from ntip.parser.parser import parse
from ntip.schema.advisory import (
    AdvisoryPriority,
    Assessment,
    AssessmentStatus,
    ReviewAction,
    SeverityBand,
    assessment_reference_errors,
)
from ntip.schema.canonical import Incident
from ntip.schema.source import SourceEvent
from ntip.triage.engine import assess as assess_incident
from ntip.triage.engine import failed_assessment
from ntip.triage.ruleset import load_ruleset

AT = datetime(2026, 11, 9, 12, 0, tzinfo=UTC)


def parse_text(*texts: str) -> Incident:
    sources = [
        SourceEvent.from_text(
            source_event_id=f"evt_{i}", incident_id="inc_1", received_at=AT, text=text
        )
        for i, text in enumerate(texts, 1)
    ]
    return parse(sources, derived_at=AT)


def assess(incident: Incident) -> Assessment:
    return assess_incident(incident, assessment_id="assess_1", assessed_at=AT)


def triage(*texts: str) -> Assessment:
    return assess(parse_text(*texts))


class TestSeverity:
    @pytest.mark.parametrize(
        ("text", "band", "priority"),
        [
            (
                "My father is not breathing and has no pulse. We are at 123 Oak Street.",
                "critical",
                "P0",
            ),
            ("Someone has been shot at 456 Elm Road and is bleeding badly.", "critical", "P0"),
            ("Smoke on the second floor and people are trapped inside.", "critical", "P0"),
            ("There is a fight and someone is being beaten at 789 Pine Street.", "high", "P1"),
            ("My husband has chest pain at 12 Oak Street.", "high", "P1"),
            ("There is smoke coming from the building at 12 Oak Street.", "elevated", "P2"),
            ("I twisted my ankle and I'm hurt at 99 Cedar Lane.", "standard", "P3"),
            ("There is a suspicious person near the park.", "standard", "P3"),
        ],
    )
    def test_band_and_priority(self, text: str, band: str, priority: str) -> None:
        result = triage(text)
        assert (result.severity_band, result.advisory_priority) == (band, priority)

    def test_escalation_for_multiple_victims(self) -> None:
        assert triage("Five people injured in a crash on Route 9.").severity_band == "elevated"
        assert triage("Smoke at 12 Oak Street, kids inside the house.").severity_band == "high"

    def test_person_unable_to_get_up_is_elevated(self) -> None:
        result = triage("My grandmother fell and can't get up. 5 Elm Road.")
        assert (result.severity_band, result.advisory_priority) == ("elevated", "P2")

    def test_recovered_critical_event_is_elevated_not_ignored(self) -> None:
        result = triage("He was not breathing earlier but he is breathing now. 9 Pine Road.")
        assert result.severity_band == "elevated"
        assert any(r.rule_id == "R-HIST-001" for r in result.reasons)
        # A past event is not a reason to ask for confirmation of a current one.
        assert ReviewAction.CONFIRM_CRITICAL_REPORT not in result.review_actions

    def test_released_ruleset_1_0_0_still_assesses_as_before(self) -> None:
        old = assess_incident(
            parse_text("He was not breathing earlier but he is breathing now."),
            assessment_id="a",
            assessed_at=AT,
            ruleset=load_ruleset("research-1.0.0"),
        )
        assert old.ruleset_version == "research-1.0.0"
        assert old.severity_band != "elevated"

    def test_negated_and_historical_cues_do_not_fire(self) -> None:
        assert triage("There is no fire and no smoke here.").severity_band == "undetermined"
        assert triage("He was bleeding yesterday, he is fine now.").severity_band != "high"

    def test_every_rule_firing_cites_existing_observations(self) -> None:
        incident = parse_text("Someone was shot, he is bleeding. Two people hurt at 12 Oak Street.")
        assert assessment_reference_errors(assess(incident), incident) == []

    def test_rule_ids_and_versions_are_recorded(self) -> None:
        result = triage("He is not breathing at 12 Oak Street.")
        firing = next(r for r in result.reasons if r.rule_id == "R-RESP-001")
        assert firing.rule_version == "1.0.0"
        assert result.ruleset_version == "research-1.1.0"


class TestSafetyInvariants:
    def test_missing_location_never_changes_severity_or_priority(self) -> None:
        with_address = triage("My wife is not breathing. We are at 12 Oak Street.")
        lost = triage("My wife is not breathing. I don't know where I am.")
        assert lost.severity_band == with_address.severity_band == SeverityBand.CRITICAL
        assert lost.advisory_priority == with_address.advisory_priority == AdvisoryPriority.P0
        assert ReviewAction.VERIFY_LOCATION in lost.review_actions

    def test_uncertain_serious_cue_keeps_full_weight_and_asks_for_confirmation(self) -> None:
        result = triage("I think I heard a gunshot at 12 Oak Street.")
        assert result.severity_band == "high"
        assert ReviewAction.CONFIRM_CRITICAL_REPORT in result.review_actions

    def test_prank_cue_does_not_suppress_credible_evidence(self) -> None:
        result = triage(
            "This is not a prank, he is not breathing at 12 Oak Street. Never mind the joke."
        )
        assert result.severity_band == "critical"
        assert ReviewAction.CONFIRM_CLASSIFICATION in result.review_actions

    def test_prank_alone_is_low_but_still_reviewed(self) -> None:
        result = triage("Never mind, it was just a prank, ignore this call.")
        assert (result.severity_band, result.advisory_priority) == ("low", "P4")
        assert ReviewAction.CONFIRM_CLASSIFICATION in result.review_actions

    def test_unintelligible_call_is_undetermined_not_low(self) -> None:
        result = triage("hello there")
        assert result.severity_band == "undetermined"
        assert result.advisory_priority == "P2"
        assert ReviewAction.CONFIRM_CLASSIFICATION in result.review_actions

    def test_contradictions_are_escalated_not_averaged(self) -> None:
        result = triage("He is bleeding. Actually there is no bleeding.")
        assert result.severity_band == "high"  # the affirmed cue still counts
        assert ReviewAction.RESOLVE_CONFLICT in result.review_actions

    def test_conflicting_address_requests_resolution(self) -> None:
        result = triage("He is not breathing at 123 Main Street.", "Sorry, 321 Main Street.")
        assert result.location_quality.status == "conflicting"
        assert {ReviewAction.RESOLVE_CONFLICT, ReviewAction.VERIFY_LOCATION} <= set(
            result.review_actions
        )

    def test_machine_assessments_always_require_review(self) -> None:
        assert triage("I twisted my ankle at 99 Cedar Lane.").requires_human_review

    def test_is_deterministic(self) -> None:
        text = "Someone was shot at 456 Elm Road and is bleeding."
        assert triage(text) == triage(text)


class TestFailure:
    def test_failed_assessment_has_no_priority(self) -> None:
        result = failed_assessment(
            incident_id="inc_1", assessment_id="a1", assessed_at=AT, reason="parser crashed"
        )
        assert result.status is AssessmentStatus.PROCESSING_FAILED
        assert result.advisory_priority is None
        assert result.review_actions[0] is ReviewAction.URGENT_HUMAN_REVIEW
