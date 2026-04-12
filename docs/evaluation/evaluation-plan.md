# Evaluation Plan

## Purpose

This document defines how the NG911 Triage Intelligence Platform measures its own behaviour. Evaluation turns development into evidence: it lets us claim improvement, not just change.

---

## Evaluation Philosophy

- **Honest metrics over optimistic ones.** Report false-P0 and missed-P0 rates explicitly — not just accuracy.
- **Labeled fixtures as ground truth.** A small, carefully labeled fixture set is more trustworthy than a large unlabeled one.
- **Version-locked comparisons.** Every evaluation run records `parser_version` and `scoring_version` so results are reproducible.
- **No overfitting to fixtures.** Fixtures are for sanity-checking, not hyperparameter tuning. Tune on generated scenarios, validate on fixtures.

---

## Metrics

### 1. Domain Accuracy

**Definition:** Fraction of fixtures where `incident.domain` matches `expected_domain`.

**Target:** ≥ 0.90

**Why it matters:** Domain misclassification routes the wrong kind of responder. EMS vs. police is operationally significant.

---

### 2. Subtype Accuracy

**Definition:** Fraction of fixtures where `incident.subtype` matches `expected_subtype`.

**Target:** ≥ 0.75

**Why it matters:** Subtype determines resource allocation details. Lower bar than domain because subtypes are more ambiguous in natural language.

---

### 3. Tier Accuracy

**Definition:** Fraction of fixtures where `triage.priority_tier` matches `expected_priority_tier`.

**Target:** ≥ 0.80

**Why it matters:** Tier drives dispatch order. Misclassified tiers have direct operational impact.

---

### 4. False-P0 Rate

**Definition:** Among fixtures whose expected tier is **not** P0, what fraction did the system assign P0?

**Formula:** `false_P0 / total_non_P0_fixtures`

**Target:** ≤ 0.05

**Why it matters:** False P0 wastes emergency resources and erodes operator trust in the platform.

---

### 5. Missed-P0 Rate

**Definition:** Among fixtures whose expected tier **is** P0, what fraction did the system fail to assign P0?

**Formula:** `missed_P0 / total_P0_fixtures`

**Target:** ≤ 0.10

**Why it matters:** Missed P0 is operationally dangerous — a life-threatening incident that was under-triaged.

---

### 6. Score Stability

**Definition:** Run the same fixture 3 times (parser is deterministic). Verify `priority_score` is identical across runs.

**Target:** 100% deterministic (zero variance)

**Why it matters:** Non-determinism in a triage system is operationally unacceptable.

---

### 7. Negation Suppression Accuracy

**Definition:** On a curated set of negated-phrase fixtures (e.g., "he is NOT having a heart attack"), verify that the corresponding severity indicator is **absent** from the parsed record.

**Target:** ≥ 0.95

**Why it matters:** Validates that the negation filter is working and not under-triggering.

---

### 8. Spanish Detection Accuracy

**Definition:** On a curated set of Spanish-language fixtures, verify that `language_hint` is `"es"` and that domain classification is correct.

**Target:** ≥ 0.85 domain accuracy on Spanish fixtures

---

## Evaluation Cadence

| Trigger | Action |
|---------|--------|
| Scoring config change | Run `npm run eval` and confirm no regressions |
| Parser keyword update | Run `npm run eval` + negation suite |
| New fixture added | Run full eval and update baseline results |
| Before any `scoring_version` bump | Run `ng911-compare` against the new config |

---

## Running the Evaluation

```bash
# Full evaluation against sample fixtures
cd packages/evaluation-harness
npx ts-node src/cli.ts

# Custom fixture file
npx ts-node src/cli.ts --fixtures ../../data/fixtures/sample-incidents.json

# Save JSON report
npx ts-node src/cli.ts --output results/eval-2026-04-11.json

# Compare two scoring configs
npx ts-node src/compare-versions.ts \
  --baseline ../../services/prioritization-engine/config/scoring-rules.json \
  --revised  ./config/scoring-rules-candidate.json
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
  "notes": "Optional — reasoning behind the expected values"
}
```

---

## Limitations and Honest Caveats

- The fixture set is 20 scenarios. Accuracy figures have high uncertainty and are directional, not statistically validated.
- Fixtures were designed to exercise the system's decision logic and edge cases, not as a statistically representative sample of real emergency calls.
- The system has not been evaluated against real PSAP call data.
- Subtype accuracy is sensitive to vocabulary coverage, not classification methodology.
- Edge-case fixtures (fixture-011 through fixture-020) test boundary conditions — vague location, prank calls, Spanish-language inputs, extreme stress, unknown victim count. These should not be interpreted as representing the distribution of real calls.

These limitations should be stated when reporting results.
