# NG911 Triage Intelligence Platform

An NG911-aligned decision-support platform that converts emergency-call inputs into structured, scored, replayable incident records — purpose-built for transparent prioritization and audit accountability.

**Stack:** TypeScript · Node.js · React 18 · Express · PostgreSQL · Zod · Vite

---

## What This Project Demonstrates

This platform addresses three concrete engineering problems in emergency call triage that are not solved by off-the-shelf tools:

- **Multilingual NLP with negation filtering** — a rules-based parser that extracts severity indicators from English and Spanish transcripts, distinguishes "he's not breathing" from "he's breathing on his own again", and measures caller stress from linguistic signals
- **Versioned, explainable scoring** — a weighted rule engine where every priority assignment comes with a machine-readable breakdown of every factor that contributed and by how much; the config is versioned independently so historical scores are always reproducible
- **Replay as an audit mechanism** — every incident stores the exact raw input and version identifiers used to produce it; any incident can be replayed against any scoring version and the system returns a structured diff, enabling retrospective analysis without separate tooling
- **Formal evaluation methodology** — a fixture-based harness that measures domain accuracy, tier accuracy, false-P0 rate, missed-P0 rate, scenario bucket performance, and latency against hand-labeled ground truth

See the [v0.2.0 benchmark report](docs/evaluation/benchmark-report-v0.2.0.md) for the current measured results.

---

## The Problem

When a 911 call comes in, a dispatcher faces an immediate judgment problem: how bad is this, right now, given everything else in the queue? Answers depend on incomplete information — a transcript fragment, a reported address that may be wrong, and the dispatcher's own read of caller stress. Modern CAD systems log the outcome, but rarely the reasoning.

This platform targets three gaps that persist even as 911 infrastructure migrates to IP-based NG911 networks:

1. **Interpretation** — raw text inputs are messy, multilingual, and laced with negation. A caller saying "he's not breathing anymore, he woke up" is very different from "he's not breathing." Getting the domain and indicators right matters before scoring.

2. **Prioritization** — scoring must be explainable to the operator reviewing it. A P0 label with no justification is worse than no label. Every score in this system comes with a full breakdown of what contributed and why.

3. **Accountability** — when a priority assignment is questioned after the fact, operators should be able to replay the incident against any historical scoring version and see exactly how the decision was made.

---

## What This Is / What This Is Not

**This is:**
- A research and decision-support prototype demonstrating explainable, auditable triage logic
- An engineering platform for exploring and measuring prioritization algorithms in the emergency dispatch domain
- A reference implementation of a rules-based NLP pipeline with formal evaluation methodology

**This is not:**
- A production emergency dispatch system or CAD replacement
- Compliant with NENA i3 or the full NG911 protocol stack
- Connected to real telephony infrastructure (SIP/i3 streams, PSAP networks, or ESInet)
- A replacement for trained dispatchers or human judgment

See [docs/standards-alignment/ng911-alignment.md](docs/standards-alignment/ng911-alignment.md) for a full accounting of what "NG911-aligned" means here, and [docs/design-decisions/decision-log.md](docs/design-decisions/decision-log.md) for why these scope limits are intentional.

---

## Measured Results (v0.2.0)

Evaluated against 23 hand-labeled emergency call transcripts covering five domains (EMS, police, fire, hazmat, other), five priority tiers, and eight edge-case categories. Full report: [docs/evaluation/benchmark-report-v0.2.0.md](docs/evaluation/benchmark-report-v0.2.0.md).

| Metric | Result | Target | Status |
|--------|--------|--------|--------|
| Domain accuracy | 91.3% | ≥ 90% | PASS |
| Tier accuracy | 87.0% | ≥ 80% | PASS |
| False-P0 rate | 0.0% | ≤ 5% | PASS |
| Missed-P0 rate | 0.0% | ≤ 10% | PASS |
| Subtype accuracy | 69.6% | ≥ 75% | FAIL |
| Ranking stability | 100% | 100% | PASS |
| Mean latency | 8ms | ≤ 50ms | PASS |
| P95 latency | 14ms | ≤ 150ms | PASS |

