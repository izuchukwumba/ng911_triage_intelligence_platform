# ML layer design (v1.1)

**For:** engineers working on the platform's ML layer, and the project owner
deciding what to fund.
**Status:** proposed. Nothing in sections 4 to 10 is built unless it says so.
**Relationship to design v1.2:** this document details §3A (Machine Learning
Intelligence Layer). It does not replace it. Where it changes a v1.2
requirement, the change is recorded in the decision log before the work
merges.
**Changes in v1.1:** B1e, a small model run locally, is the primary ML path;
the hosted language model B2 becomes an optional comparison that no
milestone depends on (DDL-020).

## 1. Why a separate design

Design v1.2 §3A sets the ML layer's research question, safety rules and
milestones ML-1 to ML-5. The first four milestones are met
([traceability matrix](../traceability-matrix.md)), but they were met with
the smallest thing that could pass each gate. Section 2 says plainly what
that leaves out. The remaining ML work is larger than everything done so far,
and needs its own design before it starts.

## 2. Where the ML layer stands

### What exists

| Component | State |
|---|---|
| B0 rules parser | Complete. The permanent baseline and fallback |
| B1 `b1-tfidf-logreg` | One logistic regression per cue over character and word n-grams; trained deterministically at load time on generated dev and regression data ([model card](../ml/model-card-b1.md)) |
| B2 `b2-claude-structured` | Adapter, prompt 1.1.0 and tests; **never run on the evaluation sets** ([model card](../ml/model-card-b2.md)) |
| Inference contract and verification | Quotes are matched to the source; ungrounded output is rejected and counted |
| Fusion and modes | `rules_only` (default), `ml_shadow`, `hybrid_review`; a model can raise but never lower; a model-only serious cue needs human confirmation |
| Inference service | Separate HTTP service with timeout and fallback |
| Evaluation | Per-cue precision, recall and F1; critical misses reported separately; Brier score, ECE, risk-coverage; slices; one ablation; bootstrap intervals; reproducibility manifests |
| Data | 50 curated cases (author-labelled), 510 generated cases (generator-labelled), split by scenario family |

### What is missing, measured against §3A

| §3A asks for | Gap |
|---|---|
| §3A.1 task 1: incident type, victim count, temporal facts by ML | Only **cues** are extracted by a model. Domain, victim count and incident type come from the rules alone |
| §3A.1 task 3: location entity extraction by ML | Rules only. No model proposes address components |
| §3A.1 task 4: uncertainty estimation and selective abstention | B1's thresholds are fixed by hand (0.35 and 0.5). Calibration is measured (ECE 0.07 to 0.10) but never corrected |
| §3A.4 B1: "a small encoder or sequence-labeling model" | B1 is an n-gram linear model. It has no notion of negation or tense, and cannot label spans |
| §3A.4 B2 evaluated | Not run. Now optional (DDL-020, section 5.4) |
| §3A.4 B3 | Not built; gated on data quality |
| §3A.7 annotation manual with evidence spans, negation scope, location components, uncertainty class | The [labelling guide](../evaluation/labelling-guide.md) records which cues are present or absent, but no spans, statuses or location components |
| §3A.7 independent annotation | None yet; protocol ready ([annotation protocol](../research/annotation-protocol.md)) |
| §3A.7 held-out **challenge set** of novel compositions | Does not exist. The generated test families are held out, but they come from the same generator |
| §3A.8 ablations of provenance validation, rules fusion, location handling | Only the abstention ablation is run |
| §3A.8 "does fusion help?" with confidence intervals | Reported, but hybrid costs precision (curated test: 1.00 to 0.79) and doubles over-triage. The fusion policy has never been tuned |

### What the current results say

On the curated test split, hybrid fusion of B0 and B1 removed both of B0's
critical under-triages (2/9 to 0/9), at the cost of more over-triage.
B1 alone is not usable: its recall falls to 0.27 on scenario families it
never saw. So far, the evidence supports "a model as a second reader that
catches what the rules miss", not "a model that reads better than the rules".
The work below tests whether a better model and better fusion change that.

