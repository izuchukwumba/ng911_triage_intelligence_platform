"""/v1 evaluation report (design v1.2, sections 10.5 and 11.1).

Runs the rules baseline B0, as currently deployed, over a committed synthetic
dataset and reports metrics with confidence intervals, the dataset and version
pins needed to reproduce it, and every case it got wrong. Only the dev and
regression splits are served: the held-out test split is looked at when
reporting results, not browsed (never tune on the test split).
"""

from enum import StrEnum
from pathlib import Path
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, ConfigDict

from ntip.api.auth import Permission, require
from ntip.evaluation.dataset import Split, load_dataset
from ntip.evaluation.report import to_markdown
from ntip.evaluation.runner import evaluate

router = APIRouter(prefix="/v1/evaluation", tags=["evaluation"])

NOTE = (
    "Synthetic, author-labelled data. These numbers describe this dataset only; they are "
    "not evidence of real-world dispatch accuracy (design v1.2, section 16.3)."
)


class DatasetName(StrEnum):
    CURATED = "curated"
    GENERATED = "generated"


DATASET_FILES = {
    DatasetName.CURATED: "curated.jsonl",
    DatasetName.GENERATED: "generated-1.0.0-seed42.jsonl",
}


class ReportSplit(StrEnum):
    """The splits that may be browsed. ``test`` is deliberately absent."""

    DEV = "dev"
    REGRESSION = "regression"


class _Out(BaseModel):
    model_config = ConfigDict(json_schema_serialization_defaults_required=True)


class Rate(_Out):
    value: float | None
    numerator: int
    denominator: int
    ci95: list[float] | None


class CueExtraction(_Out):
    precision: float | None
    recall: float | None
    f1: float | None
    f1_ci95: list[float | None]
    denied_or_past_cues_treated_as_live: int


class Metrics(_Out):
    cases: int
    critical_cue_sensitivity: Rate
    critical_undertriage: Rate
    priority_exact: Rate
    undertriage: Rate
    overtriage: Rate
    severity_exact: Rate
    domain_accuracy: Rate
    location_accuracy: Rate
    victim_count_accuracy: Rate
    cue_extraction: CueExtraction
    # priority_confusion[expected][predicted] = count
    priority_confusion: dict[str, dict[str, int]]


class Pins(_Out):
    system: str
    git_commit: str
    dataset_path: str
    dataset_digest: str
    splits: list[str]
    parser: str
    engine: str
    ruleset: str
    ruleset_digest: str
    schema_version: str
    python: str
    lockfile_digest: str | None
    seed: int
    bootstrap: str


class FailedCase(_Out):
    case_id: str
    split: str
    messages: list[str]
    expected_priority: str | None
    critical: bool  # the label is P0
    errors: list[str]


class EvaluationReport(_Out):
    note: str
    dataset: DatasetName
    pins: Pins
    metrics: Metrics
    failed_cases: list[FailedCase]


Splits = Annotated[list[ReportSplit] | None, Query(description="default: dev and regression")]


def _run(
    request: Request, dataset: DatasetName, splits: list[ReportSplit] | None
) -> tuple[dict[str, Any], dict[str, Any]]:
    data_dir: Path = request.app.state.eval_data_dir
    loaded = load_dataset(data_dir / DATASET_FILES[dataset])
    chosen = [Split(s) for s in (splits or list(ReportSplit))]
    cases = {c.case_id: c for c in loaded.split(*chosen)}
    return evaluate(loaded, chosen), cases


@router.get("/report", dependencies=[Depends(require(Permission.READ))])
def get_report(
    request: Request,
    dataset: DatasetName = DatasetName.CURATED,
    split: Splits = None,
) -> EvaluationReport:
    """Evaluate B0 now, on the dev and/or regression split of a committed dataset."""
    result, cases = _run(request, dataset, split)
    m, metrics = result["manifest"], result["metrics"]
    cue = metrics["cue_extraction"]
    failed = [
        FailedCase(
            case_id=case_id,
            split=cases[case_id].split,
            messages=cases[case_id].messages,
            expected_priority=cases[case_id].labels.priority,
            critical=cases[case_id].labels.priority == "P0",
            errors=errors,
        )
        for case_id, errors in metrics["failures"].items()
    ]
    failed.sort(key=lambda f: (not f.critical, f.case_id))  # critical misses first
    return EvaluationReport(
        note=NOTE,
        dataset=dataset,
        pins=Pins(
            system=m["system"],
            git_commit=m["git_commit"],
            dataset_path=Path(m["dataset"]["path"]).name,
            dataset_digest=m["dataset"]["digest"],
            splits=list(m["dataset"]["splits"]),
            parser=m["parser"],
            engine=m["engine"],
            ruleset=m["ruleset"]["name"],
            ruleset_digest=m["ruleset"]["digest"],
            schema_version=m["schema_version"],
            python=m["python"],
            lockfile_digest=m["lockfile_digest"],
            seed=m["seed"],
            bootstrap=m["bootstrap"],
        ),
        metrics=Metrics(
            **{k: v for k, v in metrics.items() if k not in {"cue_extraction", "failures"}},
            cue_extraction=CueExtraction(
                precision=cue["micro"]["precision"],
                recall=cue["micro"]["recall"],
                f1=cue["micro"]["f1"],
                f1_ci95=cue["micro"]["f1_ci95"],
                denied_or_past_cues_treated_as_live=cue["denied_or_past_cues_treated_as_live"],
            ),
        ),
        failed_cases=failed,
    )


@router.get(
    "/report.md",
    dependencies=[Depends(require(Permission.READ))],
    response_class=PlainTextResponse,
    responses={200: {"content": {"text/markdown": {}}}},
)
def get_report_markdown(
    request: Request,
    dataset: DatasetName = DatasetName.CURATED,
    split: Splits = None,
) -> PlainTextResponse:
    """The same evaluation as a Markdown report, for export."""
    result, _ = _run(request, dataset, split)
    splits = "-".join(s.value for s in (split or list(ReportSplit)))
    return PlainTextResponse(
        to_markdown(result),
        media_type="text/markdown; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="b0-{dataset.value}-{splits}.md"'},
    )
