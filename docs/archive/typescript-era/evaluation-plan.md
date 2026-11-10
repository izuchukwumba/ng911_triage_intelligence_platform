# Evaluation Plan

## Purpose

This document defines how the NG911 Triage Intelligence Platform measures its own behaviour. Evaluation turns development into evidence: it lets us claim improvement, not just change. It is also the basis for benchmark reports that can be cited in technical articles, public presentations, and external assessments.

---

## Evaluation Philosophy

- **Honest metrics over optimistic ones.** Report false-P0 and missed-P0 rates explicitly — not just accuracy.
- **Labeled fixtures as ground truth.** A small, carefully labeled fixture set is more trustworthy than a large unlabeled one.
- **Version-locked comparisons.** Every evaluation run records `parser_version` and `scoring_version` so results are reproducible and comparable across releases.
- **No overfitting to fixtures.** Fixtures are for sanity-checking, not hyperparameter tuning. Tune on generated scenarios, validate on fixtures.
- **Failure visibility.** Every failing fixture gets a score breakdown, not just a miss count.

---

## Metric Definitions

### 1. Domain Accuracy

**Definition:** Fraction of fixtures where `incident.domain` matches `expected_domain`.

```
domain_accuracy = |{f : f.actual_domain == f.expected_domain}| / |fixtures|
```

**Target:** ≥ 0.90

**Why it matters:** Domain misclassification routes the wrong kind of responder. An EMS incident classified as police dispatches no paramedic.

**Failure mode:** False domain is usually caused by missing or ambiguous keywords. A fixture that fails domain is almost always also wrong on tier.

---

### 2. Subtype Accuracy

**Definition:** Fraction of fixtures where `incident.subtype` matches `expected_subtype`.

```
subtype_accuracy = |{f : f.actual_subtype == f.expected_subtype}| / |fixtures|
```

**Target:** ≥ 0.75

**Why it matters:** Subtype determines resource allocation details (e.g., cardiac arrest vs. respiratory distress routes different EMS protocols). The bar is lower than domain because subtypes are more ambiguous in natural language and more sensitive to vocabulary coverage.

**Failure mode:** Subtype misclassification typically doesn't change the tier assignment. A cardiac arrest scored as "respiratory distress" is still P0.

---

### 3. Tier Accuracy

**Definition:** Fraction of fixtures where `triage.priority_tier` matches `expected_priority_tier`.

```
tier_accuracy = |{f : f.actual_tier == f.expected_tier}| / |fixtures|
```

**Target:** ≥ 0.80

**Why it matters:** Tier drives dispatch order. A tier-correct system assigns the right urgency level to the right incidents — the primary operational goal.

**Failure subtypes:**
- **Over-triage** — `actual_tier` is higher priority than `expected_tier`. Wastes resources but not life-threatening.
- **Under-triage** — `actual_tier` is lower priority than `expected_tier`. Operationally dangerous; delayed response to a real emergency.

---

### 4. False-P0 Rate

**Definition:** Among fixtures with expected tier NOT P0, what fraction did the system assign P0?

```
false_P0_rate = |{f : f.actual_tier == 'P0' AND f.expected_tier != 'P0'}|
              / |{f : f.expected_tier != 'P0'}|
```

**Target:** ≤ 0.05

**Why it matters:** False P0 dispatches maximum resources to a non-critical incident. Repeated false P0s erode operator trust and waste emergency resources. This is the over-triage safety gate.

---

### 5. Missed-P0 Rate

**Definition:** Among fixtures with expected tier P0, what fraction did the system fail to assign P0?

```
missed_P0_rate = |{f : f.expected_tier == 'P0' AND f.actual_tier != 'P0'}|
               / |{f : f.expected_tier == 'P0'}|
```

**Target:** ≤ 0.10

**Why it matters:** Missed P0 is operationally dangerous — a life-threatening incident that was under-triaged delays a life-saving response. This is the under-triage safety gate and carries higher operational weight than false-P0.

---

### 6. Ranking Stability (Score Determinism)

**Definition:** Run each fixture N times. Verify `priority_score` is identical across all runs.

