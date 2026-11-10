# Design traceability matrix

Status of each requirement of [technical design v1.2](design/technical-design-v1.2.md)
against the repository, with evidence (design §15 Phase 0 and §20).

Status key: **Done**: implemented and tested. **Partial**: implemented with
stated gaps. **Not done**: not implemented yet. **External**: needs people or
permissions outside the project (reviewers, practitioners, the data owner's
budget). **By design**: deliberately out of scope (§1 non-goals).

Last updated: 2026-11-10.

## Architecture and contracts (§3, §4)

| Requirement | Status | Evidence |
|---|---|---|
| Modular monolith, one repository (§3.2, ADR-001) | Done | `backend/src/ntip/*`, `apps/dashboard` |
| Python backend, TypeScript dashboard | Done (amends §3.3 / ADR-002) | DDL-012 |
| Versioned contracts, JSON Schema 2020-12, generated client types (§3.3, §4.3, §4.4) | Done | `backend/schemas/v1`, `v2`; `backend/openapi.json`; `npm run gen:api`; CI freshness checks |
| Layered records: source, canonical, advisory, review, audit (§4.1, §3B.4) | Done | `ntip/schema/*` |
| `unknown` / `not_reported` / `negated` / `conflicting` never collapsed (§4.3) | Done | `Fact[T]`; safety case S9 |
| Breaking changes bump the major version with old schemas kept (§4.4) | Done | schema 2.0.0 under `schemas/v2`, v1 retained |
| Published sample payloads; new optional fields backward-compatible only after compatibility tests (§4.3, §4.4) | Done | `python -m ntip.schema.samples` publishes pipeline-generated samples per schema version (`schemas/v2/examples`); `tests/test_schema_compatibility.py` checks every published sample against the current models and JSON Schemas, and that documents without the fields added since 2.0.0 stay valid and unchanged |

## ML layer (§3A)

| Requirement | Status | Evidence |
|---|---|---|
| Rules baseline B0 kept as permanent fallback (§3A.2) | Done | `ntip.parser`; fusion never removes rules findings |
| B1 small task-specific model (§3A.4) | Done | `ntip/ml/b1.py`, [model card](ml/model-card-b1.md) |
| B2 structured-output LLM (§3A.4) | Partial | Adapter and tests done (`ntip/ml/b2.py`); **not evaluated**: needs the owner's authorisation to call a paid API ([model card](ml/model-card-b2.md)) |
| B3 domain-adapted model (§3A.4) | Not done | Only after dataset quality is established, per the design |
| Inference contract, span verification, abstentions (§3A.5) | Done | `ntip/ml/contract.py`, `verify.py`; safety case S6 |
| Modes `rules_only` / `ml_shadow` / `hybrid_review`, timeout fallback (§3A.3, §3A.6) | Done | `ntip/ml/fusion.py`, pipeline; safety case S7–S8; CI smoke test runs hybrid with B1 |
| Separate inference service (§3A.3) | Done | `ntip.ml.service`, compose `inference` service |
| Recorded-output replay for models (§3A.9) | Done | `ModelOutput` records, `/v1/incidents/{id}/model-outputs` |
| Dataset with leakage-safe family splits and held-out set (§3A.7) | Done | `data/eval/curated.jsonl`, `generated-1.0.0-seed42.jsonl`; loader rejects leakage |
| Labelling guide (§3A.7) | Done | [labelling-guide.md](evaluation/labelling-guide.md) |
| Independent annotation and inter-annotator agreement (§3A.7) | External | Needs at least two qualified reviewers |
| Metrics: per-field P/R/F1, critical false negatives separately, calibration, risk-coverage, slices, ablations (§3A.8) | Done | `ntip.evaluation`, `compare.py`, `calibration.py`; [results](evaluation/results/README.md) |
| Reproducibility manifests (§3A.9, §10.3) | Done | Every report records commit, dataset, ruleset, schema, lockfile digests and seed |
| Milestones ML-1 to ML-4 | Done | Baseline reproducible by one command; contract; comparison; ML-4 gate met (hybrid never increases critical FNs) |
| ML-5 research release with independent review | External | Needs independent reviewers |

