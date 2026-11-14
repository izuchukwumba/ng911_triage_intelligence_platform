"""Labelled evaluation cases (design v1.2, sections 3A.7 and 10.5).

A dataset is a JSONL file with one EvalCase per line. Splits are assigned per
scenario *family*, never per case, so paraphrases of one scenario cannot leak
between development and test data; ``load_dataset`` enforces this.

Label schema 2.0 (ML layer design, section 4.1) adds optional, finer labels:
each mentioned cue with its status and evidence span, the parts of the
location the caller gave, and the annotator's overall certainty. Records
without them stay valid. When ``cue_annotations`` is given, ``cues`` and
``absent_cues`` are derived from it, so every existing metric keeps working.
"""

import json
from collections import defaultdict
from enum import StrEnum
from pathlib import Path
from typing import Any, Literal, Self

from pydantic import Field, model_validator

from ntip.schema.advisory import AdvisoryPriority, SeverityBand
from ntip.schema.base import Identifier, ReasonCode, SchemaModel, sha256_digest
from ntip.schema.canonical import IncidentDomain


class Split(StrEnum):
    DEV = "dev"  # free to inspect while developing rules or models
    REGRESSION = "regression"  # must not get worse; gates CI
    TEST = "test"  # held out; look only when reporting results


class LabelSource(StrEnum):
    # Written by the project author; not independently annotated.
    AUTHOR = "author"
    # Produced by the synthetic generator from its template.
    GENERATOR = "generator"
    # Independently annotated and adjudicated.
    ADJUDICATED = "adjudicated"


LABEL_SCHEMA_VERSION = "2.0.0"


class CueStatus(StrEnum):
    """How a mentioned cue was reported (annotation protocol, section 6.1)."""

    AFFIRMED = "affirmed"  # stated as happening now
    UNCERTAIN = "uncertain"  # the caller is unsure: "I think he's not breathing"
    NEGATED = "negated"  # denied: "no fire"
    HISTORICAL = "historical"  # happened earlier and has stopped
    HYPOTHETICAL = "hypothetical"  # "if he stops breathing..."
    RETRACTED = "retracted"  # taken back: "false alarm"


# Statuses that make a cue live: it belongs in ``cues``; any other status puts
# it in ``absent_cues``.
LIVE_STATUSES = frozenset({CueStatus.AFFIRMED, CueStatus.UNCERTAIN})


class TextSpan(SchemaModel):
    """Exact characters of one message: ``messages[message][start:end] == text``."""

    message: int = Field(ge=0)
    start: int = Field(ge=0)
    end: int = Field(gt=0)
    text: str = Field(min_length=1)

    @model_validator(mode="after")
    def _check(self) -> Self:
        if self.end - self.start != len(self.text):
            raise ValueError(f"span {self.start}:{self.end} does not fit text {self.text!r}")
        return self

    @classmethod
    def find(cls, messages: list[str], message: int, quote: str) -> Self:
        """The first exact occurrence of ``quote`` in a message; never fuzzy."""
        start = messages[message].find(quote) if quote and message < len(messages) else -1
        if start < 0:
            raise ValueError(f"{quote!r} does not occur verbatim in message {message}")
        return cls(message=message, start=start, end=start + len(quote), text=quote)

    def check_against(self, messages: list[str], where: str) -> None:
        if self.message >= len(messages):
            raise ValueError(f"{where}: message {self.message} does not exist")
        found = messages[self.message][self.start : self.end]
        if found != self.text:
            raise ValueError(f"{where}: span text {self.text!r} does not match {found!r}")


class CueAnnotation(SchemaModel):
    code: ReasonCode
    status: CueStatus
    # The shortest exact words supporting the cue; optional for labels written
    # before spans were recorded.
    evidence: TextSpan | None = None


class LocationComponents(SchemaModel):
    """The caller's own words for each part of the location they gave."""

    house_number: TextSpan | None = None
    street: TextSpan | None = None
    unit: TextSpan | None = None
    intersection: TextSpan | None = None
    landmark: TextSpan | None = None
    locality: TextSpan | None = None

    def spans(self) -> dict[str, TextSpan]:
        return {name: span for name, span in self if isinstance(span, TextSpan)}


class CaseUncertainty(StrEnum):
    CLEAR = "clear"
    SOME_DOUBT = "some_doubt"
    CANNOT_TELL = "cannot_tell"


