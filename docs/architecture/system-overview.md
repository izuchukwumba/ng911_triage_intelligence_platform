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
     - domain classification
     - subtype classification
     - severity indicator extraction
     - address extraction
     - confidence estimation
          ↓
  Location Validator  (packages/location-validator)
     - address completeness scoring
     - dispatchable location score
     - uncertainty detection
          ↓
  Structured Incident Record  (packages/incident-schema)
     - UUID, timestamps, raw input preserved
     - incident core (domain, subtype, summary, indicators)
     - location (address, coords, quality scores)
     - caller context
     - triage (scores populated next)
     - audit metadata
          ↓
  Prioritization Engine  (services/prioritization-engine)
     - weighted indicator rules
     - location and confidence penalties
     - reason code generation
     - priority tier assignment (P0–P4)
          ↓
  Incident Store  (in-memory / PostgreSQL in Phase 2)
          ↓
  REST API Response + Audit Trail
          ↓
  Dashboard  (apps/dashboard — Phase 2)
          ↓
  Replay Engine  (POST /replay/:id — Phase 1 stub)
```

---

## Module Map

| Module | Path | Role |
|--------|------|------|
| `incident-schema` | `packages/incident-schema` | Canonical Zod-validated TypeScript types |
| `location-validator` | `packages/location-validator` | Dispatchable location quality scoring |
| `test-data-generator` | `packages/test-data-generator` | Synthetic scenario generation + CLI |
| `transcript-parser` | `services/transcript-parser` | Rules-based NLP → structured incident |
| `prioritization-engine` | `services/prioritization-engine` | Weighted rule scoring with reason codes |
| `ingestion-api` | `services/ingestion-api` | Express REST API — ingest, score, replay |

---

## Data Flow for a Single Transcript

1. `POST /ingest` with `{ "text": "..." }` body
2. `parseTranscript(text)` builds an `IncidentRecord` with `triage` fields null
3. `validateLocation(...)` scores address quality and attaches notes
4. `scoreIncident(record)` applies the versioned rule config and produces `priority_score`, `priority_tier`, and `reason_codes`
5. The merged record is saved to the incident store
6. Response returns the full record plus `score_breakdown` array

---

## Key Design Decisions

See [decision-log.md](../design-decisions/decision-log.md) for full rationale.

- **Rules-first, not ML-first** — deterministic scoring enables explainability and auditability
- **Zod for schema validation** — runtime type safety at API boundaries, types inferred from schema
- **Versioned scoring config** — `config/scoring-rules.json` is keyed with `scoring_version`; config upgrades do not break historical records
- **Replay as a first-class endpoint** — `POST /replay/:id` re-processes any stored incident against the current parser and scorer
- **Location as a quality signal** — low `dispatchable_location_score` applies a scoring penalty so operators see that uncertainty
- **Reason codes always preserved** — every scoring decision is traceable in the audit trail

---

## Phase Roadmap

| Phase | Deliverables |
|-------|-------------|
| Phase 1 | Schema, parser, scorer, ingestion API, fixtures, tests |
| Phase 2 | Dashboard, PostgreSQL audit store, full replay engine |
| Phase 3 | Test data generator, location validator (complete), evaluation harness |
| Phase 4 | Public docs, architecture writeup, NG911 alignment narrative |
