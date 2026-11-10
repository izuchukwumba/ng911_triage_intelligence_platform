# NG911 Triage Intelligence Platform

**Stack:** TypeScript · Node.js · React 18 · Express · PostgreSQL · Zod · Vite

---

## What this is

This project is an NG911-aligned decision-support platform that:

1. Converts emergency-call-like inputs into structured incident data
2. Prioritizes incidents using explainable scoring logic
3. Enables replay, audit, and evaluation of triage decisions

---

## What this is NOT

- Not a replacement for 911 dispatch systems
- Not NG911 core infrastructure
- Not an autonomous dispatch system

See [docs/standards-alignment/ng911-alignment.md](docs/standards-alignment/ng911-alignment.md) for a full accounting of what "NG911-aligned" means here.

---

## Pipeline

```
Transcript / Input
        ↓
    Parser
    (language detection, domain classification,
     severity indicators, negation filtering,
     caller stress, address extraction)
        ↓
Structured Incident
    (UUID-keyed, Zod-validated, versioned schema —
     domain, indicators, location scores, raw input preserved)
        ↓
Prioritization Engine
    (domain base score + indicator weights + penalties
     = priority score → P0/P1/P2/P3/P4 tier
     + score_breakdown[] per-factor contribution)
        ↓
Dashboard (Human Review)
    (ranked queue, "Why this priority?" panel,
     confidence meters, reason code chips)
        ↓
Audit + Replay
    (every incident replayable against any scoring version;
     structured diff: original vs. replayed tier + score delta)
        ↓
Evaluation
    (fixture-based harness: domain/tier accuracy,
     false-P0 rate, missed-P0 rate, latency)
```

Full module-level detail: [docs/architecture/system-overview.md](docs/architecture/system-overview.md)

Target design (v1.2, proposed — not yet implemented in full): [docs/design/technical-design-v1.2.md](docs/design/technical-design-v1.2.md)

---

## Demo Walkthrough

### 1. Start the API

```bash
npm install
cd services/ingestion-api && npm run dev
# → http://localhost:3001
```

### 2. Submit a transcript — see priority + score breakdown

```bash
curl -s -X POST http://localhost:3001/ingest \
  -H "Content-Type: application/json" \
  -d '{"text": "My father just collapsed. He is not breathing and I cannot find a pulse. We are at 456 Elm Road."}' \
  | jq '{
      tier:      .triage.priority_tier,
      score:     .triage.priority_score,
      breakdown: .triage.score_breakdown
    }'
```

```json
{
  "tier": "P0",
  "score": 0.84,
  "breakdown": [
    { "reason_code": "DOMAIN_BASE",   "weight": 0.22, "description": "EMS domain base score" },
    { "reason_code": "NOT_BREATHING", "weight": 0.32, "description": "Caller reports victim is not breathing" },
    { "reason_code": "CARDIAC_EVENT", "weight": 0.30, "description": "Cardiac arrest or heart attack reported" }
  ]
}
```

The tier is **P0 — IMMEDIATE**. The `score_breakdown` shows exactly which factors drove the score and by how much. This is what powers the "Why this priority?" panel in the dashboard.

### 3. Submit a Spanish-language call — same result

```bash
curl -s -X POST http://localhost:3001/ingest \
  -H "Content-Type: application/json" \
  -d '{"text": "Mi padre no respira en 456 Calle Elm. No puedo encontrar el pulso."}' \
  | jq '{domain: .incident.domain, lang: .caller_context.language_hint, tier: .triage.priority_tier}'
```

```json
{ "domain": "ems", "lang": "es", "tier": "P0" }
```

The parser detects Spanish, applies the Spanish keyword set, and produces the same P0 assignment as the English call. Language is tracked in `caller_context.language_hint`.

### 4. See the ranked queue

```bash
curl -s "http://localhost:3001/incidents?limit=5" \
  | jq '.incidents[] | {id: .incident_id, tier: .triage.priority_tier, domain: .incident.domain, summary: .incident.summary}'
```

Incidents are returned sorted by priority score descending — P0 incidents always surface first.

### 5. Replay an incident — audit the scoring decision

```bash
INCIDENT_ID="<uuid-from-step-2-response>"

curl -s -X POST "http://localhost:3001/replay/${INCIDENT_ID}" \
  | jq '{
      original_tier:  .original.triage.priority_tier,
      original_score: .original.triage.priority_score,
      replayed_tier:  .replayed.triage.priority_tier,
      replayed_score: .replayed.triage.priority_score,
      score_delta:    .diff.score_delta,
      tier_changed:   .diff.priority_tier_changed
    }'
```

```json
{
  "original_tier":  "P0",
  "original_score": 0.84,
  "replayed_tier":  "P0",
  "replayed_score": 0.84,
  "score_delta":    0.00,
  "tier_changed":   false
}
```

When scoring rules haven't changed since ingestion, the replay is identical — confirming deterministic, reproducible scoring. When rules *have* changed, the diff surfaces exactly what moved and why.

### 6. Compare two scoring versions across all fixtures