class CaseLabels(SchemaModel):
    domain: IncidentDomain
    severity: SeverityBand
    priority: AdvisoryPriority
    # Every severity-relevant cue that is currently reported (affirmed or
    # uncertain, present tense). Exhaustive for the codes the ruleset uses.
    cues: list[ReasonCode] = Field(default_factory=list)
    # Cues mentioned but denied, historical or hypothetical: must NOT be live.
    absent_cues: list[ReasonCode] = Field(default_factory=list)
    location: Literal["present", "missing", "conflicting"]
    # None = not reported; "unknown" = mentioned but no number given.
    victim_count: int | Literal["unknown"] | None = None
    # Label schema 2.0 (optional).
    cue_annotations: list[CueAnnotation] | None = None
    location_components: LocationComponents | None = None
    case_uncertainty: CaseUncertainty | None = None

    @model_validator(mode="before")
    @classmethod
    def _derive_cue_lists(cls, data: Any) -> Any:
        """Fill ``cues``/``absent_cues`` from ``cue_annotations`` when omitted."""
        if not isinstance(data, dict) or not data.get("cue_annotations"):
            return data
        if "cues" in data or "absent_cues" in data:
            return data  # both given: checked for consistency below
        live: list[str] = []
        absent: list[str] = []
        for item in data["cue_annotations"]:
            status = item.status if isinstance(item, CueAnnotation) else item.get("status")
            code = item.code if isinstance(item, CueAnnotation) else item.get("code")
            (live if CueStatus(status) in LIVE_STATUSES else absent).append(code)
        return {**data, "cues": sorted(live), "absent_cues": sorted(absent)}

    @model_validator(mode="after")
    def _check_annotations(self) -> Self:
        if self.cue_annotations is None:
            return self
        codes = [a.code for a in self.cue_annotations]
        if len(codes) != len(set(codes)):
            raise ValueError("a cue may be annotated only once")
        live = {a.code for a in self.cue_annotations if a.status in LIVE_STATUSES}
        absent = set(codes) - live
        if set(self.cues) != live or set(self.absent_cues) != absent:
            raise ValueError("cues/absent_cues disagree with cue_annotations")
        return self


class EvalCase(SchemaModel):
    case_id: Identifier
    split: Split
    family: Identifier
    messages: list[str] = Field(min_length=1)
    synthetic: Literal[True] = True
    label_source: LabelSource
    labels: CaseLabels
    notes: str = ""

    @model_validator(mode="after")
    def _check(self) -> Self:
        overlap = set(self.labels.cues) & set(self.labels.absent_cues)
        if overlap:
            raise ValueError(f"{self.case_id}: cue both present and absent: {sorted(overlap)}")
        for annotation in self.labels.cue_annotations or []:
            if annotation.evidence is not None:
                where = f"{self.case_id} {annotation.code}"
                annotation.evidence.check_against(self.messages, where)
        if self.labels.location_components is not None:
            for name, span in self.labels.location_components.spans().items():
                span.check_against(self.messages, f"{self.case_id} {name}")
        return self


class Dataset(SchemaModel):
    path: str
    digest: str
    cases: list[EvalCase]

    def split(self, *splits: Split) -> list[EvalCase]:
        return [c for c in self.cases if not splits or c.split in splits]


def load_dataset(path: Path) -> Dataset:
    raw = path.read_text(encoding="utf-8").replace("\r\n", "\n")
    cases = [
        EvalCase.model_validate_json(line)
        for line in raw.splitlines()
        if line.strip() and not line.startswith("//")
    ]
    ids = [c.case_id for c in cases]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate case_id in dataset")
    splits_by_family: dict[str, set[Split]] = defaultdict(set)
    for case in cases:
        splits_by_family[case.family].add(case.split)
    leaking = {f: sorted(s) for f, s in splits_by_family.items() if len(s) > 1}
    if leaking:
        raise ValueError(f"families span several splits (leakage): {leaking}")
    return Dataset(path=_display_path(path), digest=sha256_digest(raw), cases=cases)


def _display_path(path: Path) -> str:
    """Repository-relative when possible, so reports never contain local paths."""
    root = Path(__file__).resolve().parents[4]
    try:
        return path.resolve().relative_to(root).as_posix()
    except ValueError:
        return path.name


def dump_case(case: EvalCase) -> str:
    return json.dumps(case.model_dump(mode="json", exclude_defaults=True), ensure_ascii=False)
