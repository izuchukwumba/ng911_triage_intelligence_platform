"""Location quality levels L0-L2 (design v1.2, section 8.3).

- L0 structural:   is there any location at all?
- L1 completeness: which components (house number, street, locality, ...) are missing?
- L2 consistency:  do the reported locations disagree?

L3 (checking against authoritative GIS data) and L4 (standards-specific
validation) are out of scope until a licensed reference dataset is available,
so a location is only ``sufficient`` once a human or an authoritative source
has verified it. Everything the parser extracted on its own therefore
"requires verification" — and says exactly what is missing.
"""

from ntip.schema.advisory import LocationQuality, LocationQualityStatus
from ntip.schema.canonical import (
    ConflictKind,
    Incident,
    LocationCandidate,
    LocationValidation,
)

_VERIFIED = {LocationValidation.OPERATOR_VERIFIED, LocationValidation.REFERENCE_VALIDATED}


def _best(candidates: list[LocationCandidate]) -> LocationCandidate:
    """The most complete candidate; among equals, the most recently mentioned."""
    return min(reversed(candidates), key=lambda c: len(c.missing_fields))


def assess_location(incident: Incident) -> LocationQuality:
    candidates = incident.locations

    # L0: nothing usable at all.
    if not candidates:
        return LocationQuality(status=LocationQualityStatus.MISSING, missing_fields=["location"])

    # L2: disagreeing reports are surfaced before anything else.
    conflicting = [
        loc_id
        for conflict in incident.conflicts
        if conflict.kind is ConflictKind.LOCATION_MISMATCH
        for loc_id in conflict.location_ids
    ]
    if conflicting:
        return LocationQuality(
            status=LocationQualityStatus.CONFLICTING,
            conflicting_location_ids=list(dict.fromkeys(conflicting)),
        )

    verified = [c for c in candidates if c.validation in _VERIFIED and not c.missing_fields]
    if verified:
        return LocationQuality(status=LocationQualityStatus.SUFFICIENT)

    # L1: report what the best available candidate still lacks.
    return LocationQuality(
        status=LocationQualityStatus.REQUIRES_VERIFICATION,
        missing_fields=list(_best(candidates).missing_fields),
    )
