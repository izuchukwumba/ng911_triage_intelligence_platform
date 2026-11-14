"""Render an evaluation result as Markdown."""

from typing import Any


def _rate(r: dict[str, Any]) -> str:
    if r["value"] is None:
        return "n/a (0 cases)"
    ci = r["ci95"]
    counts = f"{r['numerator']}/{r['denominator']}"
    return f"{r['value']:.3f} ({counts}; 95% CI {ci[0]:.3f} to {ci[1]:.3f})"


def to_markdown(result: dict[str, Any]) -> str:
    m, x = result["manifest"], result["metrics"]
    micro = x["cue_extraction"]["micro"]
    lines = [
        f"# Evaluation: {m['system']} on {', '.join(m['dataset']['splits']) or 'all'} splits",
        "",
        "> Synthetic, author-labelled data. These numbers describe this dataset only; they are not"
        " evidence of real-world dispatch accuracy (design v1.2, section 16.3).",
        "",
        "## Reproducibility",
        "",
        "| Item | Value |",
        "|---|---|",
        f"| Git commit | `{m['git_commit']}` |",
        f"| Dataset | `{m['dataset']['path']}` (`{m['dataset']['digest']}`) |",
        f"| Parser / engine | `{m['parser']}` / `{m['engine']}` |",
        f"| Ruleset | `{m['ruleset']['name']}` (`{m['ruleset']['digest']}`) |",
        f"| Schema | `{m['schema_version']}` |",
        f"| Python / lockfile | `{m['python']}` / `{m['lockfile_digest']}` |",
        f"| Seed / bootstrap | `{m['seed']}` / {m['bootstrap']} |",
        "",
        f"## Results ({x['cases']} cases)",
        "",
        "| Metric | Value |",
        "|---|---|",
        f"| Critical-cue sensitivity | {_rate(x['critical_cue_sensitivity'])} |",
        "| Critical under-triage (expected P0, predicted lower) | "
        f"{_rate(x['critical_undertriage'])} |",
        f"| Priority exact agreement | {_rate(x['priority_exact'])} |",
        f"| Under-triage (any) | {_rate(x['undertriage'])} |",
        f"| Over-triage (any) | {_rate(x['overtriage'])} |",
        f"| Severity band exact | {_rate(x['severity_exact'])} |",
        f"| Domain accuracy | {_rate(x['domain_accuracy'])} |",
        f"| Location status accuracy | {_rate(x['location_accuracy'])} |",
        f"| Victim count accuracy | {_rate(x['victim_count_accuracy'])} |",
        f"| Cue extraction micro P / R / F1 | {micro['precision']} / {micro['recall']} / "
        f"{micro['f1']} (F1 95% CI {micro['f1_ci95'][0]} to {micro['f1_ci95'][1]}) |",
        "| Denied/past cues treated as live | "
        f"{x['cue_extraction']['denied_or_past_cues_treated_as_live']} |",
        "",
        "## Priority confusion (rows: expected, columns: predicted)",
        "",
        "| | " + " | ".join(next(iter(x["priority_confusion"].values())).keys()) + " |",
        "|---" * (1 + len(next(iter(x["priority_confusion"].values())))) + "|",
    ]
    for expected, row in x["priority_confusion"].items():
        if any(row.values()):
            lines.append(f"| **{expected}** | " + " | ".join(str(v) for v in row.values()) + " |")
    lines += [
        "",
        "## Per-cue extraction",
        "",
        "| Cue | TP | FP | FN | Precision | Recall |",
        "|---|---|---|---|---|---|",
    ]
    for code, prf in x["cue_extraction"]["per_code"].items():
        cells = [code, prf["tp"], prf["fp"], prf["fn"], prf["precision"], prf["recall"]]
        lines.append("| " + " | ".join(str(c) for c in cells) + " |")
    if spans := x.get("spans"):
        exact, overlap = spans["span_exact"], spans["span_overlap"]
        lines += [
            "",
            f"## Evidence spans and cue status ({spans['annotated_cases']} annotated cases)",
            "",
            f"{spans['gold_mentions']} labelled mentions, {spans['predicted_mentions']} mentioned "
            "by the system.",
            "",
            "| Metric | Precision | Recall | F1 |",
            "|---|---|---|---|",
            f"| Span exact | {exact['precision']} | {exact['recall']} | {exact['f1']} |",
            f"| Span overlap | {overlap['precision']} | {overlap['recall']} | {overlap['f1']} |",
            "",
            f"Status accuracy (codes both mention): {_rate(spans['status_accuracy'])}",
        ]
    lines += ["", f"## Failures ({len(x['failures'])} cases)", ""]
    for case_id, errors in x["failures"].items():
        lines.append(f"- `{case_id}`: {'; '.join(errors)}")
    return "\n".join(lines) + "\n"
