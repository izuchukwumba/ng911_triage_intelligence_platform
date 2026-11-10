"""Publish sample documents for every schema contract (design v1.2, section 4.4).

The samples come from running the real pipeline, with a fixed clock and fixed
identifiers, over a synthetic call: a first message, a follow-up carrying a
structured location, an operator override and a replay. They are written to
``backend/schemas/v<major>/examples/`` as ``<contract>.<schema version>.json``,
so every schema version adds a set and earlier sets stay. Each later version
must still accept every earlier sample (``tests/test_schema_compatibility.py``).

Usage::

    python -m ntip.schema.samples            # write this version's samples
    python -m ntip.schema.samples --check    # exit 1 if they are stale
"""

import argparse
import json
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from ntip.pipeline import Pipeline
from ntip.replay import run_replay
from ntip.schema.base import SCHEMA_VERSION, CivicAddress, Coordinates
from ntip.schema.export import SCHEMA_DIR
from ntip.schema.review import ReviewDecision
from ntip.schema.source import SourceType, SuppliedLocation
from ntip.store import InMemoryEventStore

EXAMPLES_DIR = SCHEMA_DIR / "examples"
START = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
FIRST = "There is smoke coming from the second floor at 14 Elm Street."
FOLLOW_UP = "Now I can see flames and people are trapped inside."


def samples() -> dict[str, Any]:
    """One document per contract, deterministic for a given code version."""
    store = InMemoryEventStore()
    now = START
    counter = 0

    def new_id(prefix: str) -> str:
        nonlocal counter
        counter += 1
        return f"{prefix}_sample{counter:04d}"

    pipeline = Pipeline(store=store, clock=lambda: now, new_id=new_id)
    first = pipeline.ingest(FIRST, correlation_id="req_sample1")
    now = START + timedelta(seconds=40)
    second = pipeline.ingest(
        FOLLOW_UP,
        incident_id=first.incident_id,
        correlation_id="req_sample2",
        source_type=SourceType.STRUCTURED_TEST_EVENT,
        supplied_locations=[
            SuppliedLocation(
                origin="/sample/location",
                civic_address=CivicAddress(
                    house_number="14", street="Elm Street", locality="Springfield", region="IL"
                ),
                coordinates=Coordinates(lat=39.7817, lng=-89.6501, uncertainty_m=25),
            )
        ],
    )
    now = START + timedelta(seconds=90)
    review = pipeline.review(
        first.incident_id,
        assessment_id=second.assessment.assessment_id,
        reviewer_id="operator_1",
        decision=ReviewDecision.OVERRIDE_PRIORITY,
        override_priority="P1",
        reason="Sample override: crews already on scene (synthetic).",
        correlation_id="req_sample3",
    )
    run = run_replay(
        store,
        incident_ids=[first.incident_id],
        candidate_ruleset="research-1.0.0",
        requested_by="analyst_1",
        clock=lambda: now,
        new_id=new_id,
        correlation_id="req_sample4",
    )
    sources = store.source_events(first.incident_id)
    return {
        "source-event": sources[-1].model_dump(mode="json"),
        "incident": store.incident_versions(first.incident_id)[-1].model_dump(mode="json"),
        "assessment": second.assessment.model_dump(mode="json"),
        "human-review": review.model_dump(mode="json"),
        "audit-event": store.audit_events(first.incident_id)[-1].model_dump(mode="json"),
        "replay-run": run.model_dump(mode="json"),
    }


def rendered() -> dict[Path, str]:
    return {
        EXAMPLES_DIR / f"{name}.{SCHEMA_VERSION}.json": json.dumps(doc, indent=2, sort_keys=True)
        + "\n"
        for name, doc in samples().items()
    }


def stale_files() -> list[Path]:
    return [
        path
        for path, text in rendered().items()
        if not path.exists() or path.read_text(encoding="utf-8") != text
    ]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0] if __doc__ else None)
    parser.add_argument("--check", action="store_true", help="fail if files are out of date")
    args = parser.parse_args(argv)
    if args.check:
        stale = stale_files()
        for path in stale:
            print(f"stale: {path}", file=sys.stderr)
        return 1 if stale else 0
    EXAMPLES_DIR.mkdir(parents=True, exist_ok=True)
    for path, text in rendered().items():
        path.write_text(text, encoding="utf-8", newline="\n")
        print(f"wrote {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
