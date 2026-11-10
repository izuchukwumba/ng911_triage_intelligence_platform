# Synthetic GIS reference layer

`synthetic-ssap-1.0.0.csv` is a **synthetic** Site/Structure Address Point
layer for location level L3 (design v1.2, section 8.3): 136 address points in
two fictional municipal datasets, "Springfield" and "Riverton" (both `A1: IL`,
`A2: Synthetic County`). No point describes a real building. Every NGUID ends
in `gis.synthetic.example`.

The columns are field names from NENA's NG9-1-1 GIS Data Model,
`SiteStructureAddressPoint` layer, schema v3.0 (NENA-STA-006.3-2026), taken from
[NENA911/NG911GISDataModel](https://github.com/NENA911/NG911GISDataModel)
(Apache-2.0) at commit `30a42bfdf0eb316bb1266087f5f1a39e1c77e22d`. Only field
names are reused; no NENA file is copied here. The layer includes every field
the model marks as required (`DiscrpAgID`, `DateUpdate`, `NGUID`, `Country`,
`A1`) and the address and position fields matching needs.

Deliberate cases for tests and demos:
- `12 Oak Street` exists in both towns, so it is ambiguous without a
  municipality or postal code;
- `Main Street` exists in both towns with different number ranges;
- the street suffixes (`St_PosTyp`) are spelled out, so "Elm St." in a
  transcript must still match "Elm Street".

A real deployment would load its 9-1-1 authority's own layer
(`NTIP_GIS_REFERENCE`), under that data's licence.
