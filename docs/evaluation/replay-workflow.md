# Replay-Based Evaluation and Scoring Version Control

## Why Replay Matters in Emergency Triage

Emergency dispatch is one of the few domains where the cost of a wrong decision is measured in minutes and lives. A triage system that assigns the wrong priority tier isn't just inaccurate — it delays the right response. But the harder problem isn't making the initial decision; it's being able to *revisit* it.

When a scoring rule changes — because a new indicator type was added, a weight was recalibrated, or domain base scores were restructured — you cannot simply re-run the original calls through the new system. The original inputs are gone. The original reasoning is gone. All you have is the outcome.

The NG911 Triage Intelligence Platform is built around the premise that the original reasoning should *never* be gone. Every ingested incident stores:

- The raw transcript exactly as received
- The parser version that interpreted it
- The scoring version and config that assigned the tier
- The full `score_breakdown[]` showing each factor's contribution

This means any incident can be replayed against any scoring version at any time. The result is not just a new tier — it is a structured diff that answers the operational question directly:

> *"If we had used today's scoring rules when this call came in two weeks ago, would the tier have been different — and if so, by how much?"*

This document shows how to use the replay system to make that question answerable in practice.

---

## A Worked Example: v0.1.0 → v0.2.0

The most significant change between scoring versions 0.1.0 and 0.2.0 was the introduction of domain-specific base scores. In v0.1.0, all domains started with a flat base of `0.10`. In v0.2.0, EMS incidents start at `0.22`, fire/hazmat at `0.20`, and police at `0.15`.

The rationale: even an unconfirmed EMS call (a caller saying "my neighbor hasn't answered the door") warrants faster response than a vague police call. The base score encodes that domain-level prior before any indicators fire.

The following examples show the same incident scored under both configs.

---

### Example 1 — Multi-vehicle crash: under-triage corrected

**Transcript:**
> "There's been a bad crash on Route 9 near the old overpass. Multiple cars. One of the drivers is not moving, not breathing. There are at least two other people who look hurt."

#### Scoring under v0.1.0 (flat 0.10 base)

```
Score breakdown:
+0.10  DOMAIN_BASE             Flat base (all domains, v0.1.0)
+0.32  NOT_BREATHING           Victim not breathing — immediate life threat
+0.28  VICTIM_UNCONSCIOUS      Driver unresponsive
+0.10  MULTIPLE_VICTIMS        Multiple people affected
+0.08  VICTIM_COUNT_MULTIPLIER 3 victims × 0.04, capped per config
−0.08  LOW_LOCATION_CONFIDENCE "near the old overpass" — no dispatchable address
────────────────────────────────
 0.80  → P1  (URGENT)

Expected: P0
```

The incident is life-threatening — an unresponsive, non-breathing driver at a multi-vehicle crash. But the flat base (0.10) fails to account for the domain-level severity of any EMS call. With the low-location penalty applied, the score falls short of the P0 threshold (0.85) by 0.05.

#### Scoring under v0.2.0 (EMS base 0.22)

```
Score breakdown:
+0.22  DOMAIN_BASE             EMS domain base score (v0.2.0)
+0.32  NOT_BREATHING           Victim not breathing — immediate life threat
+0.28  VICTIM_UNCONSCIOUS      Driver unresponsive
+0.10  MULTIPLE_VICTIMS        Multiple people affected
+0.08  VICTIM_COUNT_MULTIPLIER 3 victims × 0.04, capped per config
−0.08  LOW_LOCATION_CONFIDENCE "near the old overpass" — no dispatchable address
────────────────────────────────
 0.92  → P0  (IMMEDIATE)

Expected: P0
```

The domain-specific base score adds +0.12, which is enough to push the incident above the P0 threshold despite the location penalty. The tier assignment changes from P1 to P0 — a meaningful correction for a life-threatening incident.

**Tier change:** P1 → P0 (`↑ improved` in comparison output)
**Score delta:** +0.120

---

### Example 2 — Welfare check: stable (no tier change)

**Transcript:**
> "Um, I'm not sure if this is even a real emergency. My elderly neighbor hasn't picked up his mail in three days. He lives alone at 14 Cedar Court."

