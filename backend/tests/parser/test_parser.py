"""End-to-end parser behaviour, including every case from the TypeScript suite."""

from datetime import UTC, datetime

import pytest

from ntip.parser.parser import PARSER_VERSION, parse
from ntip.schema.base import FactStatus
from ntip.schema.canonical import (
    Attribution,
    ConflictKind,
    Incident,
    Polarity,
    Temporality,
    provenance_errors,
)
from ntip.schema.source import SourceEvent

AT = datetime(2026, 11, 9, 12, 0, tzinfo=UTC)


def source(text: str, event_id: str = "evt_1") -> SourceEvent:
    return SourceEvent.from_text(
        source_event_id=event_id, incident_id="inc_1", received_at=AT, text=text
    )


def parse_text(*texts: str) -> Incident:
    return parse([source(t, f"evt_{i}") for i, t in enumerate(texts, 1)], derived_at=AT)


def current_affirmed(incident: Incident) -> set[str]:
    return {
        o.code
        for o in incident.observations
        if o.polarity is Polarity.AFFIRMED and o.temporality is Temporality.CURRENT
    }


class TestObservations:
    @pytest.mark.parametrize(
        ("text", "code"),
        [
            ("Someone was shot with a gun near 5th and Oak.", "WEAPON_PRESENT"),
            ("He is not breathing and I cannot find a pulse.", "NOT_BREATHING"),
            ("She is bleeding badly from her chest.", "ACTIVE_BLEEDING"),
            ("A child was injured in the car accident on Main Street.", "CHILD_INVOLVED"),
            ("Never mind, it was just a prank, ignore this call.", "POSSIBLE_PRANK"),
            ("She stopped breathing completely. She is not breathing.", "NOT_BREATHING"),
            ("He had a gun and was threatening people. No injuries so far.", "WEAPON_PRESENT"),
            ("Él no está respirando. Necesito ayuda ahora mismo.", "NOT_BREATHING"),
            ("Smoke is coming from the second floor and people are trapped.", "OCCUPANTS_TRAPPED"),
            ("I don't know where I am, my wife is not breathing.", "CALLER_LOCATION_UNKNOWN"),
            ("He's lying on the floor and won't answer me.", "UNCONSCIOUS"),
            ("My foot hurts badly.", "INJURY_REPORTED"),
            ("She fell and she can't get up.", "UNABLE_TO_GET_UP"),
            (
                "HELP HELP PLEASE MY SON IS NOT BREATHING HELP. PLEASE HURRY.",
                "CALLER_HIGH_DISTRESS",
            ),
        ],
    )
    def test_affirmed_cue(self, text: str, code: str) -> None:
        assert code in current_affirmed(parse_text(text))

    @pytest.mark.parametrize(
        ("text", "code"),
        [
            (
                "Officers searched the vehicle but found no weapon and no contraband.",
                "WEAPON_PRESENT",
            ),
            ("I looked around and there was no gun, he was unarmed.", "WEAPON_PRESENT"),
            ("The patient has a wound but there is no bleeding visible.", "ACTIVE_BLEEDING"),
            ("He walked in without a gun and sat down at 45 Oak Street.", "WEAPON_PRESENT"),
            ("She fell down the stairs but denies any bleeding.", "ACTIVE_BLEEDING"),
            ("Police ruled out a gun after searching the car.", "WEAPON_PRESENT"),
        ],
    )
    def test_negated_cue_is_kept_but_not_affirmed(self, text: str, code: str) -> None:
        incident = parse_text(text)
        assert code not in current_affirmed(incident)
        assert any(o.code == code and o.polarity is Polarity.NEGATED for o in incident.observations)

    def test_historical_and_second_hand_context_is_preserved(self) -> None:
        [fire] = [o for o in parse_text("Someone said there was a fire yesterday.").observations
                  if o.code == "FIRE_REPORTED"]  # fmt: skip
        assert fire.temporality is Temporality.HISTORICAL
        assert fire.attribution is Attribution.SECOND_HAND

    def test_unsure_whether_breathing_is_an_uncertain_critical_cue(self) -> None:
        [cue] = [o for o in parse_text("I'm not sure if he's breathing.").observations
                 if o.code == "NOT_BREATHING"]  # fmt: skip
        assert (cue.polarity, cue.temporality) == (Polarity.UNCERTAIN, Temporality.CURRENT)

    def test_uncertain_gunshot(self) -> None:
        [shot] = [o for o in parse_text("I think I heard a gunshot.").observations
                  if o.code == "WEAPON_PRESENT"]  # fmt: skip
        assert shot.polarity is Polarity.UNCERTAIN

    def test_each_observation_quotes_its_source(self) -> None:
        text = "My father is not breathing. We're in apartment 4B at 12 Oak Street."
        incident = parse_text(text)
        assert provenance_errors(incident, {"evt_1": source(text)}) == []
        [obs] = [o for o in incident.observations if o.code == "NOT_BREATHING"]
        assert obs.evidence.text == "is not breathing"
        assert obs.extractor.version == PARSER_VERSION


