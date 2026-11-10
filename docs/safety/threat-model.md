# Threat model

Scope: the research platform as deployed by `infra/docker/docker-compose.yml`
on a developer machine or isolated lab, holding synthetic data only (design
v1.2, §13.1). It is not hardened for, and must not be connected to, any live
emergency system.

## Assets

Stored source events and incidents, assessments and reviews, the audit trail,
evaluation integrity (datasets, rulesets, reports), interop credentials, and
the B2 API credential when B2 is enabled.

## Threats and controls

| Threat | Control in place | Gap / next step |
|---|---|---|
| Malicious or oversized input | Pydantic validation with `extra="forbid"`; transcript ≤ 20,000 chars; interop payload ≤ 512 KB; EIDO schema validation and quarantine | Rate limiting is not implemented (needed before any hosted deployment) |
| Prompt injection via transcripts | Rules only extract; B2 treats the transcript as delimited data, output is schema-constrained and every claim must quote the source exactly | Model-side behaviour cannot be proven; mitigated by verification and human review |
| Model-output laundering (an unsupported claim presented as fact) | Span verification rejects ungrounded candidates; model observations are marked `model`; a serious model-only cue needs human confirmation | — |
| Log or error leakage of transcripts | Errors never echo submitted values or stack traces; correlation ids instead | Structured logging configuration is basic |
| Unauthorised access | Interop endpoints: bearer tokens per tenant, fail closed, tenant-scoped receipts | **The `/v1` research API has no authentication.** Acceptable only on an isolated machine; add authentication and role-based access before any shared deployment (§13.2) |
| Audit tampering | Append-only store; PostgreSQL triggers reject UPDATE/DELETE/TRUNCATE; digests on records and audit events | A database superuser can still drop triggers; use a restricted application role in any shared deployment |
| Evaluation tampering | Datasets, rulesets and the EIDO schema are pinned by sha256; reports record commit and digests | — |
| Supply chain | Locked dependencies (`uv.lock`, `package-lock.json`); third-party schema fetched only from a pinned commit and verified; CI runs pip-audit and npm audit on every change | Scans cover known advisories only |
| Data sent to a third party | B2 is off unless `NTIP_B2_ALLOW_EXTERNAL=1`; only synthetic data exists | Real data would need authorisation, privacy review and contracts (§3B.6) |
| Inadvertent connection to real systems | No telephony, routing or dispatch code exists; interop is import-only with no writeback; simulation banner in the UI | — |
| Secrets in the repository | Defaults are local-development values; `.env` is git-ignored; CI runs gitleaks over the full history | — |

## Privacy and retention (§9.3)

Only synthetic data is accepted (`synthetic: true` is mandatory). The
append-only store keeps everything indefinitely, which is appropriate for
synthetic research data only. Any authorised real data would require a
separate retention and deletion design that reconciles audit immutability with
lawful deletion; until then real data must not be ingested.
