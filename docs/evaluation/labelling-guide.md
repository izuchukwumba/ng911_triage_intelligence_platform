# Labelling guide (v2.1)

How to label a synthetic case in `data/eval/*.jsonl` so that labels are
consistent and can be checked by a second annotator (design v1.2, §3A.7).
Labels describe **what was reported**, not what is medically or operationally
true.

## 1. Cues (`labels.cues`, `labels.absent_cues`)

List every cue from the table below that the caller reports **as happening now**,
whether stated with certainty or uncertainty ("I think he's not breathing",
"I'm not sure if he's breathing" both count). The list must be exhaustive for
these codes.

Put a cue in `absent_cues` when it is mentioned but **denied** ("no fire"),
**in the past** ("he wasn't breathing earlier, he is now"), **hypothetical**
("he might have a heart attack if…") or **retracted** ("false alarm").

| Code | Report it when the caller says… |
|---|---|
| `NOT_BREATHING` | not breathing, no pulse, heart stopped, or is unsure whether the person is breathing |
| `UNCONSCIOUS` | unconscious, unresponsive, won't wake up, not moving, collapsed, won't answer |
| `OCCUPANTS_TRAPPED` | people trapped or inside a burning/collapsed structure or vehicle |
| `WEAPON_PRESENT` | a gun, knife or other weapon, or a shooting/stabbing |
| `ACTIVE_BLEEDING` | bleeding or blood from a person |
| `ACTIVE_VIOLENCE` | fighting, assault, someone being hit or threatened |
| `CARDIAC_SYMPTOMS` | heart attack, cardiac arrest, chest pain/pressure |
| `BREATHING_DIFFICULTY` | trouble breathing, choking, gasping |
| `SEIZURE` / `STROKE_SYMPTOMS` / `OVERDOSE` | the condition or its typical description |
| `FIRE_REPORTED` / `SMOKE_REPORTED` / `FIRE_SPREADING` / `EXPLOSION_REPORTED` | as named |
| `HAZARDOUS_ENVIRONMENT` | gas smell or leak, chemicals, fumes, carbon monoxide |
| `INJURY_REPORTED` | an injury or pain not covered above |
| `UNABLE_TO_GET_UP` | the person cannot get up, stand or move from where they fell (added in v1.1) |
| `MULTIPLE_VICTIMS` | two or more people affected |
| `CHILD_INVOLVED` | a baby, toddler or child (an explicit age under 18 also counts) |
| `ALLERGIC_REACTION` | an allergic reaction or anaphylaxis: throat, tongue or face swelling, hives with distress, an EpiPen used (v2.1) |
| `DIABETIC_EMERGENCY` | a diabetic who is unwell, very low or high blood sugar, too much insulin (v2.1) |
| `CHILDBIRTH` | labour, contractions, waters broken, a baby being born (v2.1) |
| `POISONING` | a harmful substance swallowed or drunk that is not a drug overdose: bleach, cleaning products, antifreeze, rat poison (v2.1) |
| `TRAFFIC_COLLISION` | a crash or collision involving a vehicle, or a person hit by one (v2.1) |
| `DROWNING` | drowning or near-drowning, a person pulled from water or found face down in it (v2.1) |
| `BURN_INJURY` | a person burned or scalded, including chemical burns (v2.1) |
| `ELECTROCUTION` | an electric shock, a person touching a power line or live wire, a lightning strike (v2.1) |
| `FALL_FROM_HEIGHT` | a fall from a roof, ladder, balcony, window, scaffolding, tree, or down stairs (v2.1) |
| `SELF_HARM_RISK` | a person threatening or attempting suicide or self-harm (v2.1) |
| `INTRUDER_PRESENT` | someone breaking in or inside the caller's home now (v2.1) |
| `MISSING_PERSON` | a person who is missing, has wandered off or has not come home (v2.1) |

## 2. Severity and priority (`labels.severity`, `labels.priority`)

Research rubric, applied in order. Priority follows from severity
(critical→P0, high→P1, elevated→P2, standard→P3, low→P4, undetermined→P2).

| Severity | When |
|---|---|
| critical | An immediate threat to life: not breathing, unconscious, people trapped, weapon with bleeding; or a *high* situation involving a child or multiple victims |
| high | A serious current condition: weapon, active violence, significant bleeding, cardiac or breathing symptoms, seizure, stroke, overdose, spreading fire, explosion, hazardous materials; an allergic reaction, diabetic emergency, childbirth, poisoning, drowning, burn, electrocution, fall from height, risk of self-harm, or an intruder present (v2.1) |
| elevated | Fire or smoke without the above; an older person unable to get up; entrapment with no hazard; a threat that has left the scene; a traffic collision or a missing person without the above (v2.1) |
| standard | A matter for emergency services with no serious condition (minor injury, minor bleeding, property crime, welfare check) |
| low | No current emergency: prank, retraction, past event, hypothetical |
| undetermined | The nature of the call cannot be told from the transcript |

Missing or uncertain **location never changes severity** (ADR-004, DDL-011).

## 3. Location (`labels.location`)

`present` if the caller gives any address, intersection, road or landmark;
`conflicting` if they give two different addresses; otherwise `missing`.

## 4. Victim count (`labels.victim_count`)

A number when one is stated (a range counts as its upper bound), `"unknown"`
when several people are mentioned without a number, omitted when not mentioned.

## 5. Domain (`labels.domain`)

The primary service: `police`, `fire`, `ems`, `hazmat`; `other` for non-emergency
calls such as pranks; `unknown` when it cannot be told.

## 6. Finer labels (label schema 2.0, optional)

Records may also carry the fields below. Independent annotators record them
for every case ([annotation protocol](../research/annotation-protocol.md)
section 6); older author and generator records do not have them yet.

- `cue_annotations`: one entry per mentioned cue, with its `status`
  (`affirmed`, `uncertain`, `negated`, `historical`, `hypothetical`,
  `retracted`) and `evidence`, the shortest exact words supporting it, as a
  span of one message (`message`, `start`, `end`, `text`). `affirmed` and
  `uncertain` cues are the case's `cues`; every other status puts the cue in
  `absent_cues`. When both are given they must agree.
- `location_components`: spans for `house_number`, `street`, `unit`,
  `intersection`, `landmark` and `locality`, in the caller's own words. Never
  corrected or completed.
- `case_uncertainty`: `clear`, `some_doubt` or `cannot_tell`.

Spans must match the message text exactly; the dataset loader rejects any
that do not.

## Changes

- v2.1: added twelve cue codes (DDL-021) and their severities in section 2.
  These severities are the author's research rubric and are flagged for
  practitioner review. Three curated cases gained a label for a new code
  (`fx-014` and `fx-023`: `TRAFFIC_COLLISION`; `cu-124`: `DROWNING`); no
  priority changed. `generated-1.0.0-seed42.jsonl` predates v2.1 and is not
  relabelled: its "fell down the stairs" family has no `FALL_FROM_HEIGHT`
  label.
- v2.0: added the optional finer labels in section 6 (cue status and
  evidence spans, location components, case uncertainty). Sections 1 to 5
  are unchanged, so every v1.1 label is still a valid v2.0 label.
- v1.1: added `UNABLE_TO_GET_UP`; relabelled `fx-008` accordingly. A critical
  cue reported only in the past ("wasn't breathing earlier") stays in
  `absent_cues` and the case is labelled elevated, as before.

