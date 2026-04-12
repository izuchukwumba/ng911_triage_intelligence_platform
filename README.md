# NG911 Triage Intelligence Platform

An NG911-aligned decision-support platform that converts emergency-call inputs into structured, scored, replayable incident records — purpose-built for transparent prioritization and audit accountability.

---

## The Problem

When a 911 call comes in, a dispatcher faces an immediate judgment problem: how bad is this, right now, given everything else in the queue? Answers depend on incomplete information — a transcript fragment, a reported address that may be wrong, and the dispatcher's own read of caller stress. Modern CAD systems log the outcome, but rarely the reasoning.

This platform targets three gaps that persist even as 911 infrastructure migrates to IP-based NG911 networks:

1. **Interpretation** — raw text inputs are messy, multilingual, and laced with negation. A caller saying "he's not breathing anymore, he woke up" is very different from "he's not breathing." Getting the domain and indicators right matters before scoring.

2. **Prioritization** — scoring must be explainable to the operator reviewing it. A P0 label with no justification is worse than no label. Every score in this system comes with a full breakdown of what contributed and why.

3. **Accountability** — when a priority assignment is questioned after the fact, operators should be able to replay the incident against any historical scoring version and see exactly how the decision was made.

---

## End-to-End Pipeline

```
Caller transcript (raw text)
         │
         ▼
┌─────────────────────────┐
│   Language Detection    │  → en / es / unknown
│   Stress Detection      │  → low / moderate / high
└────────────┬────────────┘
             │
             ▼
┌─────────────────────────┐
│   Transcript Parser     │  Domain classification (EMS, fire, police, hazmat, other)
│   (rules-based NLP)     │  Subtype classification (cardiac_arrest, shooting, etc.)
│                         │  Severity indicator extraction with negation filtering
│                         │  Address extraction
└────────────┬────────────┘
             │
             ▼
┌─────────────────────────┐
│   Location Validator    │  location_confidence  (semantic: do we understand it?)
│                         │  dispatchable_location_score  (operational: can we route?)
└────────────┬────────────┘
             │
             ▼
┌─────────────────────────┐
│   Incident Record       │  UUID-keyed, Zod-validated, versioned schema
│   (incident-schema)     │  Captures: domain, indicators, victim count, confidence,
│                         │  caller context, location scores, raw input
└────────────┬────────────┘
             │
             ▼
┌─────────────────────────┐
│  Prioritization Engine  │  Domain base score  (EMS: 0.22, fire: 0.20, police: 0.15)
│  (rules engine)         │  + Indicator weights  (NOT_BREATHING: +0.32, etc.)
│                         │  + Victim count multiplier  (each additional × 0.04, cap 0.20)
│                         │  − Penalties  (low location confidence, low parse confidence)
│                         │  = final score → P0/P1/P2/P3/P4 tier
│                         │  + score_breakdown[]  (per-factor contribution)
└────────────┬────────────┘
             │
             ▼
┌─────────────────────────┐
│   Incident Store        │  In-memory (dev) or PostgreSQL (prod, via DATABASE_URL)
│                         │  Full record + audit trail persisted
└────────────┬────────────┘
             │
         ┌───┴───────────────────┐
         ▼                       ▼
  GET /incidents           POST /replay/:id
  Ranked queue for         Re-parse + re-score any
  operator review          stored incident; returns
                           original vs. replayed diff
                           + score delta
```

---

## Demo Walkthrough

Start the API:

```bash
npm install
cd services/ingestion-api && npm run dev
# API listening on http://localhost:3001
```

**Ingest a transcript:**

```bash
curl -s -X POST http://localhost:3001/ingest \
  -H "Content-Type: application/json" \
  -d '{"text": "My father just collapsed at 456 Elm Road. He is not breathing and I cannot find a pulse."}' \
  | jq '{tier: .triage.priority_tier, score: .triage.priority_score, breakdown: .triage.score_breakdown}'
```

Output:
```json
{
  "tier": "P0",
  "score": 0.84,
  "breakdown": [
    { "rule": "DOMAIN_BASE",             "contribution": 0.22, "description": "Base score for ems domain" },
    { "rule": "NOT_BREATHING",           "contribution": 0.32, "description": "Not breathing indicator present" },
    { "rule": "CARDIAC_EVENT",           "contribution": 0.30, "description": "Cardiac event indicator present" }
  ]
}
```

**Ingest a Spanish-language call:**

```bash
curl -s -X POST http://localhost:3001/ingest \
  -H "Content-Type: application/json" \
  -d '{"text": "Mi padre no respira en 456 Calle Elm. No puedo encontrar el pulso."}' \
  | jq '{domain: .incident.domain, lang: .caller_context.language_hint, tier: .triage.priority_tier}'
```

