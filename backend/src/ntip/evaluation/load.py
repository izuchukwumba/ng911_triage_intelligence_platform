"""Concurrency load test with correctness checks (design v1.2, sections 13.3 and 14.1).

Runs many ingests at once through the pipeline, including concurrent
follow-up messages to the *same* incident, then checks that nothing was lost:
every accepted message has its source event, an assessment and a complete
audit trail, and every incident's latest version reflects all of its
messages.

    python -m ntip.evaluation.load --workers 16 --incidents 200 --follow-ups 3
    python -m ntip.evaluation.load --database-url postgresql://...   # against PostgreSQL
"""

import argparse
import json
import statistics
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from ntip.pipeline import Pipeline
from ntip.store import EventStore, InMemoryEventStore

FIRST = "Smoke on the second floor at {n} Oak Street."
FOLLOW_UP = "Update {k}: people are trapped inside."


def _store(database_url: str | None) -> EventStore:
    if database_url is None:
        return InMemoryEventStore()
    from ntip.store.migrate import upgrade
    from ntip.store.postgres import PostgresEventStore

    upgrade(database_url)
    return PostgresEventStore(database_url)


def run(store: EventStore, *, workers: int, incidents: int, follow_ups: int) -> dict[str, Any]:
    pipeline = Pipeline(store=store)
    latencies: list[float] = []
    errors: list[str] = []
    lock = threading.Lock()

    def timed(fn: Any, *args: Any, **kwargs: Any) -> Any:
        started = time.perf_counter()
        try:
            return fn(*args, **kwargs)
        except Exception as err:  # recorded and reported, never hidden
            with lock:
                errors.append(f"{type(err).__name__}: {err}"[:200])
            return None
        finally:
            with lock:
                latencies.append((time.perf_counter() - started) * 1000)

    started = time.perf_counter()
    with ThreadPoolExecutor(max_workers=workers) as pool:
        firsts = list(
            pool.map(lambda n: timed(pipeline.ingest, FIRST.format(n=n + 1)), range(incidents))
        )
        ids = [r.incident_id for r in firsts if r is not None]
        # All follow-ups to the same incident are submitted together, so they race.
        jobs = [(incident_id, k) for incident_id in ids for k in range(follow_ups)]
        list(pool.map(lambda job: timed(
            pipeline.ingest, FOLLOW_UP.format(k=job[1]), incident_id=job[0]), jobs))  # fmt: skip
    elapsed = time.perf_counter() - started

    # Correctness: nothing lost, every message processed and audited, and the
    # latest incident version covers every message of its conversation.
    problems: list[str] = []
    for incident_id in ids:
        sources = store.source_events(incident_id)
        assessments = store.assessments(incident_id)
        versions = store.incident_versions(incident_id)
        events = store.audit_events(incident_id)
        expected = 1 + follow_ups
        if len(sources) != expected:
            problems.append(f"{incident_id}: {len(sources)} sources, expected {expected}")
        if len(assessments) != len(sources):
            problems.append(
                f"{incident_id}: {len(assessments)} assessments for {len(sources)} sources"
            )
        if len(events) != 3 * len(sources):
            problems.append(
                f"{incident_id}: {len(events)} audit events, expected {3 * len(sources)}"
            )
        if versions and set(versions[-1].source_event_ids) != {s.source_event_id for s in sources}:
            problems.append(f"{incident_id}: latest version misses messages")

    total = len(latencies)
    ordered = sorted(latencies)
    return {
        "workers": workers,
        "requests": total,
        "errors": len(errors),
        "error_samples": sorted(set(errors))[:5],
        "throughput_per_s": round(total / elapsed, 1),
        "latency_ms": {
            "p50": round(ordered[total // 2], 2),
            "p95": round(ordered[int(total * 0.95)], 2),
            "max": round(ordered[-1], 2),
            "mean": round(statistics.mean(ordered), 2),
        },
        "consistency_problems": len(problems),
        "problem_samples": problems[:5],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0] if __doc__ else None)
    parser.add_argument("--workers", type=int, default=16)
    parser.add_argument("--incidents", type=int, default=200)
    parser.add_argument("--follow-ups", type=int, default=3)
    parser.add_argument("--database-url")
    args = parser.parse_args()
    result = run(_store(args.database_url), workers=args.workers, incidents=args.incidents,
                 follow_ups=args.follow_ups)  # fmt: skip
    result["store"] = "postgresql" if args.database_url else "memory"
    print(json.dumps(result, indent=2))
    return 0 if not result["errors"] and not result["consistency_problems"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
