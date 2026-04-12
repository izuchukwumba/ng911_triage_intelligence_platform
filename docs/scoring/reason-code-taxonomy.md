# Reason Code Taxonomy

Every incident scored by the prioritization engine includes a `score_breakdown` array. Each entry in that array carries a `rule` field containing a reason code — a stable string identifier for a scoring rule or penalty that contributed to the final priority score.

This document is the authoritative reference for all reason codes. Codes are grouped by category.

---

## Domain Base Score

Applied to every incident as the starting score before any indicator weights.

| Code | Trigger | Contribution | Description |
|------|---------|-------------|-------------|
| `DOMAIN_BASE` | Always — one per incident | Varies by domain | Starting score for the incident's classified domain. EMS: +0.22, fire/hazmat: +0.20, police: +0.15, other: +0.10, unknown: +0.08 |

---

## Life-Threat Indicators

High-weight indicators that signal immediate risk to life. Any one of these, combined with the domain base, can push a score into P0 territory.

| Code | Trigger | Weight | Description |
|------|---------|--------|-------------|
| `NOT_BREATHING` | Keywords: "not breathing", "stopped breathing", "no estaba respirando" (es) | +0.32 | Patient is reported not breathing. Highest-weight single indicator. Negation filtering is applied — "he started breathing again" does not fire this code. |
| `CARDIAC_EVENT` | Keywords: "cardiac arrest", "heart attack", "ataque al corazón" (es), "no pulse" | +0.30 | Cardiac arrest or heart attack reported. Often co-fires with `NOT_BREATHING`. |
| `VICTIM_UNCONSCIOUS` | Keywords: "unconscious", "unresponsive", "won't wake up", "passed out" | +0.28 | Victim is reported unconscious or unresponsive. |
| `ACTIVE_BLEEDING` | Keywords: "bleeding", "blood", "hemorrhage", "lot of blood" | +0.22 | Active or severe bleeding reported. |
| `IMMEDIATE_MEDICAL_EMERGENCY` | Keywords: "emergency", "please help", "hurry", combined with medical domain | +0.15 | Catch-all for high-urgency EMS calls where a specific indicator is not extractable but the call is clearly time-sensitive. |

---

## Violence and Threat Indicators

Indicators that signal physical danger or active threat.

| Code | Trigger | Weight | Description |
|------|---------|--------|-------------|
| `WEAPON_PRESENT` | Keywords: "gun", "knife", "weapon", "shot", "armed", "arma" (es) | +0.25 | A weapon is reported present at the scene. Fires regardless of whether it has been used. |
| `ACTIVE_VIOLENCE` | Keywords: "fighting", "hitting", "attacking", "shooting", combined with active tense | +0.20 | Violence is ongoing or was just reported. Distinguished from past-tense reports by context scoring. |

---

## Medical Condition Indicators

Moderate-weight medical indicators below the life-threat threshold.

| Code | Trigger | Weight | Description |
|------|---------|--------|-------------|
| `RESPIRATORY_DISTRESS` | Keywords: "can't breathe", "difficulty breathing", "trouble breathing", "no puede respirar" (es) | +0.18 | Patient is conscious but experiencing significant breathing difficulty. Lower than `NOT_BREATHING` because the patient is still breathing. |
| `SEIZURE` | Keywords: "seizure", "convulsing", "shaking uncontrollably" | +0.16 | Active or recent seizure reported. |

---

## Scene Severity Indicators

Indicators tied to the scale or danger level of the scene rather than a specific victim's condition.

| Code | Trigger | Weight | Description |
|------|---------|--------|-------------|
| `FIRE_SPREADING` | Keywords: "spreading", "out of control", "engulfed", "flames spreading" | +0.18 | Fire is spreading or described as uncontrolled. |
| `HAZARDOUS_ENVIRONMENT` | Keywords: "gas leak", "chemical", "hazmat", "toxic", "fumes" | +0.16 | A hazardous material or environment is reported. |
| `MULTIPLE_VICTIMS` | Keywords: "multiple people", "several injured", "more than one", "everyone is hurt" | +0.14 | Multiple victims reported at the scene (separate from the victim count multiplier). |
| `CHILD_INVOLVED` | Keywords: "child", "baby", "infant", "kid", "toddler" | +0.12 | A child or infant is among the victims or is at risk. |

---

## Caller Context Indicators

Indicators derived from how the caller reports the incident, not the incident itself.

| Code | Trigger | Weight | Description |
|------|---------|--------|-------------|
| `CALLER_HIGH_DISTRESS` | Stress detection score ≥ HIGH threshold | +0.08 | Caller is exhibiting signs of extreme stress: repeated phrases, all-caps, exclamation marks, sentence fragmentation. Does not independently elevate tier but adds incremental weight. |

---

## Victim Count Multiplier

Applied when victim count is extractable from the transcript and exceeds one.

| Code | Trigger | Contribution | Description |
|------|---------|-------------|-------------|
| `VICTIM_COUNT_MULTIPLIER` | Extracted `victim_count_estimate` > 1 | +0.04 × (count − 1), capped at +0.20 | Each additional victim beyond the first adds 0.04 to the score. Two victims: +0.04. Five victims: +0.16. Cap is reached at six or more additional victims. |

---

## Penalty Codes

Penalty codes reduce the score when data quality is low. They are always negative contributions.

| Code | Trigger | Weight | Description |
|------|---------|--------|-------------|
| `LOW_LOCATION_CONFIDENCE` | `dispatchable_location_score` < 0.30 | −0.08 | The reported location cannot be reliably used for dispatch routing. Vague descriptions ("somewhere downtown", "near a gas station") or no location at all trigger this penalty. Does not suppress life-threat indicators from reaching P0. |
| `LOW_PARSE_CONFIDENCE` | `incident.confidence` < 0.50 | −0.06 | The transcript parser could not confidently classify the incident. May occur with very short transcripts, ambiguous language, or unsupported input formats. |
| `POSSIBLE_PRANK` | Keywords: "prank", "joke", "fake", "filming", "YouTube", "just kidding" | −0.40 | Strong signal that the call is not genuine. This is the largest single penalty and is designed to suppress prank calls below P4 in most circumstances. Still requires human review. |

---

## Negation Filtering

All indicator keywords are subject to negation filtering before being converted to reason codes. The negation filter looks at the 8 tokens preceding each keyword match and blocks the indicator if a negation word ("not", "never", "no", "isn't", "wasn't", etc.) is found within that window without an intervening sentence boundary.

Examples:
- "he is not breathing" → `NOT_BREATHING` fires ← negation is before the concept, not the indicator
- "he stopped breathing" → `NOT_BREATHING` fires
- "he is breathing on his own" → `NOT_BREATHING` does NOT fire
- "no weapon was found" → `WEAPON_PRESENT` does NOT fire

The filter is conservative: when uncertain, it allows the indicator through. False positives are corrected at the operator review stage.

---

## Code Stability Contract

Reason codes are part of the public API surface. Once a code appears in a stored incident record, it must remain decodable by all future versions of the platform.

Rules:
- Codes are never renamed or removed — only deprecated (kept in decoder, removed from active firing)
- New codes are additive — they appear in new incident records without affecting existing ones
- `scoring_version` on the audit record identifies which set of codes was active when the incident was scored

When a code's weight changes, the scoring version is bumped. The old incident records are not re-tagged — replay is the mechanism for comparing old vs. new scoring.
