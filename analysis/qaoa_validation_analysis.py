#!/usr/bin/env python
"""Analyze repeated QAOA validation attempts on small exported QUBO instances."""

from __future__ import annotations

import csv
from collections import defaultdict
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
INPUT_DIR = REPO_ROOT / "results" / "raw" / "v2_qaoa_validation_small_matrix"
ATTEMPTS_INPUT = INPUT_DIR / "attempts.csv"
SUMMARY_INPUT = INPUT_DIR / "summary.csv"
PROCESSED_DIR = REPO_ROOT / "results" / "processed" / "qaoa_validation_small_matrix"
FIGURES_DIR = REPO_ROOT / "results" / "figures" / "qaoa_validation_small_matrix"

SCENARIO_LABELS_ES = {
    "baseline_small": "Base",
    "steady_load": "Carga estable",
    "burst_load": "Rafagas",
    "critical_priority": "Prioridad critica",
    "heterogeneous_workers": "Trabajadores heterogeneos",
}

SCENARIO_LABELS_EN = {
    "baseline_small": "Baseline",
    "steady_load": "Steady load",
    "burst_load": "Burst load",
    "critical_priority": "Critical priority",
    "heterogeneous_workers": "Heterogeneous workers",
}

COLORS = {
    "qaoa": "#21745f",
    "miss": "#9b3b3b",
    "time": "#2f5f98",
}


def main() -> int:
    if not ATTEMPTS_INPUT.exists() or not SUMMARY_INPUT.exists():
        raise SystemExit(
            "QAOA validation inputs are missing. Run the v2 small QAOA matrix first."
        )

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)

    attempts = load_csv(ATTEMPTS_INPUT)
    summary = load_csv(SUMMARY_INPUT)
    by_instance = instance_summary(attempts)
    by_depth = depth_summary(attempts)
    aggregate = aggregate_summary(attempts, summary)

    write_csv(PROCESSED_DIR / "attempts_normalized.csv", attempts)
    write_csv(PROCESSED_DIR / "summary_normalized.csv", summary)
    write_csv(PROCESSED_DIR / "by_instance.csv", by_instance)
    write_csv(PROCESSED_DIR / "by_depth.csv", by_depth)
    write_csv(PROCESSED_DIR / "aggregate.csv", aggregate)
    write_figures(by_instance, by_depth)
    write_findings(attempts, by_instance, by_depth, aggregate)

    print(f"QAOA attempts: {len(attempts)}")
    print(f"QAOA instances: {len(by_instance)}")
    print(f"Tables: {PROCESSED_DIR}")
    print(f"Figures: {FIGURES_DIR}")
    return 0


def load_csv(path: Path) -> list[dict[str, Any]]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        return [normalize_row(row) for row in reader]


def normalize_row(row: dict[str, str]) -> dict[str, Any]:
    normalized: dict[str, Any] = {}

    for key, value in row.items():
        if key in {
            "batch_index",
            "variable_count",
            "reps",
            "seed",
            "shots",
            "maxiter",
            "constraint_violations",
            "qiskit_sample_count",
            "event_count",
            "worker_count",
            "best_reps",
            "best_seed",
        }:
            normalized[key] = int(float(value)) if value != "" else 0
        elif key in {
            "scale_factor",
            "elapsed_seconds",
            "exact_objective",
            "qaoa_objective",
            "objective_gap",
            "relative_gap",
            "qiskit_fval_scaled",
        }:
            normalized[key] = float(value) if value != "" else 0.0
        elif key in {"feasible", "exact_match", "same_assignment_as_exact"}:
            normalized[key] = value.lower() == "true"
        else:
            normalized[key] = value

    return normalized