class TestConflicts:
    def test_affirmed_and_denied_cue_conflict(self) -> None:
        incident = parse_text("He is bleeding. Actually there is no bleeding.")
        [conflict] = incident.conflicts
        assert conflict.kind is ConflictKind.OBSERVATION_POLARITY
        assert conflict.code == "ACTIVE_BLEEDING"

    def test_corrected_address_keeps_both_candidates(self) -> None:
        incident = parse_text("I'm at 123 Main Street.", "Sorry, I mean 321 Main Street.")
        assert [
            loc.civic_address.house_number for loc in incident.locations if loc.civic_address
        ] == [
            "123",
            "321",
        ]
        [conflict] = incident.conflicts
        assert conflict.kind is ConflictKind.LOCATION_MISMATCH
        assert [loc.evidence.source_event_id for loc in incident.locations if loc.evidence] == [
            "evt_1",
            "evt_2",
        ]

    def test_repeating_the_same_address_is_not_a_conflict(self) -> None:
        assert parse_text("We are at 12 Oak Street. Yes, 12 Oak Street.").conflicts == []


class TestVictimCount:
    def test_stated_count(self) -> None:
        incident = parse_text("There are four people injured at the scene on Route 9.")
        assert (incident.victim_count.status, incident.victim_count.value) == (
            FactStatus.REPORTED,
            4,
        )
        assert "MULTIPLE_VICTIMS" in current_affirmed(incident)

    def test_unstated_count(self) -> None:
        incident = parse_text("My father collapsed and is not breathing at 456 Elm Road.")
        assert incident.victim_count.status is FactStatus.NOT_REPORTED

    def test_count_changes_across_messages_conflict(self) -> None:
        incident = parse_text("Two people are hurt.", "Now there are three people hurt.")
        assert incident.victim_count.status is FactStatus.CONFLICTING
        assert incident.victim_count.candidates == [2, 3]


class TestIncident:
    def test_classification_and_language(self) -> None:
        incident = parse_text("Mi padre tuvo un ataque al corazón. No respira y no tiene pulso.")
        assert (incident.language, incident.classification.domain) == ("es", "ems")

    def test_location_candidates_are_reported_and_unverified(self) -> None:
        [loc] = parse_text("There is an emergency at 123 Oak Street. Please come now.").locations
        assert (loc.role, loc.validation, loc.coordinates) == ("reported", "unverified", None)
        assert loc.raw_text == "123 Oak Street"

    def test_no_location(self) -> None:
        assert (
            parse_text("Someone is hurt somewhere near here. I do not know the address.").locations
            == []
        )

    def test_is_deterministic(self) -> None:
        text = "Someone was shot at 456 Elm Road and is bleeding. Two people hurt."
        assert parse_text(text) == parse_text(text)

    def test_rejects_sources_from_different_incidents(self) -> None:
        other = SourceEvent.from_text(
            source_event_id="evt_x", incident_id="inc_2", received_at=AT, text="Fire."
        )
        with pytest.raises(ValueError, match="different incidents"):
            parse([source("Fire."), other], derived_at=AT)

    def test_rejects_an_empty_sequence(self) -> None:
        with pytest.raises(ValueError, match="at least one"):
            parse([], derived_at=AT)