Output:
```json
{
  "domain": "ems",
  "lang": "es",
  "tier": "P0"
}
```

**See the ranked queue:**

```bash
curl -s "http://localhost:3001/incidents?limit=5" | jq '.incidents[] | {id: .incident_id, tier: .triage.priority_tier, domain: .incident.domain}'
```

**Replay an incident to inspect the original scoring decision:**

```bash
INCIDENT_ID="<uuid-from-ingest-response>"

curl -s -X POST "http://localhost:3001/replay/${INCIDENT_ID}" | jq '{
  original_tier: .original.triage.priority_tier,
  replayed_tier: .replayed.triage.priority_tier,
  score_delta:   .diff.score_delta,
  tier_changed:  .diff.tier_changed
}'
```

**Batch replay all stored incidents** (returns aggregate diff stats):

```bash
curl -s -X POST http://localhost:3001/replay/stream | jq '{
  total: .total_replayed,
  tier_changed: .summary.tier_changed,
  improved: .summary.score_improved,
  degraded: .summary.score_degraded
}'
```

---

## Replay as a First-Class Feature

Replay is not a debugging convenience — it is the audit mechanism.

Every incident record stores the exact `parser_version`, `scoring_version`, and `schema_version` that produced its triage result. When scoring rules change (e.g., adjusting indicator weights or adding a new penalty), `POST /replay/:id` re-runs the full parse-and-score pipeline against the stored raw input and returns a structured diff:

```json
{
  "original": { "priority_score": 0.62, "priority_tier": "P1" },
  "replayed": { "priority_score": 0.71, "priority_tier": "P1" },
  "diff": {
    "score_delta": 0.09,
    "tier_changed": false,
    "indicator_changes": []
  }
}
```

This makes it possible to answer the question: *"If we had used the current scoring rules when this call came in, would the tier have been different?"* — without requiring separate tooling or manual re-analysis.

The `POST /replay/stream` endpoint replays all stored incidents at once and returns aggregate change stats, which feeds directly into the scoring comparison workflow:

```bash
cd packages/evaluation-harness
npx ts-node src/compare-versions.ts \
  --baseline ../../services/prioritization-engine/config/scoring-rules.json \
  --revised  ./config/scoring-rules-candidate.json \
  --fixtures ../../data/fixtures/sample-incidents.json
```

---

## Explainability

Every incident record carries a `score_breakdown` array that lists each rule that fired, its numeric contribution, and a human-readable description. This is the data source for the "Why this score?" panel in the dashboard.

The breakdown is stored alongside the incident record — not recomputed on read — so the explanation is always tied to the exact scoring version that produced it.

Operators can inspect, replay, and compare without any ML introspection tooling, model weights, or black-box reasoning.

---

## Architecture

```
ng911-triage-intelligence/
  packages/
    incident-schema/          Zod-validated TypeScript types — canonical schema, shared everywhere
    location-validator/       Dispatchable location quality scoring
    evaluation-harness/       Fixture-based evaluation: domain/tier accuracy, false-P0/missed-P0 rates
    test-data-generator/      Synthetic scenario generation + CLI
  services/
    transcript-parser/        Rules-based NLP: domain, subtype, indicators, negation, language, stress
    prioritization-engine/    Weighted rule scoring with reason codes + versioned JSON config
    ingestion-api/            Express REST API, store abstraction (in-memory ↔ PostgreSQL)
  apps/
    dashboard/                React 18 + Vite — operator queue, tabbed detail, score breakdown panel
  data/
    fixtures/                 Labeled incident fixtures for evaluation
  docs/
    architecture/
    design-decisions/
    evaluation/
    standards-alignment/
  infra/
    docker/                   docker-compose (postgres:16 + ingestion-api)
```

---

## Getting Started

### Prerequisites

- Node.js >= 18
- npm >= 8

### Install

```bash
npm install
```

### Run the API (in-memory store)

```bash
cd services/ingestion-api
npm run dev
# → http://localhost:3001
```

### Run with PostgreSQL

```bash
cd infra/docker
docker-compose up -d
# Sets DATABASE_URL; ingestion-api auto-creates the incidents table
```

### Run the dashboard

```bash
cd apps/dashboard
npm run dev
# → http://localhost:5173
```

### Run the evaluation harness

```bash
cd packages/evaluation-harness
npx ts-node src/cli.ts --fixtures ../../data/fixtures/sample-incidents.json
```

### Run tests

```bash
npm test
```

---

