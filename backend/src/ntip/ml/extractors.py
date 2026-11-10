"""Ways to obtain model candidates: in-process or over HTTP.

Both satisfy ``ModelExtractor``. The HTTP client enforces a hard timeout so a
slow or unavailable model can never hold up ingestion; the pipeline then
falls back to the rules baseline and marks the record degraded (design v1.2,
sections 3A.3 and 3B.1).
"""

import json
import time
import urllib.error
import urllib.request
from datetime import UTC, datetime
from typing import Protocol

from ntip.ml.contract import Candidate, InferenceRequest, InferenceResponse
from ntip.parser.parser import PARSER_VERSION, parse
from ntip.schema.base import SourceSpan
from ntip.schema.source import SourceEvent

# Fixed timestamp for the throwaway source events RulesAsModel builds.
_EPOCH = datetime(2026, 1, 1, tzinfo=UTC)


class ModelExtractor(Protocol):
    model_id: str
    model_version: str

    def infer(self, request: InferenceRequest) -> InferenceResponse: ...


class InferenceUnavailable(Exception):
    """The model could not produce a usable response in time."""


class HttpExtractor:
    """Calls an inference service's POST /v1/infer with a hard timeout."""

    def __init__(self, base_url: str, *, timeout_s: float = 2.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout_s = timeout_s
        info = self._get("/model-info")
        self.model_id = str(info.get("model_id", "unknown"))
        self.model_version = str(info.get("model_version", "unknown"))

    def _get(self, path: str) -> dict[str, object]:
        try:
            with urllib.request.urlopen(self.base_url + path, timeout=self.timeout_s) as resp:
                data: dict[str, object] = json.loads(resp.read())
                return data
        except (OSError, ValueError):
            return {}

    def infer(self, request: InferenceRequest) -> InferenceResponse:
        req = urllib.request.Request(
            self.base_url + "/v1/infer",
            data=request.model_dump_json().encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout_s) as resp:
                return InferenceResponse.model_validate_json(resp.read())
        except (OSError, urllib.error.URLError, ValueError) as err:
            raise InferenceUnavailable(f"{type(err).__name__}: {err}") from None


class RulesAsModel:
    """The rules parser exposed through the model contract.

    Not a learned model: it exists so the contract, service and fusion path
    can be exercised end to end, and as a reference point (its hybrid output
    must equal the rules output).
    """

    model_id = "b0-rules-as-model"
    model_version = PARSER_VERSION

    def infer(self, request: InferenceRequest) -> InferenceResponse:
        started = time.perf_counter()
        sources = [
            SourceEvent.from_text(
                source_event_id=m.source_event_id,
                incident_id=request.incident_id,
                received_at=_EPOCH,
                text=m.text,
            )
            for m in request.messages
        ]
        incident = parse(sources, derived_at=_EPOCH)
        candidates = [
            Candidate(
                code=o.code,
                polarity=o.polarity,
                temporality=o.temporality,
                source_event_id=o.evidence.source_event_id,
                span=SourceSpan(start=o.evidence.span.start, end=o.evidence.span.end),
                evidence_text=o.evidence.text,
                confidence=1.0,
            )
            for o in incident.observations
        ]
        return InferenceResponse(
            request_id=request.request_id,
            model_id=self.model_id,
            model_version=self.model_version,
            candidates=candidates,
            runtime_ms=(time.perf_counter() - started) * 1000,
        )
