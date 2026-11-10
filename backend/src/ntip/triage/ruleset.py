"""Versioned, data-driven triage rules (design v1.2, sections 7.2 and 7.5).

A ruleset is a JSON file under ``rulesets/``. Released files are immutable:
their sha256 digests are pinned in ``RELEASED`` and a test fails if one
changes. Any change to rules ships as a new file with a new version, so every
stored assessment can be traced to the exact rules that produced it.
"""

import json
from functools import cache
from importlib import resources
from typing import Literal, Self

from pydantic import Field, model_validator

from ntip.schema.advisory import AdvisoryPriority, SeverityBand
from ntip.schema.base import Identifier, ReasonCode, SchemaModel, sha256_digest

DEFAULT_RULESET = "research-1.0.0"

# Released ruleset files and their content digests. Never edit a released
# file; add a new one.
RELEASED: dict[str, str] = {
    "research-1.0.0": "sha256:8f2637172d4e395686b22e54b40e38e97c3a1b9b8a98ea824bbddfa839a29c87",
}

# Bands from least to most severe; "undetermined" is handled separately.
SEVERITY_ORDER: list[SeverityBand] = [
    SeverityBand.LOW,
    SeverityBand.STANDARD,
    SeverityBand.ELEVATED,
    SeverityBand.HIGH,
    SeverityBand.CRITICAL,
]


class Rule(SchemaModel):
    """Fires when every code in ``all_of`` is reported as a current affirmation.

    ``severity`` sets a floor on the incident's severity band. ``escalate``
    instead raises the band reached by other rules by one step (used for
    aggravating factors such as children or multiple victims), and acts as a
    floor of ``severity`` when nothing else fired.
    """

    id: Identifier
    version: str = Field(min_length=1)
    description: str = Field(min_length=1)
    all_of: list[ReasonCode] = Field(min_length=1)
    severity: SeverityBand
    effect: Literal["floor", "escalate"] = "floor"
    reason_code: ReasonCode

    @model_validator(mode="after")
    def _check(self) -> Self:
        if self.severity is SeverityBand.UNDETERMINED:
            raise ValueError("a rule cannot set severity to undetermined")
        return self


class Ruleset(SchemaModel):
    ruleset_id: Identifier
    version: str
    priority_scheme: Literal["research-v1"]
    description: str
    rules: list[Rule] = Field(min_length=1)
    # Research queue ordering per band. "undetermined" must map to a priority
    # that still puts the incident in front of a human promptly.
    priority_by_severity: dict[SeverityBand, AdvisoryPriority]
    # Classifier heuristic confidence below which a human confirms the domain.
    confirm_classification_below: float = Field(ge=0, le=1)

    @model_validator(mode="after")
    def _check(self) -> Self:
        ids = [rule.id for rule in self.rules]
        if len(ids) != len(set(ids)):
            raise ValueError("rule ids must be unique")
        missing = set(SeverityBand) - set(self.priority_by_severity)
        if missing:
            raise ValueError(f"priority_by_severity is missing {sorted(missing)}")
        return self

    @property
    def name(self) -> str:
        return f"{self.ruleset_id}-{self.version}"


def _raw(name: str) -> str:
    return resources.files("ntip.triage.rulesets").joinpath(f"{name}.json").read_text("utf-8")


def ruleset_digest(name: str) -> str:
    # Normalise line endings so the digest does not depend on git checkout settings.
    return sha256_digest(_raw(name).replace("\r\n", "\n"))


@cache
def load_ruleset(name: str = DEFAULT_RULESET) -> Ruleset:
    ruleset = Ruleset.model_validate(json.loads(_raw(name)))
    if ruleset.name != name:
        raise ValueError(f"file {name}.json declares ruleset {ruleset.name}")
    return ruleset
