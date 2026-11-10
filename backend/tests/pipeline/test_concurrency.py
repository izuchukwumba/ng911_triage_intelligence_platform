"""Concurrent messages for one incident are never lost or half-processed."""

from concurrent.futures import ThreadPoolExecutor

from ntip.evaluation.load import run
from ntip.pipeline import Pipeline
from ntip.store import InMemoryEventStore


def test_concurrent_follow_ups_are_all_kept_and_assessed_together() -> None:
    store = InMemoryEventStore()
    pipeline = Pipeline(store=store)
    first = pipeline.ingest("There is smoke at 12 Oak Street.")
    messages = ["People are trapped inside.", "The fire is spreading.", "A child is inside."] * 3

    with ThreadPoolExecutor(max_workers=9) as pool:
        list(pool.map(lambda t: pipeline.ingest(t, incident_id=first.incident_id), messages))

    sources = store.source_events(first.incident_id)
    assert len(sources) == 1 + len(messages)
    latest = store.incident_versions(first.incident_id)[-1]
    assert set(latest.source_event_ids) == {s.source_event_id for s in sources}
    assert pipeline.view(first.incident_id).assessment.severity_band == "critical"


def test_load_run_reports_no_errors_or_inconsistencies() -> None:
    result = run(InMemoryEventStore(), workers=8, incidents=40, follow_ups=3)
    assert (result["errors"], result["consistency_problems"]) == (0, 0)


def test_postgres_load_run_is_consistent(postgres_url: str) -> None:
    from ntip.store.migrate import upgrade
    from ntip.store.postgres import PostgresEventStore

    upgrade(postgres_url)
    result = run(PostgresEventStore(postgres_url), workers=8, incidents=10, follow_ups=3)
    assert (result["errors"], result["consistency_problems"]) == (0, 0)
