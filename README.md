# NG911 Triage Intelligence Platform

An NG911-aligned decision-support platform that converts emergency-call-like inputs into structured incident objects, prioritizes them using explainable scoring logic, and preserves replayable audit trails for training, evaluation, and post-incident analysis.

---

## What this is

Modern emergency response is moving toward IP-based, GIS-aware, structured data workflows. But modernizing transport infrastructure does not solve the downstream intelligence problems: inputs are messy, prioritization is inconsistent under pressure, location quality is variable, and post-incident review requires traceability.

This platform targets that gap. It is not a PSAP replacement, a SIP/i3 implementation, or a compliance certification effort. It is a credible decision-support layer designed to improve three things:

1. **Interpretation** — convert unstructured inputs into normalized incident objects
2. **Prioritization** — score and rank incidents using transparent, reviewable logic
3. **Accountability** — preserve the full decision chain for replay, review, and improvement

See [docs/standards-alignment/ng911-alignment.md](docs/standards-alignment/ng911-alignment.md) for an honest explanation of what "NG911-aligned" means.

---

## Architecture

```
POST /ingest { text: "..." }
       ↓
  Transcript Parser         — domain, subtype, severity indicators, address extraction
       ↓
  Location Validator        — dispatchable location score, validation notes
       ↓
  Incident Record           — versioned, Zod-validated, UUID-keyed
       ↓
  Prioritization Engine     — weighted rule scoring, reason codes, P0–P4 tier
       ↓
  Incident Store            — persisted with full audit trail
       ↓
  GET /incidents            — ranked list for operator review
  POST /replay/:id          — re-score any incident for evaluation
```

Full architecture: [docs/architecture/system-overview.md](docs/architecture/system-overview.md)

---

## Monorepo Structure

```
ng911-triage-intelligence/
  packages/
    incident-schema/          Zod-validated TypeScript types (canonical schema)
    location-validator/       Dispatchable location quality scoring
    test-data-generator/      Synthetic scenario generation + CLI
  services/
    transcript-parser/        Rules-based NLP → structured incident
    prioritization-engine/    Weighted scoring with reason codes + config
    ingestion-api/            Express REST API
  data/
    fixtures/                 Sample incidents for testing
    generated/                CLI-generated scenario sets
  docs/
    architecture/
    design-decisions/
    standards-alignment/
```

---

## Getting Started

### Prerequisites

- Node.js >= 18
- npm >= 8 (workspaces support)

### Install

```bash
npm install
```

### Run the ingestion API

```bash
cd services/ingestion-api
npm run dev
# → http://localhost:3001
```

### Submit a transcript

```bash
curl -s -X POST http://localhost:3001/ingest \
  -H "Content-Type: application/json" \
  -d '{"text": "My father is not breathing. Cardiac arrest at 123 Oak Street."}' \
  | jq .
```

### List incidents

```bash
curl -s http://localhost:3001/incidents | jq .
```

### Replay and compare an incident

```bash
curl -s -X POST http://localhost:3001/replay/<incident_id> | jq .
```

### Generate synthetic test data

```bash
cd packages/test-data-generator
npx ts-node src/cli.ts --count 20 --domain ems --severity critical
```

---

## Running Tests

```bash
npm test
```

Tests cover:
- `location-validator` — scoring edge cases, completeness patterns, output bounds
- `transcript-parser` — domain/subtype classification, indicator extraction, schema compliance
- `prioritization-engine` — tier assignment, reason codes, breakdown accuracy, fixture-based acceptance tests

---

