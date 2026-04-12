# NG911 Standards Alignment

## Summary

This project is described as **NG911-aligned**, not NG911-compliant. This document explains what that means, what it does not mean, and why this positioning is accurate and honest.

---

## What NG911 Is

Next Generation 9-1-1 (NG911) refers to the ongoing national transition from legacy analog PSAP infrastructure to IP-based emergency communications systems. The standards are governed primarily by:

- **NENA i3** — the NENA i3 standard (NENA-STA-010) defines the IP-based Emergency Services IP Network (ESInet), SIP-based call routing, and functional element architecture for PSAPs
- **NIEM** — the National Information Exchange Model defines data exchange schemas used in public safety
- **APCO/NENA** — joint standards body guidance on PSAP operations and data management

NG911 at the infrastructure level involves: ESInets, SIP/i3 call routing, location-based routing (ECRF, LIS), functional elements (ESRP, ESQK), and interoperability across jurisdictions.

---

## What This Project Is

This project builds a **decision-support layer** that sits at the operational intelligence level, downstream of call ingestion. It does not implement:

- SIP/i3 call routing
- ESInet transport infrastructure
- Emergency Call Routing Function (ECRF)
- Location Information Server (LIS)
- PSAP functional elements

What it does implement — aligned with the *intent and data model goals* of NG911:

| NG911 Goal | This Project's Contribution |
|------------|----------------------------|
| Structured, machine-readable incident data | Canonical `IncidentRecord` schema with Zod validation |
| Location-quality awareness | Dispatchable location scoring with confidence signals |
| Explainable, consistent triage logic | Weighted rule engine with versioned scoring config |
| Audit and traceability | Complete decision chain preserved per incident |
| Replayability for quality review | `/replay/:id` endpoint for deterministic reprocessing |
| Interoperability-friendly data | Versioned schemas; TypeScript types; JSON payloads |

---

## Why "NG911-Aligned" Is the Right Term

**Aligned** means the system's design goals, data model choices, and operational philosophy are consistent with the direction NG911 is taking public safety communications — without claiming to be a certified or compliant component of an actual ESInet deployment.

This framing is:

- **Honest** — it does not misrepresent scope
- **Technically defensible** — it focuses on areas where individual engineering contribution is credible
- **Operationally grounded** — it reflects real problems that NG911 modernization surfaces downstream of transport-layer work

---

## Specific Design Decisions Informed by NG911 Context

### Structured incident objects over free-text
NG911 systems increasingly depend on structured data exchange. This project treats the incident object as the canonical unit of work rather than an unstructured log entry.

### Location as a quality-bearing field
NENA i3 and location-based routing standards treat location quality as operationally significant. This project models `dispatchable_location_score` explicitly, rather than treating location as a plain string.

### Schema versioning
NG911 data exchange standards emphasize forward-compatible, versioned schemas. This project versions both the incident schema and scoring config independently.

### Reason-code transparency
Operational systems in high-stakes domains require explainable outputs. Reason codes on every priority assignment align with the expectation that PSAP operators can trace and override system recommendations.

---

## What This Project Does Not Claim

- This is not a certified NG911 component
- This is not a SIP/i3 implementation
- This is not a replacement for PSAP dispatchers or CAD systems
- This has not been evaluated against formal NENA compliance criteria
- This does not implement real GIS or location routing services
