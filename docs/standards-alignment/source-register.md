# Standards and source register

Sources the platform refers to, with exactly what each is used for and what
it does **not** establish (design v1.2, §3B.2 and §19). Listing a source here
is not a claim of conformance to it.

Last verified: 2026-11-10.

| Source | Issuer / document | Version used | Official location | Licence | Used for | Evidence in this repo | Claim limit |
|---|---|---|---|---|---|---|---|
| Emergency Incident Data Object (EIDO) | NENA, NENA-STA-021 series | **NENA-STA-021.1b** (reissue, Aug 2022), git tag `NENA-STA-021.1b`, commit `c3b8d2063be63d27ff7e2d3c353c597c71817a1b` | [NENA911/EIDO-JSON](https://github.com/NENA911/EIDO-JSON) | **No licence file published** in the repository; files are not redistributed here, only fetched and verified at runtime | Structural validation of EIDO JSON instances against NENA's `openapi.yaml` and 43 NIEM component files | `backend/src/ntip/interop/eido/profile.py` (sha256 per file), `tests/interop/test_eido_profile.py` (NENA's published sample validates; version, required-field and type violations are rejected) | Schema validation of one edition only; not EIDO conformance, not NG911 or i3 compliance |
| EIDO (newer edition) | NENA, NENA-STA-021.1.1 | Public review 1 (Oct 2026) | tag `NENA-STA-021.1.1-public-review-1` | as above | Not used | — | Not supported until published; instances declaring other versions are rejected |
| EIDO conveyance | NENA, NENA-STA-024 series | Not pinned | [NENA911/WebSocket-Subscribe-Notify](https://github.com/NENA911/WebSocket-Subscribe-Notify), [NENA911/EIDO-Conveyance-Incident-Data-API](https://github.com/NENA911/EIDO-Conveyance-Incident-Data-API) | Not reviewed | Not used; the platform's gateway endpoint is project-defined | — | No conveyance compliance is claimed |
| NG9-1-1 (i3) solution | NENA, NENA-STA-010 series | Not pinned | [NENA standards catalogue](https://www.nena.org/page/Standards) | NENA terms | Architectural context only: which NG911 functions the platform does **not** implement (ESInet, NGCS, ECRF, LVF, call routing) | `docs/standards-alignment/ng911-alignment.md` | No i3 compliance claim |
| NG9-1-1 GIS Data Model | NENA | Not pinned | [NENA911/NG911GISDataModel](https://github.com/NENA911/NG911GISDataModel) (Apache-2.0) | Apache-2.0 | Not used yet (location level L3 is future work) | — | Location checks are completeness/consistency only, not LVF validation |
| NG911 interoperability test development | Texas A&M | Not pinned | [tamu-edu/ng911-dev](https://github.com/tamu-edu/ng911-dev) | Not reviewed | Not used; coverage of EIDO not yet checked | — | No claim of passing its tests |
| National 911 Program | NHTSA / 911.gov | — | [911.gov NG911](https://www.911.gov/issues/ng911/) | Public | Problem framing and ecosystem context | README | Program guidance is not an integration API |

## Open items

- Ask NENA for the licence terms of NENA911/EIDO-JSON before redistributing any
  schema file or sample.
- Pin and review an NENA-STA-024 conveyance profile before claiming anything
  about transport, acknowledgements or retries.
- Check which NENA requirements Texas A&M's `ng911-dev` covers before using it
  (design v1.2, §3B.9 Phase IV).