```
stability = 1  if  std_dev(scores_for_fixture_i) == 0  for all i
          = 0  otherwise
```

**Target:** 100% (zero variance across runs)

**Why it matters:** Non-determinism in a rules-based triage system has no legitimate cause. Any variance indicates a bug — not a feature. The platform makes no probabilistic decisions; given the same input and config version, the output must be identical.

**Note:** The current pipeline (keyword matching → weighted sum → tier lookup) is fully deterministic. This metric is a regression guard, not a tuning target.

---

### 7. Negation Suppression Accuracy

**Definition:** On fixtures containing negated indicator phrases, verify the corresponding severity indicator is absent from the parsed record.

```
negation_accuracy = |{f_neg : f_neg has no false-positive indicators}|
                  / |{f_neg}|
```

**Target:** ≥ 0.95

**Why it matters:** Validates the negation filter. An indicator extracted from a negated phrase (e.g., "no weapons found" → `weapon_present`) inflates the score incorrectly. Negation suppression is the primary mechanism that distinguishes "not breathing" (critical) from "breathing on his own again" (resolved).

---

### 8. Spanish Detection Accuracy

**Definition:** On Spanish-language fixtures, verify `language_hint` is `"es"` and domain classification is correct.

```
es_domain_accuracy = |{f_es : f_es.domain_correct AND f_es.language_hint == 'es'}|
                   / |{f_es}|
```

**Target:** ≥ 0.85

**Why it matters:** Spanish is the second-most-common language in US emergency calls. Failing to detect Spanish falls back to the English keyword set, potentially missing domain-critical terms.

---

### 9. Latency

**Definition:** Wall-clock time from raw transcript string to scored `IncidentRecord`, per fixture. Measured as mean, p50, and p95.

```
latency_per_fixture = time(parseTranscript) + time(scoreIncident)   [ms]
```

**Target:** Mean ≤ 50ms, P95 ≤ 150ms (single-core, no parallelism)

**Why it matters:** Emergency triage must be fast enough to support real-time operator review. The rules pipeline has no I/O on the hot path and no model inference — latency should be dominated by string operations, not compute.

**Note:** These latency figures are for the in-process pipeline only. Network, database, and middleware overhead are measured separately.

---

## Scenario Buckets

Fixtures are grouped into scenario buckets by expected priority tier. Bucket accuracy is reported separately from overall tier accuracy to surface which priority levels the system handles well and which need improvement.

| Bucket | Expected tier | Operational meaning |
|--------|--------------|---------------------|
| **P0 — Critical** | P0 | Life-threatening. Highest operational weight. |
| **P1 — High** | P1 | Urgent. Active danger or rapidly evolving situation. |
| **P2 — Elevated** | P2 | Moderate. Needs response but not immediately life-threatening. |
| **P3 — Standard** | P3 | Low to moderate. Welfare checks, minor injuries. |
| **P4 — Non-urgent** | P4 | Monitor or defer. Pranks, false alarms, administrative. |

Each bucket is scored independently:

```
bucket_accuracy(tier) = |{f : f.expected_tier == tier AND f.tier_correct}|
                      / |{f : f.expected_tier == tier}|
```

P0 bucket accuracy carries the highest operational weight. A system can miss several P3/P4 classifications and still be considered safe; it cannot miss P0 classifications.

---

## Evaluation Cadence

| Trigger | Action |
|---------|--------|
| Any scoring config change | Run full eval; confirm no regressions in P0 bucket |
| Parser keyword update | Run full eval + negation suite |
| New fixture added | Run full eval; update baseline if results improve |
| Before `scoring_version` bump | Run `ng911-compare` + full eval |
| Before any public-facing benchmark claim | Re-run full eval; save JSON output; record parser/scoring versions |

---

## Running the Evaluation

