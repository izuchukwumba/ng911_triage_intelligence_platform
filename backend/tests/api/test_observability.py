"""Structured logs, metrics and the explicit simulation mode (design v1.2, 13.2-13.3)."""

import io
import json
import logging

import pytest
from fastapi.testclient import TestClient

from ntip.api import create_app
from ntip.api.auth import Principal, Role
from ntip.api.settings import ConfigurationError, Settings
from ntip.observability import JsonFormatter, Metrics
from ntip.store import InMemoryEventStore

CALL = {"text": "My father is not breathing at 12 Oak Street.", "synthetic": True}


@pytest.fixture
def client() -> TestClient:
    return TestClient(create_app(store=InMemoryEventStore(), settings=Settings()))


def test_metrics_count_requests_by_route_template_and_outcomes(client: TestClient) -> None:
    created = client.post("/v1/incidents", json=CALL).json()
    client.get(f"/v1/incidents/{created['incident_id']}")
    text = client.get("/metrics").text

    assert "ntip_build_info{" in text and 'mode="simulation"' in text
    assert (
        'ntip_http_requests_total{method="GET",route="/v1/incidents/{incident_id}",status="200"} 1'
        in text
    )
    assert created["incident_id"] not in text  # identifiers never become labels
    assert 'ntip_assessments_total{inference="disabled",status="completed"} 1' in text
    assert 'ntip_http_request_duration_seconds_bucket{route="/v1/incidents",le="+Inf"} 1' in text


def test_metrics_need_credentials_when_authentication_is_on() -> None:
    settings = Settings(api_tokens={"v": Principal("vera", Role.VIEWER)}, auth_disabled=False)
    client = TestClient(create_app(store=InMemoryEventStore(), settings=settings))
    assert client.get("/metrics").status_code == 401
    response = client.get("/metrics", headers={"Authorization": "Bearer v"})
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/plain; version=0.0.4")


def test_every_response_states_the_simulation_mode(client: TestClient) -> None:
    assert client.get("/health/live").json()["mode"] == "simulation"
    for response in (client.get("/health/live"), client.get("/v1/incidents/nope")):
        assert response.headers["X-NTIP-Mode"] == "simulation"


def test_any_other_deployment_mode_refuses_to_start(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NTIP_AUTH_DISABLED", "1")
    monkeypatch.setenv("NTIP_DEPLOYMENT_MODE", "production")
    with pytest.raises(ConfigurationError, match="only runs as a simulation"):
        Settings.from_env()


def test_request_logs_are_json_with_correlation_and_no_transcript(client: TestClient) -> None:
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(JsonFormatter())
    logger = logging.getLogger("ntip.api.errors")
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    try:
        client.post("/v1/incidents", json=CALL, headers={"X-Correlation-ID": "req-abc123"})
    finally:
        logger.removeHandler(handler)
    [line] = [json.loads(x) for x in stream.getvalue().splitlines()]
    assert line["event"] == "request"
    assert (line["route"], line["status"], line["correlation_id"]) == (
        "/v1/incidents",
        202,
        "req-abc123",
    )
    assert "breathing" not in stream.getvalue()


def test_exceptions_are_logged_by_type_only() -> None:
    record = logging.LogRecord("x", logging.ERROR, __file__, 1, "failed", None, None)
    try:
        raise ValueError("caller said: my address is 12 Oak Street")
    except ValueError:
        import sys

        record.exc_info = sys.exc_info()
    entry = json.loads(JsonFormatter().format(record))
    assert entry["exception"] == "ValueError"
    assert "Oak" not in json.dumps(entry)


def test_histograms_are_cumulative() -> None:
    metrics = Metrics()
    metrics.histogram("latency", "test")
    for value in (0.003, 0.03, 3.0):
        metrics.observe("latency", value)
    text = metrics.render()
    assert 'latency_bucket{le="0.005"} 1' in text
    assert 'latency_bucket{le="0.05"} 2' in text
    assert 'latency_bucket{le="+Inf"} 3' in text
    assert "latency_count 3" in text
