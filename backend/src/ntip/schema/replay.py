"""Replay runs (design v1.2, section 10).

A replay re-assesses stored incidents without changing them. It answers two
separate questions and records the answers as an immutable ReplayRun:

- reproducibility: does re-assessing the stored incident with the ruleset
  recorded on its assessment give exactly the stored result?
- comparison: what would a candidate ruleset change, case by case?
"""

from typing import Self

from pydantic import Field, model_validator

from ntip.schema.advisory import AdvisoryPriority, SeverityBand
from ntip.schema.base import (
    DEFAULT_TENANT,
    SCHEMA_VERSION,
    Identifier,
    ReasonCode,
    SchemaModel,
    UtcDatetime,
)


class ReplayOutcome(SchemaModel):
    """What one ruleset produced for one incident."""

    ruleset_version: str
    severity_band: SeverityBand
    advisory_priority: AdvisoryPriority | None
    reason_codes: list[ReasonCode]


class ReplayCase(SchemaModel):
    incident_id: Identifier
    stored_assessment_id: Identifier
    stored: ReplayOutcome
    # Re-assessment with the stored assessment's own ruleset.
    reproduced: ReplayOutcome | None
    reproducible: bool | None
    # Re-assessment with the candidate ruleset, if one was requested.
    candidate: ReplayOutcome | None
    priority_changed: bool | None
    # The candidate gives a less urgent priority than what is stored.
    candidate_lowers_priority: bool | None
    # Why the incident could not be replayed (e.g. its processing had failed).
    skipped_reason: str | None = None


class ReplaySummary(SchemaModel):
    incidents: int
    skipped: int
    reproducible: int
    not_reproducible: int
    priority_changed: int
    candidate_lowers_priority: int


class ReplayRun(SchemaModel):
    schema_version: str = SCHEMA_VERSION
    run_id: Identifier
    created_at: UtcDatetime
    requested_by: Identifier
    candidate_ruleset: str | None
    engine_version: str
    # A run covers one tenant's incidents and is visible to that tenant only (2.5.0).
    tenant_id: Identifier = DEFAULT_TENANT
    cases: list[ReplayCase]
    summary: ReplaySummary
    note: str = Field(
        default=(
            "Replay never modifies stored incidents or assessments. Differences are "
            "illustrative and are not validated improvements."
        )
    )

    @model_validator(mode="after")
    def _check(self) -> Self:
        if self.summary.incidents != len(self.cases):
            raise ValueError("summary.incidents must equal the number of cases")
        return self
