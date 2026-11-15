"""Post-hoc analyses of the ML-10 frozen comparison (exploratory, not pre-registered).

The ML-10 reports give aggregates only. This module **reproduces** the
pre-registered systems case by case, checks that the aggregates match the
archived reports exactly, and then adds analyses the pre-registration did
not specify. They were requested in review:

1. **Family-clustered statistics.** Generated calls are paraphrases within
   27 families, so call-level tests overstate the evidence. Durkalski's
   clustered McNemar test, a family sign test and family-resampled bootstrap
   intervals (``ntip.evaluation.clustered``).
2. **False P0s.** Calls labelled below P0 that a system raised to P0, the
   costliest kind of over-triage.
3. **P0 as a screening decision at realistic prevalence.** Sensitivity, the
   false-positive rate and the positive predictive value of a P0 assignment
   when 35% (as in the data), 10% or 5% of calls are truly P0.
4. **Where priority errors come from.** A priority error with exactly the
   labelled cues is a rubric or engine disagreement; otherwise it is a cue
   error.
5. **B1 refitted on generator 2.2.** The pre-registered B1 was fitted on
   generator 1.0.0, so H5 confounded the model with its training data. A
   B1 hybrid refitted on generator 2.2's dev and regression splits separates
   the two.
6. **A latency benchmark** (``--latency``), separate from the comparison, with
   warm-up and repetitions.

Nothing here changes a pre-registered decision. Reproduction is the only
second run the pre-registration allows, and no system is tuned.

    python -m ntip.evaluation.ml10_posthoc --with-b1e B1E_DIR \\
        --preregistration ../docs/evaluation/preregistration/ml-10-frozen-comparison.md
"""

import argparse
import json
import os
import platform
import statistics
import sys
import time
from collections import Counter
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from ntip.evaluation.clustered import cluster_bootstrap, clustered_mcnemar, family_sign_test
from ntip.evaluation.compare import model_system, preregistration_record
from ntip.evaluation.dataset import Split, load_dataset
from ntip.evaluation.runner import (
    REPO_ROOT,
    CaseResult,
    System,
    case_counts,
    critical_codes,
    evaluate_case,
    rule_codes,
    rules_baseline,
    score,
)

DATASETS = {
    "generated": "generated-2.2.0-seed42.jsonl",
    "curated": "curated.jsonl",
    "challenge": "challenge-1.0.0.jsonl",
}
REFIT_DATA = "generated-2.2.0-seed42.jsonl"
PREVALENCES = (0.35, 0.10, 0.05)
SEED = 20261109
HYBRID = "Hybrid B0+B1e"
REFIT = "Hybrid B0+B1 (refit on generator 2.2)"
PAIRS = (
    (HYBRID, "B0 rules"),
    (HYBRID, "Hybrid B0+B1"),
    (HYBRID, REFIT),
    (REFIT, "Hybrid B0+B1"),
)
CHECKED = ("critical_undertriage", "overtriage", "undertriage", "priority_exact")


def _rank(priority: str | None) -> int:
    return int(priority[1]) if priority else 9


def _systems(b1e_dir: Path) -> dict[str, System]:
    from ntip.ml.b1 import B1Model, load_training_set
    from ntip.ml.b1e import B1eModel

    b1e = B1eModel(b1e_dir)
    refit = B1Model(load_training_set(REPO_ROOT / "data" / "eval" / REFIT_DATA))
    return {
        "B0 rules": rules_baseline(),
        "Hybrid B0+B1": model_system(B1Model(), model_only=False),
        "B1e only": model_system(b1e, model_only=True),
        HYBRID: model_system(b1e, model_only=False),
        REFIT: model_system(refit, model_only=False),
    }


def _check(name: str, metrics: dict[str, Any], archived: dict[str, Any]) -> list[str]:
    """Differences between a reproduced system and the archived report."""
    problems = []
    for key in CHECKED:
        if metrics[key]["numerator"] != archived[key]["numerator"]:
            problems.append(
                f"{name} {key}: {metrics[key]['numerator']} != {archived[key]['numerator']}"
            )
    f1, old = metrics["cue_extraction"]["micro"]["f1"], archived["cue_extraction"]["micro"]["f1"]
    if f1 != old:
        problems.append(f"{name} cue F1: {f1} != {old}")
    return problems