## 3. Goals and non-goals

**Goals**

1. Cover all four §3A.1 tasks with at least one model, not just cue
   recognition.
2. Replace hand-set thresholds with calibrated scores and abstention chosen
   from data.
3. Make a small encoder (B1e), trained on the project's data and run
   locally on CPU, the primary model, and evaluate it against B0 and B1 under
   one pre-registered protocol.
4. Recover hybrid precision without losing the critical-recall gain.
5. Make the labels good enough that B3 is worth building: spans,
   statuses, location components, independent annotation, a challenge set.

**Non-goals** (unchanged from v1.2)

- No model decides, dispatches, or lowers a priority.
- No real call data. Everything stays synthetic until v1.2 §3B.6's
  conditions are met.
- No claim of novelty for fine-tuning alone (§3A.4).

## 4. Data

### 4.1 Label schema 2.0

`CaseLabels` gains optional fields, so existing records stay valid:

| Field | Content |
|---|---|
| `cue_annotations` | For each mentioned cue: code, status (`affirmed`, `uncertain`, `negated`, `historical`, `hypothetical`, `retracted`), message index, character span of the evidence |
| `location_components` | Spans for house number, street, unit, intersection, landmark, locality |
| `case_uncertainty` | `clear`, `some_doubt`, `cannot_tell` |
| `annotations` | Per-annotator labels and the adjudication reason, when `label_source` is `adjudicated` |

`cues` and `absent_cues` stay and are derived from `cue_annotations` when
it is present, so every existing metric keeps working. The labelling guide
becomes v2.0, aligned with the annotation protocol.

### 4.2 Datasets

| Dataset | Content | Labels | Use |
|---|---|---|---|
| `curated` 2.0 | The 50 existing cases plus about 150 new hand-written ones, 40 or more families | Author first, then adjudicated (annotation protocol) | Dev, regression, test, as now |
| `generated` 2.0 | Generator 2.0 (section 4.3), about 2,000 cases | Generator-intended, with spans | Training (dev and regression families only) and stress tests |
| `challenge` 1.0 (new) | About 100 cases written *after* the models are frozen, by someone other than the person tuning them where possible | Adjudicated | Reported once per frozen release; never used for development |

The challenge set targets compositions none of the families contain:

- two incidents in one call;
- a caller who corrects themselves twice;
- third-party relays ("my neighbour texted that…");
- heavy speech-recognition noise;
- code-switching mid-sentence;
- prompt-injection text inside the transcript;
- critical cues phrased only indirectly ("his lips are going blue");
- long transcripts with the critical cue in the last message.

Every dataset gets a **dataset card**: provenance, label source, splits,
family list, known biases, digest. As now, `load_dataset` rejects a family
that appears in two splits.

### 4.3 Generator 2.0

**Built** (`ntip.generator.generate_v2`, `data/eval/generated-2.0.0-seed42.jsonl`):
66 families, 279 phrasings, 32 cue codes each in training and test families,
evidence spans, speech-recognition noise. Multiple speakers and longer
multi-message incidents are not built yet.

**Generator 2.1** (`ntip.generator.generate_v21`,
`data/eval/generated-2.1.0-seed42.jsonl`): generator 2.0 plus four
additions, each closing a gap found in B1e's curated-dev errors. They are:
- denials of cues that are not part of the call;
- an all-capitals variant;
- `NOT_BREATHING` without `UNCONSCIOUS` in training;
- Spanish family words drawn at random.

See `data/eval/README.md`.

- Emits spans and statuses with each case, so generated data can train span
  models.
- New perturbations: speech-recognition errors (homophones, dropped words,
  no punctuation), multiple speakers, longer multi-message incidents,
  indirect symptom descriptions.
- Template wording reviewed for stereotypes and for uneven error rates across
  language varieties (§3A.7).
- Remains seeded and reproducible: a test fails if a committed file no longer
  matches the generator.

### 4.4 Annotation tooling

