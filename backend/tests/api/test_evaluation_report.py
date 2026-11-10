"""The evaluation report endpoint (design v1.2, section 11.1)."""

from fastapi.testclient import TestClient

from ntip.api import create_app
from ntip.api.settings import Settings
from ntip.parser.parser import PARSER_VERSION
from ntip.store import InMemoryEventStore
from ntip.triage.ruleset import DEFAULT_RULESET

client = TestClient(create_app(store=InMemoryEventStore(), settings=Settings()))


def test_report_has_metrics_pins_and_failed_cases() -> None:
    response = client.get("/v1/evaluation/report")
    assert response.status_code == 200
    report = response.json()
    assert "Synthetic" in report["note"]
    pins = report["pins"]
    assert pins["parser"].endswith(PARSER_VERSION)
    assert pins["ruleset"] == DEFAULT_RULESET
    assert pins["dataset_digest"].startswith("sha256:")
    assert sorted(pins["splits"]) == ["dev", "regression"]

    metrics = report["metrics"]
    assert metrics["cases"] == 30
    assert metrics["critical_undertriage"]["denominator"] > 0
    assert set(metrics["priority_confusion"]) == {"P0", "P1", "P2", "P3", "P4", "none"}

    failed = report["failed_cases"]
    assert failed, "the curated set has known errors to show"
    assert all(case["messages"] and case["errors"] for case in failed)
    # Critical cases first.
    flags = [case["critical"] for case in failed]
    assert flags == sorted(flags, reverse=True)


def test_one_split_and_the_generated_dataset() -> None:
    report = client.get("/v1/evaluation/report?dataset=generated&split=regression").json()
    assert report["dataset"] == "generated"
    assert report["pins"]["splits"] == ["regression"]
    assert report["pins"]["dataset_path"].startswith("generated-")


def test_the_held_out_test_split_is_not_served() -> None:
    response = client.get("/v1/evaluation/report?split=test")
    assert response.status_code == 422


def test_markdown_export() -> None:
    response = client.get("/v1/evaluation/report.md?split=dev")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/markdown")
    assert 'filename="b0-curated-dev.md"' in response.headers["content-disposition"]
    assert "# Evaluation" in response.text
