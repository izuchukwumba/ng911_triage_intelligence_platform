"""Publish the API's OpenAPI document for clients (the dashboard generates its
TypeScript types from it, so Pydantic stays the single source of truth).

    python -m ntip.api.openapi            # rewrite backend/openapi.json
    python -m ntip.api.openapi --check    # exit 1 if it is stale
"""

import argparse
import json
import sys
from pathlib import Path

from ntip.api.app import create_app
from ntip.api.settings import Settings
from ntip.store import InMemoryEventStore

PATH = Path(__file__).resolve().parents[3] / "openapi.json"


def render() -> str:
    app = create_app(store=InMemoryEventStore(), settings=Settings())
    return json.dumps(app.openapi(), indent=2, sort_keys=True) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0] if __doc__ else None)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    text = render()
    if args.check:
        current = PATH.read_text(encoding="utf-8") if PATH.exists() else ""
        if current != text:
            print(f"stale: {PATH}", file=sys.stderr)
            return 1
        return 0
    PATH.write_text(text, encoding="utf-8", newline="\n")
    print(f"wrote {PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
