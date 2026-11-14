# Design Decision Log

This log records significant architectural and implementation decisions, the rationale behind them, and any alternatives that were considered.

---

## DDL-001: Zod for schema definition and runtime validation

> **Superseded for the backend by DDL-012.** Schemas move to Pydantic; the dashboard consumes TypeScript types generated from the backend's OpenAPI document.

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
- allows it to influence priority scoring (low dispatchability applies a penalty) — *superseded by DDL-011: location quality is now a zero-weight verification flag*
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

> **Superseded by DDL-012** (Python backend, TypeScript frontend).

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

---

## DDL-011: Uncertainty never lowers priority

**Decision:** Low location dispatchability and low parser confidence are reported as zero-weight *verification flags* rather than score penalties. Supersedes the penalty described in DDL-004. Introduced in scoring 0.3.0.

**Rationale:**
Through scoring 0.2.0, `LOW_LOCATION_CONFIDENCE` (−0.08) and `LOW_PARSE_CONFIDENCE` (−0.06) were subtracted from the same score that selects the priority tier. That couples two independent questions — *how urgent is this?* and *how sure are we about where it is / what it is?* — and the coupling fails in exactly the wrong direction: a caller who cannot give an address, or whose speech is hard to parse, is not less urgent and is often more vulnerable. On the 23 fixtures, removing the deduction moved fixture-020 (domestic violence, caller does not know where they are) from P4 to P3 with no regressions elsewhere.

Uncertainty should change the *workflow* (verify the location, confirm the classification), not the *priority*. This matches the safety invariants in the v1.2 design document (sections 3A.6 and 7.5) and ADR-004 there.

**Implementation:**
- `penalty_rules` in `scoring-rules.json` is replaced by `verification_flags`, which has no weight field, so the invariant cannot be reintroduced by a config edit alone
- Flags still appear in `reason_codes` and in `score_breakdown` with `weight: 0`; the dashboard shows them in their own section
- Invariant tests score the same record with and without degraded location/confidence and require identical scores and tiers

**Alternatives considered:**
- Setting the penalties to 0 in config: leaves a knob that silently reintroduces the problem
- Clamping so penalties cannot cross a tier boundary: still lowers scores, and tier boundaries move

**Not addressed here:** `POSSIBLE_PRANK` (−0.40) can still suppress credible emergency evidence, which the v1.2 design also prohibits. It is a separate behaviour change and needs its own decision.

---

## DDL-012: Python backend, TypeScript frontend

**Decision:** Move all backend code — API, parser, triage engine, location assessment, audit store, NG911 interop adapters, ML inference, and evaluation — to a single Python package under `backend/`. Keep TypeScript only for the operator dashboard (`apps/dashboard`). Supersedes DDL-008, the backend half of DDL-001, and §3.3 / ADR-002 of the v1.2 design document, which proposed a TypeScript core with a separate Python ML service.

**Rationale:**
DDL-008 rested on the NLP being rule-based ("Python's NLP library advantage does not apply to a keyword-matching pipeline") and named Python as the way forward once models were involved. The v1.2 design makes machine learning the core research component, which removes that premise:

- **The central experiment is a comparison.** The rules parser (baseline B0) must be evaluated against ML models (B1/B2) on the same frozen dataset, with the same scoring code and one reproducibility manifest. With B0 in TypeScript and B1/B2 in Python, that needs either two evaluation harnesses or a cross-language bridge — both undermine "reproduce from a single command" (design §3A.10, ML-1).
- **The ML and statistics ecosystem is Python.** Model training and serving, calibration, span-aware NLP and bootstrap confidence intervals (design §3A.8) are first-class in Python and partial or absent in Node.
- **Single-maintainer cost.** Two backend languages mean two type systems, two test runners, two lockfiles and a schema-sync step, for no isolation benefit at this stage.
- **Migration is cheapest now.** The TypeScript backend is about 3.5k lines, and its schema, parser output and scorer need a structural rewrite for v1.2 anyway (layered source/canonical/advisory records, evidence spans, severity separated from location quality).

