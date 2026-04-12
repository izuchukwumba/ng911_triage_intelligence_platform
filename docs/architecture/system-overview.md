# System Architecture Overview

## Platform Summary

This platform is an NG911-aligned decision-support layer for emergency call triage. It converts messy, unstructured emergency-call-like inputs into structured incident objects, scores them using explainable logic, and preserves a complete audit trail for replay and post-incident review.

---

## Pipeline

```
Raw Input (transcript / JSON / API call)
          ↓
    Ingestion API  (services/ingestion-api)
          ↓
 Transcript Parser  (services/transcript-parser)
     - language detection (en / es / unknown)
     - caller stress detection (low / moderate / high)
     - domain classification (ems, police, fire, hazmat, other)
     - subtype classification (cardiac_arrest, shooting, etc.)
     - severity indicator extraction with negation filtering
     - address extraction
     - parse confidence estimation
          ↓
  Location Validator  (packages/location-validator)
     - address completeness scoring
     - dispatchable location score
     - semantic location confidence
     - uncertainty detection
          ↓
  Structured Incident Record  (packages/incident-schema)
     - UUID, timestamps, raw input preserved
     - incident core (domain, subtype, summary, indicators)
     - location (address, quality scores)
     - caller context (language, stress level)
     - triage (scores populated next)
     - audit metadata (parser_version, scoring_version, schema_version)
          ↓
  Prioritization Engine  (services/prioritization-engine)
     - domain base score
     - weighted indicator rules
     - victim count multiplier
     - location and confidence penalties
     - reason code generation
     - priority tier assignment (P0–P4)
     - score_breakdown[] per-factor contribution array
          ↓
  Incident Store  (services/ingestion-api — in-memory / PostgreSQL)
          ↓
  REST API Response + Audit Trail
          ↓
    ┌─────────────────┬────────────────────┐
    ▼                 ▼                    ▼
Dashboard         Replay Engine       Evaluation Harness
(apps/dashboard)  POST /replay/:id    (packages/evaluation-harness)
Operator queue,   Re-parse + re-score  Fixture-based accuracy
score breakdown,  any stored incident  and safety-gate metrics
"Why this tier?"  against any version
```

---

## Module Map

| Module | Path | Role |
|--------|------|------|
| `incident-schema` | `packages/incident-schema` | Canonical Zod-validated TypeScript types |
| `location-validator` | `packages/location-validator` | Dispatchable location quality scoring |
| `evaluation-harness` | `packages/evaluation-harness` | Fixture-based evaluation harness and compare-versions CLI |
| `test-data-generator` | `packages/test-data-generator` | Synthetic scenario generation + CLI |
| `transcript-parser` | `services/transcript-parser` | Rules-based NLP → structured incident |
| `prioritization-engine` | `services/prioritization-engine` | Weighted rule scoring with reason codes |
| `ingestion-api` | `services/ingestion-api` | Express REST API — ingest, score, replay |
| `dashboard` | `apps/dashboard` | React 18 + Vite operator interface |

---

## Data Flow for a Single Transcript

1. `POST /ingest` with `{ "text": "..." }` body
2. `parseTranscript(text)` builds a partial `IncidentRecord`:
   - Language and stress heuristics run first
   - Domain and subtype classification via keyword matching
   - Severity indicators extracted, negation filter applied (8-token lookback)
   - Address tokens extracted, location validator scores quality
3. `scoreIncident(record)` applies the versioned rule config:
   - Domain base score selected
   - Each indicator weight added to running total
   - Victim count multiplier applied
   - Confidence and location penalties subtracted
   - Score clamped to [0, 1], tier assigned against thresholds
   - `score_breakdown[]` array assembled in contribution order
4. Merged record saved to incident store
5. Response returns full record + `score_breakdown`

---

## Replay Flow

`POST /replay/:id` re-processes a stored incident:

1. Load incident by UUID from store
2. Extract `raw_input.text` (always preserved)
3. Run `parseTranscript` + `scoreIncident` against current versions
4. Compute diff: `score_delta`, `tier_changed`, `indicator_changes`
5. Return `{ original, replayed, diff }` — no mutation of stored record

`POST /replay/stream` runs the same flow for all stored incidents and returns aggregate stats.

---

## Evaluation Flow

The evaluation harness (`packages/evaluation-harness`) runs independently of the live API:

1. Load fixture set (`data/fixtures/sample-incidents.json`)
2. For each fixture: run `parseTranscript` + `scoreIncident` in-process
3. Compare `actual_domain`, `actual_subtype`, `actual_tier` against fixture expected values
4. Compute aggregate metrics: domain/subtype/tier accuracy, false-P0 rate, missed-P0 rate
5. Group results by expected tier (scenario buckets)
6. Compute latency stats (mean, p50, p95, min, max)
7. Print formatted report or write JSON output

The `compare-versions.ts` CLI accepts two scoring config paths and runs both against the same fixtures, producing a tier transition matrix and change summary.

See [docs/evaluation/evaluation-plan.md](../evaluation/evaluation-plan.md) for metric definitions and [docs/evaluation/benchmark-report-v0.2.0.md](../evaluation/benchmark-report-v0.2.0.md) for the current baseline results.

---

## Key Design Decisions

See [decision-log.md](../design-decisions/decision-log.md) for full rationale.

- **Rules-first, not ML-first** — deterministic scoring enables explainability and auditability
- **Zod for schema validation** — runtime type safety at API boundaries, types inferred from schema
- **Versioned scoring config** — `config/scoring-rules.json` is keyed with `scoring_version`; config upgrades do not break historical records
- **Replay as a first-class endpoint** — `POST /replay/:id` re-processes any stored incident against the current parser and scorer
- **Location as a quality signal** — low `dispatchable_location_score` applies a scoring penalty so operators see that uncertainty
- **Reason codes always preserved** — every scoring decision is traceable in the audit trail
- **Negation filter with sentence boundary detection** — 8-token lookback window; indicators only suppressed if all keyword occurrences are negated

---

## Phase Roadmap

| Phase | Deliverables | Status |
|-------|-------------|--------|
| Phase 1 | Schema, parser, scorer, ingestion API, fixtures, tests | Complete |
| Phase 2 | Dashboard, PostgreSQL audit store, full replay engine, test data generator, location validator | Complete |
| Phase 3 | Evaluation harness, benchmark reporting, reason code taxonomy, fixture expansion (23 labeled scenarios) | Complete |
| Phase 4 | Public demo environment, expanded fixture set with real linguistic variation, architecture writeup | Next |
