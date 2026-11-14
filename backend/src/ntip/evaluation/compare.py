"""Compare extraction systems on the same cases (design v1.2, sections 3A.8 and 10.6).

Systems:

- B0: rules only.
- B1-only: B1's verified candidates replace the rules' cue observations
  (locations, classification and counts still come from the parser, so only
  cue extraction differs).
- Hybrid: rules plus verified B1 candidates (hybrid_review fusion).
- Ablation: hybrid with B1's candidate threshold lowered to the abstention
  threshold, i.e. without abstention.

    python -m ntip.evaluation.compare --dataset ../data/eval/curated.jsonl --split test
"""

import argparse
import json
from collections.abc import Callable, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ntip.evaluation.calibration import summarise
from ntip.evaluation.dataset import Dataset, EvalCase, Split, load_dataset
from ntip.evaluation.runner import (
    FIXED_TIME,
    REPO_ROOT,
    System,
    critical_codes,
    evaluate_case,
    manifest,
    rule_codes,
    rules_baseline,
    score,
)
from ntip.ml.b1 import ABSTAIN_FROM, B1Model
from ntip.ml.contract import InferenceMessage, InferenceRequest
from ntip.ml.extractors import ModelExtractor
from ntip.ml.fusion import fuse
from ntip.ml.verify import verify
from ntip.parser.parser import parse
from ntip.schema.advisory import Assessment
from ntip.schema.canonical import Incident, InferenceMode
from ntip.schema.source import SourceEvent
from ntip.triage.engine import assess

MIN_SLICE = 10


def _messages(messages: list[str]) -> list[InferenceMessage]:
    return [InferenceMessage(source_event_id=f"evt_{i}", text=m) for i, m in enumerate(messages, 1)]


def model_system(model: ModelExtractor, *, model_only: bool) -> System:
    def run(messages: list[str]) -> tuple[Incident, Assessment]:
        sources = [
            SourceEvent.from_text(
                source_event_id=f"evt_{i}", incident_id="eval", received_at=FIXED_TIME, text=m
            )
            for i, m in enumerate(messages, 1)
        ]
        rules = parse(sources, derived_at=FIXED_TIME)
        response = model.infer(
            InferenceRequest(request_id="eval", incident_id="eval", messages=_messages(messages))
        )
        verified = verify(response, {s.source_event_id: s.text for s in sources})
        if model_only:
            rules = rules.model_copy(update={"observations": [], "conflicts": []})
        incident = fuse(
            rules,
            InferenceMode.HYBRID_REVIEW,
            verified=verified,
            model_id=model.model_id,
            model_version=model.model_version,
            abstained_codes=[a.code for a in response.abstentions],
        )
        if model_only:
            # No rules observations to disagree with.
            incident = incident.model_copy(update={"conflicts": []})
        return incident, assess(incident, assessment_id="eval", assessed_at=FIXED_TIME)

    return run


def _variants(case: EvalCase) -> list[str]:
    if "; " not in case.notes:
        return []
    return case.notes.split("; ", 1)[1].split(", ")


def _slices(results: Sequence[Any], seed: int) -> dict[str, Any]:
    by_variant: dict[str, list[Any]] = {}
    for result in results:
        for variant in _variants(result.case):
            by_variant.setdefault(variant, []).append(result)
    return {
        name: {
            "cases": len(members),
            "micro_f1": score(members, seed=seed, critical=critical_codes())["cue_extraction"][
                "micro"
            ]["f1"],
            "critical_cue_sensitivity": score(members, seed=seed, critical=critical_codes())[
                "critical_cue_sensitivity"
            ]["value"],
        }
        for name, members in sorted(by_variant.items())
        if len(members) >= MIN_SLICE
    }


def compare(
    dataset: Dataset,
    splits: Sequence[Split],
    *,
    seed: int = 20261109,
    extra_models: dict[str, ModelExtractor] | None = None,
) -> dict[str, Any]:
    cases = dataset.split(*splits)
    relevant = rule_codes()
    b1 = B1Model()
    b1_no_abstain = B1Model(candidate_at=ABSTAIN_FROM)
    systems: dict[str, System] = {
        "B0 rules": rules_baseline(),
        "B1 only": model_system(b1, model_only=True),
        "Hybrid B0+B1": model_system(b1, model_only=False),
        "Hybrid without abstention": model_system(b1_no_abstain, model_only=False),
    }
    for name, model in (extra_models or {}).items():
        systems[f"{name} only"] = model_system(model, model_only=True)
        systems[f"Hybrid B0+{name}"] = model_system(model, model_only=False)
    results: dict[str, Any] = {}
    for name, system in systems.items():
        case_results = [evaluate_case(case, system, relevant) for case in cases]
        metrics = score(case_results, seed=seed, critical=critical_codes())
        results[name] = {
            "metrics": {k: v for k, v in metrics.items() if k != "failures"},
            "slices": _slices(case_results, seed),
        }

    # Calibration of B1's scores against the labels, for the cues B1 knows.
    pairs = [
        (score_, code in case.labels.cues)
        for case in cases
        for code, score_ in b1.cue_scores(_messages(case.messages)).items()
    ]
    return {
        "manifest": {
            **manifest(dataset, splits, seed, "comparison"),
            "b1_model_version": b1.model_version,
            "b1_training_digest": b1.training_digest,
            "extra_models": {
                name: {"model_id": model.model_id, "model_version": model.model_version}
                for name, model in (extra_models or {}).items()
            },
            "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
        },
        "systems": results,
        "b1_calibration": summarise(pairs),
    }


