# Replay and Version Comparison Workflow

This document describes the step-by-step workflow for using the replay system to evaluate, compare, and safely deploy scoring rule changes.

---

## Overview

The platform's replay system has two modes:

| Mode | Tool | What it does |
|------|------|-------------|
| **Single incident replay** | `POST /replay/:id` | Re-parse and re-score one stored incident; returns diff against original |
| **Batch replay** | `POST /replay/stream` | Re-score all (or selected) stored incidents; returns aggregate stats |
| **Config comparison** | `ng911-compare` CLI | Replays a fixture set under two configs; shows which fixtures changed tier |
| **Fixture evaluation** | `ng911-eval` CLI | Runs labeled fixtures through the full pipeline; reports accuracy metrics |

---

## When to use which tool

| Situation | Tool |
|-----------|------|
| You changed a scoring weight and want to see the impact on known fixtures | `ng911-compare` |
| You want to check whether a stored incident's tier would change under the new config | `POST /replay/:id` |
| You want to see the blast radius of a config change across all stored incidents | `POST /replay/stream` |
| You want to measure overall system accuracy against labeled ground truth | `ng911-eval` |

---

## Workflow: Changing a scoring rule safely

This is the recommended sequence for any change to `scoring-rules.json`.

### Step 1 — Make a candidate config

Copy the current config and apply your changes:

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

Read the output:
- `↑ improved` — fixture was wrong under baseline, correct under revised
- `↓ degraded` — fixture was correct under baseline, wrong under revised
- `  same` — no change in whether the tier matched expected

**If there are any `↓ degraded` fixtures, investigate before proceeding.**

To focus only on regressions:

```bash
npx ts-node src/compare-versions.ts \
  --revised ./config/scoring-rules-candidate.json \
  --only-degraded
```

---

### Step 3 — Inspect the tier transition matrix

The comparison output includes a transition matrix showing how many fixtures moved between tiers:

```
Tier Transition Matrix  (row = baseline tier, col = revised tier)

                P0      P1      P2      P3      P4
  ──────────────────────────────────────────────────
  P0             6       1       ·       ·       ·
  P1             ·       3       ·       ·       ·
  P2             ·       ·       2       ·       ·
  P3             ·       ·       ·       2       ·
  P4             ·       ·       ·       ·       1
```

Diagonal entries are unchanged. Off-diagonal entries are tier changes. P0→P1 is a missed-P0 under the new config; P1→P0 is a false-P0 increase. Both are worth examining.

---

### Step 4 — Save a JSON report for record-keeping

```bash
npx ts-node src/compare-versions.ts \
  --revised  ./config/scoring-rules-candidate.json \
  --json-output ./results/comparison-$(date +%Y-%m-%d).json
```

The JSON file contains the full per-fixture comparison including reason code diffs, which is useful for PR review commentary.

---

### Step 5 — Run the full evaluation harness

The comparison CLI only checks against labeled fixtures. Run the full evaluator to get accuracy metrics and the P0 safety rates:

```bash
npx ts-node src/cli.ts \
  --fixtures ../../data/fixtures/sample-incidents.json \
  --output   ./results/eval-$(date +%Y-%m-%d).json
```

Check the report:
- Domain accuracy ≥ 90%
- Tier accuracy ≥ 80%
- False-P0 rate ≤ 5%
- Missed-P0 rate ≤ 10%

If the candidate config passes these targets and the comparison shows no regressions, proceed.

---

### Step 6 — Bump scoring_version and deploy

In `scoring-rules-candidate.json`, increment `scoring_version` (e.g., `0.2.0` → `0.3.0`).

Replace the production config:

```bash
cp packages/evaluation-harness/config/scoring-rules-candidate.json \
   services/prioritization-engine/config/scoring-rules.json
```

All new incidents will now be scored with the new version. Their `audit.scoring_version` field will reflect the change.

---

### Step 7 — Replay stored incidents to measure real-world impact

With the API running, replay all stored incidents under the new scoring:

```bash
curl -s -X POST http://localhost:3001/replay/stream \
  -H "Content-Type: application/json" \
  -d '{"incident_ids": "all"}' \
  | jq '{total: .total_replayed, tier_changed: .summary.tier_changed, improved: .summary.score_improved, degraded: .summary.score_degraded}'
```

The `tier_changed` count tells you how many historical incidents would have been classified differently under the new rules. Review `results[]` in the response to see which specific incidents changed and by how much.

---

## Replay single incident (operator use)

During operational review, an operator can replay any stored incident to understand why it was scored as it was, or to compare against a newer scoring version:

```bash
# Replace with the incident ID from the queue
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

The `score_breakdown` in the response gives the full per-factor contribution list for the replayed result.

---

## Audit trail fields

Every incident record stores the following version fields in `audit`:

| Field | What it records |
|-------|----------------|
| `schema_version` | The incident schema version at parse time |
| `parser_version` | The transcript parser version |
| `scoring_version` | The scoring config version that produced the triage result |
| `processed_at` | Timestamp of the triage decision |

When `POST /replay/:id` shows that `original.audit.scoring_version !== replayed.audit.scoring_version`, the diff reflects a scoring rule change between the original ingestion and the replay.

---

## Adding new fixtures

To add a fixture to the labeled set:

1. Add an entry to `data/fixtures/sample-incidents.json` following the fixture format
2. Set `expected_priority_tier` to the tier you believe the system should assign
3. Add a `notes` field explaining the edge case or scenario being tested
4. Run the full evaluation: `npx ts-node src/cli.ts`
5. If the new fixture fails, decide: is the expected tier wrong, or does the system need adjustment?

Fixtures added to test edge cases (negation, Spanish, prank indicators, vague location) should have explicit notes so their purpose is clear when reviewing evaluation results.