## NG911 interoperability (§3B)

| Requirement | Status | Evidence |
|---|---|---|
| Phase I: pinned edition, source register, licence review (§3B.2, §3B.9) | Done | [eido-profile.md](standards-alignment/eido-profile.md), [source-register.md](standards-alignment/source-register.md) |
| Phase II: import-only adapter, source preservation, idempotency, INT-001…012 (§3B.3, §3B.7) | Done | `ntip/interop/*`; [interop-verification.md](standards-alignment/interop-verification.md) |
| Phase III: ML advisory attached without blocking ingestion | Done (synchronous, bounded by timeout) | INT-007; safety case S8 |
| Phase IV: lab interoperability with NENA artefacts / Texas A&M tooling | Done (reviewed) | NENA's published sample validates; NENA's conveyance message schema is pinned and tested. Texas A&M `ng911-dev` reviewed: it tests i3 functional elements and covers EIDO only as logging events, so none of its tests applies ([review](standards-alignment/tamu-ng911-dev-review.md)) |
| Phase V: external engineering and practitioner review | External | — |
| Mapping beyond notes (locations, persons, PIDF-LO) | Done | PIDF-LO civic addresses, points and circles become supplied (`device_provided`) locations with provenance; conflicts with the narrative are detected; reference URLs are never dereferenced; persons deliberately unmapped (data minimisation). `ntip/interop/eido/pidf.py`, `tests/interop/test_pidf.py`, `tests/interop/test_eido_locations.py` |
| NENA-STA-024 conveyance | Done (subscriber role) | `ntip/interop/conveyance`: WebSocket subscriber with acknowledgements, retries/reconnect, renewal and fail-closed TLS; messages validated against NENA's pinned schema; `tests/interop/test_conveyance.py`. Notifier, push and dereference roles are out of scope (DDL-018) |
| Tenant isolation (INT-010) | Done | Incidents, replay runs, idempotency keys and interop receipts are scoped to a tenant; another tenant's incident is indistinguishable from a missing one (DDL-017); `tests/api/test_tenants.py` |

## Parser, triage and location (§6, §7, §8)

| Requirement | Status | Evidence |
|---|---|---|
| Negation, hypothetical, historical, hearsay, conflicts (§6.2–6.3) | Done | `ntip/parser/context.py`, conflicts in `Incident` |
| Heuristic confidence labelled as such (§6.4) | Done | `heuristic_confidence` fields |
| Unit, golden, metamorphic, property-based tests (§6.5) | Done | `tests/parser/*`, `test_properties.py` (Hypothesis) |
| Multilingual input | Partial | English and some Spanish |
| Severity separate from location quality and review urgency (§7.1) | Done | `Assessment` fields; DDL-011, DDL-013 |
| Versioned rules with ids, immutable releases (§7.2, §7.5) | Done | `rulesets/*.json` pinned by sha256 |
| Explainability: rule id, version, evidence per recommendation (§7.4) | Done | `Assessment.reasons`; dashboard "Why this recommendation?" |
| Location L0–L2 (§8.3) | Done | `ntip.location` |
| Location L3 (GIS reference) (§8.3) | Done (synthetic reference) | `ntip/location/reference.py`: a unique match in a Site/Structure Address Point layer (NENA-STA-006.3 field names) adds a `reference_validated`, geocoded candidate citing the point's NGUID; ambiguous or unknown addresses still need verifying; never affects priority. Opt-in (`NTIP_GIS_REFERENCE`), on in the compose stack with the synthetic layer in `data/gis`; `tests/location/test_reference.py` |
| Location L4 (standards validation, e.g. LVF) | Not done | Needs an NG911 Location Validation Function and authoritative data |

