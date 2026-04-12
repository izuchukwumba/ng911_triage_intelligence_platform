# Design Decision Log

This log records significant architectural and implementation decisions, the rationale behind them, and any alternatives that were considered.

---

## DDL-001: Zod for schema definition and runtime validation

**Decision:** Use Zod to define the incident schema rather than plain TypeScript interfaces.

**Rationale:**
TypeScript types are erased at runtime. API boundaries receive untyped JSON. Zod provides both the TypeScript type inference (via `z.infer<>`) and runtime validation from a single source of truth.

**Alternatives considered:**
- Plain TypeScript interfaces with manual validation: loses runtime safety
- JSON Schema + TypeScript codegen: two sources of truth, harder to maintain
- io-ts: more powerful but significantly higher learning curve for contributors

**Impact:** Schema changes are always both type-safe and runtime-safe. The ingestion API's `/ingest/score` endpoint uses `IncidentRecordSchema.safeParse()` to validate externally-supplied records.

---

## DDL-002: Rules-first prioritization engine

**Decision:** Implement the prioritization engine as a weighted rule engine with a JSON configuration file, rather than a machine learning model.

**Rationale:**
In high-stakes operational domains, explainability matters more than marginal accuracy gains. A rule-based system:
- generates reason codes for every score contribution
- is fully deterministic and testable
- can be reviewed and adjusted by non-ML engineers
- is auditable without model introspection tooling

ML can be layered later as an advisory signal without replacing the explainable baseline.

**Alternatives considered:**
- Logistic regression: requires labeled training data and loses transparent reason codes
- LLM-based scoring: high cost, latency, and non-determinism — unsuitable for auditability

---

## DDL-003: Versioned scoring configuration

**Decision:** Store scoring weights in `config/scoring-rules.json` with a `scoring_version` field, and attach this version to every `AuditSchema` record.

**Rationale:**
When scoring logic changes, historical incidents should be re-scorable with the old or new config. Without versioning, it is impossible to know whether a priority assignment reflects current or past logic.

**Impact:** The `POST /replay/:id` endpoint can compare old vs. new scoring by checking `audit.scoring_version`.

---

## DDL-004: Dispatchable location score as a first-class field

**Decision:** Model location quality as two numeric scores (`location_confidence` and `dispatchable_location_score`) rather than a boolean or a plain string.

**Rationale:**
Emergency response is fundamentally limited by location quality. An incident may be high severity but unserviceable if there is no actionable location. Treating this as a numeric signal:
- allows it to influence priority scoring (low dispatchability applies a penalty)
- makes location uncertainty visible to operators in the UI
- distinguishes between semantic confidence (do we understand the location?) and operational dispatchability (can we route a response?)

---

## DDL-005: In-memory store for Phase 1

**Decision:** Use a `Map<string, IncidentRecord>` as the incident store in Phase 1 rather than connecting to PostgreSQL immediately.

**Rationale:**
The store interface (`incidentStore.save`, `findById`, `findAll`) is defined as a stable contract. Replacing the implementation with a PostgreSQL adapter in Phase 2 requires no changes to route handlers.

Fast iteration on the core parsing and scoring logic is more valuable in Phase 1 than persistence durability.

---

## DDL-006: Monorepo with npm workspaces

**Decision:** Use a single monorepo with npm workspaces, with packages in `packages/` and services in `services/`.

**Rationale:**
Monorepo structure makes the platform's coherence visible. Internal packages share TypeScript base config, test tooling, and versioning context. Cross-package imports resolve without publication or symlinks.

---

## DDL-007: score_breakdown returned alongside priority result

**Decision:** Return a `score_breakdown` array in scoring results, listing each contributing rule with its weight and description.

**Rationale:**
Operators using the platform need to understand not just the score but why it was assigned. `score_breakdown` provides the machine-readable basis for a "why this score?" panel in the dashboard. It is also essential for the evaluation harness.