#### Under v0.1.0

```
+0.10  DOMAIN_BASE             Flat base (misclassified as other)
+0.14  LOW_SIGNAL_MATCH        (spurious low-confidence match)
────────────────────────────────
 0.24  → P3  (STANDARD — incorrect, but close)
```

#### Under v0.2.0

```
+0.10  DOMAIN_BASE             Other domain base (still misclassified)
+0.14  LOW_SIGNAL_MATCH        (spurious match unchanged)
────────────────────────────────
 0.24  → P3  (no change)
```

The domain-specific base only helps if the domain classification is *correct*. This incident is misclassified as `other` in both versions because the welfare-check keyword set is missing. The base score change has no effect here — the root cause is a parser gap, not a scoring config issue.

**Tier change:** none  
**Score delta:** 0.000

---

### Reading the comparison output

Running `compare-versions.ts` with these two configs against the full 23-fixture set produces output like this:

```
Scoring Version Comparison
Baseline : v0.1.0  services/prioritization-engine/config/scoring-rules-v0.1.0.json
Revised  : v0.2.0  services/prioritization-engine/config/scoring-rules.json
Fixtures : 23
────────────────────────────────────────────────────────────────────────────────

fixture-011  Expected: P0   ↑ improved
  Caller reports man collapsed on the sidewalk, vague location near the park...
  Tier: P1 → P0   Score: 0.800 → 0.920  Δ +0.120
  + Codes added: (none — same indicators fired, base score drove the change)

fixture-023  Expected: P0   ↑ improved
  There's been a bad crash on Route 9 near the old overpass. One driver is not...
  Tier: P1 → P0   Score: 0.800 → 0.920  Δ +0.120

fixture-008  Expected: P2     same
  An elderly woman fell on the sidewalk near the park. She can't get up and say...
  Tier: P3 → P3   Score: 0.100 → 0.140  Δ +0.040

fixture-017  Expected: P3     same
  I'm not sure if this is a real emergency. My elderly neighbor hasn't picked up...
  Tier: P3 → P3   Score: 0.240 → 0.240  Δ +0.000

[... 19 more fixtures — all unchanged ...]

────────────────────────────────────────────────────────────────────────────────

Tier Transition Matrix  (row = baseline tier, col = revised tier)

                P0      P1      P2      P3      P4
  ──────────────────────────────────────────────────
  P0            10       ·       ·       ·       ·
  P1             2       2       ·       ·       ·
  P2             ·       ·       2       ·       ·
  P3             ·       ·       ·       3       ·
  P4             ·       ·       ·       ·       2

────────────────────────────────────────────────────────────────────────────────

Summary
  Improved : 2   (baseline wrong → revised correct)
  Degraded : 0   (baseline correct → revised wrong)
  Unchanged: 21
  Net change: +2

  No regressions. Safe to bump scoring_version if manual review passes.
```

**How to read the transition matrix:** Each row is the baseline tier; each column is the revised tier. Diagonal entries (grey) are fixtures whose tier did not change. Off-diagonal entries are tier changes. The two entries in row P1, column P0 represent the two critical EMS incidents that were under-triaged under v0.1.0 and correctly identified as P0 under v0.2.0.

A P0 → P1 entry (if it existed) would be a missed-P0 under the revised config — a regression requiring investigation before deploying the change.

---

## Tools Reference

| Mode | Tool | What it does |
|------|------|-------------|
| **Single incident replay** | `POST /replay/:id` | Re-parse and re-score one stored incident; returns diff against original |
| **Batch replay** | `POST /replay/stream` | Re-score all stored incidents; returns per-incident diffs and aggregate stats |
| **Config comparison** | `compare-versions.ts` | Replays a fixture set under two scoring configs; shows which fixtures changed tier and why |
| **Fixture evaluation** | `cli.ts` (`ng911-eval`) | Runs labeled fixtures through the full pipeline; reports domain/tier accuracy and P0 safety rates |

The key distinction: `compare-versions.ts` compares two *scoring configs* against *labeled fixtures* (ground truth is known). `POST /replay/stream` compares two *scoring versions* against *stored incidents* (ground truth is the original assignment). Use both: the CLI for pre-deployment validation, the API for post-deployment blast-radius analysis.

