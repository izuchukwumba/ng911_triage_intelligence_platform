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
  tests/
```

Further modules (`schema`, `parser`, `triage`, `location`, `audit`, `interop`,
`ml`, `evaluation`) are added as each part of the design is ported.
