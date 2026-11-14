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

## Stream replay

[`stream-escalation-research-1.1.0-vs-1.0.0.md`](stream-escalation-research-1.1.0-vs-1.0.0.md)
replays [`data/streams/escalation.jsonl`](../../../data/streams/escalation.jsonl)
on a simulated clock (design v1.2, section 10.2). It shows the queue after
each message and how long each incident took to reach P0 (A: 45 s after its
first message, B: 70 s). Against `research-1.0.0`, one step changes: the fall
where the person cannot get up drops from P2 to P3, because that ruleset
predates the unable-to-get-up rule. This is an illustrative difference, not a
validated improvement.


## Rules on generator 2.0 (dev + regression, 1,188 calls)

[Report](b0-generated-2.0.0-parser-1.5.0-research-1.2.0-dev-regression.md):
parser 1.5.0, ruleset research-1.2.0.

| | Generator 1.0.0 (parser 1.3.0) | Generator 2.0.0 (parser 1.5.0) |
|---|---|---|
| Critical-cue sensitivity | 0.985 (67/68) | 0.686 (129/188) |
| Critical under-triage | 1/109 | 102/334 (0.305) |
| Cue micro recall | 0.978 | 0.756 |
| Cue micro precision | 1.000 | 0.958 |
| Priority exact | 0.937 | 0.638 |

