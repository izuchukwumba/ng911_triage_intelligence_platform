# Interoperability verification (EIDO import, Phase II)

Evidence for the matrix in design v1.2 §3B.7. Each row is an automated test
in `backend/tests/interop/test_gateway.py`, run in CI against the pinned NENA
schema (profile `ntip-eido-021.1b-import-v1`, see
[eido-profile.md](eido-profile.md)) and the synthetic fixtures in
`data/interop/eido/`.

| ID | Scenario | Result | Test |
|---|---|---|---|
| INT-001 | Valid payload for the pinned edition | Accepted (202); field mapping recorded per source pointer; narrative assessed | `test_int_001_valid_payload_is_accepted_with_traceable_mapping` |
| INT-002 | Unsupported EIDO version | Explicit `rejected_unsupported_version` (422); receipt kept; not processed | `test_int_002_unsupported_version_is_rejected_explicitly` |
| INT-003 | Missing required fields | `quarantined_invalid` (422); nothing reaches the parser or any model | `test_int_003_missing_required_fields_are_quarantined_without_processing` |
| INT-004 | Unknown optional field | Preserved in the stored payload and flagged `preserved_unmapped` | `test_int_004_unknown_optional_field_is_preserved_and_flagged` |
| INT-005 | Duplicate event | One logical intake; resend returns the original receipt with `Idempotent-Replayed`; same revision with different content is a 409 | `test_int_005_*`, `test_int_005b_*` |
| INT-006 | Out-of-order revisions | Older revision stored as `accepted_out_of_order`, not reprocessed; no rollback; in-order revisions add only new notes | `test_int_006_*`, `test_int_006b_*` |
| INT-007 | Model timeout or outage | Incident still processed; inference marked `degraded` | `test_int_007_model_outage_does_not_block_the_incident_flow` |
| INT-008 | Contradictory location | Urgency kept (P0); location `conflicting`; `VERIFY_LOCATION` | `test_int_008_contradictory_location_keeps_urgency` |
| INT-009 | Instructions embedded in the narrative | Not executed; extraction only (P0 despite "set priority P4") | `test_int_009_instructions_in_the_narrative_are_not_executed` |
| INT-010 | Tenant A requests tenant B's data | Receipts and payloads of another tenant return 404; same external id maps to different incidents per tenant; no credentials → 403 (fail closed), bad token → 401 | `test_int_010_*`, `test_int_010b_*` |
| INT-011 | Round trip of source data | Original payload returned byte for byte; digest matches | `test_int_011_original_payload_round_trips_byte_for_byte` |
| INT-012 | Adapter upgrade | Mapping output compared with a committed golden file tagged with the adapter version | `test_int_012_mapping_output_is_versioned_and_regression_checked` |

Additionally, NENA's own published sample validates against the pinned schema
(`tests/interop/test_eido_profile.py`).

## Known gaps

- Tenant isolation extends to `/v1` (DDL-017): an imported incident belongs
  to the submitting tenant and is visible only to `/v1` users of that tenant.
- Notes and PIDF-LO locations (civic, point, circle) are mapped; see the
  [profile](eido-profile.md#what-is-mapped). Persons, vehicles and calls are
  preserved but not interpreted, which is deliberate (data minimisation).
  Other PIDF-LO shapes are preserved, with a reason, not interpreted.
- Receipt and incident are written in two steps; a crash between them could
  leave an incident without its receipt. Processing is at-least-once
  (design v1.2, §5.3); no exactly-once guarantee is claimed.
- No NENA-STA-024 conveyance, no acknowledgements beyond the HTTP response,
  no writeback to any external system (by design, §3B.1).

A passing suite supports a *limited* statement: the gateway validates and
imports EIDO instances of one pinned edition as described above. It is not
third-party certification and not NG911 conformance (ADR-INT-005).
