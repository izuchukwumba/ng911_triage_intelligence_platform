# NG911 alignment

This project is described as **NG911-aligned**, not NG911-compliant. This page explains what that means, what it does not mean, and why the positioning is accurate (design v1.2, §2.2, §3B and ADR-007).

---

## What NG911 is

Next Generation 911 is the transition of US emergency communications from analogue, circuit-switched infrastructure to IP-based, location-aware systems, defined largely by NENA standards:

- **NENA i3** (NENA-STA-010): the Emergency Services IP Network (ESInet), SIP-based call routing, and the functional elements of NG911 Core Services (ECRF, LVF, ESRP, ...)
- **NENA EIDO** (NENA-STA-021): a structured JSON object for exchanging emergency incident data between authorised systems, with conveyance in NENA-STA-024
- **NENA GIS Data Model**: authoritative geospatial data for routing and validation

---

## What this platform does **not** implement

- SIP/i3 call routing, ESInet or any NG911 Core Services functional element
- Location Validation Function (LVF) or Emergency Call Routing Function (ECRF)
- NENA-STA-024 EIDO conveyance
- Any connection to a live PSAP, CAD or emergency network
- Any automated dispatch action

## What it does

It is a downstream **decision-support research layer** positioned where incident information is *exchanged*, not where calls are *routed* (ADR-INT-001):

| NG911 concern | How the platform reflects it | Evidence |
|---|---|---|
| Structured incident data | Accepts EIDO instances of one pinned edition (NENA-STA-021.1b), validated against NENA's own schema, through an import-only gateway; never modifies the EIDO | [eido-profile.md](eido-profile.md), [interop-verification.md](interop-verification.md) |
| Location quality | Keeps reported, device-provided and geocoded locations apart; reports missing components and conflicts; never invents coordinates; location quality changes the review workflow, never the urgency | `ntip.location`, safety case S1 and S10 |
| Provenance and accountability | Every fact quotes its source span; append-only history; versioned rules and models; replay | [safety case](../safety/safety-case.md) |
| Non-interference | AI is optional, bounded by timeouts, and can be disabled without affecting anything upstream | INT-007, safety case S8 |

## What "aligned" means

The design choices follow the direction NG911 sets (structured, standards-based, location-aware and auditable incident data) without claiming to be a certified or compliant component of an ESInet deployment. Specifically:

- This is not a certified NG911 component and has not been assessed against NENA conformance criteria.
- Passing its own interoperability tests supports a *limited* statement about one pinned EIDO edition, not third-party certification (ADR-INT-005).
- Every external source it refers to, and the limit of each claim, is listed in the [source register](source-register.md).
