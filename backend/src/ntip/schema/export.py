"""Publish the schema contracts as JSON Schema 2020-12 documents.

The Pydantic models are the source of truth; the generated files under
``backend/schemas/v<major>/`` are committed so that other tools and readers
can consume the contract without running Python. A test fails if they drift.

Usage::

    python -m ntip.schema.export            # rewrite the files
    python -m ntip.schema.export --check    # exit 1 if they are stale
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from ntip.schema.advisory import Assessment
from ntip.schema.audit import AuditEvent
from ntip.schema.base import SCHEMA_VERSION
from ntip.schema.canonical import Incident
from ntip.schema.replay import ReplayRun
from ntip.schema.review import HumanReview
from ntip.schema.source import SourceEvent

DIALECT = "https://json-schema.org/draft/2020-12/schema"
ID_PREFIX = "https://ntip.local/schemas"

CONTRACTS: dict[str, type[BaseModel]] = {
    "source-event": SourceEvent,
    "incident": Incident,
    "assessment": Assessment,
    "human-review": HumanReview,
    "audit-event": AuditEvent,
    "replay-run": ReplayRun,
}

SCHEMA_DIR = Path(__file__).resolve().parents[3] / "schemas" / f"v{SCHEMA_VERSION.split('.')[0]}"


def render(name: str, model: type[BaseModel]) -> str:
    schema: dict[str, Any] = {
        "$schema": DIALECT,
        "$id": f"{ID_PREFIX}/v{SCHEMA_VERSION}/{name}.schema.json",
        **model.model_json_schema(mode="validation"),
    }
    schema["x-schema-version"] = SCHEMA_VERSION
    return json.dumps(schema, indent=2, sort_keys=True) + "\n"


def rendered() -> dict[Path, str]:
    return {SCHEMA_DIR / f"{name}.schema.json": render(name, m) for name, m in CONTRACTS.items()}


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

    SCHEMA_DIR.mkdir(parents=True, exist_ok=True)
    for path, text in rendered().items():
        path.write_text(text, encoding="utf-8", newline="\n")
        print(f"wrote {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