## API Reference

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/ingest` | Submit transcript. Runs full parse → score pipeline. Returns incident record + score_breakdown. |
| `POST` | `/ingest/score` | Re-score an existing incident record (no storage). |
| `GET` | `/incidents` | List incidents. Supports `?limit`, `?offset`, `?domain`, `?priority_tier`. |
| `GET` | `/incidents/:id` | Retrieve incident by UUID. |
| `POST` | `/replay/:id` | Re-parse and re-score a stored incident. Returns original vs. replayed + diff. |
| `POST` | `/replay/stream` | Batch replay all incidents. Returns per-incident diffs + aggregate stats. |
| `GET` | `/health` | Service health + incident count. |

---

## Priority Tiers

| Tier | Score | Label |
|------|-------|-------|
| P0 | ≥ 0.85 | IMMEDIATE — Life-threatening |
| P1 | ≥ 0.65 | URGENT — High severity |
| P2 | ≥ 0.40 | ELEVATED — Moderate severity |
| P3 | ≥ 0.20 | STANDARD — Low to moderate |
| P4 | < 0.20 | NON-URGENT — Monitor or defer |

---

## Scoring Logic

Driven by `services/prioritization-engine/config/scoring-rules.json`. The config is versioned independently of the codebase; every incident record stores `audit.scoring_version`.

**Domain base scores** (applied before any indicators):

| Domain | Base Score |
|--------|-----------|
| EMS | 0.22 |
| Fire / Hazmat | 0.20 |
| Police | 0.15 |
| Other | 0.10 |
| Unknown | 0.08 |

**Key indicator weights:**

| Indicator | Weight | Reason Code |
|-----------|--------|-------------|
| Not breathing | +0.32 | `NOT_BREATHING` |
| Cardiac event | +0.30 | `CARDIAC_EVENT` |
| Victim unconscious | +0.28 | `VICTIM_UNCONSCIOUS` |
| Weapon present | +0.25 | `WEAPON_PRESENT` |
| Active bleeding | +0.22 | `ACTIVE_BLEEDING` |
| Active violence | +0.20 | `ACTIVE_VIOLENCE` |
| Respiratory distress | +0.18 | `RESPIRATORY_DISTRESS` |
| Multiple victims | +0.14 | `MULTIPLE_VICTIMS` |
| Child involved | +0.12 | `CHILD_INVOLVED` |
| Caller high distress | +0.08 | `CALLER_HIGH_DISTRESS` |
| Possible prank | −0.40 | `POSSIBLE_PRANK` |
| Low location confidence | −0.08 | `LOW_LOCATION_CONFIDENCE` |

**Victim count multiplier:** each additional victim beyond one adds 0.04, capped at 0.20.

Full taxonomy: [docs/scoring/reason-code-taxonomy.md](docs/scoring/reason-code-taxonomy.md)

---

## Operational Limitations

This platform is a research and decision-support prototype. It is **not** suitable for production emergency dispatch without significant additional work:

- **No real telephony** — inputs are text strings, not SIP/i3 call streams
- **No GIS integration** — location scoring is heuristic; there is no geocoding or ESInet routing
- **No NG911 compliance** — the platform is informed by NENA i3 concepts but does not implement the protocol stack
- **Rules-based NLP only** — parsing relies on keyword matching with negation filtering, not a trained NLP model
- **English and Spanish only** — language detection supports two languages; all others fall back to `unknown`
- **No CAD integration** — incidents are not dispatched; the platform supports operator review, not autonomous action
- **In-memory store resets on restart** — persistent storage requires Docker + PostgreSQL

See [docs/standards-alignment/ng911-alignment.md](docs/standards-alignment/ng911-alignment.md) for a full honest accounting of what "NG911-aligned" means here.

---

## Design Principles

- **Human-in-the-loop** — supports operators, does not replace them
- **Explainability before accuracy** — every score has a breakdown; a wrong but explainable score is more useful than a right but opaque one
- **Deterministic before probabilistic** — rule-based scoring is fully testable and auditable without model introspection
- **Replayability is first-class** — every incident can be re-processed against any scoring version; the audit trail is the feature
- **Location quality as a priority signal** — low dispatchability is a penalty, not a footnote

See [docs/design-decisions/decision-log.md](docs/design-decisions/decision-log.md) for full rationale on each decision.

---

## Scope Boundaries

This project does **not** implement or claim:

- Full NG911 / ESInet compliance or certification
- Direct SIP/i3 call routing or PSAP integration
- Replacement of dispatchers or CAD systems
- Autonomous dispatching decisions
- Production GIS, telephony, or network infrastructure

---

## Roadmap

- **Phase 1** (complete): Schema, parser, scorer, ingestion API, fixtures, tests
- **Phase 2** (complete): React dashboard, PostgreSQL store, replay engine, evaluation harness
- **Phase 3** (next): Advanced location validation, scenario stress-testing, operator simulation mode
- **Phase 4**: Public demo environment, architecture writeup, external evaluation