P0 (life-threatening) and P1 (urgent) scenario buckets both score 100%. The subtype failure is a vocabulary coverage gap, not an architectural issue — detailed in the report.

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

Full data flow with module-level detail: [docs/architecture/system-overview.md](docs/architecture/system-overview.md)

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
    { "rule": "DOMAIN_BASE",   "contribution": 0.22, "description": "Base score for ems domain" },
    { "rule": "NOT_BREATHING", "contribution": 0.32, "description": "Not breathing indicator present" },
    { "rule": "CARDIAC_EVENT", "contribution": 0.30, "description": "Cardiac event indicator present" }
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

**See the ranked incident queue:**

```bash
curl -s "http://localhost:3001/incidents?limit=5" \
  | jq '.incidents[] | {id: .incident_id, tier: .triage.priority_tier, domain: .incident.domain}'
```

**Replay an incident to inspect the scoring decision:**

```bash
INCIDENT_ID="<uuid-from-ingest-response>"

curl -s -X POST "http://localhost:3001/replay/${INCIDENT_ID}" | jq '{
  original_tier: .original.triage.priority_tier,
  replayed_tier: .replayed.triage.priority_tier,
  score_delta:   .diff.score_delta,
  tier_changed:  .diff.tier_changed
}'
```

**Batch replay all stored incidents:**

```bash
curl -s -X POST http://localhost:3001/replay/stream | jq '{
  total: .total_replayed,
  tier_changed: .summary.tier_changed,
  improved: .summary.score_improved,
  degraded: .summary.score_degraded
}'
```

### Dashboard

The operator dashboard runs at `http://localhost:5173` after `cd apps/dashboard && npm run dev`.

It displays the live incident queue ranked by priority tier, with a detail panel showing:
- "Why this priority?" — plain-English prose generated from the score breakdown
- Per-factor contribution bars (domain base / severity indicators / penalties)
- Three confidence meters: parse quality, location semantic, location dispatchable
- Reason code chips linking to [docs/scoring/reason-code-taxonomy.md](docs/scoring/reason-code-taxonomy.md)
- Full audit block (parser version, scoring version, schema version)

---

## Replay as a First-Class Feature

Replay is not a debugging convenience — it is the audit mechanism.

Every incident record stores the exact `parser_version`, `scoring_version`, and `schema_version` that produced its triage result. When scoring rules change (e.g., adjusting indicator weights or adding a new penalty), `POST /replay/:id` re-runs the full parse-and-score pipeline against the stored raw input and returns a structured diff:

```json
{
  "original": { "priority_score": 0.80, "priority_tier": "P1" },
  "replayed": { "priority_score": 0.92, "priority_tier": "P0" },
  "diff": {
    "score_delta": 0.12,
    "priority_tier_changed": true,
    "reason_codes_added": [],
    "reason_codes_removed": []
  }
}
```

This answers the question: *"If we had used today's scoring rules when this call came in, would the tier have been different?"* — without separate tooling or manual re-analysis.

The v0.1.0 → v0.2.0 upgrade is a concrete example of why this matters: the shift from a flat domain base score (0.10 for all domains) to domain-specific base scores (EMS: 0.22) caused two critical EMS incidents to correctly move from P1 to P0 in evaluation — incidents that were being under-triaged under the original config. The replay system surfaced these regressions-in-reverse before deployment.

**Scoring version comparison** across the labeled fixture set:

```bash
cd packages/evaluation-harness
npx ts-node src/compare-versions.ts \
  --baseline ../../services/prioritization-engine/config/scoring-rules-v0.1.0.json \
  --revised  ../../services/prioritization-engine/config/scoring-rules.json \
  --fixtures ../../data/fixtures/sample-incidents.json
```

Output includes a tier transition matrix showing exactly which fixtures changed and in which direction:

