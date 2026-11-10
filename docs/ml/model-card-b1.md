# Model card: B1 (`b1-tfidf-logreg`)

| | |
|---|---|
| Model | One logistic-regression classifier per cue over character (2–5) and word (1–2) n-gram TF-IDF features |
| Library | scikit-learn (BSD-3-Clause) |
| Version | `1.0.0+<12-hex fingerprint>`; the fingerprint is a digest of the training data, hyperparameters, seed and scikit-learn version |
| Code | `backend/src/ntip/ml/b1.py` |
| Role | Baseline B1 in design v1.2 §3A.4: a small task-specific model to compare against the rules (B0) and to use in `ml_shadow` / `hybrid_review` |

## Intended use

Research only, on **synthetic** text. B1 proposes *candidate* cues with quoted
evidence. Candidates are verified against the source, never override a rules
finding, and a serious cue found only by B1 always requires human confirmation
(engine policy P-REVIEW-006). It is not a clinical or dispatch model.

## Training data

- `data/eval/generated-1.0.0-seed42.jsonl`, **dev and regression splits only**
  (300 generated cases, 10 of the 17 scenario families).
- Labels are generator-intended (from the labelling rubric, not checked by a
  person).
- Training happens deterministically when the model is loaded (seeded,
  `liblinear` solver). No weight files are distributed.

Not used for training: any `test` split, and the entire curated dataset.

## Inference

Each clause of each message is scored. A cue's score is its best clause
(max pooling), and that clause is the quoted evidence. Pre-declared
thresholds: a candidate at score ≥ 0.5, an abstention between 0.35 and 0.5.
Every candidate is reported as `affirmed`/`current`; B1 does not model the
caller's certainty or tense.

## Known limitations

- **Only cues seen in training families are learnable.** Codes that appear only
  in held-out families (for example stroke symptoms, breathing difficulty and
  violence in the generated test families) are not predicted. Measuring this
  generalisation gap is the point of the family split.
- **Correlated labels:** in the training families, `NOT_BREATHING` and
  `UNCONSCIOUS` always occur together, so B1 cannot separate them.
- **Scores are not calibrated probabilities** (`calibrated: false`).
  Calibration is measured in the evaluation reports, not assumed.
- No model of negation scope or tense beyond what the n-grams capture; the
  rules baseline remains the reference for denied and past cues.
- English and a little Spanish only; synthetic phrasing only.

## Evaluation

See `docs/evaluation/results/` for B0, B1 and hybrid comparisons on data B1
never saw, including critical-cue sensitivity and calibration.
