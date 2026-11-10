"""Canonical layer: normalised incident facts with provenance.

Everything here is derived from source events and points back to them. An
observation records *what the source said*, how it was said (affirmed,
negated, hypothetical, second-hand, ...) and which extractor produced it. It
does not record urgency; that belongs to the advisory layer.
"""

from collections.abc import Iterable, Iterator, Mapping
from enum import StrEnum
from typing import Self

from pydantic import Field, model_validator

from ntip.schema.base import (
    SCHEMA_VERSION,
    Fact,
    FactStatus,
    Identifier,
    ReasonCode,
    SchemaModel,
    SourceSpan,
    UtcDatetime,
)
from ntip.schema.source import SourceEvent

# ---------------------------------------------------------------------------
# Provenance
# ---------------------------------------------------------------------------


class ExtractorKind(StrEnum):
    RULE = "rule"
    MODEL = "model"
    OPERATOR = "operator"


class Extractor(SchemaModel):
    """The component that produced a fact, pinned to a version."""

    kind: ExtractorKind
    extractor_id: Identifier
    version: str = Field(min_length=1)


class Evidence(SchemaModel):
    """A quoted stretch of a specific source event."""

    source_event_id: Identifier
    span: SourceSpan
    text: str = Field(min_length=1)


# ---------------------------------------------------------------------------
# Observations
# ---------------------------------------------------------------------------


class Polarity(StrEnum):
    AFFIRMED = "affirmed"  # "he is not breathing" -> NOT_BREATHING affirmed
    NEGATED = "negated"  # "there is no fire"
    UNCERTAIN = "uncertain"  # "I think I heard a gunshot"


class Temporality(StrEnum):
    CURRENT = "current"
    HISTORICAL = "historical"  # "there was a fire here yesterday"
    HYPOTHETICAL = "hypothetical"  # "if he stops breathing ..."


class Attribution(StrEnum):
    FIRST_HAND = "first_hand"  # the speaker observed it
    SECOND_HAND = "second_hand"  # "someone said there was a fire"
    UNSPECIFIED = "unspecified"


class Observation(SchemaModel):
    observation_id: Identifier
    code: ReasonCode
    polarity: Polarity
    temporality: Temporality = Temporality.CURRENT
    attribution: Attribution = Attribution.UNSPECIFIED
    evidence: Evidence
    extractor: Extractor
    # Heuristic and uncalibrated: must not be read as a probability
    # (design v1.2, section 6.4).
    heuristic_confidence: float | None = Field(default=None, ge=0, le=1)


# ---------------------------------------------------------------------------
# Locations
# ---------------------------------------------------------------------------


class LocationRole(StrEnum):
    """Location concepts that must not be conflated (design v1.2, section 8.1)."""

    REPORTED = "reported"  # what the speaker said
    DEVICE_PROVIDED = "device_provided"  # supplied by an authorised test payload
    GEOCODED = "geocoded"  # derived point, possibly approximate


class LocationValidation(StrEnum):
    UNVERIFIED = "unverified"
    STRUCTURALLY_COMPLETE = "structurally_complete"  # L0/L1 checks passed
    CONFLICTING = "conflicting"  # disagrees with another candidate (L2)
    OPERATOR_VERIFIED = "operator_verified"
    REFERENCE_VALIDATED = "reference_validated"  # checked against GIS data (L3)


_EXTERNALLY_VALIDATED = {
    LocationValidation.OPERATOR_VERIFIED,
    LocationValidation.REFERENCE_VALIDATED,
}


class CivicAddress(SchemaModel):
    house_number: str | None = None
    street: str | None = None
    unit: str | None = None
    floor: str | None = None
    locality: str | None = None
    region: str | None = None
    postal_code: str | None = None
    landmark: str | None = None


class Coordinates(SchemaModel):
    lat: float = Field(ge=-90, le=90)
    lng: float = Field(ge=-180, le=180)
    crs: str = "EPSG:4326"
    uncertainty_m: float | None = Field(default=None, gt=0)


class LocationCandidate(SchemaModel):
    location_id: Identifier
    role: LocationRole
    raw_text: str | None = None
    civic_address: CivicAddress | None = None
    coordinates: Coordinates | None = None
    evidence: Evidence | None = None
    extractor: Extractor
    validation: LocationValidation = LocationValidation.UNVERIFIED
    validation_source: str | None = None
    missing_fields: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _check(self) -> Self:
        if self.role is LocationRole.REPORTED:
            if self.evidence is None:
                raise ValueError("a reported location must quote its evidence")
            # A parser or language model must never invent coordinates for
            # something a caller said (design v1.2, section 3A.1).
            if self.coordinates is not None:
                raise ValueError("a reported location cannot carry coordinates; geocode it")
        if self.validation in _EXTERNALLY_VALIDATED:
            if self.validation_source is None:
                raise ValueError(f"{self.validation} requires a validation_source")
            if self.extractor.kind is ExtractorKind.MODEL:
                raise ValueError("a model cannot mark a location as validated")
        return self


