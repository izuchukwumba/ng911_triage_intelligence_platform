"""Property-based and metamorphic tests (design v1.2, section 6.5).

Hypothesis generates inputs; each test states a property that must hold for
all of them, not just for hand-picked examples.
"""

from datetime import UTC, datetime

from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from ntip.parser.parser import parse
from ntip.schema.canonical import Incident, Polarity, provenance_errors
from ntip.schema.source import SourceEvent
from ntip.triage.engine import assess

AT = datetime(2026, 11, 10, tzinfo=UTC)
SETTINGS = settings(max_examples=150, deadline=None, suppress_health_check=[HealthCheck.too_slow])

CRITICAL = [
    "my father is not breathing",
    "she is unconscious",
    "people are trapped inside",
    "he has been shot and is bleeding",
]
ADDRESSES = ["at 12 Oak Street", "near 5th and Main", "outside the library", ""]


def source(text: str) -> SourceEvent:
    return SourceEvent.from_text(source_event_id="e1", incident_id="i1", received_at=AT, text=text)


def parse_text(text: str) -> Incident:
    return parse([source(text)], derived_at=AT)


@SETTINGS
@given(st.text(min_size=1, max_size=400).filter(lambda t: t.strip()))
def test_parser_never_crashes_and_every_span_quotes_the_source(text: str) -> None:
    incident = parse_text(text)
    assert provenance_errors(incident, {"e1": source(text)}) == []
    assess(incident, assessment_id="a", assessed_at=AT)  # assessment never crashes either


@SETTINGS
@given(st.sampled_from(CRITICAL), st.sampled_from([".", "!", "!!", "...", ""]))
def test_punctuation_does_not_change_the_assessment(phrase: str, ending: str) -> None:
    plain = assess(parse_text(phrase), assessment_id="a", assessed_at=AT)
    punctuated = assess(parse_text(phrase.capitalize() + ending), assessment_id="a", assessed_at=AT)
    assert (punctuated.severity_band, punctuated.advisory_priority) == (
        plain.severity_band,
        plain.advisory_priority,
    )


@SETTINGS
@given(st.sampled_from(["fire", "smoke", "a gun", "bleeding", "a knife"]))
def test_adding_a_negation_flips_polarity(cue: str) -> None:
    def polarities(text: str) -> set[Polarity]:
        return {o.polarity for o in parse_text(text).observations}

    assert Polarity.AFFIRMED in polarities(f"There is {cue}.")
    assert polarities(f"There is no {cue}.") == {Polarity.NEGATED}


@SETTINGS
@given(st.sampled_from(CRITICAL), st.sampled_from(ADDRESSES))
def test_removing_the_location_never_lowers_priority(phrase: str, address: str) -> None:
    with_location = assess(parse_text(f"{phrase} {address}."), assessment_id="a", assessed_at=AT)
    without = assess(
        parse_text(f"{phrase}. I don't know where I am."), assessment_id="a", assessed_at=AT
    )
    assert without.advisory_priority is not None and with_location.advisory_priority is not None
    assert int(without.advisory_priority[1]) <= int(with_location.advisory_priority[1])


@SETTINGS
@given(
    st.sampled_from(CRITICAL),
    st.sampled_from(["This is not a prank. ", "Never mind the joke, ", ""]),
)
def test_prank_words_never_lower_a_critical_report(phrase: str, prefix: str) -> None:
    result = assess(parse_text(prefix + phrase + "."), assessment_id="a", assessed_at=AT)
    assert result.advisory_priority == "P0"


@SETTINGS
@given(st.text(alphabet=st.characters(categories=["L", "N", "Zs", "P"]), max_size=200))
def test_appending_unrelated_text_never_lowers_a_critical_report(noise: str) -> None:
    base = "My father is not breathing."
    result = assess(parse_text(f"{base} {noise}".strip()), assessment_id="a", assessed_at=AT)
    assert result.severity_band == "critical"