- `python -m ntip.evaluation.annotation export`: blinded, per-annotator
  shuffled workbooks (annotation protocol §7).
- `python -m ntip.evaluation.annotation import`: reads returned workbooks,
  validates them and resolves spans from quoted evidence.
- `python -m ntip.evaluation.agreement`: the agreement report (annotation
  protocol §8).

## 5. Models

### 5.1 B0: rules (unchanged)

The reference for negation and tense, and the fallback whenever a model
fails. It is not retuned against adjudicated test labels.

### 5.2 B1: n-gram baseline (kept)

Kept as the cheap baseline. It does not change, so every later model has a
stable point of comparison.

### 5.3 B1e: small encoder, multi-task (new, primary)

The model §3A.4 actually describes, and the platform's **primary ML path**
(DDL-020). It is what a real deployment could run: a few milliseconds per
call on an ordinary CPU, no cost per call, no call content leaving the
machine, and the same output every time from weights pinned by hash.

| | |
|---|---|
| Backbone | An openly licensed English (preferably also Spanish) encoder of roughly 20 to 120 million parameters. Candidates are compared on licence, size and dev-set results; the choice and its licence are recorded in a decision-log entry |
| Heads | (1) cue presence per clause; (2) cue status (six classes, as in the label schema); (3) token tagging for location components and evidence spans; (4) victim-count class (none, 1, 2 to 5, more than 5, unknown) |
| Training data | Generated 2.0 dev and regression families, plus curated dev. Never test or challenge data |
| Output | The existing inference contract: candidates with quoted evidence, status, temporality and a score; abstentions |
| Runtime | CPU inference; target p95 under 150 ms per incident on the reference machine. A target, reported as measured |
| Reproducibility | Training script with a seed, a pinned dependency set and a manifest. The manifest records the data digest, base-model hash, hyperparameters and weight hash. Weights are not committed; they are rebuilt from the manifest or downloaded and checked against the hash |

Dependencies go in a new optional extra (`ml-encoder`) so the core platform
and CI stay light. CI trains a tiny configuration only, to check the code
path; full training is run by hand and its manifest committed.

### 5.4 B2: hosted language model (optional comparison)

B2 sends the transcript to a hosted language model. No emergency
communications centre would run that on real calls: call content would leave
the building, every call would cost money and add seconds, and the hosted
model can change underneath the platform. Design v1.2 §3B.6 already forbids
it for real data. B2 is therefore **not on the platform's path** (DDL-020):

- the code stays, off by default, with its tests;
- no milestone, gate, default or fusion policy depends on it;
- it is run **at most once**, on synthetic data, only if the project owner
  approves the cost.

**What one run would add.** A zero-shot ceiling: how well a strong general
model does with no training on this data. It would show whether B1e's
remaining errors come from the data or from the model's size, and how B2
handles denial, past tense and uncertainty. Ungrounded quotes would measure
fabrication.

**Protocol, if run.** Prompt 1.1.0, as committed, on every split of both
datasets, once, before anyone looks at an output. Nothing was tuned on any
split, so this is an honest held-out result. The prompt is not developed
further.

**Cost estimate.** Claude Opus 5.5 is priced at $4 per million input tokens
and $20 per million output tokens. A case is about 1,000 input tokens and 700
to 2,200 output tokens, about $0.02 to $0.05 per case: roughly **$12 to $30**
for the 560 cases once. A 5-case trial measures real token use first, and the
report records the tokens actually used.

**Alternative without per-call cost.** The same comparison can be made with
an open-weight language model run locally, which also keeps the data on the
machine. It is slower to set up and needs more memory than the reference
machine may have.

### 5.5 B3: domain-adapted model (gated)

Starts only when all of these hold:

1. Adjudicated labels exist for at least 200 cases, and cue agreement (kappa)
   is at least 0.6 (annotation protocol §8).
2. B1e results are published.
3. There is a documented gap B3 is meant to close, for example "B1e misses
   indirect phrasing of critical cues".

