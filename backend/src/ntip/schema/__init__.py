"""Versioned data contracts (design v1.2, section 4).

Three layers, never merged into one mutable record:

- source:    immutable inputs exactly as received
- canonical: normalised incident facts with provenance
- advisory:  machine assessments and, separately, human decisions
"""
