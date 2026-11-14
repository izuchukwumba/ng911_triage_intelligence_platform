"""The twelve cues added in parser 1.5.0 and ruleset research-1.2.0 (DDL-021)."""

from datetime import UTC, datetime

import pytest

from ntip.parser.parser import parse
from ntip.schema.advisory import SeverityBand
from ntip.schema.canonical import Incident, Polarity, Temporality
from ntip.schema.source import SourceEvent
from ntip.triage.engine import assess
from ntip.triage.ruleset import load_ruleset

AT = datetime(2026, 11, 13, 12, 0, tzinfo=UTC)

NEW_CODES = {
    "ALLERGIC_REACTION": SeverityBand.HIGH,
    "DIABETIC_EMERGENCY": SeverityBand.HIGH,
    "CHILDBIRTH": SeverityBand.HIGH,
    "POISONING": SeverityBand.HIGH,
    "DROWNING": SeverityBand.HIGH,
    "BURN_INJURY": SeverityBand.HIGH,
    "ELECTROCUTION": SeverityBand.HIGH,
    "FALL_FROM_HEIGHT": SeverityBand.HIGH,
    "SELF_HARM_RISK": SeverityBand.HIGH,
    "INTRUDER_PRESENT": SeverityBand.HIGH,
    "TRAFFIC_COLLISION": SeverityBand.ELEVATED,
    "MISSING_PERSON": SeverityBand.ELEVATED,
}


def parse_text(text: str) -> Incident:
    source = SourceEvent.from_text(
        source_event_id="evt_1", incident_id="inc_1", received_at=AT, text=text
    )
    return parse([source], derived_at=AT)


def live(incident: Incident) -> set[str]:
    return {
        o.code
        for o in incident.observations
        if o.polarity is not Polarity.NEGATED and o.temporality is Temporality.CURRENT
    }


@pytest.mark.parametrize(
    ("text", "code"),
    [
        ("He is having an allergic reaction, his throat is closing up.", "ALLERGIC_REACTION"),
        ("She used her EpiPen but her lips are swelling.", "ALLERGIC_REACTION"),
        ("My dad is diabetic and his blood sugar is really low.", "DIABETIC_EMERGENCY"),
        ("My wife is in labor and her water broke.", "CHILDBIRTH"),
        ("The baby is coming right now, I can see it crowning.", "CHILDBIRTH"),
        ("My toddler drank some bleach from under the sink.", "POISONING"),
        ("There's been a car crash on the highway.", "TRAFFIC_COLLISION"),
        ("A man was hit by a car outside the store.", "TRAFFIC_COLLISION"),
        ("We pulled him out of the pool, he nearly drowned.", "DROWNING"),
        ("She got burned with boiling water.", "BURN_INJURY"),
        ("He was electrocuted by a live wire.", "ELECTROCUTION"),
        ("My brother fell off the roof.", "FALL_FROM_HEIGHT"),
        ("He says he wants to kill himself.", "SELF_HARM_RISK"),
        ("Someone is breaking in right now, I'm hiding upstairs.", "INTRUDER_PRESENT"),
        ("My mother has dementia and she wandered off.", "MISSING_PERSON"),
        # Spanish
        ("Mi hijo tiene una reacción alérgica.", "ALLERGIC_REACTION"),
        ("Mi esposa está de parto, se le rompió la fuente.", "CHILDBIRTH"),
        ("Hubo un choque en la esquina.", "TRAFFIC_COLLISION"),
        ("Mi hermano se cayó del techo.", "FALL_FROM_HEIGHT"),
        ("Hay alguien en mi casa, tengo miedo.", "INTRUDER_PRESENT"),
        ("Mi abuela está desaparecida, no la encontramos.", "MISSING_PERSON"),
    ],
)  # fmt: skip
def test_new_cue_is_reported(text: str, code: str) -> None:
    assert code in live(parse_text(text))


@pytest.mark.parametrize(
    ("text", "code"),
    [
        ("There is no intruder, it was just the cat.", "INTRUDER_PRESENT"),
        ("He is not suicidal, he just needs to talk.", "SELF_HARM_RISK"),
        ("She is not having an allergic reaction.", "ALLERGIC_REACTION"),
    ],
)
def test_denied_new_cue_is_not_live(text: str, code: str) -> None:
    incident = parse_text(text)
    assert code not in live(incident)
    assert any(o.code == code and o.polarity is Polarity.NEGATED for o in incident.observations)


@pytest.mark.parametrize(
    ("text", "code"),
    [
        # Ordinary injuries are not self-harm.
        ("He fell and hurt himself but he is fine.", "SELF_HARM_RISK"),
        # A house that burned is a fire, not a burn injury.
        ("The garage is burning.", "BURN_INJURY"),
        # The caller being lost is a location problem, not a missing person.
        ("I'm lost and I don't know where I am.", "MISSING_PERSON"),
        # A noise is not a collision.
        ("I heard a loud bang outside.", "TRAFFIC_COLLISION"),
    ],
)
def test_lookalike_phrases_do_not_fire(text: str, code: str) -> None:
    assert code not in {o.code for o in parse_text(text).observations}


def test_every_new_code_has_a_rule_with_its_declared_severity() -> None:
    ruleset = load_ruleset("research-1.2.0")
    by_code = {r.all_of[0]: r for r in ruleset.rules if len(r.all_of) == 1}
    for code, severity in NEW_CODES.items():
        assert by_code[code].severity is severity, code


@pytest.mark.parametrize(
    ("text", "priority"),
    [
        ("My toddler drank some bleach.", "P0"),  # high, escalated for a child
        ("There's been a car crash, nobody is hurt.", "P2"),
        ("There's been a car crash and the driver is trapped.", "P0"),
        ("My wife is in labor.", "P1"),
    ],
)
def test_new_cues_set_priority(text: str, priority: str) -> None:
    assessment = assess(parse_text(text), assessment_id="a", assessed_at=AT)
    assert assessment.advisory_priority == priority


def test_older_rulesets_ignore_the_new_cues() -> None:
    incident = parse_text("My wife is in labor.")
    old = assess(
        incident, assessment_id="a", assessed_at=AT, ruleset=load_ruleset("research-1.1.0")
    )
    assert old.advisory_priority != "P1"
