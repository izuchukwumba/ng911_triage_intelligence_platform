# EIDO profile `ntip-eido-021.1b-import-v1`

The single EIDO edition the platform accepts, and exactly what it does with it
(design v1.2, §3B.2 version-lock policy).

| Field | Value |
|---|---|
| `eidoStandardEdition` | NENA-STA-021.1b |
| Schema source | NENA911/EIDO-JSON, tag `NENA-STA-021.1b`, commit `c3b8d2063be63d27ff7e2d3c353c597c71817a1b` |
| `schemaArtifactDigest` | `PROFILE.schema_artifact_digest` — sha256 over the per-file digests of `Schema/openapi.yaml` and 43 NIEM component files |
| Root type | `EmergencyIncidentDataObjectType` |
| Accepted `eidoVersion` | `1.0` (the only value the schema's enum allows) |
| `conveyanceProfile` | none: the platform's endpoint is project-defined, not NENA-STA-024 |
| `adapterVersion` | `eido-adapter-0.1.0` |

## Why the schema is fetched, not vendored

The upstream repository publishes no licence file. Copying its schemas or
sample into this public repository could breach NENA's rights, so the platform
fetches the pinned files from the pinned commit at runtime and refuses to use
any file whose sha256 differs from the pinned value
(`python -m ntip.interop.eido.fetch`). Nothing from that repository is
committed here.

## What validation covers

Validation uses NENA's OpenAPI 3.0 schema objects as JSON Schema (draft 7)
with cross-file references resolved only within the pinned, verified files.
Covered: structure, required properties, types, enumerations (including
`eidoVersion`) and date-time formats where the schema declares them.

Not covered, and not claimed:

- semantic rules in the NENA-STA-021 text that the schema does not encode
- the JSON-LD contexts
- conveyance (NENA-STA-024), authentication or acknowledgement semantics
- any NG911 or i3 conformance

NENA's own published sample (`Samples/Sample call transfer EIDO.json` at the
pinned commit) validates with no errors; this is checked in CI.
