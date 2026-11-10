# Contributing

## Scope

This is a research and simulation platform. Contributions must keep it that
way: synthetic data only, advisory output only, no connection to real
emergency systems, and no claims (in code, docs or UI) beyond what tests and
reports show. Read the [safety case](docs/safety/safety-case.md) before
changing parsing, triage, fusion or storage.

## Setup

```sh
cd backend
uv sync --extra dev --extra ml --extra llm
cd ../apps/dashboard
npm ci
```

PostgreSQL tests need a server where the user may create databases:

```sh
export NTIP_TEST_DATABASE_URL=postgresql://postgres@localhost:5432/postgres
```

Without it they are skipped locally; CI always runs them.

## Checks (all run in CI)

```sh
cd backend
ruff check . && ruff format --check . && mypy && pytest
python -m ntip.evaluation --split regression --gate     # safety gate
python -m ntip.schema.export --check && python -m ntip.api.openapi --check
cd ../apps/dashboard
npm run gen:api && git diff --exit-code -- src/api/schema.ts && npm run build
```

## Rules of the road

- **Never weaken a safety invariant silently.** Uncertainty, missing location,
  prank cues and model output may add review actions; they must not lower
  severity or priority (DDL-011, DDL-013).
- **Rulesets are immutable once released.** Change rules by adding a new
  ruleset file with a new version and pinning its digest.
- **Schemas are versioned.** Additive changes bump the minor version; breaking
  changes bump the major version and publish under a new `schemas/vN/`. After
  any model change, regenerate the JSON Schema files, `openapi.json` and the
  dashboard types.
- **Evaluation discipline.** Tune only on `dev` and `regression` splits. Never
  change the parser, rules or models in response to `test` failures. Report
  results with counts and intervals, including failures.
- **Every extracted fact needs evidence**, quoted from the source.
- **Decisions go in the decision log** (`docs/design-decisions/decision-log.md`)
  when they change architecture or safety behaviour.

## Pull requests

One concern per branch; commits small enough that each message explains one
change. A PR description says what changed, why, how it was tested, and what
it deliberately does not do. CI must be green before merging.