---

## Workflow: Changing a Scoring Rule Safely

This is the recommended sequence for any change to `scoring-rules.json`.

### Step 1 — Make a candidate config

```bash
cp services/prioritization-engine/config/scoring-rules.json \
   packages/evaluation-harness/config/scoring-rules-candidate.json
```

Edit the candidate. Do **not** bump `scoring_version` yet — wait until the comparison passes.

---

### Step 2 — Compare against labeled fixtures

```bash
cd packages/evaluation-harness

npx ts-node src/compare-versions.ts \
  --baseline ../../services/prioritization-engine/config/scoring-rules.json \
  --revised  ./config/scoring-rules-candidate.json \
  --fixtures ../../data/fixtures/sample-incidents.json
```

The output shows per-fixture results. Key indicators:
- `↑ improved` — fixture was wrong under baseline, correct under revised
- `↓ degraded` — fixture was correct under baseline, wrong under revised (**requires investigation**)
- `same` — no change in whether the tier matched expected

Focus on the tier transition matrix. Any entry in the P0 row that moves off-diagonal is a missed-P0 risk — the most operationally dangerous regression type.

**To focus only on regressions:**

```bash
npx ts-node src/compare-versions.ts \
  --revised ./config/scoring-rules-candidate.json \
  --only-degraded
```

**To focus only on fixtures that changed tier (ignoring score-only changes):**

```bash
npx ts-node src/compare-versions.ts \
  --revised ./config/scoring-rules-candidate.json \
  --only-changed
```

---

### Step 3 — Save a JSON report for review

```bash
npx ts-node src/compare-versions.ts \
  --revised  ./config/scoring-rules-candidate.json \
  --json-output ./results/comparison-$(date +%Y-%m-%d).json
```

The JSON file contains the full per-fixture comparison including `reason_codes_added`, `reason_codes_removed`, and the tier transition matrix. Useful for attaching to PR review or documenting a config change decision.

**JSON output structure:**

```json
{
  "run_at": "2026-04-11T14:00:00Z",
  "baseline_version": "0.1.0",
  "revised_version": "0.2.0",
  "fixtures_count": 23,
  "summary": {
    "improved": 2,
    "degraded": 0,
    "unchanged": 21,
    "net": 2
  },
  "transition_matrix": {
    "P0": { "P0": 10 },
    "P1": { "P0": 2, "P1": 2 },
    "P2": { "P2": 2 },
    "P3": { "P3": 3 },
    "P4": { "P4": 2 }
  },
  "results": [ ... ]
}
```

---

### Step 4 — Run the full evaluation harness

The comparison CLI only tells you about *tier changes*. Run the evaluator to see the full accuracy picture with the new config:

```bash
cd packages/evaluation-harness

npx ts-node src/cli.ts \
  --fixtures ../../data/fixtures/sample-incidents.json \
  --output   ./results/eval-$(date +%Y-%m-%d).json
```

Minimum pass criteria before bumping `scoring_version`:

| Metric | Target |
|--------|--------|
| Domain accuracy | ≥ 90% |
| Tier accuracy | ≥ 80% |
| False-P0 rate | ≤ 5% |
| Missed-P0 rate | ≤ 10% |

If the candidate config passes these targets and the comparison shows `Degraded: 0`, proceed.

---

### Step 5 — Bump `scoring_version` and deploy

In the candidate config, increment `scoring_version` (e.g., `0.2.0` → `0.3.0`). Then replace the production config:

```bash
cp packages/evaluation-harness/config/scoring-rules-candidate.json \
   services/prioritization-engine/config/scoring-rules.json
```

All new incidents will now be scored with the new version. Their `audit.scoring_version` field records this. Historical incidents retain their original `scoring_version` — their triage decisions are preserved as they were made.

---

### Step 6 — Replay stored incidents to measure real-world impact

With the API running, replay all stored incidents under the new scoring:

```bash
curl -s -X POST http://localhost:3001/replay/stream \
  | jq '{
      total:        .total_replayed,
      tier_changed: .summary.tier_changed,
      improved:     .summary.score_improved,
      degraded:     .summary.score_degraded
    }'
```

