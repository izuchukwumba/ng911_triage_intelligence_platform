from datetime import UTC, datetime, timedelta
from itertools import count
from typing import Any

import pytest
from fastapi.testclient import TestClient

from ntip.api import create_app
from ntip.pipeline import Pipeline
from ntip.replay import UnknownRuleset, run_replay
from ntip.schema.canonical import Incident
from ntip.store import InMemoryEventStore

RECOVERED = "He was not breathing earlier but he is breathing now. We are at 9 Pine Road."


def make_pipeline(**overrides: Any) -> Pipeline:
    ticks, ids = count(), count(1)
    defaults: dict[str, Any] = {
        "store": InMemoryEventStore(),
        "clock": lambda: datetime(2026, 11, 9, 12, tzinfo=UTC) + timedelta(seconds=next(ticks)),
        "new_id": lambda prefix: f"{prefix}_{next(ids)}",
    }
    return Pipeline(**{**defaults, **overrides})


def replay(pipeline: Pipeline, **kwargs: Any) -> Any:
    params: dict[str, Any] = {"incident_ids": None, "candidate_ruleset": None}
    return run_replay(
        pipeline.store,
        **{**params, **kwargs},
        requested_by="analyst_1",
        clock=pipeline.clock,
        new_id=pipeline.new_id,
        correlation_id="req_replay",
    )


def test_stored_assessments_are_reproducible() -> None:
    pipeline = make_pipeline()
    for text in ("He is not breathing at 12 Oak Street.", RECOVERED, "Smoke at 5 Elm Road."):
        pipeline.ingest(text)

    run = replay(pipeline)

    assert run.summary.incidents == 3
    assert run.summary.reproducible == 3
    assert run.summary.not_reproducible == 0


def test_candidate_ruleset_comparison_flags_lower_priority() -> None:
    pipeline = make_pipeline()
    result = pipeline.ingest(RECOVERED)  # default ruleset research-1.2.0 -> elevated (P2)

    run = replay(pipeline, candidate_ruleset="research-1.0.0")
    [case] = run.cases

    assert case.stored.advisory_priority == "P2"
    assert case.candidate is not None
    assert case.candidate.ruleset_version == "research-1.0.0"
    assert case.priority_changed and case.candidate_lowers_priority
    assert run.summary.candidate_lowers_priority == 1
    assert case.incident_id == result.incident_id


def test_replay_never_modifies_the_incident() -> None:
    pipeline = make_pipeline()
    result = pipeline.ingest(RECOVERED)
    before = (pipeline.store.assessments(result.incident_id), pipeline.view(result.incident_id))

    replay(pipeline, candidate_ruleset="research-1.0.0")

    assert pipeline.store.assessments(result.incident_id) == before[0]
    assert pipeline.view(result.incident_id) == before[1]
    events = pipeline.store.audit_events(result.incident_id)
    assert events[-1].event_type == "incident.replayed"
    assert events[-1].actor.actor_id == "analyst_1"


def test_failed_incidents_are_skipped_with_a_reason() -> None:
    def broken(*_: Any, **__: Any) -> Incident:
        raise RuntimeError("boom")

    pipeline = make_pipeline(parser=broken)
    pipeline.ingest("anything")
    [case] = replay(pipeline).cases
    assert case.skipped_reason == "stored processing failed"


def test_unknown_candidate_ruleset_is_rejected() -> None:
    with pytest.raises(UnknownRuleset):
        replay(make_pipeline(), candidate_ruleset="research-9.9.9")


def test_replay_runs_are_stored() -> None:
    pipeline = make_pipeline()
    pipeline.ingest("Smoke at 5 Elm Road.")
    run = replay(pipeline)
    assert pipeline.store.replay_run(run.run_id) == run
    assert pipeline.store.replay_runs(limit=5) == [run]


class TestApi:
    @pytest.fixture
    def client(self) -> TestClient:
        return TestClient(create_app(store=InMemoryEventStore()))

    def test_create_and_fetch_a_replay_run(self, client: TestClient) -> None:
        client.post("/v1/incidents", json={"text": RECOVERED, "synthetic": True})
        response = client.post(
            "/v1/replay-runs",
            json={"requested_by": "analyst_1", "candidate_ruleset": "research-1.0.0"},
        )
        assert response.status_code == 201
        run = response.json()
        assert run["summary"]["reproducible"] == 1
        assert run["summary"]["candidate_lowers_priority"] == 1
        assert client.get(f"/v1/replay-runs/{run['run_id']}").json() == run
        assert client.get("/v1/replay-runs").json()[0]["run_id"] == run["run_id"]

    def test_unknown_ruleset_is_422(self, client: TestClient) -> None:
        response = client.post(
            "/v1/replay-runs", json={"requested_by": "a", "candidate_ruleset": "nope"}
        )
        assert response.status_code == 422
        assert response.json()["error"]["code"] == "unknown_ruleset"

    def test_unknown_run_is_404(self, client: TestClient) -> None:
        assert client.get("/v1/replay-runs/replay_missing").status_code == 404

    def test_lists_released_rulesets(self, client: TestClient) -> None:
        rulesets = {r["name"]: r for r in client.get("/v1/rulesets").json()}
        assert rulesets["research-1.2.0"]["default"] is True
        assert rulesets["research-1.0.0"]["digest"].startswith("sha256:")