def _screening(results: Sequence[CaseResult]) -> dict[str, Any]:
    p0 = [r for r in results if r.case.labels.priority == "P0"]
    other = [r for r in results if r.case.labels.priority != "P0"]
    tp = sum(r.predicted_priority == "P0" for r in p0)
    fp = sum(r.predicted_priority == "P0" for r in other)
    sens = tp / len(p0) if p0 else None
    fpr = fp / len(other) if other else None
    ppv: dict[str, float | None] = {}
    for prevalence in PREVALENCES:
        if sens is None or fpr is None or sens * prevalence + fpr * (1 - prevalence) == 0:
            ppv[str(prevalence)] = None
        else:
            value = sens * prevalence / (sens * prevalence + fpr * (1 - prevalence))
            ppv[str(prevalence)] = round(value, 4)
    return {
        "p0_labelled": len(p0),
        "false_p0": fp,
        "false_p0_from": dict(
            Counter(r.case.labels.priority for r in other if r.predicted_priority == "P0")
        ),
        "sensitivity": None if sens is None else round(sens, 4),
        "false_positive_rate": None if fpr is None else round(fpr, 4),
        "ppv_at_prevalence": ppv,
    }


def _error_sources(results: Sequence[CaseResult]) -> dict[str, int]:
    out = Counter[str]()
    for r in results:
        if r.predicted_priority == r.case.labels.priority:
            continue
        direction = (
            "under" if _rank(r.predicted_priority) > _rank(r.case.labels.priority) else "over"
        )
        cues_right = r.predicted_cues == set(r.case.labels.cues) & r.relevant
        out[f"{direction}: {'cues right (rubric/engine)' if cues_right else 'cue error'}"] += 1
    return dict(sorted(out.items()))


def _family_p0_hits(results: Sequence[CaseResult]) -> dict[str, int]:
    hits = Counter[str]()
    for r in results:
        if r.case.labels.priority == "P0":
            hits[r.case.family] += r.predicted_priority == "P0"
    return hits


def analyse(b1e_dir: Path, preregistration: Path) -> dict[str, Any]:
    systems = _systems(b1e_dir)
    relevant, critical = rule_codes(), critical_codes()
    archive = REPO_ROOT / "docs" / "evaluation" / "results"
    out: dict[str, Any] = {
        "kind": "exploratory post-hoc analysis of the ML-10 frozen comparison",
        "preregistration": preregistration_record(preregistration),
        "systems": list(systems),
        "datasets": {},
    }
    for key, filename in DATASETS.items():
        dataset = load_dataset(REPO_ROOT / "data" / "eval" / filename)
        cases = dataset.split(Split.TEST)
        results = {
            name: [evaluate_case(c, s, relevant) for c in cases] for name, s in systems.items()
        }
        stem = f"compare-{filename.split('-')[0].removesuffix('.jsonl')}-test-b1e-"
        archived_path = next(archive.glob(f"{stem}*.json"))
        archived = json.loads(archived_path.read_text("utf-8"))["systems"]
        problems: list[str] = []
        metrics = {}
        for name, rs in results.items():
            metrics[name] = score(rs, seed=SEED, critical=critical)
            if name in archived:
                problems += _check(name, metrics[name], archived[name]["metrics"])
        families = [c.family for c in cases]
        counts = {n: [case_counts(r, critical) for r in rs] for n, rs in results.items()}
        p0_index = [i for i, c in enumerate(cases) if c.labels.priority == "P0"]
        comparisons = {}
        for a, b in PAIRS:
            hits_a, hits_b = _family_p0_hits(results[a]), _family_p0_hits(results[b])
            fams = sorted(hits_a)
            comparisons[f"{a} vs {b}"] = {
                "clustered_mcnemar_p0": clustered_mcnemar(
                    [not counts[a][i].p0_missed for i in p0_index],
                    [not counts[b][i].p0_missed for i in p0_index],
                    [families[i] for i in p0_index],
                ),
                "family_sign_test_p0": family_sign_test(
                    [hits_a[f] for f in fams], [hits_b[f] for f in fams]
                ),
                "cluster_bootstrap": cluster_bootstrap(counts[a], counts[b], families, seed=SEED),
            }
        out["datasets"][key] = {
            "dataset": dataset.path,
            "digest": dataset.digest,
            "calls": len(cases),
            "families": len(set(families)),
            "p0_families": len({families[i] for i in p0_index}),
            "reproduction": {
                "archived_report": archived_path.name,
                "matches": not problems,
                "differences": problems,
            },
            "per_system": {
                name: {
                    "critical_undertriage": metrics[name]["critical_undertriage"]["numerator"],
                    "overtriage": metrics[name]["overtriage"]["numerator"],
                    "cue_f1": metrics[name]["cue_extraction"]["micro"]["f1"],
                    "denied_or_past_live": metrics[name]["cue_extraction"][
                        "denied_or_past_cues_treated_as_live"
                    ],
                    "screening": _screening(results[name]),
                    "priority_error_sources": _error_sources(results[name]),
                }
                for name in systems
            },
            "comparisons": comparisons,
        }
    return out