Likely forms: B1e fine-tuned further on adjudicated dev data, or a small
open-weight generative model adapted with low-rank adapters. Licence,
training-data rights, compute, model size and hash are recorded as §3A.4
requires.

## 6. Calibration and abstention

Today a model's score is used as given, against thresholds set by hand. The
change:

1. **Calibrate per cue on development data only.** Temperature scaling for
   B1e. Isotonic regression where there is enough data, with cross-fitting
   because dev data is small.
2. **Choose abstention from the risk-coverage curve.** For each cue, choose the
   threshold that keeps selective risk under a pre-declared level on dev data.
   For critical cues, choose instead for a pre-declared recall, because a
   missed critical cue costs more than a false one.
3. **Report calibration on held-out data**, ECE and Brier with intervals,
   before calling any score calibrated. Until then the contract keeps
   `calibrated: false` and the dashboard labels scores as uncalibrated.
4. The calibration maps and thresholds are versioned artefacts, recorded in
   the model manifest and the replay envelope.

## 7. Fusion v2

Hybrid fusion today adds every verified model cue. That catches B0's critical
misses but halves precision. Proposed policy:

| Situation | Effect on priority | Shown to the reviewer |
|---|---|---|
| Rules and model agree | As now | As now |
| Critical cue found by the model only | **Raises** priority and requires confirmation (unchanged: never risk a critical miss) | "Model-only: confirm" |
| Non-critical cue found by the model only, above its calibrated threshold | **No change** to priority | Listed as a suggestion with its evidence |
| Model abstains | No change | Listed as an open question |
| Model says negated or past, rules say current | No change (rules stay the reference for negation) | Disagreement flagged for review |
| Rules say negated or past, model says current, critical cue | Raises priority and requires confirmation | Disagreement flagged |

The rule that no model lowers a priority stays (§3A.6). The policy is
versioned like a ruleset and recorded in every assessment. It is adopted only
if, on dev and regression data, it keeps critical under-triage at zero and
recovers precision. The decision and its numbers go in a decision-log entry.

## 8. Evaluation protocol

1. **Pre-registration in the repository.** Before any test or challenge run, a
   file in `docs/evaluation/preregistration/` fixes:
   - the systems compared, with their frozen versions and hashes;
   - the metrics, the slices and the primary comparison;
   - the pass and fail conditions, as in §3A.8.

   The run's manifest records that file's digest.
2. **Test and challenge data are run once per frozen release.** A second run
   on the same data is allowed only to reproduce, never to tune.
3. **Paired comparisons.** McNemar's test for critical misses and for
   correct versus incorrect priority between two systems on the same cases.
   Paired bootstrap intervals for differences in F1, sensitivity and
   over-triage.
4. **Slices:**
   - negation;
   - past and hypothetical;
   - uncertainty;
   - hearsay;
   - Spanish;
   - misspelling and speech-recognition noise;
   - missing and conflicting location;
   - multiple victims;
   - children;
   - challenge composition type.
5. **Ablations** (§3A.8):
   - without abstention (exists);
   - without span verification;
   - without rules fusion (model only);
   - without calibration;
   - without location handling.
6. **Cost and latency** for every system: p50 and p95, tokens and dollars
   for B2 if it is run, CPU time for B1e.
7. **Reports** keep the existing format: JSON and Markdown, failures listed,
   denominators and intervals, label source stated. Results against author,
   generator and adjudicated labels are reported separately, never pooled.

## 9. Engineering changes

| Change | Where |
|---|---|
| Label schema 2.0 and dataset cards | `ntip.evaluation.dataset`, `data/eval/` |
| Annotation export, import and agreement | `ntip.evaluation.annotation`, `ntip.evaluation.agreement` |
| Generator 2.0 | `ntip.generator` |
| Span-level metrics (exact and overlap F1) and status accuracy | `ntip.evaluation.metrics` |
| B1e training, manifest and adapter | `ntip.ml.b1e`, `ntip.ml.train`, `models/manifests/` |
| Calibration maps and threshold selection | `ntip.ml.calibrate`; applied in `ntip.ml.verify` |
| Location-component and victim-count candidates in the contract | `ntip.ml.contract` (schema minor version bump; additive) |
| Location candidates from models feed L1 to L3, never marked validated | `ntip.location` |
| Fusion policy v2, versioned | `ntip.ml.fusion`, `rulesets/` |
| Paired statistics, pre-registration digest in manifests | `ntip.evaluation` |
| **RP-E1:** study build for the explanation study (score-only display, participant ids, per-trial timing), off unless explicitly enabled | `apps/dashboard`, `ntip.api` ([research protocol](../research/research-protocol.md) §4) |

