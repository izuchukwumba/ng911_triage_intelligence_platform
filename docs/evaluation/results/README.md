# Evaluation results

Reports produced by `python -m ntip.evaluation`. Each has a JSON and a Markdown
version, and each records the git commit, dataset digest, ruleset digest,
versions and seed needed to reproduce it.

| Report | Parser / ruleset | Data | Notes |
|---|---|---|---|
| [1.0.0 dev+regression](b0-curated-1.0.0-research-1.0.0-dev-regression.md) | 1.0.0 / research-1.0.0 | curated dev + regression (30) | First development view |
| [1.0.0 test](b0-curated-1.0.0-research-1.0.0-test.md) | 1.0.0 / research-1.0.0 | curated test (20) | **Held-out baseline.** Recorded once; its failures are not used to change the parser |
| [1.1.0 dev+regression](b0-curated-1.1.0-research-1.0.0-dev-regression.md) | 1.1.0 / research-1.0.0 | curated dev + regression (30) | After closing the regression miss; CI gate enabled |
| [1.2.0 dev+regression](b0-curated-1.2.0-research-1.1.0-dev-regression.md) | 1.2.0 / research-1.1.0 | curated dev + regression (30), labelling guide v1.1 | Rubric gaps closed; no under-triage |

## First baseline (B0, curated v1)

- On the regression split, one expected-P0 case is under-triaged:
  `cu-126` ("I'm not sure if he's breathing … won't answer me"), where neither
  the uncertain breathing cue nor "won't answer" is recognised. This is the
  first gap the CI safety gate will hold closed once fixed.
- On the held-out test split, 2 of 9 expected-P0 cases are under-triaged
  (critical under-triage 0.222, 95% CI 0.000–0.556). They are left as they are, so
  this report remains an honest held-out baseline for comparing B1/B2.
- Over-triage concentrates on cues the rules cannot grade (minor bleeding,
  retracted or past events), which the rubric places lower.

These are measurements on 50 author-labelled synthetic cases. They are not
evidence of real-world dispatch performance (design v1.2, §16.3).

`../benchmark-report-v0.2.0.md` describes the retired TypeScript scorer and is
kept for history.

## Parser 1.1.0 (dev + regression only)

Changes were driven only by dev and regression failures. Critical-cue
sensitivity 15/15 (was 13/15), critical under-triage 0/13 (was 1/13), cue
micro F1 0.985 (was 0.906), priority agreement 0.800 (was 0.667). The
remaining failures are triage-rubric gaps (older adult unable to get up, a
recovered critical event, retractions and past events), not extraction
errors. The held-out test split has not been re-run.

## Parser 1.2.0 + ruleset research-1.1.0 (dev + regression only)

Priority agreement 0.867 (26/30), under-triage 0/30, critical under-triage 0/13.
All four remaining disagreements are **over-triage**, the safe direction, and
are kept deliberately:

- `fx-021`, `fx-022`, `cu-103`: a threat that has left, a retracted report and
  a past hearsay event. Lowering priority from what a caller says happened (or
  "takes back") is a judgement left to the human reviewer; the engine adds
  review actions instead.
- `cu-119`: a hypothetical cardiac event is assessed "undetermined" (P2), not low.

## Generated stress set (generator 1.0.0, seed 42; dev + regression, 300 cases)

[Report](b0-generated-1.2.0-research-1.1.0-dev-regression.md). Cue micro F1
0.963, critical-cue sensitivity 0.926 (63/68), critical under-triage 9/109,
priority agreement 0.870. Failures group into:

- **Rules gaps worth fixing:** "convulsing a minute ago and is *still*
  convulsing" read as past; "overdosed" not voting for EMS; Spanish
  "atrapadas" missing.
- **Misspellings and disfluency** splitting a cue ("chest perssure",
  "not um, breathing"): out of reach for exact phrase matching, and the main
  case for the ML baselines.
- **Denial-only calls** assessed "undetermined" (P2) rather than low: over-triage,
  kept deliberately.

Labels here are generator-intended, so these numbers are a stress test, not
accuracy.

## Parser 1.3.0 (dev + regression only)

Fixes for the generated-set gaps above ("still", "overdosed", "atrapadas").

| | Curated (30) | Generated (300) |
|---|---|---|
| Critical under-triage | 0/13 | 1/109 (was 9/109) |
| Priority exact | 0.867 | 0.937 (was 0.870) |
| Cue micro F1 | 0.986 | 0.989 (was 0.963) |