def latency(b1e_dir: Path, *, repeats: int, warmup: int) -> dict[str, Any]:
    """Per-call wall time for B0 and the B1e hybrid on generator 2.2 test, repeated."""
    systems = _systems(b1e_dir)
    relevant = rule_codes()
    cases = load_dataset(REPO_ROOT / "data" / "eval" / DATASETS["generated"]).split(Split.TEST)
    out: dict[str, Any] = {
        "machine": {
            "platform": platform.platform(),
            "processor": platform.processor(),
            "cpu_count": os.cpu_count(),
            "python": platform.python_version(),
        },
        "calls": len(cases),
        "warmup_calls": warmup,
        "repeats": repeats,
        "systems": {},
    }
    try:
        import torch

        out["machine"]["torch_threads"] = torch.get_num_threads()
    except ImportError:
        pass
    for name in ("B0 rules", HYBRID):
        system = systems[name]
        for case in cases[:warmup]:
            evaluate_case(case, system, relevant)
        runs = []
        for _ in range(repeats):
            seconds = []
            for case in cases:
                started = time.perf_counter()
                evaluate_case(case, system, relevant)
                seconds.append(time.perf_counter() - started)
            seconds.sort()
            runs.append({
                "p50_ms": round(1000 * seconds[len(seconds) // 2], 2),
                "p95_ms": round(1000 * seconds[int(0.95 * len(seconds))], 2),
                "p99_ms": round(1000 * seconds[int(0.99 * len(seconds))], 2),
                "max_ms": round(1000 * seconds[-1], 2),
            })  # fmt: skip
        out["systems"][name] = {
            "runs": runs,
            "median_of_p95_ms": round(statistics.median(r["p95_ms"] for r in runs), 2),
        }
    return out


def _fmt_p(p: float) -> str:
    return f"{p:.3g}"


def to_markdown(result: dict[str, Any]) -> str:
    lines = [
        "# ML-10 post-hoc analyses (exploratory)",
        "",
        "> Not pre-registered. These analyses reproduce the ML-10 systems case by case and add",
        "> statistics requested in review. They do not change any pre-registered decision.",
        "",
        f"Pre-registration `{result['preregistration']['digest']}`.",
    ]
    for key, d in result["datasets"].items():
        rep = d["reproduction"]
        lines += [
            "",
            f"## {key}: {d['calls']} calls, {d['families']} families "
            f"({d['p0_families']} with P0 calls)",
            "",
            f"Reproduction of `{rep['archived_report']}`: "
            + (
                "**matches exactly**."
                if rep["matches"]
                else "**differs**: " + "; ".join(rep["differences"])
            ),
            "",
            "| System | P0 missed | False P0 | Over-triage | Cue F1 | Denied/past live "
            "| PPV of P0 at 35% / 10% / 5% prevalence |",
            "|---|---|---|---|---|---|---|",
        ]
        for name, s in d["per_system"].items():
            ppv = s["screening"]["ppv_at_prevalence"]
            lines.append(
                f"| {name} | {s['critical_undertriage']}/{s['screening']['p0_labelled']} | "
                f"{s['screening']['false_p0']} | {s['overtriage']} | {s['cue_f1']} | "
                f"{s['denied_or_past_live']} | "
                + " / ".join("n/a" if v is None else f"{v:.2f}" for v in ppv.values())
                + " |"
            )
        lines += ["", "Priority error sources:", ""]
        for name, s in d["per_system"].items():
            parts = ", ".join(f"{k} {v}" for k, v in s["priority_error_sources"].items())
            lines.append(f"- {name}: {parts}")
        lines += [
            "",
            "| A vs B | P0: clustered McNemar (A-only / B-only, X², p) "
            "| Families A / B better (sign test p) | Δ P0 missed, family bootstrap "
            "| Δ cue F1, family bootstrap | Δ over-triage, family bootstrap |",
            "|---|---|---|---|---|---|",
        ]
        for pair, c in d["comparisons"].items():
            m, s, cb = c["clustered_mcnemar_p0"], c["family_sign_test_p0"], c["cluster_bootstrap"]

            def ci(stat: str, cb: dict[str, Any] = cb) -> str:
                x = cb[stat]
                if x["difference"] is None:
                    return "n/a"
                return f"{x['difference']:+.3f} [{x['ci95'][0]:+.3f}, {x['ci95'][1]:+.3f}]"

            lines.append(
                f"| {pair} | {m['a_right_b_wrong']} / {m['b_right_a_wrong']}, "
                f"X²={m['chi_square']}, p={_fmt_p(m['p_value'])} "
                f"({m['clusters_with_discordance']} of {m['clusters']} families discordant) | "
                f"{s['a_better']} / {s['b_better']} (p={_fmt_p(s['p_value'])}) | "
                f"{ci('critical_undertriage')} | {ci('cue_micro_f1')} | {ci('overtriage')} |"
            )
    if "latency" in result:
        lat = result["latency"]
        lines += [
            "",
            "## Latency benchmark",
            "",
            f"{lat['calls']} calls, {lat['warmup_calls']} warm-up calls, {lat['repeats']} repeats. "
            f"Machine: {lat['machine']}.",
            "",
            "| System | Run | p50 ms | p95 ms | p99 ms | max ms |",
            "|---|---|---|---|---|---|",
        ]
        for name, s in lat["systems"].items():
            for i, r in enumerate(s["runs"], 1):
                cells = " | ".join(str(r[k]) for k in ("p50_ms", "p95_ms", "p99_ms", "max_ms"))
                lines.append(f"| {name} | {i} | {cells} |")
    return "\n".join(lines) + "\n"


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("--with-b1e", type=Path, required=True, metavar="MODEL_DIR")
    parser.add_argument("--preregistration", type=Path, required=True)
    parser.add_argument("--out", type=Path, default=REPO_ROOT / "docs" / "evaluation" / "results")
    parser.add_argument("--latency", action="store_true", help="also run the latency benchmark")
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--warmup", type=int, default=50)
    args = parser.parse_args(argv)
    result = analyse(args.with_b1e, args.preregistration)
    if args.latency:
        result["latency"] = latency(args.with_b1e, repeats=args.repeats, warmup=args.warmup)
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "ml-10-posthoc.json").write_text(
        json.dumps(result, indent=2) + "\n", encoding="utf-8"
    )
    markdown = to_markdown(result)
    (args.out / "ml-10-posthoc.md").write_text(markdown, encoding="utf-8", newline="\n")
    reconfigure = getattr(sys.stdout, "reconfigure", None)
    if callable(reconfigure):
        reconfigure(errors="replace")
    print(markdown)
    return 0 if all(d["reproduction"]["matches"] for d in result["datasets"].values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
