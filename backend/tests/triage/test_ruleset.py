import pytest
from pydantic import ValidationError

from ntip.parser.lexicon import OBSERVATION_CUES
from ntip.schema.advisory import SeverityBand
from ntip.triage.ruleset import RELEASED, Rule, Ruleset, load_ruleset, ruleset_digest


@pytest.mark.parametrize("name", sorted(RELEASED))
def test_released_rulesets_are_immutable(name: str) -> None:
    assert ruleset_digest(name) == RELEASED[name], (
        f"{name}.json changed after release. Revert it and add a new ruleset version instead."
    )


@pytest.mark.parametrize("name", sorted(RELEASED))
def test_released_rulesets_load(name: str) -> None:
    assert load_ruleset(name).name == name


def test_rules_only_reference_codes_the_parser_emits() -> None:
    emitted = set(OBSERVATION_CUES)
    for rule in load_ruleset().rules:
        assert set(rule.all_of) <= emitted, rule.id


def test_undetermined_severity_still_gets_a_prompt_priority() -> None:
    ruleset = load_ruleset()
    assert (
        ruleset.priority_by_severity[SeverityBand.UNDETERMINED]
        <= (ruleset.priority_by_severity[SeverityBand.STANDARD])
    )


def test_rule_cannot_set_undetermined_severity() -> None:
    with pytest.raises(ValidationError, match="undetermined"):
        Rule(
            id="R-X",
            version="1",
            description="x",
            all_of=["FIRE_REPORTED"],
            severity=SeverityBand.UNDETERMINED,
            reason_code="X",
        )


def test_ruleset_needs_a_priority_for_every_band() -> None:
    raw = load_ruleset().model_dump()
    del raw["priority_by_severity"]["low"]
    with pytest.raises(ValidationError, match="missing"):
        Ruleset.model_validate(raw)