```bash
# Full evaluation against all fixtures (terminal output)
cd packages/evaluation-harness
npx ts-node src/cli.ts

# Custom fixture file
npx ts-node src/cli.ts --fixtures ../../data/fixtures/sample-incidents.json

# Save JSON report for archiving or citation
npx ts-node src/cli.ts \
  --fixtures ../../data/fixtures/sample-incidents.json \
  --output   ./results/eval-$(date +%Y-%m-%d).json

# Compare two scoring configs side by side
npx ts-node src/compare-versions.ts \
  --baseline ../../services/prioritization-engine/config/scoring-rules.json \
  --revised  ./config/scoring-rules-candidate.json \
  --fixtures ../../data/fixtures/sample-incidents.json

# Show only fixtures that changed tier (useful during tuning)
npx ts-node src/compare-versions.ts \
  --revised  ./config/scoring-rules-candidate.json \
  --only-changed

# Save comparison results as JSON
npx ts-node src/compare-versions.ts \
  --revised  ./config/scoring-rules-candidate.json \
  --json-output ./results/comparison-$(date +%Y-%m-%d).json
```

---

## Fixture Format

```json
{
  "id": "fixture-001",
  "transcript": "Someone has been shot near 5th and Oak. There is a lot of blood.",
  "expected_domain": "police",
  "expected_subtype": "shooting",
  "expected_priority_tier": "P0",
  "severity": "critical",
  "notes": "Reasoning behind the expected values — required for edge-case fixtures"
}
```

Field descriptions:

| Field | Required | Description |
|-------|----------|-------------|
| `id` | Yes | Unique stable identifier (e.g., `fixture-001`) |
| `transcript` | Yes | Raw text input exactly as the system would receive it |
| `expected_domain` | Yes | Ground-truth domain: `ems`, `police`, `fire`, `hazmat`, `other`, `unknown` |
| `expected_subtype` | Yes | Ground-truth subtype (e.g., `cardiac_arrest`, `shooting`) |
| `expected_priority_tier` | Yes | Ground-truth tier: `P0` through `P4` |
| `severity` | Yes | Narrative severity: `critical`, `high`, `moderate`, `low` |
| `notes` | Recommended | Explanation of edge-case behavior and what the fixture tests |

---

## Reporting and Evidence

### For technical articles and public posts

When citing evaluation results, always include:

1. The fixture count and fixture set version
2. Parser and scoring version numbers (from the JSON report's `parser_version` and `scoring_version` fields)
3. The date the evaluation was run
4. An honest acknowledgment of the fixture set limitations (see below)

**Suggested citation format:**

> "Evaluated on 23 hand-labeled emergency call transcripts (data/fixtures/sample-incidents.json, parser v0.2.0, scoring v0.2.0, run 2026-04-11). Domain accuracy: 91.3%. Tier accuracy: 87.0%. False-P0 rate: 0.0%. Missed-P0 rate: 0.0%."

### For immigration evidence and credential materials

The evaluation harness demonstrates:

- **Quantitative methodology** — metrics are formally defined, not anecdotal
- **Safety awareness** — false-P0 and missed-P0 are tracked separately from general accuracy, reflecting domain expertise
- **Reproducibility** — every report is version-locked and can be regenerated
- **Intellectual contribution** — the negation filter, Spanish bilingual pipeline, and scenario bucket reporting represent original engineering work in the emergency response AI domain

The JSON output from `--output` provides a machine-readable artifact that can be attached to an application or reviewed by a third party. The benchmark report in `docs/evaluation/benchmark-report-v0.2.0.md` provides a human-readable narrative suitable for recommenders or reviewers unfamiliar with the codebase.

---

## Limitations and Honest Caveats

- The fixture set is 23 scenarios. Accuracy figures are directional, not statistically validated. A 95% confidence interval on 87% tier accuracy over 23 fixtures is approximately ±14%.
- Fixtures were designed to exercise decision logic and edge cases, not sampled from real PSAP call data. The distribution does not represent the distribution of real emergency calls.
- The system has not been evaluated against real PSAP call transcripts.
- Subtype accuracy is sensitive to vocabulary coverage, not classification architecture — it can be improved by adding synonyms to the keyword lists.
- Edge-case fixtures (fixture-011 through fixture-023) test boundary conditions. fixture-022 (false alarm retraction) is documented as an expected failure — it tests a known gap, not a system regression.
- Latency measurements are from a development machine under no load. Production latency depends on server configuration, middleware, and storage backend.

These limitations must be stated when reporting results in any external context.
