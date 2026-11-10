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
