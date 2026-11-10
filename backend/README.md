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
    parser/         Rules-based transcript parser (baseline B0)
    schema/         Versioned data contracts (Pydantic, source of truth)
  schemas/v1/, v2/  Generated JSON Schema 2020-12 files (committed, one dir per major)
  tests/
```

Further modules (`triage`, `location`, `audit`, `interop`, `ml`,
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

## Rules parser (baseline B0)

`ntip.parser.parse(sources, derived_at=...)` turns one or more source events
into a canonical `Incident`. It is deterministic and dependency-free, and is
the baseline the ML extractors are measured against (design v1.2, section 3A.4).

| Stage | Module | What it does |
|---|---|---|
| Matching | `text` | Word-bounded phrase matching on the original text; clause and sentence windows |
| Context | `context` | Polarity (affirmed / negated / uncertain), temporality (current / historical / hypothetical), attribution (first- / second-hand) |
| Lexicon | `lexicon` | English and Spanish cue phrases per observation code; domain and subtype keywords |
| Classification | `classify` | Language detection and a provisional domain/subtype vote from non-negated cues |
| Counts | `counts` | Victim count as a `Fact`: reported, unknown, conflicting or not reported |
| Locations | `locations` | Every reported address, intersection, route, street or landmark, with missing components |
| Assembly | `parser` | Builds the incident, merges counts across messages, records conflicts |

The parser assigns no urgency; that is the triage engine's job.