```
Tier Transition Matrix  (row = baseline tier, col = revised tier)

                P0      P1      P2      P3      P4
  ──────────────────────────────────────────────────
  P0            10       ·       ·       ·       ·
  P1             2       2       ·       ·       ·
  P2             ·       ·       2       ·       ·
  P3             ·       ·       ·       3       ·
  P4             ·       ·       ·       ·       2

Summary
  Improved : 2   (baseline wrong → revised correct)
  Degraded : 0   (baseline correct → revised wrong)
  Net change: +2

  No regressions. Safe to bump scoring_version if manual review passes.
```

The two P1 → P0 entries are the under-triaged critical EMS incidents. Zero entries on the P0 row confirm no missed-P0 regressions were introduced.

Full replay and version comparison workflow: [docs/evaluation/replay-workflow.md](docs/evaluation/replay-workflow.md)

---

## Explainability

Every incident record carries a `score_breakdown` array that lists each rule that fired, its numeric contribution, and a human-readable description. This is the data source for the "Why this score?" panel in the dashboard.

The breakdown is stored alongside the incident record — not recomputed on read — so the explanation is always tied to the exact scoring version that produced it.

Operators can inspect, replay, and compare without ML introspection tooling, model weights, or black-box reasoning.

Full reason code reference: [docs/scoring/reason-code-taxonomy.md](docs/scoring/reason-code-taxonomy.md)

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
    fixtures/                 23 hand-labeled incident fixtures for evaluation
  docs/
    architecture/             System overview and data flow
    design-decisions/         Decision log (DDL-001 through DDL-010)
    evaluation/               Evaluation plan, benchmark reports, replay workflow
    scoring/                  Reason code taxonomy
    standards-alignment/      NG911 alignment narrative
  infra/
    docker/                   docker-compose (postgres:16 + ingestion-api)
```

Detailed data flow with per-module responsibilities: [docs/architecture/system-overview.md](docs/architecture/system-overview.md)

Key design decisions with rationale: [docs/design-decisions/decision-log.md](docs/design-decisions/decision-log.md)

Replay and version comparison workflow with worked example: [docs/evaluation/replay-workflow.md](docs/evaluation/replay-workflow.md)

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

Save a JSON report:

```bash
npx ts-node src/cli.ts \
  --fixtures ../../data/fixtures/sample-incidents.json \
  --output   ./results/eval-$(date +%Y-%m-%d).json
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

Full reason code taxonomy with negation behavior and stability contract: [docs/scoring/reason-code-taxonomy.md](docs/scoring/reason-code-taxonomy.md)

---

## Design Principles

- **Human-in-the-loop** — supports operators, does not replace them
- **Explainability before accuracy** — every score has a breakdown; a wrong but explainable score is more useful than a right but opaque one
- **Deterministic before probabilistic** — rule-based scoring is fully testable and auditable without model introspection
- **Replayability is first-class** — every incident can be re-processed against any scoring version; the audit trail is the feature
- **Location quality as a priority signal** — low dispatchability is a penalty, not a footnote

Full rationale for each decision: [docs/design-decisions/decision-log.md](docs/design-decisions/decision-log.md)

---

## Operational Limitations

This platform is a research and decision-support prototype. It is **not** suitable for production emergency dispatch:

- **No real telephony** — inputs are text strings, not SIP/i3 call streams
- **No GIS integration** — location scoring is heuristic; there is no geocoding or ESInet routing
- **No NG911 compliance** — the platform is informed by NENA i3 concepts but does not implement the protocol stack
- **Rules-based NLP only** — parsing relies on keyword matching with negation filtering, not a trained NLP model
- **English and Spanish only** — language detection supports two languages; all others fall back to `unknown`
- **No CAD integration** — incidents are not dispatched; the platform supports operator review, not autonomous action
- **In-memory store resets on restart** — persistent storage requires Docker + PostgreSQL

---

## Roadmap

- **Phase 1** (complete): Schema, parser, scorer, ingestion API, fixtures, tests
- **Phase 2** (complete): React dashboard, PostgreSQL store, replay engine, test data generator, location validator
- **Phase 3** (complete): Evaluation harness, benchmark reporting, reason code taxonomy, fixture expansion to 23 labeled scenarios
- **Phase 4** (next): Public demo environment, expanded fixture set with real linguistic variation, architecture writeup for external audiences