Generator 2.0's phrasings were written without reference to the rules'
phrase lists ("went limp", "is out cold", "can't get any air in", "the
blood won't stop"). Exact phrase matching misses almost a third of the
critical calls. This is the gap a learned model is meant to close, measured
on phrasing the rules were not written for. The rules are **not** changed to
fit this data, so it stays a fair test of them. Labels are
generator-intended; this is a stress test, not accuracy.

## B1e 0.1.0 baseline (curated dev + regression)

[Report](compare-curated-dev-regression-b1e-0.1.0.md) · model manifest
[`b1e-0.1.0+69412079012c`](b1e-0.1.0+69412079012c-manifest.json) (trained on
a laptop CPU in 16 minutes, from commit `a5b62bd` plus the positive-weighting
fix committed next as `c65bbcf`; the manifest's `params` record the settings
used).

| | B0 rules | B1 only | B1e only | Hybrid B0+B1 | Hybrid B0+B1e |
|---|---|---|---|---|---|
| Critical-cue sensitivity | 15/15 | 10/15 | 8/15 | 15/15 | 15/15 |
| Critical under-triage | 0/13 | 4/13 | 5/13 | 0/13 | 0/13 |
| Cue micro recall | 1.00 | 0.56 | 0.47 | 1.00 | 1.00 |
| Cue micro precision | 0.97 | 0.59 | 0.55 | 0.71 | 0.71 |

B1e fits its training data completely: 96 of 96 training cues, every one
scored 1.0. On curated calls it never saw, it does no better than B1. It has
memorised its training templates rather than learned the cues. Those are
the 10 scenario families of generator 1.0.0, with 3 sentence templates each,
so 30 base sentences in all. This is the narrow-data problem the ML layer
design describes (§4.2), measured. The training method works; the data
cannot teach generalisation. Generator 2.0 (more scenario families, more
templates, every cue in both training and test families) comes before any
further model work.

A first run without positive weighting underfitted instead: it recognised
26 of 96 cues in its own training calls and 6% on curated calls.

## B1e on generator 2.0 (curated dev + regression)

[Report](compare-curated-dev-regression-b1e-0.1.0+3cf9758d0861.md) · model
manifest [`b1e-0.1.0+3cf9758d0861`](b1e-0.1.0+3cf9758d0861-manifest.json).
The model was trained on a free Colab T4 GPU from commit `a786e6f`. It used
the 1,188 dev and regression calls of `generated-2.0.0-seed42.jsonl` (39
families), with the same fixed settings as the 0.1.0 baseline. The
evaluation was then run on a laptop CPU at commit `800da31`, which adds the
`cu-116` relabel. Before the relabel, the CPU run reproduced the Colab
report exactly.

| | B0 rules | B1 only | B1e 0.1.0 (generator 1.0) | **B1e (generator 2.0)** | Hybrid B0+B1 | **Hybrid B0+B1e** |
|---|---|---|---|---|---|---|
| Critical-cue sensitivity | 15/15 | 10/15 | 8/15 | **11/15** | 15/15 | **15/15** |
| Critical under-triage | 0/13 | 4/13 | 5/13 | **3/13** | 0/13 | **0/13** |
| Under-triage (any) | 1/30 | 10/30 | – | **5/30** | 1/30 | **0/30** |
| Over-triage (any) | 4/30 | 4/30 | – | **6/30** | 5/30 | **6/30** |
| Priority exact | 25/30 | 16/30 | – | **19/30** | 24/30 | **24/30** |
| Cue micro recall | 0.97 | 0.51 | 0.47 | **0.73** | 0.97 | **1.00** |
| Cue micro precision | 0.97 | 0.59 | 0.55 | **0.68** | 0.72 | **0.73** |
| Denied/past cues reported live | 0 | 0 | 1 | **3** | 0 | **3** |

The 0.1.0 column was measured before the `cu-116` relabel, so its
under-triage, over-triage and priority figures are left out. Its cue
figures change by at most one cue.

- **Broader data was the right fix.** The model and the settings were
  unchanged. Recall on unseen calls rose from 0.47 to 0.73, and B1e is now
  better than B1 on every cue metric. This confirms the narrow-data
  diagnosis above.
- **Hybrid B0+B1e** finds every labelled cue and under-triages no case. It
  catches the one case the rules under-triage: `cu-116`, "two cars crashed",
  which the rules do not match. The cost is two more over-triaged cases
  than the rules alone:
  - `fx-006`: B1e adds a false `MULTIPLE_VICTIMS`, so P1 becomes P0.
  - `fx-008`: B1e adds `FALL_FROM_HEIGHT` for a fall on a pavement, so P2
    becomes P1.
- **30 cases.** None of these differences is statistically meaningful. The
  pre-registered test-split comparison (ML-10) is the measure that counts.

**Error analysis** (B1e on its own, per case):

| Pattern | Cases | What B1e did |
|---|---|---|
| Denials | `fx-022` "Nobody seems to be hurt", `cu-120` "Nobody is hurt", `cu-101` "There is no fire" | Scored the denied cue live (0.92, 0.98, 0.66). The hybrid keeps these cues too, but none of them changed a priority here. The generator labels `INJURY_REPORTED` only as a side effect of other cues, so it never denies it on its own. |
| Shouting | `fx-018` "HE IS NOT BREATHING" in capitals | Missed it: score 0.00. The base model is case-sensitive, and the generator has no all-capitals variant. |
| Cues that often appear together | `fx-002`, `fx-011`, `cu-106`, `fx-001` | Added `UNCONSCIOUS` whenever someone is not breathing, including "He's still conscious". The generator's families almost always pair the two. |
| Spanish | `fx-015` "Mi esposo no está respirando… ataque al corazón", `cu-115` "Mi hija" | Read "esposo" (husband) as a child (0.99), missed "ataque al corazón", and missed `CHILD_INVOLVED` for "hija" (daughter). |
| Unseen phrasing | `cu-105` "collapsed", `cu-110` "trouble breathing" next to chest pain, `fx-003` "people inside" a burning house, `cu-126` "not sure if he's breathing" | Missed each one (scores 0.01 to 0.39). |

Most of these are gaps in the generator, not in the model: no all-capitals
variant, no denials of side-effect cues, cues that always appear together,
and thin Spanish. They were found on curated **dev** cases, so closing them
in the generator is legitimate development. However, curated dev then stops
being an independent check of those patterns, which makes the held-out test
split (ML-10) all the more important.

The model directory (540 MB) is not committed. Its manifest records the
sha256 of every file, and the platform refuses a copy that does not match.

## B1e on generator 2.1 (curated dev + regression)

[Report](compare-curated-dev-regression-b1e-0.1.0+e6517d2f2406.md) · model
manifest [`b1e-0.1.0+e6517d2f2406`](b1e-0.1.0+e6517d2f2406-manifest.json).

- **Training:** a Colab T4 at commit `695f568`, on the 1,200 dev and
  regression calls of `generated-2.1.0-seed42.jsonl`, with the same
  settings as before. Only the training data changed.
- **Evaluation:** a laptop CPU run of the same model at the same commit
  reproduced the Colab report exactly.
- **B1 version:** the B1 column carries a different B1 version from the
  generator 2.0 report (`a20d70dfc761` against `f764c2172d5a`). B1 is
  refitted when it loads, and its digest differs between the Colab and the
  laptop environments. Its figures are identical.

| | B0 rules | B1e (gen 2.0) | **B1e (gen 2.1)** | Hybrid B0+B1e (gen 2.0) | **Hybrid B0+B1e (gen 2.1)** |
|---|---|---|---|---|---|
| Critical-cue sensitivity | 15/15 | 11/15 | **13/15** | 15/15 | **15/15** |
| Critical under-triage | 0/13 | 3/13 | **2/13** | 0/13 | **0/13** |
| Under-triage (any) | 1/30 | 5/30 | **4/30** | 0/30 | **0/30** |
| Over-triage (any) | 4/30 | 6/30 | **7/30** | 6/30 | **6/30** |
| Priority exact | 25/30 | 19/30 | **19/30** | 24/30 | **24/30** |
| Cue micro recall | 0.97 | 0.73 | **0.73** | 1.00 | **1.00** |
| Cue micro precision | 0.97 | 0.68 | **0.77** | 0.73 | **0.80** |
| Cue micro F1 | 0.97 | 0.70 | **0.75** | 0.84 | **0.89** |
| Denied/past cues reported live | 0 | 3 | **1** | 3 | **1** |

**The four patterns generator 2.1 targeted**, case by case:

| Pattern | Result |
|---|---|
| Denials ("Nobody is hurt", "There is no fire") | **Fixed.** `fx-022`, `cu-101` and `cu-120` are no longer reported live. |
| Shouting (`fx-018`, "HE IS NOT BREATHING") | **Fixed.** `NOT_BREATHING` is now found. |
| `UNCONSCIOUS` added whenever someone is not breathing | **Partly fixed.** "He's still conscious" (`fx-001`) is now respected. `fx-002`, `fx-011` and `cu-106` still get `UNCONSCIOUS`, at scores 0.59 to 0.99. |
| Spanish family words (`fx-015` "Mi esposo", `cu-115` "Mi hija") | **Not fixed.** "esposo" still scores 0.91 as a child, and "hija" 0.28. About 320 Spanish training calls were not enough to separate the family words. |

**Hybrid priority errors** (these remain after 2.1, or are new):

| Case | Error | Status |
|---|---|---|
| `cu-104`: "He was not breathing earlier but he is breathing now, he's awake and talking" | B1e scores `UNCONSCIOUS` 0.78 on "he's awake and talking", so the hybrid raises P2 to **P0** | New. The worst error in this run: a critical over-triage. The training data has "awake" only as a denial of `UNCONSCIOUS`, yet the model reads it as the cue. |
| `cu-103`: "Someone said there was a fire at the school yesterday" | `FIRE_REPORTED` scored live (0.94), P3 to P2 | New. Gold is P4; the rules already give P3. |
| `fx-008`: a fall on the pavement | `FALL_FROM_HEIGHT`, P2 to P1 | As before. |
| `cu-116`: "two cars crashed" | Hybrid gives P2 | Correct, as before. The rules alone give P3. |

**Reading:** better precision and F1 overall, and B1e on its own now finds
13 of 15 critical cues. Two of the four targeted patterns are fixed, one
partly and one not.

The hybrid still under-triages nothing. Its over-triage is unchanged in
number but different in kind: `cu-104` is now raised to P0.

Milestone ML-9 is where this gets addressed. Fusion v2 (ML layer design §7)
keeps raising priority for a critical cue only the model found, but marks
it "model-only: confirm" for a reviewer. Per-cue calibration and threshold
selection (§6) are what would stop a 0.78 score from counting as a finding.

On 30 cases none of these differences is statistically meaningful.

## B1e calibration on the regression split: a negative result (ML-9)

**Plan.** Train B1e on generator 2.1's **dev** split only, then fit the
temperature and per-cue thresholds (`ntip.ml.calibrate`, #82) on the
**regression** split, whose families the model never saw.

**Run:**
- model `b1e-0.1.0+30718f35865b`
  ([manifest](b1e-0.1.0+30718f35865b-manifest.json)), trained on a Colab T4
  at `fcf9333` on 630 calls;
- [calibration file](b1e-0.1.0+30718f35865b-calibration-regression.json),
  fitted on the 570 regression calls.

Reports, uncalibrated and calibrated:
- [uncalibrated](compare-curated-dev-regression-b1e-0.1.0+30718f35865b.md);
- [calibrated](compare-curated-dev-regression-b1e-0.1.0+30718f35865b-calibrated.md).

| Curated dev + regression (30) | B0 | Hybrid, fusion 2, uncalibrated | Hybrid, fusion 2, **calibrated** |
|---|---|---|---|
| Critical under-triage | 0/13 | 0/13 | 0/13 |
| Under-triage | 1/30 | 1/30 | 0/30 |
| Over-triage | 4/30 | 6/30 | **15/30** |
| Cue precision | 0.973 | 0.923 | **0.439** |
| Cue F1 | 0.973 | 0.947 | **0.605** |

**Calibration made the system much worse. Not adopted.** The reason is the
design of the split, not the calibration method.

- **The two training splits do not share cue codes.** Generator 2.x
  guarantees each code is in *some* training family and in a test family.
  It does not guarantee a family in both dev and regression; the data cards
  show the zeros. So 12 codes exist only in regression families. These
  include `WEAPON_PRESENT`, `ACTIVE_VIOLENCE`, `DROWNING`,
  `TRAFFIC_COLLISION` and `SEIZURE`. The dev-only model never learned them,
  and calibration correctly concluded they could never be proposed at
  precision 0.9. Another 11 codes have no regression family, so they kept
  the default threshold.
- **The critical-recall rule collapses on unseen families.** To find 95%
  of `NOT_BREATHING`, `UNCONSCIOUS` and `OCCUPANTS_TRAPPED` in families
  never trained on, the thresholds fell to 0.06, 0.08 and 0.03, with
  precision 0.30, 0.20 and 0.07. Almost every call then has a critical cue,
  and half the curated calls are over-triaged.
- **Temperature scaling barely helped.** T = 2.04 reduced ECE from 0.029 to
  0.012 on the regression split, but Brier score and AURC were unchanged.
  The scores were already about as well calibrated as a single temperature
  can make them.

**What this shows:**
1. Calibrating per code by held-out family needs every code to appear in
   families on both sides of the split.
2. A recall target for critical cues, fitted on families the model never
   saw, pushes thresholds towards zero. The rule needs a floor, or a
   different target.

**A side result.** The uncalibrated dev-only model with fusion 2 had the
best cue F1 of any hybrid so far (0.947, precision 0.923). That is on 30
cases, with a model that never saw 12 codes; on these cases the rules
supply those codes. It is not evidence that less training data is better.

## ML-9 outcome: calibration and fusion 2 on generator 2.2 (not adopted)

The second attempt, after fixing both causes of the first:
- **Data:** generator 2.2 puts every cue code in dev, regression and test (#84).
- **Floor:** critical thresholds can no longer fall below 0.3 (#85).
- **Model:** B1e `0.1.0+a576fe617662`
  ([manifest](b1e-0.1.0+a576fe617662-manifest.json)), trained on a Colab T4
  at `62a232b` on generator 2.2's **dev** split (930 calls, 31 families).
- **Calibration:** [fitted](b1e-0.1.0+a576fe617662-calibration-regression.json)
  on the **regression** split (870 calls, 29 unseen families).

**The calibration itself is now sound.**
- T = 1.53. On the regression split, ECE fell from 0.016 to 0.005 and Brier
  score from 0.0199 to 0.0190.
- Three cues are never proposed (`HAZARDOUS_ENVIRONMENT`, `MISSING_PERSON`,
  `WEAPON_PRESENT`), against 12 in the first attempt.
- The floor held all three critical thresholds at 0.3. The recall target
  alone would again have set them below 0.01.

**On curated dev + regression (30 cases)**
([uncalibrated](compare-curated-dev-regression-b1e-0.1.0+a576fe617662.md),
[calibrated](compare-curated-dev-regression-b1e-0.1.0+a576fe617662-calibrated.md)):

| | B0 | Hybrid fusion 1 | Hybrid fusion 1, calibrated | Hybrid fusion 2 | Hybrid fusion 2, calibrated |
|---|---|---|---|---|---|
| Under-triage | 1/30 | 0/30 | 0/30 | 1/30 | 1/30 |
| Over-triage | 4/30 | 6/30 | 8/30 | 4/30 | 4/30 |
| Cue precision | 0.973 | 0.861 | 0.787 | 0.973 | 0.973 |

**On the 870 regression calls**
([report](compare-generated-regression-b1e-0.1.0+a576fe617662.md); the
uncalibrated model, which never saw these families):

| | B0 | B1e only | Hybrid fusion 1 | Hybrid fusion 2 |
|---|---|---|---|---|
| Critical under-triage (labelled P0) | 82/249 | 128/249 | **41/249** | 81/249 |
| Under-triage (any) | 313/870 | 354/870 | **123/870** | 312/870 |
| Over-triage (any) | 48/870 | 60/870 | 80/870 | 56/870 |
| Priority exact | 509/870 | 456/870 | **667/870** | 502/870 |
| Cue precision / recall | 0.961 / 0.699 | 0.882 / 0.573 | 0.893 / 0.850 | 0.946 / 0.700 |

**Findings:**
1. **Calibration does not help the system.** Under fusion 2 it changes
   nothing on curated. Under fusion 1 it adds two over-triaged calls and
   lowers precision. Calibration is **skipped for now**, as agreed
   beforehand (DDL-022).
2. **Fusion 2 fails its own adoption gate.** Its definition of "critical"
   is the three codes that make a call critical on their own. Many P0
   calls, however, are a *high* cue plus a child or several victims:
   - "my son… is cutting themselves";
   - "can't catch their breath… two people hurt".

   The rules miss those phrasings and B1e finds them. Fusion 2 then holds
   them back as non-critical suggestions, so the call loses its P0. Critical
   under-triage doubles from 41 to 81 of 249, which is no better than the
   rules alone (82). The 30 curated cases could not show this: there, fusion
   2 looked best. **Fusion 2 is not adopted** (DDL-022).
3. **Fusion 1 with B1e is the strongest result so far.** On families the
   model never saw, it halves critical under-triage against the rules (82 to
   41 of 249) and cuts all under-triage by 61% (313 to 123). Over-triage
   rises from 48 to 80. Labels are generator-intended, so this is a stress
   test, not accuracy.
