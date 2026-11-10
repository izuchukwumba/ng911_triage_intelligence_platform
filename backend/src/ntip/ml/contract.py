"""The inference contract between the platform and any extraction model.

Design v1.2, section 3A.5. A model returns *candidates*: hypotheses about
what the source says, each quoting the span it is based on. Nothing a model
returns is a fact or a decision; candidates are verified against the source
(``ntip.ml.verify``) and only then may join an incident as model-extracted
observations.
"""

from typing import Literal

from pydantic import Field

from ntip.schema.base import Identifier, ReasonCode, SchemaModel, SourceSpan, UtcDatetime
from ntip.schema.canonical import InferenceMode, Polarity, Temporality

CONTRACT_VERSION = "1.0.0"


class InferenceMessage(SchemaModel):
    source_event_id: Identifier
    text: str


class InferenceRequest(SchemaModel):
    contract_version: Literal["1.0.0"] = "1.0.0"
    request_id: Identifier
    incident_id: Identifier
    messages: list[InferenceMessage] = Field(min_length=1)
    language_hint: str | None = None


class Candidate(SchemaModel):
    code: ReasonCode
    polarity: Polarity
    temporality: Temporality = Temporality.CURRENT
    source_event_id: Identifier
    span: SourceSpan
    evidence_text: str = Field(min_length=1)
    # A model score in [0, 1]. Not a probability unless the response says it
    # is calibrated (design v1.2, section 3A.5).
    confidence: float = Field(ge=0, le=1)
    status: Literal["unverified_model_hypothesis"] = "unverified_model_hypothesis"


class Abstention(SchemaModel):
    """The model declines to decide about a code (design v1.2, section 3A.1)."""

    code: ReasonCode
    reason: str = Field(min_length=1)


class InferenceResponse(SchemaModel):
    contract_version: Literal["1.0.0"] = "1.0.0"
    request_id: Identifier
    model_id: Identifier
    model_version: str = Field(min_length=1)
    candidates: list[Candidate] = Field(default_factory=list)
    abstentions: list[Abstention] = Field(default_factory=list)
    # True only when calibration has been measured on held-out data.
    calibrated: bool = False
    runtime_ms: float = Field(ge=0)


class ModelOutput(SchemaModel):
    """The exact request and response of one model call, kept for audit.

    Generative or retrained models are not guaranteed to reproduce their
    output, so replay of a model-assisted incident uses this recorded output
    rather than calling the model again (design v1.2, section 3A.9).
    """

    output_id: Identifier
    incident_id: Identifier
    recorded_at: UtcDatetime
    mode: InferenceMode
    request: InferenceRequest
    response: InferenceResponse | None
    error: str | None = None