```bash
cd packages/evaluation-harness
npx ts-node src/compare-versions.ts \
  --baseline ../../services/prioritization-engine/config/scoring-rules-v0.1.0.json \
  --revised  ../../services/prioritization-engine/config/scoring-rules.json \
  --fixtures ../../data/fixtures/sample-incidents.json
```

```
Scoring Version Comparison
Baseline : v0.1.0    Revised : v0.2.0    Fixtures: 23
────────────────────────────────────────────────────────────────────────────────

fixture-011  Expected: P0   ↑ improved
  Caller reports man collapsed, vague location near the park...
  Tier: P1 → P0   Score: 0.800 → 0.920  Δ +0.120

fixture-023  Expected: P0   ↑ improved
  Bad crash on Route 9. One driver not breathing. Multiple injured...
  Tier: P1 → P0   Score: 0.800 → 0.920  Δ +0.120

Tier Transition Matrix  (row = baseline tier, col = revised tier)

                P0      P1      P2      P3      P4
  ──────────────────────────────────────────────────
  P0            10       ·       ·       ·       ·
  P1             2       2       ·       ·       ·
  P2             ·       ·       2       ·       ·
  P3             ·       ·       ·       3       ·
  P4             ·       ·       ·       ·       2

Summary
  Improved: 2   Degraded: 0   Net: +2

  No regressions. Safe to bump scoring_version.
```

The two P1→P0 entries are critical EMS incidents that were under-triaged under the flat base score (v0.1.0) and correctly identified as P0 after the domain-specific base was introduced (v0.2.0). Zero P0 row off-diagonal entries confirm no missed-P0 regressions.

### 7. Run the full evaluation harness

```bash
cd packages/evaluation-harness
npx ts-node src/cli.ts --fixtures ../../data/fixtures/sample-incidents.json
```

```
NG911 Triage Intelligence Platform — Evaluation Report
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Parser: 0.2.0   Scoring: 0.2.0   Fixtures: 23

§1  Accuracy Metrics
────────────────────────────────────────────────────────────────────────
  ✓ Domain accuracy    ████████████████████  91.3%  target ≥ 90%
  ✗ Subtype accuracy   █████████████░░░░░░░  69.6%  target ≥ 75%
  ✓ Tier accuracy      ████████████████████  87.0%  target ≥ 80%

§2  P0 Safety Metrics  (most operationally significant)
────────────────────────────────────────────────────────────────────────
  ✓ False-P0 rate    0.0%   target ≤ 5%
  ✓ Missed-P0 rate   0.0%   target ≤ 10%

§3  Scenario Buckets
────────────────────────────────────────────────────────────────────────
  P0  ████████████  100.0%  12/12  IMMEDIATE (life-threatening)
  P1  ████████████  100.0%   4/4   URGENT (high severity)
  P2  ██████░░░░░░   50.0%   1/2   ELEVATED (moderate severity)
  P3  ████████████  100.0%   3/3   STANDARD (low-moderate)
  P4  ██████░░░░░░   50.0%   1/2   NON-URGENT / edge-case
```

Full benchmark report: [docs/evaluation/benchmark-report-v0.2.0.md](docs/evaluation/benchmark-report-v0.2.0.md)

### 8. Open the dashboard

```bash
cd apps/dashboard && npm run dev
# → http://localhost:5173
```

The dashboard shows the live incident queue ranked by priority tier. Selecting any incident opens:
- **"Why this priority?"** — plain-English explanation from the score breakdown
- Per-factor contribution bars (domain base / indicators / penalties)
- Three confidence meters: parse quality, location semantic, dispatchable
- Reason code chips (green = contributing indicators, red = penalties)
- Audit block: parser version, scoring version, schema version
- **Replay tab** — re-run the full pipeline and see the diff in the UI

---

## Measured Results (v0.2.0)

Evaluated against 23 hand-labeled emergency call transcripts. Full report: [docs/evaluation/benchmark-report-v0.2.0.md](docs/evaluation/benchmark-report-v0.2.0.md).

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

P0 and P1 scenario buckets both score 100%. Subtype failure is a vocabulary coverage gap, not an architectural issue — detailed in the report.

---

## The Problem

When a 911 call comes in, a dispatcher faces an immediate judgment problem: how bad is this, right now, given everything else in the queue? Answers depend on incomplete information — a transcript fragment, a reported address that may be wrong, and the dispatcher's own read of caller stress. Modern CAD systems log the outcome, but rarely the reasoning.

This platform targets three gaps:

1. **Interpretation** — raw text inputs are messy, multilingual, and laced with negation. "He's not breathing anymore, he woke up" is very different from "he's not breathing." Getting the domain and indicators right matters before scoring.

2. **Prioritization** — scoring must be explainable to the operator reviewing it. A P0 label with no justification is worse than no label. Every score comes with a full breakdown of what contributed and why.

3. **Accountability** — when a priority assignment is questioned after the fact, operators should be able to replay the incident against any historical scoring version and see exactly how the decision was made.

---

## Replay and Evaluation

Replay is not a debugging convenience — it is the audit mechanism.

