# Synthetic EIDO fixtures

Hand-written by this project for the interoperability tests (design v1.2,
§3B.7). They are **synthetic**: no real incident, agency or person. They
follow the structure of NENA-STA-021.1b and, except
`unsupported-version.json` (deliberately `eidoVersion: "2.0"`), validate
against the pinned NENA schema; see `docs/standards-alignment/eido-profile.md`.
NENA's own sample is not copied here because its repository publishes no
licence; the tests fetch it from the pinned commit instead.

| File | Used for |
|---|---|
| `rev1-smoke.json`, `rev2-trapped.json` | Revisions of one incident: idempotency, ordering, new-note detection |
| `injection.json` | Instructions embedded in the narrative are not executed |
| `conflicting-location.json` | Contradictory addresses keep urgency and request verification |
| `unknown-optional-field.json` | An unknown optional field is preserved and flagged, not discarded |
| `unsupported-version.json` | Explicit rejection of an unsupported edition |
