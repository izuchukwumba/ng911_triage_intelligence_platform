"""Location quality assessment (design v1.2, section 8).

Judges whether an incident's location can be acted on, independently of how
serious the incident is. The result changes the review workflow (verify the
location), never the severity.
"""

from ntip.location.quality import assess_location

__all__ = ["assess_location"]
