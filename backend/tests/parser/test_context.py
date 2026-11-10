import pytest

from ntip.parser.context import CueContext, analyse
from ntip.parser.text import Match
from ntip.schema.canonical import Attribution, Polarity, Temporality


def context(text: str, cue: str) -> CueContext:
    start = text.lower().index(cue)
    return analyse(text, Match(start, start + len(cue), text[start : start + len(cue)]))


class TestPolarity:
    @pytest.mark.parametrize(
        ("text", "cue"),
        [
            ("There is no fire.", "fire"),
            ("I looked around and there was no gun, he was unarmed.", "gun"),
            ("He walked in without a gun.", "gun"),
            ("She fell down the stairs but denies any bleeding.", "bleeding"),
            ("Police ruled out a gun after searching the car.", "gun"),
            ("He isn't bleeding anymore.", "bleeding"),
            ("He is no longer bleeding.", "bleeding"),
            ("No hay sangre.", "sangre"),
        ],
    )
    def test_negated(self, text: str, cue: str) -> None:
        assert context(text, cue).polarity is Polarity.NEGATED

    @pytest.mark.parametrize(
        ("text", "cue"),
        [
            ("He is not breathing.", "not breathing"),  # negation inside the cue itself
            ("He can't stop bleeding.", "bleeding"),  # pseudo-negation
            ("No, he is bleeding badly.", "bleeding"),  # interjection
            ("He had a gun. No injuries so far.", "gun"),  # negation in another sentence
            ("He is conscious but bleeding.", "bleeding"),
            ("There is no smoke, my mother fell.", "fell"),  # scope ends at a comma
            ("No fire and he is bleeding.", "bleeding"),  # scope ends at "and"
        ],
    )
    def test_affirmed(self, text: str, cue: str) -> None:
        assert context(text, cue).polarity is Polarity.AFFIRMED

    def test_negation_does_not_reach_across_a_long_gap(self) -> None:
        text = "I do not know what happened to him at all but there is blood"
        assert context(text, "blood").polarity is Polarity.AFFIRMED

    @pytest.mark.parametrize(
        ("text", "cue"),
        [
            ("I think I heard a gunshot.", "gunshot"),
            ("It sounds like a gunshot.", "gunshot"),
            ("I'm not sure if he is breathing.", "breathing"),
            ("Creo que hay un incendio.", "incendio"),
        ],
    )
    def test_uncertain(self, text: str, cue: str) -> None:
        assert context(text, cue).polarity is Polarity.UNCERTAIN


class TestTemporality:
    def test_historical_cue_after_the_match(self) -> None:
        text = "He was not breathing earlier but is now."
        assert context(text, "not breathing").temporality is Temporality.HISTORICAL

    def test_historical_cue_before_the_match(self) -> None:
        assert context("Yesterday there was a fire here.", "fire").temporality is (
            Temporality.HISTORICAL
        )

    def test_hypothetical(self) -> None:
        text = "I'm calling in case he stops breathing."
        assert context(text, "stops breathing").temporality is Temporality.HYPOTHETICAL

    def test_conditional_with_modal_is_hypothetical(self) -> None:
        text = "I'm worried my dad might have a heart attack if he keeps shoveling snow."
        assert context(text, "heart attack").temporality is Temporality.HYPOTHETICAL

    def test_modal_without_condition_stays_current_and_uncertain(self) -> None:
        result = context("He might be having a heart attack.", "heart attack")
        assert (result.temporality, result.polarity) == (Temporality.CURRENT, Polarity.UNCERTAIN)

    def test_embedded_question_if_is_not_a_condition(self) -> None:
        text = "I'm not sure if he's breathing, he's on the floor and won't answer me."
        assert context(text, "won't answer").temporality is Temporality.CURRENT

    def test_current_by_default(self) -> None:
        assert context("There is a fire.", "fire").temporality is Temporality.CURRENT


class TestAttribution:
    def test_second_hand(self) -> None:
        text = "Someone said there was a fire yesterday."
        result = context(text, "fire")
        assert result.attribution is Attribution.SECOND_HAND
        assert result.temporality is Temporality.HISTORICAL

    def test_first_hand(self) -> None:
        assert context("I can see flames.", "flames").attribution is Attribution.FIRST_HAND

    def test_unspecified_by_default(self) -> None:
        assert context("There are flames.", "flames").attribution is Attribution.UNSPECIFIED
