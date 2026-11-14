# Model card: B2 (`b2-claude-structured`)

| | |
|---|---|
| Model | Claude Opus 5.5 (`claude-opus-5-5`) through the Anthropic Messages API, with a strict JSON-schema structured output |
| Adapter | `backend/src/ntip/ml/b2.py`, prompt version 1.0.0; model version `1.0.0+claude-opus-5-5` |
| Role | Baseline B2 in design v1.2 §3A.4: a zero-shot structured-output language model to compare with the rules (B0) and the small learned model (B1) |
| Settings | Adaptive thinking, effort `medium`, `max_tokens` 16000, 30 s timeout, 2 retries, server-side refusal fallback enabled |

## Data governance

B2 sends transcript text to an external provider. It is **off unless
`NTIP_B2_ALLOW_EXTERNAL=1` is set**, and the platform holds only synthetic
data. Real emergency-call data must never be sent without authorisation, a
privacy review and contractual safeguards (design v1.2, §3B.6).

## How output is grounded

The model returns, per cue, a code, the message id, a **verbatim quote**,
polarity, tense and a self-estimated confidence. It never supplies character
offsets: the adapter finds the quote in the message by exact match. A quote
that does not appear verbatim is passed on as ungrounded, and verification
rejects and counts it; nothing is repaired. Every call's exact request and
response is stored (ModelOutput), so incidents can be audited and replayed
from the recorded output, because the model is not guaranteed to be
deterministic (§3A.9).

## Prompt-injection resistance

The transcript is placed in a delimited `<transcript>` data block, and the
system prompt states that its contents are data and never instructions. The
output schema only admits known cue codes and the request's own message ids,
and a cue still has to be grounded and verified before it can affect anything.

## Known limitations

- Self-reported confidence is not calibrated.
- Results depend on the hosted model version; recorded outputs, not fresh
  calls, are the reproducible artefact.
- Costs money per call and adds network latency; in the pipeline it runs under
  the same timeout and fallback rules as any model.

## Evaluation status

**Not yet run.** Running B2 over the evaluation sets calls a paid external API,
so it needs the project owner's authorisation. B2 is zero-shot and nothing was
tuned on any split, so the first run covers every split, test included, with
prompt 1.0.0 frozen as committed. The plan, measures and cost estimate (about
$20 to $45) are in the [ML layer design](../design/ml-layer-design-v1.0.md),
section 5.4 (milestone ML-7).

    NTIP_B2_ALLOW_EXTERNAL=1 python -m ntip.evaluation.compare \
        --dataset ../data/eval/curated.jsonl \
        --split dev --split regression --split test --with-b2

No B2 performance figures exist in this repository until that run is made and
its report committed.