**Shape:**
- One installable package, `ntip`, organised as a modular monolith (`api`, `schema`, `parser`, `triage`, `location`, `audit`, `interop`, `ml`, `evaluation`). Modules are split into services only when isolation or scaling is measured to require it (design §3.2).
- **Contracts:** Pydantic v2 models are the single source of truth. They produce JSON Schema 2020-12 (design §4.3) and, through FastAPI, an OpenAPI document from which the dashboard's TypeScript types are generated.
- **Tooling:** Python 3.12, FastAPI, Pydantic v2, pytest, ruff, mypy (strict). PostgreSQL access through SQLAlchemy 2 with Alembic migrations when persistence is ported.

**Migration plan (strangler, not big-bang):**
1. Scaffold `backend/` alongside the existing TypeScript services; nothing is removed yet.
2. Implement the v1.2 layered schema in Pydantic.
3. Port the rules parser and triage engine as baseline B0, driven by the existing fixtures plus the intended behaviour in the TypeScript tests (including the 11 tests that currently fail on `main`).
4. Port persistence as an append-only event store, then the API surface, then replay and evaluation.
5. Point the dashboard at the Python API using generated types.
6. Delete `services/*` and the TypeScript backend packages once the dashboard runs end to end on the Python backend.

Until step 6, the TypeScript backend remains the running system and receives only safety fixes.

**Alternatives considered:**
- TypeScript core + Python ML service (design v1.2 §3A.3): adds a network boundary and duplicate contracts between B0 and the models it is compared against; better suited to a larger existing TypeScript codebase than this one.
- Stay on TypeScript and call ML via ONNX/transformers.js: viable for inference, poor for training, calibration and statistical evaluation.

**Trade-off:** The existing TypeScript tests and Express API are rewritten rather than reused, and backend/frontend types are no longer shared directly — they are generated from OpenAPI instead.

---

## DDL-013: Triage severity comes only from reported conditions

**Decision:** The Python triage engine (`ntip.triage`, ruleset `research-1.0.0`) sets severity only from current, non-negated observation codes through versioned ruleset rules. Every other signal becomes a review action for a human. Resolves the `POSSIBLE_PRANK` issue left open in DDL-011.

**Rationale:**
DDL-011 stopped location and parser confidence from lowering priority in the TypeScript scorer, but left one more way for a weak signal to bury a strong one: `POSSIBLE_PRANK` subtracted 0.40, so "this is not a prank, he's not breathing" could be pushed down the queue. The design forbids this (v1.2, section 7.1: "an apparent prank indicator must not silently suppress credible emergency evidence").

The engine therefore separates two kinds of input:

| Input | Effect |
|---|---|
| Current affirmed or uncertain cue | Fires severity rules (floor or escalate) |
| Negated, historical, hypothetical cue | Ignored for severity; kept in the record |
| Uncertain high/critical cue | Full weight + `CONFIRM_CRITICAL_REPORT` |
| Location quality below sufficient | `VERIFY_LOCATION` |
| Contradiction / conflicting count | `RESOLVE_CONFLICT`; the affirmed side still counts |
| Possible prank | `CONFIRM_CLASSIFICATION`; sets `low` only if nothing else was reported |
| Weak or unknown classification | `CONFIRM_CLASSIFICATION` |
| Nothing reported, unknown domain | `undetermined` severity, P2 — never the bottom of the queue |

**Versioning:** severity rules live in released JSON rulesets pinned by sha256 (a test fails if a released file changes). Review policies live in code and are versioned with the engine (`P-REVIEW-00x`, engine 1.0.0). Both appear in `Assessment.reasons`.

**Alternatives considered:**
- Port the weighted score: keeps the coupling that caused DDL-011.
- Down-weight uncertain cues: "I think he's not breathing" is exactly the call that must not wait; uncertainty is resolved by a human, not by arithmetic.

**Limitations:** the bands and the research-v1 priority labels are project-defined and have not been reviewed by public-safety practitioners (design v1.2, open question 6).

---

## DDL-014: Rules-only stays the default inference mode

**Decision:** The platform defaults to `rules_only`. `ml_shadow` and `hybrid_review` with B1 remain available for research and are exercised in CI, but are not the default.

