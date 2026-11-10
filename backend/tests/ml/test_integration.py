import threading
import time
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from itertools import count
from typing import Any

import pytest
from fastapi.testclient import TestClient

from ntip.ml.contract import InferenceMessage, InferenceRequest, InferenceResponse
from ntip.ml.extractors import HttpExtractor, InferenceUnavailable, RulesAsModel
from ntip.ml.service import create_inference_app
from ntip.pipeline import Pipeline
from ntip.schema.canonical import ConflictKind, ExtractorKind, InferenceMode, InferenceStatus
from ntip.store import InMemoryEventStore

TEXT = "My father is not breathing. We are at 12 Oak Street."


def make_pipeline(**overrides: Any) -> Pipeline:
    ticks, ids = count(), count(1)
    defaults: dict[str, Any] = {
        "store": InMemoryEventStore(),
        "clock": lambda: datetime(2026, 11, 9, 12, tzinfo=UTC) + timedelta(seconds=next(ticks)),
        "new_id": lambda prefix: f"{prefix}_{next(ids)}",
    }
    return Pipeline(**{**defaults, **overrides})


class Broken:
    model_id = "broken"
    model_version = "0"

    def infer(self, request: InferenceRequest) -> InferenceResponse:
        raise InferenceUnavailable("model process crashed")


class TestPipelineModes:
    def test_rules_only_is_the_default_and_marked_disabled(self) -> None:
        pipeline = make_pipeline()
        result = pipeline.ingest(TEXT)
        assert result.incident is not None and result.incident.inference is not None
        assert result.incident.inference.status is InferenceStatus.DISABLED
        assert pipeline.store.model_outputs(result.incident_id) == []

    def test_hybrid_with_rules_as_model_agrees_with_the_rules(self) -> None:
        pipeline = make_pipeline(
            inference_mode=InferenceMode.HYBRID_REVIEW, extractor=RulesAsModel()
        )
        result = pipeline.ingest(TEXT)
        incident = result.incident
        assert incident is not None and incident.inference is not None
        assert incident.inference.status is InferenceStatus.OK
        model_codes = {
            o.code for o in incident.observations if o.extractor.kind is ExtractorKind.MODEL
        }
        rule_codes = {
            o.code for o in incident.observations if o.extractor.kind is ExtractorKind.RULE
        }
        assert model_codes == rule_codes
        assert not [c for c in incident.conflicts if c.kind is ConflictKind.MODEL_RULE_DISAGREEMENT]
        assert result.assessment.advisory_priority == "P0"

    def test_shadow_records_the_model_but_assesses_on_rules(self) -> None:
        pipeline = make_pipeline(inference_mode=InferenceMode.ML_SHADOW, extractor=RulesAsModel())
        result = pipeline.ingest(TEXT)
        assert result.incident is not None
        assert all(o.extractor.kind is ExtractorKind.RULE for o in result.incident.observations)
        [output] = pipeline.store.model_outputs(result.incident_id)
        assert output.response is not None and output.response.candidates
        assert output.mode is InferenceMode.ML_SHADOW

    def test_model_failure_degrades_but_ingestion_succeeds(self) -> None:
        pipeline = make_pipeline(inference_mode=InferenceMode.HYBRID_REVIEW, extractor=Broken())
        result = pipeline.ingest(TEXT)
        assert result.incident is not None and result.incident.inference is not None
        assert result.incident.inference.status is InferenceStatus.DEGRADED
        assert "crashed" in (result.incident.inference.detail or "")
        assert result.assessment.advisory_priority == "P0"  # rules still see the critical cue
        [output] = pipeline.store.model_outputs(result.incident_id)
        assert output.response is None and output.error

    def test_mode_without_a_model_is_degraded(self) -> None:
        result = make_pipeline(inference_mode=InferenceMode.HYBRID_REVIEW).ingest(TEXT)
        assert result.incident is not None and result.incident.inference is not None
        assert result.incident.inference.detail == "no model configured"


class TestService:
    def test_infer_and_model_info(self) -> None:
        client = TestClient(create_inference_app(RulesAsModel()))
        request = InferenceRequest(
            request_id="r1",
            incident_id="inc_1",
            messages=[InferenceMessage(source_event_id="evt_1", text=TEXT)],
        )
        response = InferenceResponse.model_validate(
            client.post("/v1/infer", json=request.model_dump(mode="json")).json()
        )
        assert {c.code for c in response.candidates} >= {"NOT_BREATHING"}
        assert all(c.status == "unverified_model_hypothesis" for c in response.candidates)
        assert client.get("/model-info").json()["model_id"] == "b0-rules-as-model"


@pytest.fixture
def slow_server() -> Iterator[str]:
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            time.sleep(1.0)

        do_POST = do_GET

        def log_message(self, *_: object) -> None:
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{server.server_address[1]}"
    server.shutdown()


def test_http_extractor_times_out_quickly(slow_server: str) -> None:
    extractor = HttpExtractor(slow_server, timeout_s=0.2)
    request = InferenceRequest(
        request_id="r1", incident_id="i", messages=[InferenceMessage(source_event_id="e", text="x")]
    )
    started = time.perf_counter()
    with pytest.raises(InferenceUnavailable):
        extractor.infer(request)
    assert time.perf_counter() - started < 0.9
    assert extractor.model_id == "unknown"  # model-info also timed out


def test_api_exposes_recorded_model_outputs() -> None:
    from ntip.api import create_app

    app = create_app(store=InMemoryEventStore())
    app.state.pipeline.inference_mode = InferenceMode.ML_SHADOW
    app.state.pipeline.extractor = RulesAsModel()
    client = TestClient(app)
    incident_id = client.post("/v1/incidents", json={"text": TEXT, "synthetic": True}).json()[
        "incident_id"
    ]
    [output] = client.get(f"/v1/incidents/{incident_id}/model-outputs").json()
    assert output["mode"] == "ml_shadow"
    assert output["response"]["model_id"] == "b0-rules-as-model"
    assert client.get("/v1/incidents/inc_missing/model-outputs").status_code == 404
