# Changelog

All notable changes to this project are recorded here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and versions follow
[Semantic Versioning](https://semver.org/). Each release also has notes in
[docs/releases](docs/releases/) covering schema compatibility, component
versions, results and known limitations (design v1.2, section 14.3).

Component versions (schema, parser, triage engine, rulesets, model contract)
are versioned independently and recorded on every result they produce; the
release version identifies the platform as a whole.

## [Unreleased]

### Added

- **Stream replay** (`python -m ntip.stream`): replays timed message
  streams, from files or stored traffic, in order on a simulated clock. It
  reports the queue after each message and each incident's time to P0, and
  compares a candidate ruleset step by step (design v1.2, section 10.2).
- **Tenant separation** (schema 2.5.0, migration 0007): every incident and
  replay run belongs to a tenant. API tokens may name one
  (`token:principal:role:tenant`). Users see only their tenant's incidents,
  idempotency keys are per tenant, and EIDO imports belong to the submitting
  tenant. Another tenant's incident answers 404 (DDL-017).
- **EIDO locations** (schema 2.6.0, adapter 0.2.0, parser 1.4.0): PIDF-LO civic
  addresses, points and circles become supplied locations, kept apart from the
  narrative. Contradictions are flagged as location conflicts, and a revision
  that only moves the location still updates the incident. Reference URLs are
  never fetched, and unsafe or unsupported PIDF-LO is preserved with a reason.

- **NENA-STA-024 conveyance, subscriber role** (`python -m ntip.interop.conveyance`):
  subscribes to EIDOs from an authorised notifier over `wss://` and feeds each
  through the gateway. It acknowledges every notification with a status derived
  from the gateway's receipt, re-acknowledges resends without reprocessing them,
  renews before expiry, and reconnects with backoff. Every message is validated
  against NENA's pinned message schema v1.1 (DDL-018).

- **Evaluation report screen** (dashboard *Evaluation* tab, `GET /v1/evaluation/report`):
  evaluates the deployed rules baseline live on the dev and regression splits of a
  committed dataset. It shows metrics with confidence intervals, the priority
  confusion matrix, failed cases (critical first) and version pins, with
  Markdown and JSON export. The held-out test split is never served.

- **Automated accessibility tests** (`npm run test:a11y`, CI job): axe-core checks
  WCAG 2.0/2.1 A and AA on every dashboard screen against a real backend, and
  keyboard-only tests cover switching views, submitting a message and opening an
  incident.

- **Schema samples and compatibility tests**: sample documents for every contract
  are published per schema version (`backend/schemas/v2/examples`), and CI checks
  that every published sample, including those reconstructed without the fields
  added since 2.0.0, is still accepted unchanged.

- **Observability** (design v1.2, section 13.3): JSON logs carrying correlation ids
  (never transcript text or tracebacks), and Prometheus `/metrics` (requests and
  latency by route template, assessment outcomes and model status, interop
  receipts, build info).
- **Explicit simulation mode**: `NTIP_DEPLOYMENT_MODE` accepts only `simulation`,
  and every API response says so (`X-NTIP-Mode`).

- **Retention and lawful erasure** (migration 0008, DDL-019): an owner-only,
  audited procedure (`python -m ntip.store.retention`) erases incidents by id or
  by retention period, with everything derived from them, and leaves content-free
  tombstones. The application still cannot delete anything.

- **End-to-end workflow test** (Playwright, real API): ingest, evidence, override
  with a reason, audit attribution, replay and the evaluation report.
- **CI run summaries** now show test results and the evaluation report, and a
  **weekly benchmark workflow** measures latency and PostgreSQL load.

- **Human-review replay** (`GET /v1/review-comparison`, dashboard Replay tab): each
  reviewed assessment's machine output beside the operator's decision (confirmed,
  raised, lowered, reclassified, escalated), labelled as human judgement rather
  than ground truth.

- **Location level L3** (`NTIP_GIS_REFERENCE`): addresses are matched against a
  Site/Structure Address Point layer in NENA-STA-006.3 field names. A unique match
  adds a reference-validated, geocoded candidate (with the point's NGUID and
  coordinates); ambiguous or unknown addresses still need verifying. Priority is
  never affected. It ships with a synthetic layer (`data/gis`), and the dashboard
  now shows each location's origin.

### Fixed

- "Main St" and "Main Street" no longer count as a location conflict.
- Small priority badges failed WCAG contrast (faded label text). Screen readers
  also heard "P0Immediate", because the priority and its label had no space and
  an `aria-label` was misused on a generic element.

## [0.1.0] - 2026-11-10

First tagged release: a research prototype that implements the technical
design v1.2 end to end on synthetic data. **Simulation only, not for live
dispatch.** See the [release notes](docs/releases/0.1.0.md).

### Added

- **Schema 2.4.0**: layered source, canonical and advisory contracts with
  human reviews, audit events, replay runs, model outputs and interop
  receipts; JSON Schema published under `backend/schemas` (#12–#16, #24, #27,
  #32, #41).
- **Rules parser 1.3.0 (B0)**: word-bounded cue matching with polarity,
  temporality and attribution, evidence spans, victim counts, locations and
  conflicts (#12, #20, #21, #23).
- **Location quality L0–L2** (#13) and the **advisory triage engine 1.2.0**
  with sha256-pinned rulesets `research-1.0.0` and `research-1.1.0` (default);
  severity comes only from reported conditions (#14, #21, DDL-011, DDL-013).
- **Append-only event store**, in memory and on PostgreSQL with
  reversible migrations and triggers that reject updates and deletes (#15).
- **Processing pipeline** with fail-safe handling, idempotent ingest, human
  review and incident closure (#16, #41), and the **HTTP API v1** (#17).
- **Operator dashboard** (React) on API v1 with evidence, review and audit
  views, using types generated from the OpenAPI document (#18, #41).
- **Evaluation**: curated and generated synthetic datasets with frozen
  splits, bootstrap confidence intervals, a CI safety gate (no critical
  under-triage on the regression split), a scenario generator, latency and
  concurrency load benchmarks (#19, #20, #22, #33, #42).
- **Replay runs** that check reproducibility and compare rulesets (#24).
- **ML layer**: inference contract with verification and fusion modes
  (`rules_only` default, `ml_shadow`, `hybrid_review`), an inference
  service, recorded model outputs, the B1 TF-IDF + logistic regression
  baseline, a B0/B1/hybrid comparison with calibration, and an opt-in B2
  language-model adapter (#26–#30, DDL-014).
- **NG911 interop**: a pinned NENA EIDO profile (fetched and verified by
  digest, never vendored), validation, and an EIDO import gateway passing
  INT-001 to INT-012 (#31, #32).
- **Security**: bearer-token authentication with roles that fails closed
  (#39, DDL-015), per-client rate limiting (#40), a restricted read-and-append
  database role for the application (#44), and dependency and secret
  scanning in CI (#35).
- **Containers**: compose stack (PostgreSQL, migrations, API, inference
  service, dashboard) with a CI smoke test (#25).
- **Documentation**: safety case and threat model (#34), architecture
  overview, contributing guide and README (#36), property-based and
  metamorphic tests (#37), design traceability matrix (#38), and the
  decision log DDL-001 to DDL-016.

### Changed

- The backend moved from TypeScript to Python; TypeScript remains for the
  dashboard only (DDL-012, #25).
- PostgreSQL connections are pooled: about 18 times the throughput under the
  concurrency load test (#43).

### Fixed

- Concurrent follow-up messages to one incident could be lost or leave the
  current assessment blind to part of the conversation; ingest now uses
  optimistic concurrency control per incident (#42, DDL-016).
- The negation cue list and uncertainty handling: uncertainty never lowers
  priority (DDL-011).

### Security

- Vite upgraded to 6.4.6 for a published advisory (#35).

[Unreleased]: https://github.com/izuchukwumba/ng911_triage_intelligence_platform/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/izuchukwumba/ng911_triage_intelligence_platform/releases/tag/v0.1.0