**Rationale:**
The first comparison (docs/evaluation/results, "ML comparison") shows hybrid B0+B1 never increases critical false negatives and removes the two critical under-triages B0 makes on the curated test split (milestone ML-4 gate met). It also roughly doubles over-triage and lowers cue precision, B1 is uncalibrated, it has no negation or tense model, and every result is on synthetic, author- or generator-labelled data. Trading precision for recall is a judgement about operator workload that should be made with qualified practitioners, not by the author on synthetic benchmarks (design v1.2, sections 3A.6 and 16.3).

`ml_shadow` is the recommended next step for any pilot: it records model output beside every incident without affecting what operators see, so the trade-off can be measured on realistic traffic before anyone relies on it.

**Revisit when:** independent annotation, practitioner review of the over-triage cost, or a calibrated model with negation handling changes the trade-off.

---

## DDL-015: Token authentication with roles, failing closed

**Decision:** Every `/v1` route except the health checks requires a bearer token mapped to a principal and a role (`viewer`, `operator`, `analyst`, `admin`). The server refuses to start with neither `NTIP_API_TOKENS` nor an explicit `NTIP_AUTH_DISABLED=1`. With authentication on, the reviewer of an incident and the requester of a replay are the token's principal; any name in the request body is ignored.

**Rationale:**
The threat model listed the unauthenticated research API as the main gap before any shared deployment, and design v1.2 §2.3 already distinguishes operators, researchers and viewers. Attributing reviews from the body would let anyone record a decision in someone else's name, undermining the audit trail that the platform's accountability rests on.

**Alternatives considered:**
- *Open by default with a warning:* easy to deploy by accident; rejected in favour of an explicit opt-out.
- *OAuth/OIDC:* the right choice for a real deployment, but needs an identity provider; static tokens keep the research setup self-contained and the route-level permission model carries over unchanged.

**Limits:** tokens are static (no expiry or rotation), and incidents are not partitioned by tenant.

---

## DDL-016: Optimistic concurrency control per incident

**Decision:** Every ingest writes with an expectation on how many messages the incident had when the conversation was read; the store checks it atomically (PostgreSQL: per-incident advisory transaction lock) and the pipeline re-reads and retries on a mismatch. Incident versions are numbered by message count, not identified by derivation time.

**Rationale:** The concurrency load test showed that simultaneous follow-up messages to one incident could (a) collide on the incident-version key and drop a caller's message, or (b) each be interpreted without the other, leaving the current assessment blind to part of the conversation, e.g. a report that people are trapped. Both are safety failures. Optimistic control keeps the common case lock-free, works across processes, and guarantees that every stored version and assessment covers the whole conversation.

**Alternatives considered:**
- *An in-process lock per incident:* simpler, but does not hold across multiple API processes.
- *Serialising all writes:* correct but throttles unrelated incidents.

**Trade-off:** heavy contention on one incident costs retries (bounded at 20 attempts; the caller gets an error rather than a silently partial result if they run out).

---

## DDL-017: Tenants separate incidents; other tenants see nothing

**Decision:** Every source event and replay run carries a `tenant_id` (schema 2.5.0). Each API principal belongs to exactly one tenant, set with its token. EIDO imports take the tenant of the interop credential. Every incident route checks the incident's tenant and answers **404** for another tenant's incident, exactly as for one that does not exist. Lists and replays are filtered, and idempotency keys are scoped per tenant. Records written before tenants existed belong to the `default` tenant.

**Rationale:** INT-010 and the threat model required isolation beyond the interop receipts. Answering 403 would confirm that an incident id exists in another organisation; 404 reveals nothing. A shared idempotency key space would let one tenant replay, and so read, another tenant's result.

**Alternatives considered:**
- *A database per tenant:* the strongest isolation, but heavy for a research platform; the column-based design can move there later without API changes.
- *Admins see all tenants:* convenient, but it would make a single token a cross-tenant credential; rejected until there is a real need and an audit design for it.

---

## DDL-018: NENA-STA-024 conveyance as a subscriber only

