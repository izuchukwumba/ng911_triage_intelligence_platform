"""Labelled evaluation cases (design v1.2, sections 3A.7 and 10.5).

A dataset is a JSONL file with one EvalCase per line. Splits are assigned per
scenario *family*, never per case, so paraphrases of one scenario cannot leak
between development and test data; ``load_dataset`` enforces this.
"""

import json
from collections import defaultdict
from enum import StrEnum
from pathlib import Path
from typing import Literal, Self

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
    return Dataset(path=path.as_posix(), digest=sha256_digest(raw), cases=cases)


def dump_case(case: EvalCase) -> str:
    return json.dumps(case.model_dump(mode="json", exclude_defaults=True), ensure_ascii=False)