def _fmt(rate: dict[str, Any]) -> str:
    if rate["value"] is None:
        return "n/a"
    return f"{rate['value']:.3f} ({rate['numerator']}/{rate['denominator']})"


def to_markdown(result: dict[str, Any]) -> str:
    m = result["manifest"]
    rows: list[tuple[str, Callable[[dict[str, Any]], str]]] = [
        ("Critical-cue sensitivity", lambda x: _fmt(x["critical_cue_sensitivity"])),
        ("Critical under-triage", lambda x: _fmt(x["critical_undertriage"])),
        ("Priority exact", lambda x: _fmt(x["priority_exact"])),
        ("Under-triage (any)", lambda x: _fmt(x["undertriage"])),
        ("Over-triage (any)", lambda x: _fmt(x["overtriage"])),
        ("Cue micro precision", lambda x: str(x["cue_extraction"]["micro"]["precision"])),
        ("Cue micro recall", lambda x: str(x["cue_extraction"]["micro"]["recall"])),
        ("Cue micro F1", lambda x: str(x["cue_extraction"]["micro"]["f1"])),
        ("Denied/past cues treated as live", lambda x: str(
            x["cue_extraction"]["denied_or_past_cues_treated_as_live"])),
    ]  # fmt: skip
    if any("spans" in result["systems"][n]["metrics"] for n in result["systems"]):
        rows += [
            ("Evidence span F1 (exact / overlap)", lambda x: (
                f"{x['spans']['span_exact']['f1']} / {x['spans']['span_overlap']['f1']}"
                if "spans" in x else "n/a")),
            ("Cue status accuracy", lambda x: (
                _fmt(x["spans"]["status_accuracy"]) if "spans" in x else "n/a")),
        ]  # fmt: skip
    names = list(result["systems"])
    lines = [
        f"# Comparison on {m['dataset']['path']} ({', '.join(m['dataset']['splits'])})",
        "",
        "> Synthetic data. B1 was trained only on the generated dev + regression splits and has"
        " never seen these cases unless they come from those splits.",
        "",
        f"Commit `{m['git_commit']}` · dataset `{m['dataset']['digest']}` · parser "
        f"`{m['parser']}` · engine `{m['engine']}` · ruleset `{m['ruleset']['name']}` · B1 "
        f"`{m['b1_model_version']}`"
        + "".join(
            f" · {name} `{x['model_version']}`" for name, x in m.get("extra_models", {}).items()
        )
        + f" · seed `{m['seed']}`",
        "",
        "| Metric | " + " | ".join(names) + " |",
        "|---" * (len(names) + 1) + "|",
    ]
    for label, get in rows:
        lines.append(
            f"| {label} | " + " | ".join(get(result["systems"][n]["metrics"]) for n in names) + " |"
        )
    cal = result["b1_calibration"]
    lines += [
        "",
        "## B1 calibration (cue scores vs labels)",
        "",
        f"{cal['pairs']} (case, cue) pairs, {cal['positives']} positive. Brier {cal['brier']}, "
        f"ECE {cal['ece']}, AURC {cal['aurc']}, selective risk {cal['risk_at']}.",
    ]
    slice_names = sorted({s for n in names for s in result["systems"][n]["slices"]})
    if slice_names:
        header = "| Slice | " + " | ".join(names) + " |"
        rule = "|---" * (len(names) + 1) + "|"
        lines += ["", "## Slices (cue micro F1 / critical-cue sensitivity)", "", header, rule]
        for s in slice_names:
            cells = []
            for n in names:
                sl = result["systems"][n]["slices"].get(s)
                cells.append(
                    f"{sl['micro_f1']} / {sl['critical_cue_sensitivity']} (n={sl['cases']})"
                    if sl
                    else ""
                )
            lines.append(f"| {s} | " + " | ".join(cells) + " |")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Compare B0, B1 and hybrid.")
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--split", action="append", choices=[s.value for s in Split])
    parser.add_argument("--out", type=Path, default=REPO_ROOT / "docs" / "evaluation" / "results")
    parser.add_argument(
        "--with-b2",
        action="store_true",
        help="also run B2 (calls the Anthropic API: costs money, needs NTIP_B2_ALLOW_EXTERNAL=1)",
    )
    parser.add_argument(
        "--with-b1e",
        type=Path,
        metavar="MODEL_DIR",
        help="also run B1e from a trained model directory (needs the ml-encoder extra)",
    )
    args = parser.parse_args()
    splits = [Split(s) for s in (args.split or ["test"])]
    extra: dict[str, ModelExtractor] = {}
    if args.with_b1e:
        from ntip.ml.b1e import B1eModel

        extra["B1e"] = B1eModel(args.with_b1e)
    if args.with_b2:
        from ntip.ml.b2 import B2Model

        extra["B2"] = B2Model()
    result = compare(load_dataset(args.dataset), splits, extra_models=extra)
    stem = f"compare-{args.dataset.stem.split('-')[0]}-{'-'.join(splits)}"
    # Reports with an extra model are named after it, so they never overwrite the B0/B1 report.
    stem += "".join(
        f"-{model.model_id.split('-')[0]}-{model.model_version}" for model in extra.values()
    )
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / f"{stem}.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    markdown = to_markdown(result)
    (args.out / f"{stem}.md").write_text(markdown, encoding="utf-8", newline="\n")
    print(markdown)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
