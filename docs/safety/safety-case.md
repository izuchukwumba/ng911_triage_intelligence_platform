# Safety case

What the platform must never do, how each rule is enforced, and the automated
evidence that it holds. Scope: a **research simulation** on synthetic data. It
is not certified for emergency operations, routes no calls and dispatches
nothing (design v1.2, safety and scope notice). Nothing here argues fitness for
live use; it argues that the research system behaves as its design says.

Enforcement is layered: the schema makes many violations impossible to
represent, the engine and pipeline implement the policy, the database refuses
mutation, and CI gates changes.

## Invariants

| # | Invariant (design ref.) | Enforced by | Evidence (tests; all run in CI) |
|---|---|---|---|
| S1 | Missing or uncertain location never lowers severity or priority (§3A.6.1, §7.5, ADR-004, DDL-011) | Location quality only adds `VERIFY_LOCATION` (`ntip/triage/engine.py`); severity comes only from reported conditions (DDL-013); the schema requires `VERIFY_LOCATION` whenever location is not sufficient (`Assessment` validator) | `test_missing_location_never_changes_severity_or_priority`, `test_critical_severity_with_missing_location_stays_critical`, `test_insufficient_location_requires_verify_location`, `test_int_008_contradictory_location_keeps_urgency` |
| S2 | A processing failure never becomes low priority (§2.4, §5.3, §7.5) | Pipeline catches any parse/assess error and stores a `processing_failed` assessment; the schema forbids a priority on a failed assessment and requires `URGENT_HUMAN_REVIEW`; the queue shows failures first | `test_parser_crash_keeps_the_source_and_demands_urgent_review`, `test_failed_assessment_cannot_assign_a_priority`, `test_failed_assessment_requires_urgent_review` |
| S3 | A prank cue never suppresses credible evidence (§7.1, DDL-013) | Prank adds `CONFIRM_CLASSIFICATION`; sets "low" only when nothing else was reported | `test_prank_cue_does_not_suppress_credible_evidence`, `test_prank_alone_is_low_but_still_reviewed` |
| S4 | Negated, past and hypothetical cues do not fire affirmative rules (§7.5) | Cue context analysis (`ntip/parser/context.py`); engine uses current, non-negated cues only | `test_negated_and_historical_cues_do_not_fire`, `test_negated_cue_is_kept_but_not_affirmed`, `test_conditional_with_modal_is_hypothetical` |
| S5 | Uncertainty is resolved by a human, not discounted (§3A.6) | Uncertain serious cues keep full weight and add `CONFIRM_CRITICAL_REPORT`; when unsure, negation scope errs towards affirming | `test_uncertain_serious_cue_keeps_full_weight_and_asks_for_confirmation`, `test_unsure_whether_breathing_is_an_uncertain_critical_cue` |
| S6 | No fabricated facts: every extracted claim quotes the source (§3A.5–3A.6) | `Evidence` on every observation/location/count; `provenance_errors()`; model candidates verified by exact span match and rejected otherwise; B2 quotes are located by exact match, never repaired | `test_each_observation_quotes_its_source`, `test_rejects_unsupported_candidates`, `test_ungrounded_quote_is_rejected_by_verification_not_repaired` |
| S7 | A model never removes a rules finding; disagreements go to a human (§3A.6.3) | `fuse()` only adds; `MODEL_RULE_DISAGREEMENT` conflicts → `RESOLVE_CONFLICT`; a serious cue seen only by a model needs `CONFIRM_CRITICAL_REPORT` (P-REVIEW-006) | `test_hybrid_never_removes_a_rules_finding`, `test_model_only_serious_cue_raises_severity_but_needs_confirmation` |
| S8 | A model failure never blocks processing (§3A.6.6, §3B.1 non-interference) | Hard timeout on the inference client; any model error leaves the rules result marked `degraded` | `test_model_failure_degrades_but_ingestion_succeeds`, `test_http_extractor_times_out_quickly`, `test_int_007_model_outage_does_not_block_the_incident_flow` |
| S9 | `unknown` is never stored as `false` or `0` (§3A.6.4, §4.3) | `Fact[T]` validator; victim count defaults to `not_reported` | `test_states_without_a_value_reject_one`, `test_unstated_count_is_not_reported_rather_than_one` |
| S10 | Text alone never yields a validated location or coordinates (§3A.1, §8) | `LocationCandidate` validator: reported locations cannot carry coordinates; a model cannot mark a location validated | `test_reported_location_cannot_carry_coordinates`, `test_a_model_cannot_validate_a_location` |
| S11 | A human override never destroys the machine's assessment (§7.5) | Reviews are separate records; the projection shows override next to original | `test_override_is_recorded_separately_and_wins_in_the_view`, `test_override_keeps_machine_output` |
| S12 | History is append-only (§9, ADR-005) | Store has no update/delete; PostgreSQL triggers reject UPDATE, DELETE and TRUNCATE on every table | `test_rows_cannot_be_updated_or_deleted`, `test_tables_cannot_be_truncated` |
| S13 | Released rulesets are immutable (§7.5) | sha256 pins in `RELEASED` | `test_released_rulesets_are_immutable` |
| S14 | Only synthetic data is accepted (ADR-006) | `SourceEvent` validator; API requires `synthetic: true` | `test_rejects_non_synthetic_input` (schema and API) |
| S15 | Transcript text is data, never instructions (§3A.6.7) | Rules parser only extracts; B2 delimits the transcript and states it is data; outputs are schema-constrained and verified | `test_int_009_instructions_in_the_narrative_are_not_executed`, `test_transcript_is_delimited_as_data` |
| S16 | Invalid or unauthorised external input is never processed (ADR-INT-003) | Gateway: profile check, size limit, version rejection, schema quarantine, fail-closed auth | `test_int_002_*`, `test_int_003_*`, `test_int_010b_interop_fails_closed` |
| S17 | No critical call is silently under-triaged by a change (§14.2) | CI gate: zero critical under-triage on the curated regression split | `python -m ntip.evaluation --split regression --gate` (CI step) |
| S18 | Concurrent messages for one incident are never lost or half-processed | Optimistic concurrency: writes carry an expected message count, checked atomically (PostgreSQL advisory lock); the pipeline re-reads and retries | `test_concurrent_follow_ups_are_all_kept_and_assessed_together`, `test_expectation_rejects_a_stale_write`, `test_postgres_load_run_is_consistent` |

## Residual risks (accepted for a research prototype)

- **Over-triage:** the design chooses false alarms over missed emergencies; hybrid ML roughly doubles over-triage (see evaluation results).
- **Lexicon coverage:** the rules miss misspellings and unseen phrasings; recall on real speech is unknown.
- **Labels are author- or generator-written:** no independent annotation or practitioner review yet; the severity rubric is project-defined.
- **No authentication on the research `/v1` API** outside the interop endpoints (see the threat model).
- **Synthetic data only:** no claim about real calls, real operators or outcomes.

## Change control

Changes that could weaken an invariant must update this table, keep or add the
evidence test, and pass the CI safety gate. Safety-relevant decisions are
recorded in `docs/design-decisions/decision-log.md` (DDL-011, DDL-013, DDL-014).