## API, audit, replay (§5, §9, §10)

| Requirement | Status | Evidence |
|---|---|---|
| `/v1` endpoints, 202 ingest, idempotency, structured errors, correlation ids (§5.2–5.3) | Done | `ntip/api/*` |
| Live and ready health checks (§5.2) | Done | `/health/live`, `/health/ready` |
| Structured logs, metrics and trace correlation ids (§13.3) | Done | JSON logs with correlation ids, never transcript text or tracebacks (`ntip/observability.py`); Prometheus `/metrics` (requests and latency by route template, assessment outcomes and model status, interop receipts, build info); `tests/api/test_observability.py`, container smoke test |
| Retention and deletion rules; audit retention does not override lawful deletion (§9.3, §13.2) | Done | `python -m ntip.store.retention` (owner-only, dry run by default, by incident or retention period and tenant), migration 0008 (`erasures` tombstones, deletion only inside a flagged transaction), DDL-019; `tests/store/test_retention.py` |
| Explicit simulation-only deployment flag (§13.2) | Done | `NTIP_DEPLOYMENT_MODE` (only `simulation`; anything else refuses to start), `X-NTIP-Mode` on every response |
| Append-only events enforced by the database (§9.2) | Done | Triggers on every table; safety case S12 |
| Restricted database role (§9.2) | Done | Migration 0006 (`ntip_app`); contract tests run as the role; `tests/store/test_postgres_app_role.py`; compose backend connects as `ntip_api` |
| Replay: reproducibility and version comparison (§10.1–10.4) | Done | `POST /v1/replay-runs`; dashboard Replay tab |
| Human-review replay: machine output beside operator correction, not ground truth (§10.2) | Done | `GET /v1/review-comparison` (`ntip/review_replay.py`): latest decision per reviewed assessment, raised/lowered/confirmed/reclassified, tenant-scoped; dashboard Replay tab; `tests/test_review_replay.py`, end-to-end test |
| Stream replay with relative timing (§10.2) | Done | `python -m ntip.stream` (simulated clock, queue timeline, time to P0, candidate comparison; streams from files or stored traffic); `tests/test_stream.py`; [example](evaluation/results/stream-escalation-research-1.1.0-vs-1.0.0.md) |
| Latency baseline (§10.5, §13.3) | Done | `ntip.evaluation.latency`; results README |
| Human-factors study (§10.5, §16.1 RQ4) | External | Needs a controlled study with consent |

## Dashboard (§11)

| Requirement | Status | Evidence |
|---|---|---|
| Simulation banner, queue, detail with evidence, why panel, review/override, replay, audit (§11.1) | Done | `apps/dashboard` |
| No colour-only signals, keyboard focus, labels (§11.2) | Done | `apps/dashboard/e2e/accessibility.spec.ts`: axe (WCAG 2.0/2.1 A and AA) on the queue, detail, replay and evaluation screens; keyboard-only triage; priorities in text; simulation warning on every screen. Runs in CI against a real backend |
| Evaluation report screen (§11.1) | Done | Dashboard **Evaluation** tab over `GET /v1/evaluation/report` (and `report.md`): live B0 metrics with intervals, confusion matrix, failed cases (critical first), version pins, Markdown/JSON export; dev and regression splits only. `tests/api/test_evaluation_report.py` |
| State machine RECEIVED → … → CLOSED (§11.3) | Done | `awaiting_review` / `reviewed` / `processing_failed` / `closed`; closing is a review decision and a new message reopens |

## Generator, security, CI (§12, §13, §14)