**Decision:** The platform implements only the subscriber role of NENA's WebSocket subscribe/notify conveyance. It connects out to an authorised notifier over TLS, subscribes to EIDOs, acknowledges each notification and passes every EIDO through the existing import gateway. It does not act as a notifier, send push messages or dereference EIDOs by URL. Messages are validated against NENA's message schema, pinned to a commit and a sha256, and fetched rather than vendored because the repository has no licence.

**Rationale:** The platform consumes incident data and never writes back (§3B.1, ADR-INT-002), so the subscriber is the only role it needs. Routing conveyed EIDOs through the gateway means they get the same validation, idempotency, revision ordering, tenant scoping and receipts as HTTP imports. Fetching by reference would make the platform send requests to addresses an external party chose, so it is not done.

**Acknowledgements:** 200 only when every EIDO in a notification was accepted, 400 when any was rejected (its receipt is kept), 413 when too large, 500 on a processing failure, and 481 for an unknown subscription. A resent transaction gets its original answer, so a notifier's retries cannot cause double processing.

**Limits:** Only the message schema has been reviewed, not the standard's normative text, so no conveyance compliance is claimed (§3B.2). Validation dispatches on the message's top-level key because the published `oneOf` unions are ambiguous.

---

## DDL-019: Lawful erasure through an owner-only, audited procedure

**Decision:** The store stays append-only for the application, but there is one sanctioned way to delete. `python -m ntip.store.retention`, run with the table owner's credentials, erases selected incidents (by id or by retention period, optionally per tenant): every row derived from each incident, and the EIDO receipts carrying its raw payload. It works in one transaction per incident, under the same advisory lock ingest uses, and writes a content-free tombstone to an append-only `erasures` table. The append-only trigger allows `DELETE` only inside a transaction that has set the transaction-local `ntip.erasure_id`; UPDATE and TRUNCATE stay refused, and the application role has no DELETE privilege. The procedure is a dry run unless `--execute` is given.

**Rationale:** Design v1.2 section 9.3 requires explicit retention and deletion rules, and says audit retention must not override lawful deletion. An append-only store with no deletion path cannot hold any real personal data lawfully. Tombstones keep accountability (that something was erased, when, by whom and why) without keeping the content.

**Alternatives considered:**
- *Crypto-shredding (per-incident encryption keys, deleted on erasure):* keeps rows physically immutable, but needs key management and makes every read decrypt; disproportionate for a research platform.
- *Disabling the triggers during erasure:* takes table-wide exclusive locks and briefly removes the protection for every writer; the flagged-transaction check is narrower.

**Kept on purpose:** Replay runs, which hold identifiers, priorities and reason codes but no transcript text or payloads.


---

## DDL-020: A small local model is the primary ML path; the hosted LLM is an optional comparison

**Decision:** B1e, a small openly licensed encoder trained on the project's own data and run locally on CPU, is the platform's primary ML model (ML layer design v1.0, section 5.3). B2, the hosted structured-output LLM, is demoted to an optional, research-only comparison: it stays in the code, off by default, and is run at most once on synthetic data if the project owner approves the cost. No milestone, gate or default depends on it.

**Rationale:**
- *Deployment reality:* an emergency communications centre would not send call content to a third-party API. Privacy, legal and network constraints rule it out, and design v1.2 section 3B.6 already forbids it for real data. A model that could never be deployed should not be the platform's main path.
- *Latency and cost:* a hosted LLM adds seconds and a per-call charge; a small encoder runs in milliseconds on an ordinary CPU at no cost per call, inside the existing timeout and fallback rules.
- *Reproducibility:* local weights are pinned by hash and give the same output every run; a hosted model can change underneath the platform.
- *What is lost:* the evaluation loses its zero-shot ceiling (how well a strong general model does untrained). If that comparison is wanted, it can be made with B2 once, or with an open-weight model run locally.

**Alternatives considered:**
- *Keep B2 as a full baseline (ML layer design v1.0 as first written):* gives the zero-shot comparison but costs money on every run, and puts an undeployable model on the critical path of the milestones.
- *Remove B2:* saves maintenance, but discards working, tested code that a later paper may want for the comparison.

**Revisit when:** a locally run open-weight language model becomes practical on the reference hardware, or a deployment arrangement allows hosted inference under appropriate agreements.

---

