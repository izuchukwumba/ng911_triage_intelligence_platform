# ntip — research backend

Python backend for the NG911 Triage Intelligence Platform: rules parser,
triage engine, append-only event store, HTTP API, replay, evaluation harness
and synthetic data generator. It replaced the original TypeScript services
(see [DDL-012](../docs/design-decisions/decision-log.md)).

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
NTIP_AUTH_DISABLED=1 uvicorn ntip.api:create_app --factory --reload   # local demo, no auth
NTIP_API_TOKENS=dev:me:admin uvicorn ntip.api:create_app --factory --reload
```

Without a database URL the API uses an in-memory event store (lost on restart).
To persist to PostgreSQL:

```sh
OWNER_URL=postgresql://owner:pass@localhost:5432/ntip
python -m ntip.store.migrate "$OWNER_URL"               # apply migrations
python -m ntip.store.migrate "$OWNER_URL" --down 0000   # roll back (dev only)
```

Migrations run as the owner of the tables. The API should **not**: it should
connect as a login role in `ntip_app`, which migration 0006 creates (if a DBA
has not already) and grants read and append access only. Such a role cannot
update, delete or truncate records, nor disable the append-only triggers.

```sql
CREATE ROLE ntip_api LOGIN PASSWORD '...' IN ROLE ntip_app;  -- after migrating
```

```sh
export NTIP_DATABASE_URL=postgresql://ntip_api:...@localhost:5432/ntip
```

The compose stack does this; if you reuse a PostgreSQL volume created before
the role existed, recreate it (`docker compose ... down --volumes`).

| Variable | Default | Purpose |
|---|---|---|
| `NTIP_DATABASE_URL` | unset (in-memory) | PostgreSQL event store |
| `NTIP_DATABASE_POOL_SIZE` | `10` | Maximum connections in the event store's pool, per API process |
| `NTIP_CORS_ORIGINS` | `http://localhost:5173` | Comma-separated dashboard origins |
| `NTIP_API_TOKENS` | none | `token:principal:role[:tenant],...`; roles `viewer`, `operator` (+ingest, review), `analyst` (+replay), `admin`; tenant defaults to `default`. Users see only their tenant's incidents and replay runs; EIDO imports belong to the submitting interop tenant |
| `NTIP_AUTH_DISABLED` | unset | `1` runs without authentication, for an isolated local demo only. Without tokens or this flag the server refuses to start |
| `NTIP_RATE_LIMIT_PER_MINUTE` | `600` | Requests per client (token, else address) per minute; `0` disables. 429 with `Retry-After` when exceeded; `/health` is exempt |
| `NTIP_INTEROP_TOKENS` | none | `token:tenant,...` for the EIDO gateway; unset disables interop |

The NENA-STA-024 conveyance subscriber runs as a separate worker
(`python -m ntip.interop.conveyance`), configured with `NTIP_CONVEYANCE_URL`
(`wss://` only), `NTIP_CONVEYANCE_TENANT`, `NTIP_CONVEYANCE_TOKEN` and,
optionally, `NTIP_CONVEYANCE_INCIDENT` and `NTIP_CONVEYANCE_EXPIRES_S`. It
uses the same database and model settings as the API.

### API (`/v1`)

| Method | Path | Purpose |
|---|---|---|
| POST | `/v1/incidents` | Open an incident from a synthetic message (202, honours `Idempotency-Key`) |
| POST | `/v1/incidents/{id}/messages` | Add a follow-up message; the conversation is re-assessed |
| GET | `/v1/incidents` | Paginated list, newest first |
| GET | `/v1/incidents/{id}` | Current state, sources, incident, assessment, reviews |
| GET | `/v1/incidents/{id}/events` | Append-only audit trail |
| POST | `/v1/incidents/{id}/reviews` | Confirm, correct, override, escalate or annotate |
| GET | `/v1/assessments/{id}` | One assessment |
| GET | `/health/live`, `/health/ready` | Liveness; readiness (checks the event store) |

Every response carries `X-Correlation-ID`. Errors look like
`{"error": {"code", "message", "correlation_id"}}` and never echo submitted
text. Interactive docs: <http://localhost:8000/docs>.

## Check

```sh
pytest              # tests (PostgreSQL tests need NTIP_TEST_DATABASE_URL, else skipped)
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