| Requirement | Status | Evidence |
|---|---|---|
| Seeded generator with perturbations, generator-intended labels (§12) | Done | `ntip.generator` |
| Authentication and role-based access (§2.3, §13.2) | Done | `ntip/api/auth.py`, `tests/api/test_auth.py`; DDL-015 |
| Rate limiting (§5.3, §13.2) | Done (per process) | `ntip/api/ratelimit.py`, `tests/api/test_rate_limit.py` |
| Threat model and controls (§13) | Done | [threat-model.md](safety/threat-model.md); remaining limits listed there |
| CI: lint, types, tests, PostgreSQL, safety gate, contract freshness, containers, dependency and secret scanning (§14.2) | Done | `.github/workflows/ci.yml` |
| End to end: ingest → dashboard → human review → replay → report (§14.1) | Done | `apps/dashboard/e2e/workflow.spec.ts` (Playwright, real API): ingest through the UI, evidence, override with a reason, audit attribution, replay reproducibility, evaluation report; runs in CI |
| Test and benchmark summaries attached to runs; expensive suites scheduled (§14.2) | Done | CI writes test results and the evaluation report to each run's summary; `.github/workflows/benchmarks.yml` runs latency and PostgreSQL load weekly (and on demand) with summaries and artifacts |
| Load tests under concurrency (§14.1) | Done | `ntip.evaluation.load` (correctness checks, memory and PostgreSQL); found and fixed two concurrency bugs (DDL-016) |
| Release tags and changelog (§14.3) | Done | [CHANGELOG.md](../CHANGELOG.md), [release notes](releases/) with schema compatibility, component versions, results, limitations and demo; the `Release` workflow re-verifies the tagged commit and attaches its test and evaluation reports (with its SHA); `tests/test_release.py` |

## Definition of done (§20)

| Item | Status |
|---|---|
| Synthetic scenario runs end to end on a clean machine | Done (compose stack, CI smoke test) |
| Core payloads pass published schema validation | Done |
| Severity and location uncertainty separated in code and UI | Done |
| Critical-cue safety regression tests pass | Done (CI gate) |
| Each assessment links to evidence, rule version, source event | Done |
| Human overrides create immutable audit entries | Done |
| Replay deterministic under pinned inputs | Done (reproducibility check) |
| Evaluation reports include baselines, denominators, limitations | Done |
| No real caller data in public artefacts | Done (synthetic only; enforced) |
| Standards claims mapped to specific documents and limited | Done (source register) |
| README with architecture, quick start, demo, limitations, benchmark commands | Done |
| Independent technical or domain feedback recorded | **External** — none obtained yet |
| Pinned EIDO edition and source-to-canonical mapping documented | Done |
| Official source records immutable, AI assessments separate | Done |
| Integration tests for version rejection, idempotency, source preservation, inference-failure isolation | Done |
| Claimed interoperability scoped to verified schemas and tests | Done |
| Platform can be disabled without disrupting an external NG911 workflow | Done by construction (import-only, no writeback) |

## Open questions (§18)

| # | Question | Answer / status |
|---|---|---|
| 1 | What exists in the latest revision? | This matrix |
| 2 | Framework and package manager | FastAPI + uv (backend), React + npm (dashboard) |
| 3 | Persistence | PostgreSQL append-only store; in-memory for tests and demos |
| 4 | Did the scorer conflate location with urgency? | Yes, in the TypeScript scorer; fixed in DDL-011 and designed out in DDL-013 |
| 5 | NENA editions | EIDO NENA-STA-021.1b pinned; i3 and GIS Data Model not pinned |
| 6 | Authoritative P0–P4 definitions and reviewers | Project-defined research rubric (labelling guide); **needs practitioner review** |
| 7 | Independent annotators | **Open** |
| 8 | Repository licence compatible with dependencies and reused artefacts | **Open**: the repository has no licence file yet; the owner should choose one. NENA's EIDO schema is not redistributed because it has none |
| 9 | Data retention for hosted demos | Synthetic only; see the threat model |
| 10 | Results replicable by an external reviewer without private infrastructure | Yes: every report regenerates from committed data with one command; B2 needs an API key |