## DDL-021: Twelve more reported conditions, with research severities

**Decision:** The cue vocabulary grows from 23 to 35 codes. Parser 1.5.0 detects, in English and Spanish:
- `ALLERGIC_REACTION`, `DIABETIC_EMERGENCY`, `CHILDBIRTH`, `POISONING`;
- `TRAFFIC_COLLISION`, `DROWNING`, `BURN_INJURY`, `ELECTROCUTION`, `FALL_FROM_HEIGHT`;
- `SELF_HARM_RISK`, `INTRUDER_PRESENT`, `MISSING_PERSON`.

Ruleset `research-1.2.0`, now the default, rates each one `high`, except `TRAFFIC_COLLISION` and `MISSING_PERSON`, which are `elevated`. The existing rules still raise severity when other cues are present: people trapped, a child, several people hurt. The labelling guide moves to v2.1.

**Rationale:** The platform could not represent a large share of ordinary emergency calls (crashes, falls, burns, labour, overdose-like poisonings, mental-health crises, break-ins). Those calls fell back to generic injury or `undetermined`. The ML layer also needs a vocabulary broad enough to learn from (ML layer design §4.2). Every severity comes only from the reported condition, as DDL-013 requires.

**Not validated:** the severities are the author's research rubric. They are flagged for the practitioner review in the [research protocol](../research/research-protocol.md) (study A), and are not a dispatch protocol.

**Consequences:**
- Three curated cases gained a label for a new code. No priority changed, and the regression safety gate still passes.
- `generated-1.0.0-seed42.jsonl` predates the new codes and is kept unchanged, so earlier reports stay reproducible. Its "fell down the stairs" family has no `FALL_FROM_HEIGHT` label, so results on that file under `research-1.2.0` show over-triage for that family.
- B2's output schema lists every code, so its prompt version moves to 1.1.0.
- A B1e model trained for 23 codes is refused by the current code, which expects 35.

**Revisit when:** practitioner review (study A) or independent annotation disagrees with a severity or a definition.

## DDL-022: Neither score calibration nor fusion policy 2.0.0 is adopted

**Decision:**
- **Fusion:** hybrid fusion stays on policy 1.0.0, so every verified model
  cue is added. Policy 2.0.0 stays in the code and the schema for research,
  selectable with `NTIP_FUSION_POLICY`, but it is not the default.
- **Calibration:** B1e runs uncalibrated. Temperature scaling and per-cue
  thresholds (`ntip.ml.calibrate`) stay available, but no calibration file
  is applied (milestone ML-9; [results](../evaluation/results/README.md#ml-9-outcome-calibration-and-fusion-2-on-generator-22-not-adopted)).

**Evidence:**
- **Setup:** a B1e trained on generator 2.2's dev split, calibrated on its
  regression split (870 calls from families it never saw), and compared on
  those calls and on curated dev + regression.
- **Fusion 2 fails its adoption gate** (ML layer design §7 required
  critical under-triage not to rise). It treats only the three codes that
  are critical on their own as critical. Many P0 calls, however, are a
  *high* cue plus a child or several victims. Fusion 2 held those back as
  suggestions, and critical under-triage rose from 41 to 81 of 249 P0
  calls, about the rules' own 82.
- **Calibration did not improve the system** on either dataset. It made
  fusion 1 over-triage two more curated calls (8 instead of 6).
- **The project owner set the stopping rule in advance:** one more attempt
  at calibration after fixing the data, then skip it if it did not help.

**Rationale:** Never risking a critical miss (design v1.2 §3A.6) outweighs
precision. Fusion 1 has the most over-triage (80 of 870 calls against the
rules' 48), but it also has by far the least under-triage (123 against 313).

**Lessons:**
- The 30 curated cases favoured fusion 2, and the 870 regression calls
  reversed that. A policy choice needs a sample large enough to see rare
  escalation paths.
- A split-based design should first check that each cue code appears on
  both sides of the split. The data cards show this.

**Revisit when:** a fusion policy treats "would this cue change the
priority" as critical, rather than a fixed code list. Calibration is worth
retrying once adjudicated labels exist (ML-11) or B1e trains on much more
varied data.