## API Reference

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/ingest` | Submit a transcript. Runs parse + score pipeline. Returns full incident record + score_breakdown. |
| `POST` | `/ingest/score` | Re-score an existing incident record (no storage). |
| `GET` | `/incidents` | List incidents. Supports `?limit`, `?offset`, `?domain`, `?priority_tier`. |
| `GET` | `/incidents/:id` | Retrieve incident by UUID. |
| `POST` | `/replay/:id` | Re-parse and re-score a stored incident. Returns original vs. replayed + diff. |
| `GET` | `/health` | Service health + incident count. |

---

## Example Incident Record

```json
{
  "incident_id": "a3f1b2c4-...",
  "received_at": "2026-04-11T20:00:00.000Z",
  "source_type": "transcript",
  "raw_input": {
    "text": "My father is not breathing. Cardiac arrest at 123 Oak Street."
  },
  "incident": {
    "domain": "ems",
    "subtype": "cardiac_arrest",
    "summary": "Reported cardiac arrest with not breathing at 123 Oak Street",
    "severity_indicators": ["not_breathing", "cardiac_event", "immediate_medical_emergency"],
    "victim_count_estimate": 1,
    "confidence": 0.87
  },
  "location": {
    "address_text": "123 Oak Street",
    "lat": null,
    "lng": null,
    "location_confidence": 0.50,
    "dispatchable_location_score": 0.48,
    "validation_notes": []
  },
  "triage": {
    "priority_score": 0.9,
    "priority_tier": "P0",
    "reason_codes": [
      "NOT_BREATHING",
      "CARDIAC_EVENT",
      "IMMEDIATE_MEDICAL_EMERGENCY"
    ]
  },
  "audit": {
    "schema_version": "0.1.0",
    "parser_version": "0.1.0",
    "scoring_version": "0.1.0",
    "processed_at": "2026-04-11T20:00:00.000Z"
  }
}
```

---

## Priority Tiers

| Tier | Score Range | Label |
|------|-------------|-------|
| P0 | ≥ 0.85 | IMMEDIATE — Life-threatening |
| P1 | ≥ 0.65 | URGENT — High severity |
| P2 | ≥ 0.40 | ELEVATED — Moderate severity |
| P3 | ≥ 0.20 | STANDARD — Low to moderate severity |
| P4 | < 0.20 | NON-URGENT — Monitor or defer |

---

## Scoring Logic

Scoring is driven by `services/prioritization-engine/config/scoring-rules.json`. The config is versioned independently of the codebase. Every score change is traceable via `audit.scoring_version` on each incident.

Key indicators and their weights:

| Indicator | Weight | Reason Code |
|-----------|--------|-------------|
| Not breathing | +0.32 | `NOT_BREATHING` |
| Cardiac event | +0.30 | `CARDIAC_EVENT` |
| Victim unconscious | +0.28 | `VICTIM_UNCONSCIOUS` |
| Weapon present | +0.25 | `WEAPON_PRESENT` |
| Active bleeding | +0.22 | `ACTIVE_BLEEDING` |
| Active violence | +0.20 | `ACTIVE_VIOLENCE` |
| Multiple victims | +0.14 | `MULTIPLE_VICTIMS` |
| Possible prank | −0.40 | `POSSIBLE_PRANK` |
| Low location confidence | −0.08 | `LOW_LOCATION_CONFIDENCE` |

---

## Design Principles

- **Human-in-the-loop** — supports operators, does not replace them
- **Structured before intelligent** — strong schema before fancy models
- **Deterministic before probabilistic** — rule-based scoring is explainable and auditable
- **Replayability is first-class** — every incident can be reprocessed against any scoring version
- **Location quality matters** — dispatchable location score influences triage priority

See [docs/design-decisions/decision-log.md](docs/design-decisions/decision-log.md) for full rationale behind each decision.

---

## Scope Boundaries

This project does **not** implement or claim:

- Full NG911 compliance or ESInet certification
- Direct SIP/i3 call routing
- Replacement of dispatchers or CAD systems
- Autonomous dispatching decisions
- Production GIS or telephony infrastructure

See [docs/standards-alignment/ng911-alignment.md](docs/standards-alignment/ng911-alignment.md).

---

## Roadmap

- **Phase 1 (current):** Schema, parser, scorer, ingestion API, fixtures, tests
- **Phase 2:** Dashboard (React), PostgreSQL audit store, full replay engine
- **Phase 3:** Evaluation harness, advanced location validation, scenario stress-testing
- **Phase 4:** Public documentation, architecture writeup, demo environment