# ---------------------------------------------------------------------------
# Incident
# ---------------------------------------------------------------------------


class IncidentDomain(StrEnum):
    POLICE = "police"
    FIRE = "fire"
    EMS = "ems"
    HAZMAT = "hazmat"
    OTHER = "other"
    UNKNOWN = "unknown"


class ClassificationStatus(StrEnum):
    PROVISIONAL = "provisional"
    CONFIRMED = "confirmed"  # only through a human review


class Classification(SchemaModel):
    domain: IncidentDomain
    subtype: str | None = None
    status: ClassificationStatus = ClassificationStatus.PROVISIONAL
    # Heuristic and uncalibrated, like Observation.heuristic_confidence.
    heuristic_confidence: float | None = Field(default=None, ge=0, le=1)


class ConflictKind(StrEnum):
    # The same cue is both affirmed and denied, e.g. "he's breathing ... he's not breathing".
    OBSERVATION_POLARITY = "observation_polarity"
    # Two reported locations disagree, e.g. the caller corrects the address.
    LOCATION_MISMATCH = "location_mismatch"


class Conflict(SchemaModel):
    """Incompatible statements, kept side by side instead of resolved silently."""

    conflict_id: Identifier
    kind: ConflictKind
    code: ReasonCode | None = None
    observation_ids: list[Identifier] = Field(default_factory=list)
    location_ids: list[Identifier] = Field(default_factory=list)

    @model_validator(mode="after")
    def _check(self) -> Self:
        refs = (
            self.observation_ids
            if self.kind is ConflictKind.OBSERVATION_POLARITY
            else self.location_ids
        )
        if len(set(refs)) < 2:
            raise ValueError(f"a {self.kind} conflict must reference at least two items")
        return self


def _not_reported() -> Fact[int]:
    return Fact[int](status=FactStatus.NOT_REPORTED)


class Incident(SchemaModel):
    """The canonical interpretation of one or more source events."""

    schema_version: str = SCHEMA_VERSION
    incident_id: Identifier
    source_event_ids: list[Identifier] = Field(min_length=1)
    derived_at: UtcDatetime
    classification: Classification
    observations: list[Observation] = Field(default_factory=list)
    locations: list[LocationCandidate] = Field(default_factory=list)
    victim_count: Fact[int] = Field(default_factory=_not_reported)
    conflicts: list[Conflict] = Field(default_factory=list)
    language: str | None = None

    @model_validator(mode="after")
    def _check(self) -> Self:
        _require_unique("observation_id", (o.observation_id for o in self.observations))
        _require_unique("location_id", (loc.location_id for loc in self.locations))
        _require_unique("conflict_id", (c.conflict_id for c in self.conflicts))
        known = set(self.source_event_ids)
        for evidence in self.evidence():
            if evidence.source_event_id not in known:
                raise ValueError(
                    f"evidence cites unknown source event {evidence.source_event_id!r}"
                )
        observation_ids = {o.observation_id for o in self.observations}
        location_ids = {loc.location_id for loc in self.locations}
        for conflict in self.conflicts:
            for ref in conflict.observation_ids:
                if ref not in observation_ids:
                    raise ValueError(f"conflict cites unknown observation {ref!r}")
            for ref in conflict.location_ids:
                if ref not in location_ids:
                    raise ValueError(f"conflict cites unknown location {ref!r}")
        return self

    def evidence(self) -> Iterator[Evidence]:
        for observation in self.observations:
            yield observation.evidence
        for location in self.locations:
            if location.evidence is not None:
                yield location.evidence


def _require_unique(name: str, values: Iterable[str]) -> None:
    seen: set[str] = set()
    for value in values:
        if value in seen:
            raise ValueError(f"duplicate {name} {value!r}")
        seen.add(value)


def provenance_errors(incident: Incident, sources: Mapping[str, SourceEvent]) -> list[str]:
    """Check that every quoted evidence span matches its source text.

    Returns a list of problems; empty means every span is grounded. An
    extracted claim whose quote does not match the source is unsupported and
    must not enter the record (design v1.2, sections 3A.5 and 3A.6).
    """
    errors: list[str] = []
    for evidence in incident.evidence():
        source = sources.get(evidence.source_event_id)
        if source is None:
            errors.append(f"source event {evidence.source_event_id!r} not provided")
            continue
        span = evidence.span
        if span.end > len(source.text):
            errors.append(f"span [{span.start}, {span.end}) is outside {source.source_event_id!r}")
            continue
        quoted = span.slice(source.text)
        if quoted != evidence.text:
            errors.append(
                f"span [{span.start}, {span.end}) of {source.source_event_id!r} reads "
                f"{quoted!r}, not {evidence.text!r}"
            )
    return errors
