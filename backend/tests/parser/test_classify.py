import pytest

from ntip.parser.classify import classify, detect_language
from ntip.schema.canonical import Classification, IncidentDomain


def classify_text(text: str) -> Classification:
    return classify(text, detect_language(text))


class TestLanguage:
    def test_spanish(self) -> None:
        text = "Mi esposo no está respirando en la Calle Pino 789. Por favor vengan rápido."
        assert detect_language(text) == "es"

    def test_english(self) -> None:
        text = "My father is not breathing and there is no pulse. We are at 123 Oak Street."
        assert detect_language(text) == "en"

    def test_no_signal(self) -> None:
        assert detect_language("12345") is None


class TestDomain:
    @pytest.mark.parametrize(
        ("text", "domain"),
        [
            # Failed in the TypeScript parser: "blood" contained "od" (overdose).
            ("Someone has been shot near 5th street. There is blood everywhere.", "police"),
            ("My father is having a heart attack. He is not breathing at 123 Oak Street.", "ems"),
            ("The house at 742 Evergreen Terrace is on fire. Flames are coming out.", "fire"),
            ("There is a strong chemical smell and a gas leak at 88 Lincoln Drive.", "hazmat"),
            ("Mi padre tuvo un ataque al corazón. No respira y no tiene pulso.", "ems"),
            ("hello there", "unknown"),
        ],
    )
    def test_domain(self, text: str, domain: str) -> None:
        assert classify_text(text).domain == domain

    def test_negated_keywords_do_not_vote(self) -> None:
        assert classify_text("There is no fire and no smoke, my mother fell.").domain == "ems"

    def test_classification_is_provisional_with_bounded_confidence(self) -> None:
        result = classify_text("Someone was shot. He is bleeding. There is a gun.")
        assert result.status == "provisional"
        assert result.heuristic_confidence is not None
        assert 0 < result.heuristic_confidence <= 0.9

    def test_prank_only_call_is_other(self) -> None:
        text = "Ha ha it's just a prank, we were filming. Nobody is actually hurt."
        assert classify_text(text).domain == "other"

    def test_prank_word_does_not_override_a_real_domain(self) -> None:
        assert classify_text("This is not a prank, there is a fire.").domain == "fire"

    @pytest.mark.parametrize(
        ("text", "domain"),
        [
            ("Two cars crashed on Route 66.", "ems"),
            ("Someone broke into my car on Elm Street.", "police"),
            ("Can you do a welfare check? My neighbor lives alone.", "ems"),
            ("I think a woman overdosed on something.", "ems"),
            ("My grandfather is seizing on the floor.", "ems"),
        ],
    )
    def test_extended_domain_keywords(self, text: str, domain: str) -> None:
        assert classify_text(text).domain == domain

    def test_unknown_has_low_confidence(self) -> None:
        assert classify_text("hello there").heuristic_confidence == 0.1


class TestSubtype:
    @pytest.mark.parametrize(
        ("text", "domain", "subtype"),
        [
            ("My friend was stabbed with a knife at 456 Elm Road.", "police", "stabbing"),
            (
                "My brother is not breathing. We are at 123 Oak Street.",
                "ems",
                "respiratory_distress",
            ),
            (
                "There is a house fire at 350 Fifth Avenue. Flames are spreading.",
                "fire",
                "structure_fire",
            ),
        ],
    )
    def test_subtype(self, text: str, domain: IncidentDomain, subtype: str) -> None:
        result = classify_text(text)
        assert (result.domain, result.subtype) == (domain, subtype)

    def test_no_subtype_when_nothing_specific_matches(self) -> None:
        assert classify_text("There is smoke somewhere.").subtype is None