The `tier_changed` count tells you how many historical incidents would have been classified differently. Review the `results[]` array for which specific incidents changed and by how much. This is the "blast radius" check — the labeled fixture comparison tells you about accuracy on known ground truth; the batch replay tells you about magnitude of change on real ingested data.

---

## Replaying a Single Incident

During operational review, replay any incident to inspect why it was scored or to compare against the current scoring version:

```bash
curl -s -X POST http://localhost:3001/replay/a3f1b2c4-... | jq '{
  original_tier:  .original.triage.priority_tier,
  original_score: .original.triage.priority_score,
  replayed_tier:  .replayed.triage.priority_tier,
  replayed_score: .replayed.triage.priority_score,
  score_delta:    .diff.score_delta,
  tier_changed:   .diff.priority_tier_changed,
  codes_added:    .diff.reason_codes_added,
  codes_removed:  .diff.reason_codes_removed,
  breakdown:      .score_breakdown
}'
```

**Sample response (no scoring config change since ingestion):**

```json
{
  "original_tier":  "P0",
  "original_score": 0.920,
  "replayed_tier":  "P0",
  "replayed_score": 0.920,
  "score_delta":    0.000,
  "tier_changed":   false,
  "codes_added":    [],
  "codes_removed":  [],
  "breakdown": [
    { "reason_code": "DOMAIN_BASE",       "weight": 0.22, "description": "EMS domain base score" },
    { "reason_code": "NOT_BREATHING",     "weight": 0.32, "description": "Victim not breathing" },
    { "reason_code": "VICTIM_UNCONSCIOUS","weight": 0.28, "description": "Victim unresponsive" },
    { "reason_code": "MULTIPLE_VICTIMS",  "weight": 0.10, "description": "Multiple people affected" },
    { "reason_code": "VICTIM_COUNT_MULTIPLIER", "weight": 0.08, "description": "3 victims × 0.04" },
    { "reason_code": "LOW_LOCATION_CONFIDENCE", "weight": -0.08, "description": "Vague location — routing impaired" }
  ]
}
```

When `original.audit.scoring_version !== replayed.audit.scoring_version`, the diff reflects a rule change between ingestion and the replay. When they match, the replay confirms the original scoring was deterministic and reproducible.

---

## Audit Trail Fields

Every incident record stores the following in `audit`:

| Field | What it records |
|-------|----------------|
| `schema_version` | Incident schema version at parse time |
| `parser_version` | Transcript parser version |
| `scoring_version` | Scoring config version that produced the triage result |
| `processed_at` | Timestamp of the triage decision |

These fields make every scoring decision fully traceable: you know exactly which version of the system produced a given tier assignment, and you can reproduce or compare it at any time without reprocessing the original call.

---

## What This Enables

The combination of replay, version comparison, and fixture evaluation is what distinguishes this platform from a system that just produces scores. It is a system for *evaluating and governing* scoring logic over time:

- **Safe iteration** — every config change is validated against labeled ground truth before deployment
- **Retroactive analysis** — any historical incident can be re-scored under any config version
- **Regression protection** — the tier transition matrix catches missed-P0 regressions before they reach production
- **Audit accountability** — the scoring decision is permanently recorded and reproducible, not just the outcome

This is the audit mechanism that emergency dispatch triage requires: not just "what did we decide?" but "why, under what logic, and would we decide differently today?"

---

## Adding New Fixtures

To add a fixture to the labeled evaluation set:

1. Add an entry to `data/fixtures/sample-incidents.json` following the fixture format
2. Set `expected_priority_tier` to the tier a trained dispatcher would assign
3. Add a `notes` field explaining what edge case or capability the fixture tests
4. Run the full evaluation: `npx ts-node src/cli.ts`
5. If the new fixture fails: diagnose whether the expected tier is wrong, or whether the system needs adjustment

Fixtures designed to test known gaps (negation, retraction language, welfare check vocabulary) should explicitly document the gap in `notes` so evaluation failures are distinguishable from regressions.

See [evaluation-plan.md](evaluation-plan.md) for the full metric definitions and cadence, and [benchmark-report-v0.2.0.md](benchmark-report-v0.2.0.md) for the current baseline results.
