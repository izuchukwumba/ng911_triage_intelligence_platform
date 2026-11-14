# Model card: B1e (`b1e-encoder`)

| | |
|---|---|
| Model | `distilbert/distilbert-base-multilingual-cased` (Apache-2.0, 6 layers, about 134 million parameters), pinned to revision `45c032ab32cc946ad88a166f7cb282f58c753c2e`, plus one linear scoring layer |
| Version | `0.1.0+<12-hex weights digest>`; the digest covers every file in the model directory |
| Code | `backend/src/ntip/ml/b1e.py` (inference), `backend/src/ntip/ml/train_b1e.py` (training), [`notebooks/train_b1e.ipynb`](../../notebooks/train_b1e.ipynb) (training on Colab or Kaggle) |
| Role | The platform's **primary ML model** (DDL-020; [ML layer design](../design/ml-layer-design-v1.0.md) §5.3). Runs locally on CPU; no call content leaves the machine |

## What it does

Scores each clause of a call with two outputs per cue code:

- **live**: the clause reports the cue as happening now;
- **absent**: the clause mentions the cue but denies it, or places it in the
  past or a hypothetical.

Case labels say which cues a call contains, not which clause, so training is
multiple-instance: a call's score is its best clause's score. The absent
output teaches the encoder the difference between "the kitchen is on fire"
and "there is no fire", which B1's n-grams cannot learn.

Only live cues become candidates. The best clause is the quoted evidence, so
every candidate is grounded in the source and passes verification. The
thresholds are the same as B1's and were declared in advance: a candidate at
0.5 or more, an abstention from 0.35 to 0.5.

## Training

- **Data:** `data/eval/generated-1.0.0-seed42.jsonl`, **dev and regression
  splits only** (300 synthetic calls, generator-intended labels). Test data is
  never read by the training code.
- **Fixed in advance:**
  - 6 epochs;
  - batches of 8 calls;
  - AdamW, learning rate 5e-5, weight decay 0.01;
  - 10% linear warm-up;
  - clauses truncated to 64 tokens;
  - seed `20261113`.

  There is no early stopping on evaluation data.
- **Hardware:** a free Colab or Kaggle T4 GPU trains it in minutes; a laptop
  CPU also works, more slowly. GPU training is not bit-for-bit repeatable, so
  each run's weights digest identifies that run.

## Reproducibility and integrity

Weights are not committed to git. Each training run writes a directory with
`manifest.json`, which records:

- the base model and revision;
- the training data digest;
- hyperparameters and seed;
- library versions and hardware;
- the git commit;
- the sha256 of every file.

`B1eModel` refuses a directory whose files, cue codes or digest do not match
its manifest. Inference on CPU is deterministic: the same input gives the
same scores.

## Using it

```sh
# evaluation alongside B0 and B1 (development splits only)
python -m ntip.evaluation.compare --dataset ../data/eval/curated.jsonl \
    --split dev --split regression --with-b1e path/to/b1e

# as the inference service behind the platform
NTIP_MODEL=b1e-encoder NTIP_B1E_PATH=path/to/b1e \
    uvicorn ntip.ml.service:create_inference_app --factory --port 8100
```

Needs the `ml-encoder` extra (`uv sync --extra ml-encoder`).

## Known limitations

- **Version 0.1 covers cue extraction only.** The heads for cue status spans,
  location components and victim count (ML layer design §5.3) need
  span-level training data from generator 2.0.
- **Absent cues are learned, not reported.** The absent output shapes the
  encoder, but only live cues are returned. The rules stay the reference for
  negation and tense.
- **Small, synthetic training set:** 300 calls from 10 of the generator's 17
  scenario families, with generator-intended labels. Cues that occur only in
  held-out families are unlikely to be learned.
- **Scores are not calibrated** (`calibrated: false`); calibration is milestone
  ML-9.
- Research only, synthetic text only. Not a clinical or dispatch model.

## Evaluation

No results are published yet. They will be added under
`docs/evaluation/results/` from the first training run, on the curated dev and
regression splits. The held-out test split is reserved for the pre-registered
frozen comparison (milestone ML-10).