Every incident record stores the raw input, parser version, scoring version, and full `score_breakdown[]`. Any incident can be replayed against any scoring version and the system returns a structured diff. This makes the question *"would we have decided differently under today's rules?"* answerable without manual re-analysis.

The v0.1.0 → v0.2.0 scoring upgrade is the concrete demonstration: switching from a flat domain base (0.10 for all domains) to domain-specific bases (EMS: 0.22) caused two critical EMS incidents to correctly move from P1 to P0. The replay and comparison tools surfaced this improvement — and confirmed zero regressions — before the new config was deployed.

Full workflow with worked examples: [docs/evaluation/replay-workflow.md](docs/evaluation/replay-workflow.md)

---

## Explainability

Every incident carries a `score_breakdown` array — each rule that fired, its numeric contribution, and a human-readable description. Stored with the incident at write time, so the explanation is always tied to the exact scoring version that produced it.

```json
[
  { "reason_code": "DOMAIN_BASE",            "weight":  0.22, "description": "EMS domain base score" },
  { "reason_code": "NOT_BREATHING",          "weight":  0.32, "description": "Caller reports victim is not breathing" },
  { "reason_code": "CARDIAC_EVENT",          "weight":  0.30, "description": "Cardiac arrest or heart attack reported" },
  { "reason_code": "LOW_LOCATION_CONFIDENCE","weight":  0.00, "description": "Dispatchable location score is low — verify location with caller (does not lower priority)" }
]
```

Full reason code reference: [docs/scoring/reason-code-taxonomy.md](docs/scoring/reason-code-taxonomy.md)

---

## Architecture

```
ng911-triage-intelligence/
  packages/
    incident-schema/          Zod-validated TypeScript types — canonical schema
    location-validator/       Dispatchable location quality scoring
    evaluation-harness/       Fixture-based evaluation + compare-versions CLI
    test-data-generator/      Synthetic scenario generation
  services/
    transcript-parser/        Rules-based NLP: domain, subtype, indicators, negation, stress
    prioritization-engine/    Weighted rule scoring + versioned JSON config
    ingestion-api/            Express REST API, store abstraction (in-memory ↔ PostgreSQL)
  apps/
    dashboard/                React 18 + Vite — queue, detail panel, replay tab
  data/
    fixtures/                 23 hand-labeled incident fixtures
  docs/
    architecture/             System overview and data flow
    design/                   Technical design specification (target architecture)
    design-decisions/         Decision log (DDL-001 through DDL-011)
    evaluation/               Evaluation plan, benchmark reports, replay workflow
    scoring/                  Reason code taxonomy
    standards-alignment/      NG911 alignment narrative
  infra/
    docker/                   docker-compose (postgres:16 + ingestion-api)
```

Key design decisions: [docs/design-decisions/decision-log.md](docs/design-decisions/decision-log.md)

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

Driven by `services/prioritization-engine/config/scoring-rules.json`. Config is versioned independently of the codebase; every incident record stores `audit.scoring_version`.

**Domain base scores:**

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
| Low location confidence | 0 (verification flag) | `LOW_LOCATION_CONFIDENCE` |
| Low parse confidence | 0 (verification flag) | `LOW_PARSE_CONFIDENCE` |

**Victim count multiplier:** each additional victim beyond one adds 0.04, capped at 0.20.

Full taxonomy: [docs/scoring/reason-code-taxonomy.md](docs/scoring/reason-code-taxonomy.md)

---

## Design Principles

- **Human-in-the-loop** — supports operators, does not replace them
- **Explainability before accuracy** — every score has a breakdown; a wrong but explainable score is more useful than a right but opaque one
- **Deterministic before probabilistic** — rule-based scoring is fully testable and auditable without model introspection
- **Replayability is first-class** — every incident can be re-processed against any scoring version; the audit trail is the feature
- **Location quality as a verification signal** — low dispatchability is flagged for the operator, but never lowers the priority of an urgent call

Full rationale: [docs/design-decisions/decision-log.md](docs/design-decisions/decision-log.md)

---

## Operational Limitations

This is a research and decision-support prototype. It is **not** suitable for production emergency dispatch:

- **No real telephony** — inputs are text strings, not SIP/i3 call streams
- **No GIS integration** — location scoring is heuristic; no geocoding or ESInet routing
- **No NG911 compliance** — informed by NENA i3 concepts but does not implement the protocol stack
- **Rules-based NLP only** — keyword matching with negation filtering, not a trained NLP model
- **English and Spanish only** — all other languages fall back to `unknown`
- **No CAD integration** — the platform supports operator review, not autonomous dispatch

---

## Roadmap

- **Phase 1** (complete): Schema, parser, scorer, ingestion API, fixtures, tests
- **Phase 2** (complete): React dashboard, PostgreSQL store, replay engine, test data generator, location validator
- **Phase 3** (complete): Evaluation harness, benchmark reporting, reason code taxonomy, fixture expansion to 23 labeled scenarios
- **Phase 4** (next): Public demo environment, expanded fixture set with real linguistic variation, architecture writeup for external audiences