def instance_summary(attempts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []

    for instance_id, group in sorted(group_by(attempts, "instance_id").items()):
        best_attempt = min(group, key=lambda row: (not row["feasible"], row["objective_gap"]))
        exact_matches = count_true(group, "exact_match")
        feasible = count_true(group, "feasible")

        rows.append(
            {
                "instance_id": instance_id,
                "scenario": group[0]["scenario"],
                "variable_count": group[0]["variable_count"],
                "attempts": len(group),
                "feasible_attempts": feasible,
                "feasible_rate": round_number(feasible / len(group)),
                "exact_matches": exact_matches,
                "exact_match_rate": round_number(exact_matches / len(group)),
                "best_reps": best_attempt["reps"],
                "best_seed": best_attempt["seed"],
                "best_objective_gap": round_number(best_attempt["objective_gap"]),
                "best_relative_gap": round_number(best_attempt["relative_gap"]),
                "average_elapsed_seconds": round_number(mean(row["elapsed_seconds"] for row in group)),
                "max_elapsed_seconds": round_number(max(row["elapsed_seconds"] for row in group)),
            }
        )

    return rows


def depth_summary(attempts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []

    for reps, group in sorted(group_by(attempts, "reps").items()):
        exact_matches = count_true(group, "exact_match")
        feasible = count_true(group, "feasible")

        rows.append(
            {
                "reps": reps,
                "attempts": len(group),
                "feasible_attempts": feasible,
                "feasible_rate": round_number(feasible / len(group)),
                "exact_matches": exact_matches,
                "exact_match_rate": round_number(exact_matches / len(group)),
                "average_elapsed_seconds": round_number(mean(row["elapsed_seconds"] for row in group)),
                "max_elapsed_seconds": round_number(max(row["elapsed_seconds"] for row in group)),
            }
        )

    return rows


def aggregate_summary(
    attempts: list[dict[str, Any]], summary: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    exact_matches = count_true(attempts, "exact_match")
    feasible = count_true(attempts, "feasible")
    best_exact_matches = count_true(summary, "exact_match")
    best_feasible = count_true(summary, "feasible")

    return [
        {
            "metric": "all_attempts",
            "instances": len({row["instance_id"] for row in attempts}),
            "attempts": len(attempts),
            "feasible_count": feasible,
            "feasible_rate": round_number(feasible / len(attempts)),
            "exact_match_count": exact_matches,
            "exact_match_rate": round_number(exact_matches / len(attempts)),
            "average_elapsed_seconds": round_number(mean(row["elapsed_seconds"] for row in attempts)),
        },
        {
            "metric": "best_attempt_per_instance",
            "instances": len(summary),
            "attempts": len(summary),
            "feasible_count": best_feasible,
            "feasible_rate": round_number(best_feasible / len(summary)),
            "exact_match_count": best_exact_matches,
            "exact_match_rate": round_number(best_exact_matches / len(summary)),
            "average_elapsed_seconds": round_number(mean(row["elapsed_seconds"] for row in summary)),
        },
    ]


def write_figures(by_instance: list[dict[str, Any]], by_depth: list[dict[str, Any]]) -> None:
    write_bar_chart(
        FIGURES_DIR / "exact_match_rate_by_instance.svg",
        rows=by_instance,
        label_key="scenario",
        value_key="exact_match_rate",
        label_map=SCENARIO_LABELS_ES,
        title="Tasa de acierto exacto QAOA por instancia",
        y_label="Tasa de acierto",
        color=COLORS["qaoa"],
        percent=True,
    )
    write_bar_chart(
        FIGURES_DIR / "exact_match_rate_by_instance_en.svg",
        rows=by_instance,
        label_key="scenario",
        value_key="exact_match_rate",
        label_map=SCENARIO_LABELS_EN,
        title="QAOA exact match rate by instance",
        y_label="Exact match rate",
        color=COLORS["qaoa"],
        percent=True,
    )
    write_bar_chart(
        FIGURES_DIR / "exact_match_rate_by_depth.svg",
        rows=by_depth,
        label_key="reps",
        value_key="exact_match_rate",
        label_map={1: "p=1", 2: "p=2"},
        title="Tasa de acierto exacto por profundidad QAOA",
        y_label="Tasa de acierto",
        color=COLORS["qaoa"],
        percent=True,
    )
    write_bar_chart(
        FIGURES_DIR / "exact_match_rate_by_depth_en.svg",
        rows=by_depth,
        label_key="reps",
        value_key="exact_match_rate",
        label_map={1: "p=1", 2: "p=2"},
        title="Exact match rate by QAOA depth",
        y_label="Exact match rate",
        color=COLORS["qaoa"],
        percent=True,
    )
    write_bar_chart(
        FIGURES_DIR / "average_runtime_by_instance.svg",
        rows=by_instance,
        label_key="scenario",
        value_key="average_elapsed_seconds",
        label_map=SCENARIO_LABELS_ES,
        title="Tiempo medio de validacion QAOA por instancia",
        y_label="Segundos",
        color=COLORS["time"],
        percent=False,
    )
    write_bar_chart(
        FIGURES_DIR / "average_runtime_by_instance_en.svg",
        rows=by_instance,
        label_key="scenario",
        value_key="average_elapsed_seconds",
        label_map=SCENARIO_LABELS_EN,
        title="Mean QAOA validation runtime by instance",
        y_label="Seconds",
        color=COLORS["time"],
        percent=False,
    )


def write_bar_chart(
    path: Path,
    rows: list[dict[str, Any]],
    label_key: str,
    value_key: str,
    label_map: dict[Any, str],
    title: str,
    y_label: str,
    color: str,
    percent: bool,
) -> None:
    width = 1120
    height = 620
    margin_left = 92
    margin_right = 48
    margin_top = 82
    margin_bottom = 128
    plot_width = width - margin_left - margin_right
    plot_height = height - margin_top - margin_bottom
    values = [float(row[value_key]) for row in rows]
    max_value = 1.0 if percent else max(values) * 1.12
    max_value = max(max_value, 1.0)
    slot_width = plot_width / max(len(rows), 1)
    bar_width = min(92, slot_width * 0.58)
    grid_values = [0.0, 0.25, 0.5, 0.75, 1.0] if percent else numeric_grid(max_value)

    svg = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#ffffff"/>',
        f'<text x="{width / 2}" y="44" text-anchor="middle" font-family="Arial, sans-serif" font-size="24" font-weight="700" fill="#17212b">{escape_xml(title)}</text>',
        f'<text x="24" y="{margin_top + plot_height / 2}" transform="rotate(-90 24 {margin_top + plot_height / 2})" text-anchor="middle" font-family="Arial, sans-serif" font-size="15" fill="#17212b">{escape_xml(y_label)}</text>',
    ]

    for tick in grid_values:
        y = margin_top + plot_height - (tick / max_value) * plot_height
        label = f"{tick * 100:.0f}%" if percent else f"{tick:.0f}"
        svg.extend(
            [
                f'<line x1="{margin_left}" y1="{y:.2f}" x2="{width - margin_right}" y2="{y:.2f}" stroke="#dfe5ea" stroke-width="1"/>',
                f'<text x="{margin_left - 12}" y="{y + 5:.2f}" text-anchor="end" font-family="Arial, sans-serif" font-size="13" fill="#17212b">{label}</text>',
            ]
        )

    for index, row in enumerate(rows):
        value = float(row[value_key])
        x_center = margin_left + slot_width * index + slot_width / 2
        bar_height = (value / max_value) * plot_height
        x = x_center - bar_width / 2
        y = margin_top + plot_height - bar_height
        label = label_map.get(row[label_key], str(row[label_key]))
        value_label = f"{value * 100:.0f}%" if percent else f"{value:.1f}"

        svg.extend(
            [
                f'<rect x="{x:.2f}" y="{y:.2f}" width="{bar_width:.2f}" height="{bar_height:.2f}" rx="3" fill="{color}"/>',
                f'<text x="{x_center:.2f}" y="{y - 8:.2f}" text-anchor="middle" font-family="Arial, sans-serif" font-size="13" fill="#17212b">{value_label}</text>',
                f'<text x="{x_center:.2f}" y="{margin_top + plot_height + 34}" transform="rotate(-28 {x_center:.2f} {margin_top + plot_height + 34})" text-anchor="end" font-family="Arial, sans-serif" font-size="13" fill="#17212b">{escape_xml(label)}</text>',
            ]
        )

    svg.extend(
        [
            f'<line x1="{margin_left}" y1="{margin_top + plot_height}" x2="{width - margin_right}" y2="{margin_top + plot_height}" stroke="#17212b" stroke-width="1"/>',
            f'<line x1="{margin_left}" y1="{margin_top}" x2="{margin_left}" y2="{margin_top + plot_height}" stroke="#17212b" stroke-width="1"/>',
            "</svg>",
        ]
    )
    path.write_text("\n".join(svg), encoding="utf-8")


def write_findings(
    attempts: list[dict[str, Any]],
    by_instance: list[dict[str, Any]],
    by_depth: list[dict[str, Any]],
    aggregate: list[dict[str, Any]],
) -> None:
    all_attempts = aggregate[0]
    best_attempts = aggregate[1]
    misses = [row for row in attempts if not row["exact_match"]]
    slowest = max(attempts, key=lambda row: row["elapsed_seconds"])

    lines = [
        "# QAOA Small-Matrix Findings",
        "",
        "This file is generated by `analysis/qaoa_validation_analysis.py`.",
        "",
        "## Scope",
        "",
        f"- QAOA attempts: {all_attempts['attempts']}",
        f"- Exported QUBO instances: {all_attempts['instances']}",
        "- QAOA depths: "
        + ", ".join(f"p={row['reps']}" for row in by_depth),
        "- Seeds per depth: 5",
        "",
        "## Aggregate Result",
        "",
        f"- Feasible assignments: {all_attempts['feasible_count']}/{all_attempts['attempts']} "
        f"({percent(all_attempts['feasible_rate'])}).",
        f"- Exact matches across all attempts: {all_attempts['exact_match_count']}/{all_attempts['attempts']} "
        f"({percent(all_attempts['exact_match_rate'])}).",
        f"- Best attempt per instance matched the exact solution in "
        f"{best_attempts['exact_match_count']}/{best_attempts['instances']} instances "
        f"({percent(best_attempts['exact_match_rate'])}).",
        f"- Average attempt runtime: {all_attempts['average_elapsed_seconds']:.3f} seconds.",
        "",
        "## Depth Sensitivity",
        "",
    ]

    for row in by_depth:
        lines.append(
            f"- p={row['reps']}: {row['exact_matches']}/{row['attempts']} exact matches "
            f"({percent(row['exact_match_rate'])}), average runtime "
            f"{row['average_elapsed_seconds']:.3f} seconds."
        )

    lines.extend(["", "## Instance Sensitivity", ""])

    for row in by_instance:
        lines.append(
            f"- {row['scenario']} ({row['variable_count']} variables): "
            f"{row['exact_matches']}/{row['attempts']} exact matches "
            f"({percent(row['exact_match_rate'])}), average runtime "
            f"{row['average_elapsed_seconds']:.3f} seconds."
        )

    lines.extend(["", "## Non-Exact Attempts", ""])

    if not misses:
        lines.append("- None.")
    else:
        for row in misses:
            lines.append(
                f"- {row['instance_id']}, p={row['reps']}, seed={row['seed']}: "
                f"relative gap {percent(row['relative_gap'])}, objective gap "
                f"{row['objective_gap']:.6f}."
            )

    lines.extend(
        [
            "",
            "## Runtime Note",
            "",
            f"- Slowest attempt: {slowest['instance_id']}, p={slowest['reps']}, "
            f"seed={slowest['seed']}, {slowest['elapsed_seconds']:.3f} seconds.",
            "- These are statevector-simulated QAOA results. They validate the QUBO-to-QAOA path, "
            "not scalable quantum advantage.",
            "",
        ]
    )

    (PROCESSED_DIR / "key_findings.md").write_text("\n".join(lines), encoding="utf-8")


def group_by(rows: list[dict[str, Any]], key: str) -> dict[Any, list[dict[str, Any]]]:
    grouped: dict[Any, list[dict[str, Any]]] = defaultdict(list)

    for row in rows:
        grouped[row[key]].append(row)

    return grouped


def count_true(rows: list[dict[str, Any]], key: str) -> int:
    return sum(1 for row in rows if row[key])


def mean(values: Any) -> float:
    materialized = list(values)
    return sum(materialized) / len(materialized) if materialized else 0.0


def numeric_grid(max_value: float) -> list[float]:
    step = max_value / 4
    return [round(step * index, 2) for index in range(5)]


def round_number(value: float) -> float:
    return round(value, 6)


def percent(value: float) -> str:
    return f"{value * 100:.2f}%"


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return

    fieldnames = list(rows[0].keys())

    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def escape_xml(value: Any) -> str:
    return (
        str(value)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


if __name__ == "__main__":
    raise SystemExit(main())
