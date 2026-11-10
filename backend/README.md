# ntip — research backend

Python backend for the NG911 Triage Intelligence Platform. It replaces the
TypeScript services under `services/` and `packages/` incrementally — see
[DDL-012](../docs/design-decisions/decision-log.md) for the decision and the
migration plan. Until the migration completes, the TypeScript backend remains
the running system.

> Simulation and research use only. Not certified for emergency operations and
> not a substitute for trained telecommunicators or approved dispatch protocols.

## Setup

Requires Python 3.12+.

With [uv](https://docs.astral.sh/uv/) (recommended, uses `uv.lock`):

```sh
cd backend
uv sync --extra dev
```

With plain pip:

```sh
cd backend
python -m venv .venv
# Windows: .venv\Scripts\activate    macOS/Linux: source .venv/bin/activate
pip install -e ".[dev]"
```

## Run

```sh
uvicorn ntip.api:create_app --factory --reload
```

- Liveness: <http://localhost:8000/health/live>
- Readiness: <http://localhost:8000/health/ready>
- OpenAPI docs: <http://localhost:8000/docs>

## Check

```sh
pytest              # tests
ruff check .        # lint
ruff format --check .
mypy                # strict type check
```

## Layout

```text
backend/
  src/ntip/
    api/            HTTP boundary (FastAPI app factory, routes)
    schema/         Versioned data contracts (Pydantic, source of truth)
  schemas/v1/       Generated JSON Schema 2020-12 files (committed)
  tests/
```

Further modules (`parser`, `triage`, `location`, `audit`, `interop`, `ml`,
`evaluation`) are added as each part of the design is ported.

## Data contracts

The schema follows the three layers of the v1.2 design (section 3B.4), and
keeps them as separate objects rather than one mutable record:

| Layer | Model | Holds |
|---|---|---|
| Source | `SourceEvent` | Input exactly as received, with a sha256 digest. Never edited; revisions are new events. |
| Canonical | `Incident` | Observations and location candidates, each quoting the source span it came from. |
| Advisory | `Assessment` | Severity, location quality, review actions and research priority — kept separate. |
| Human | `HumanReview` | Confirmations, corrections and overrides. Never modifies the assessment. |
| Audit | `AuditEvent` | One append-only event per action. |

Invariants enforced by the models include: `unknown` is never stored as a value
(`Fact`), a reported location cannot carry invented coordinates, a model cannot
mark a location as validated, poor location quality adds `VERIFY_LOCATION`
rather than lowering severity, and a processing failure can never carry a
priority.

After changing a model, regenerate the published JSON Schema files:

```sh
python -m ntip.schema.export
```
