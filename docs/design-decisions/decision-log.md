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

---

## DDL-008: TypeScript/Node.js for the full backend stack

**Decision:** Implement all backend services, packages, and tooling in TypeScript running on Node.js, rather than Python or a mixed-language approach.

**Rationale:**
The platform's schema layer (Zod) is the single source of truth for both TypeScript types and runtime validation. Keeping the entire backend in one language means schema definitions, API handlers, scoring logic, and test harnesses all share the same type system without serialization boundaries or codegen steps.

Python was the primary alternative considered (strong NLP ecosystem, familiar for data-heavy work). It was deferred for the following reasons:
- Zod's design — one definition for both type inference and runtime parsing — does not have a direct Python equivalent without significantly more boilerplate
- The cross-package import story in a Python monorepo (editable installs, path manipulation) is more fragile than npm workspaces + `paths` aliases
- The NLP work here is rule-based, not model-based; Python's NLP library advantage does not apply to a keyword-matching pipeline

**Alternatives considered:**
- Python + Pydantic for the full stack: loses the Zod single-source-of-truth property
- Mixed stack (TypeScript API + Python scoring service): adds a network boundary and serialization overhead for no gain in Phase 1–2

**Impact:** All packages and services use the same `tsconfig.base.json`, test runner (jest + ts-jest), and `@ng911/*` import namespace. Adding Python components later remains feasible as advisory services communicating via HTTP.

---

## DDL-009: Replay as a first-class architectural feature, not a debug tool

**Decision:** Design `POST /replay/:id` and `POST /replay/stream` as core platform capabilities from the start, storing the full raw input alongside every incident record.

**Rationale:**
In emergency response, a priority assignment that cannot be re-examined is an audit liability. Post-incident review and quality assurance both depend on being able to answer: "given this call, what would the system decide today — and how does that compare to what it decided then?"

This requires:
1. Storing `raw_input` (the original transcript text) on every incident record — not just the parsed output
2. Attaching `audit.parser_version` and `audit.scoring_version` so the replay can detect when logic has changed
3. Returning a structured diff (score delta, tier change, indicator changes) rather than just the replayed record

The alternative — adding replay capability later as a debugging feature — would have required retrofitting raw input storage to existing records and would have missed incidents ingested before the feature landed.

**Impact:** The `replay/stream` endpoint makes it possible to evaluate the full impact of a scoring rule change across all stored incidents before deploying the change, which is the foundation of the scoring comparison workflow in `packages/evaluation-harness`.

---

## DDL-010: Negation filtering with token-window boundary awareness

**Decision:** Implement negation handling as a token-position-aware filter with an 8-token lookback window and sentence boundary detection, rather than simple prefix matching.

**Rationale:**
Simple negation detection ("if 'not' appears anywhere before a keyword, suppress it") produces false positives at sentence boundaries. The phrase "He is not conscious of how serious this is. He is bleeding heavily" should not suppress `ACTIVE_BLEEDING` because "not" appears earlier in the paragraph.

The 8-token window was chosen to cover natural phrasing distances ("he is definitely not", "does not appear to be", "I was told he is not") while not being so wide that it crosses clause boundaries in compound sentences.

Sentence boundary characters (`.`, `!`, `?`, `;`) are treated as hard stops for the negation window. A negation word that precedes a sentence boundary cannot negate an indicator that follows it.

**Alternatives considered:**
- Dependency parsing (spaCy-style): accurate but requires a model dependency and is overkill for a rules-based keyword pipeline
- Simple "not" prefix matching within 3 tokens: too narrow — misses "he is no longer breathing" (4 tokens between "no" and "breathing")
- Negation blocklist per indicator: maintainable but requires curating negative phrases for every indicator keyword

**Impact:** The negation filter is called from `extractSeverityIndicators()` in the transcript parser. False negatives (indicators that should fire but don't) remain possible with unusual phrasing; the conservative default is to allow ambiguous indicators through for operator review.