## 10. Safety

The rules in v1.2 §3A.6 all still apply. New hazards:

| Hazard | Control |
|---|---|
| A retrained or recalibrated model silently changes behaviour | Every model, calibration map and fusion policy is versioned and pinned in the replay envelope; the regression safety gate runs on each |
| Calibration fitted on too little data looks better than it is | Cross-fitting on dev; held-out ECE reported with intervals; `calibrated` stays false until shown |
| Fusion v2 suppresses a non-critical cue that mattered | Suppressed suggestions are still shown; the gate is checked on every cue, not only critical ones |
| Model-proposed address parts are treated as verified | They enter location handling as reported candidates and go through the same L1 to L3 checks; a model can never set `validated` |
| Prompt-injection text in a transcript | Challenge set includes it; B1e cannot follow instructions, and B2, if run, is limited by its output schema and span verification; results reported |
| Training data leaks test families | Family-level split check at load time; manifests record training data digests; the test set is never read by training code |

New safety-case claims are added when each piece merges.

## 11. Milestones

| Milestone | Delivers | Gate | Depends on |
|---|---|---|---|
| **ML-6** Data foundations | Label schema 2.0; annotation tooling; dataset cards; span metrics | Existing reports reproduce unchanged; annotation workbooks round-trip | None |
| ML-7 (optional) B2 comparison | B2 prompt 1.1.0 on every split, once | Report published, including failures | Owner's spending authorisation; nothing depends on it |
| **ML-8** B1e | Encoder model, manifest, adapter, results on dev and regression | Beats B1 on dev cue F1 without lowering critical recall; p95 within target, or the miss reported | Generator 2.0 |
| **ML-9** Calibration and fusion v2 | Calibrated scores, chosen thresholds, fusion policy v2 | Critical under-triage stays 0 on regression; precision recovered against current hybrid; decision-log entry | ML-8 |
| **ML-10** Frozen comparison | Pre-registered test and challenge run of B0, B1, B1e and hybrids (B2 too, if ML-7 was run) | Published with paired statistics, slices, ablations; ML-4 gate re-checked | ML-8, ML-9; challenge set |
| **ML-11** Adjudicated re-evaluation | ML-10 repeated against adjudicated labels; author-versus-adjudicated label differences | Published | Annotation round |
| **ML-12** B3 (gated) | See section 5.5 | Its own pre-registered comparison | ML-11 and the section 5.5 conditions |

ML-6 and ML-8 can start now; no milestone on the main path needs a
spending decision.

## 12. Decisions needed from the project owner

1. **Optional B2 run:** whether to spend about $12 to $30 on the one-off
   comparison in section 5.4. Nothing depends on it.
2. **Compute for B1e:** a small encoder trains on a laptop CPU in hours;
   a GPU (local or rented, roughly a few dollars per training run) makes
   iterating practical. Choose one.
3. **Annotator and reviewer compensation**
   ([annotation protocol](../research/annotation-protocol.md) §10,
   [research protocol](../research/research-protocol.md) §9).
4. **Repository licence**, which must be compatible with the chosen encoder's
   licence (open question 8).

## 13. Open questions

- Does the encoder need to handle Spanish from the start, or is a separate
  Spanish evaluation slice enough for now?
- Should the challenge set be written by an annotator rather than by the
  author, to keep it fully independent of development?
- Is the zero-shot comparison worth making at all, and if so with B2 or
  with a locally run open-weight model (section 5.4)?