The remaining generated critical miss is a misspelled cue, the expected limit
of exact phrase matching. Neither test split was re-run.

## ML comparison: B0 vs B1 vs hybrid (milestones ML-3 / ML-4)

Reports: [curated test](compare-curated-test.md),
[curated dev + regression](compare-curated-dev-regression.md),
[generated test](compare-generated-test.md). B1 (`b1-tfidf-logreg`, see the
[model card](../../ml/model-card-b1.md)) was trained only on the generated
dev + regression splits, so none of these cases were seen in training.

| | Curated test (20) | Curated dev+reg (30) | Generated test (210) |
|---|---|---|---|
| Critical under-triage: B0 → hybrid | 2/9 → **0/9** | 0/13 → 0/13 | 0/47 → 0/47 |
| Critical-cue sensitivity: B0 / hybrid | 0.857 / 0.857 | 1.000 / 1.000 | 1.000 / 1.000 |
| Cue precision: B0 → hybrid | 1.00 → 0.79 | 0.97 → 0.71 | 0.98 → 0.87 |
| Over-triage: B0 → hybrid | 0.10 → 0.20 | 0.13 → 0.17 | 0.12 → 0.22 |
| B1-only cue recall | 0.63 | 0.56 | 0.27 |

**ML-4 gate ("no increase in critical-cue false negatives on a frozen test
set"): met** on all three sets. On the curated test split, hybrid fusion
removes both critical under-triages B0 makes, at the cost of more
over-triage and lower precision, which the review workflow absorbs (every
model-only serious cue requires human confirmation).

Other findings:

- **B1 alone is not usable:** recall collapses on scenario families it never
  saw (0.27 on generated test). Fusion, not replacement, is what helps.
- **Abstention matters:** lowering B1's candidate threshold to the abstention
  threshold reduces precision and raises over-triage on every set.
- **B1 is not calibrated:** ECE 0.07–0.10. Its scores are reported as
  uncalibrated; selective risk is low at 50% coverage (≤ 0.011).
- **B1 has no negation or tense model:** hybrid lets 1–2 denied or past cues
  through as live. The rules remain the reference for negation.

These are synthetic-benchmark results with author- or generator-intended
labels; they are not evidence of real-world performance.

## Processing latency baseline

[latency.json](latency.json), from `python -m ntip.evaluation.latency --repeat 5`:
end-to-end ingest through the pipeline (parse, optional in-process model,
assess, store) with an in-memory store, one request at a time, over the 50
curated cases, on `Windows-11-10.0.26300-SP0`, Python 3.12.10.

| Mode | Model | Requests | p50 ms | p95 ms | p99 ms |
|---|---|---|---|---|---|
| rules_only | - | 250 | 0.57 | 0.95 | 1.51 |
| hybrid_review | b1-tfidf-logreg | 250 | 3.16 | 3.82 | 4.19 |

These are measurements, not targets (design v1.2, §13.3). They exclude HTTP,
PostgreSQL and a networked inference service, whose time is bounded separately
by the 2 s inference timeout; the model is optional and can never block
ingestion (§3B.1, RQ-INT4).

## Concurrency (load test)

`python -m ntip.evaluation.load --workers 16 --incidents 200 --follow-ups 3`
sends three simultaneous follow-ups per incident to stress same-incident
contention, then checks that every message, assessment and audit event is
present and that each incident's latest version covers every message.

| Store | Requests | Errors | Inconsistencies | Throughput | p50 / p95 |
|---|---|---|---|---|---|
| memory, before DDL-016 | 800 | 124 (lost messages) | 125 | — | — |
| memory, after | 800 | 0 | 0 | ~480/s | 13 ms / 90 ms |
| PostgreSQL, before DDL-016 | 400 | 0 | 100 (stale versions) | — | — |
| PostgreSQL, after | 400 | 0 | 0 | ~17/s | 0.7 s / 1.7 s |
| PostgreSQL, pooled connections | 400 | 0 | 0 | ~310/s | 49 ms / 90 ms |

Before pooling, every store call opened a new PostgreSQL connection; a
pool of 10 (`NTIP_DATABASE_POOL_SIZE`) raised throughput about 18-fold on
the same run. The workload is deliberately extreme contention (every
incident receives simultaneous follow-ups), measured on one development
machine; treat the figures as a regression baseline, not a capacity claim.
