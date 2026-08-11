#!/usr/bin/env python
"""Generate processed QUBO/QAOA analysis tables and lightweight SVG figures."""

from __future__ import annotations

import csv
import json
import math
from collections import defaultdict
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
PROCESSED_DIR = REPO_ROOT / "results" / "processed" / "qubo_analysis"
FIGURES_DIR = REPO_ROOT / "results" / "figures" / "qubo_analysis"

QUBO_INPUTS = [
    ("reduced_comparison", REPO_ROOT / "results" / "raw" / "v1_qubo_reduced_comparison" / "summary.csv"),
    ("sensitivity", REPO_ROOT / "results" / "raw" / "v1_qubo_sensitivity" / "summary.csv"),
    (
        "sequencing_comparison",
        REPO_ROOT / "results" / "raw" / "v1_qubo_sequencing_comparison" / "summary.csv",
    ),
]

QAOA_INPUT = REPO_ROOT / "results" / "raw" / "v1_qaoa_validation" / "summary.csv"

SCENARIO_ORDER = [
    "baseline_small",
    "steady_load",
    "burst_load",
    "critical_priority",
    "heterogeneous_workers",
]

PRIMARY_STRATEGIES = [
    "qubo_batch_exact",
    "qubo_batch_exact_critical_focused",
    "qubo_batch_exact_sequencing",
    "priority_aware",
    "shortest_queue",
]

SENSITIVITY_STRATEGIES = [
    "qubo_batch_exact",
    "qubo_batch_exact_deadline_focused",
    "qubo_batch_exact_critical_focused",
    "qubo_batch_exact_low_balance",
]

NUMERIC_COLUMNS = {
    "total_events",
    "makespan_ms",
    "throughput_events_per_second",
    "average_latency_ms",
    "p95_latency_ms",
    "p99_latency_ms",
    "max_latency_ms",
    "average_waiting_time_ms",
    "max_waiting_time_ms",
    "deadline_hit_rate",
    "critical_deadline_hit_rate",
    "starvation_count",
    "event_count_fairness_jain_index",
    "worker_utilization_fairness_jain_index",
    "objective_total_cost",
    "objective_average_cost_per_event",
    "batch_index",
    "event_count",
    "worker_count",
    "variable_count",
    "best_reps",
    "best_seed",
    "exact_objective",
    "qaoa_objective",
    "objective_gap",
    "relative_gap",
    "constraint_violations",
    "elapsed_seconds",
}

STRATEGY_LABELS = {
    "qubo_batch_exact": "QUBO v0",
    "qubo_batch_exact_deadline_focused": "Deadline focused",
    "qubo_batch_exact_critical_focused": "Critical focused",
    "qubo_batch_exact_low_balance": "Low balance",
    "qubo_batch_exact_sequencing": "QUBO v1 sequencing",
    "priority_aware": "Priority aware",
    "shortest_queue": "Shortest queue",
    "min_cost_greedy": "Min-cost greedy",
    "least_loaded": "Least loaded",
    "round_robin": "Round robin",
}

FIGURE_TEXT = {
    "es": {
        "suffix": "",
        "scenario_labels": {
            "baseline_small": "Base",
            "steady_load": "Carga estable",
            "burst_load": "Carga en ráfagas",
            "critical_priority": "Prioridad crítica",
            "heterogeneous_workers": "Trabajadores heterogéneos",
        },
        "strategy_labels": {
            "qubo_batch_exact": "QUBO v0",
            "qubo_batch_exact_deadline_focused": "QUBO plazo",
            "qubo_batch_exact_critical_focused": "QUBO crítico",
            "qubo_batch_exact_low_balance": "QUBO bajo balance",
            "qubo_batch_exact_sequencing": "QUBO v1 sec.",
            "priority_aware": "Prioridad",
            "shortest_queue": "Cola más corta",
            "min_cost_greedy": "Costo mínimo",
            "least_loaded": "Menor carga",
            "round_robin": "Round robin",
        },
        "objective_title": "Costo objetivo promedio por evento",
        "objective_y": "Costo por evento",
        "critical_deadline_title": "Tasa de cumplimiento de plazos críticos",
        "critical_deadline_y": "Tasa de cumplimiento",
        "improvement_title": "Mejora de QUBO v1 frente a QUBO v0",
        "improvement_y": "Mejora (%)",
        "qaoa_gap_title": "Brecha objetivo de QAOA frente al solver exacto",
        "qaoa_gap_y": "Brecha objetivo",
    },
    "en": {
        "suffix": "_en",
        "scenario_labels": {
            "baseline_small": "Baseline",
            "steady_load": "Steady load",
            "burst_load": "Burst load",
            "critical_priority": "Critical priority",
            "heterogeneous_workers": "Heterogeneous workers",
        },
        "strategy_labels": STRATEGY_LABELS,
        "objective_title": "Objective average cost per event",
        "objective_y": "Cost per event",
        "critical_deadline_title": "Critical deadline hit rate",
        "critical_deadline_y": "Hit rate",
        "improvement_title": "QUBO v1 improvement vs QUBO v0",
        "improvement_y": "Improvement (%)",
        "qaoa_gap_title": "QAOA objective gap vs exact solver",
        "qaoa_gap_y": "Objective gap",
    },
}

COLORS = {
    "qubo_batch_exact": "#2f5f98",
    "qubo_batch_exact_deadline_focused": "#8b6f24",
    "qubo_batch_exact_critical_focused": "#9b3b3b",
    "qubo_batch_exact_low_balance": "#6d5f8f",
    "qubo_batch_exact_sequencing": "#21745f",
    "priority_aware": "#8f4f21",
    "shortest_queue": "#3d6b8f",
    "positive": "#21745f",
    "negative": "#9b3b3b",
    "neutral": "#5f6b73",
}


def main() -> int:
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)

    all_qubo_rows = load_qubo_rows()
    qaoa_rows = load_csv(QAOA_INPUT) if QAOA_INPUT.exists() else []

    sequencing_rows = filter_experiment(all_qubo_rows, "sequencing_comparison")
    sensitivity_rows = filter_experiment(all_qubo_rows, "sensitivity")

    write_csv(PROCESSED_DIR / "all_qubo_runs.csv", all_qubo_rows)
    write_csv(PROCESSED_DIR / "sequencing_strategy_comparison.csv", sequencing_table(sequencing_rows))
    write_csv(PROCESSED_DIR / "sequencing_best_by_scenario.csv", best_by_scenario(sequencing_rows))
    write_csv(PROCESSED_DIR / "qubo_v0_v1_delta.csv", qubo_v0_v1_delta(sequencing_rows))
    write_csv(PROCESSED_DIR / "qubo_sensitivity_rankings.csv", sensitivity_rankings(sensitivity_rows))
    write_csv(PROCESSED_DIR / "qaoa_validation_instances.csv", qaoa_instances(qaoa_rows))
    write_csv(PROCESSED_DIR / "qaoa_validation_aggregate.csv", qaoa_aggregate(qaoa_rows))

    write_figures(sequencing_rows, qaoa_rows)
    write_key_findings(sequencing_rows, sensitivity_rows, qaoa_rows)

    print(f"Processed QUBO rows: {len(all_qubo_rows)}")
    print(f"Processed QAOA rows: {len(qaoa_rows)}")
    print(f"Tables: {PROCESSED_DIR}")
    print(f"Figures: {FIGURES_DIR}")
    return 0


def load_qubo_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []

    for experiment, path in QUBO_INPUTS:
        if not path.exists():
            continue

        for row in load_csv(path):
            row["experiment"] = experiment
            rows.append(row)

    return rows


def load_csv(path: Path) -> list[dict[str, Any]]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        return [normalize_row(row) for row in reader]


def normalize_row(row: dict[str, str]) -> dict[str, Any]:
    normalized: dict[str, Any] = {}

    for key, value in row.items():
        if key in NUMERIC_COLUMNS:
            normalized[key] = parse_number(value)
        elif value in {"True", "False"}:
            normalized[key] = value == "True"
        else:
            normalized[key] = value

    return normalized


def filter_experiment(rows: list[dict[str, Any]], experiment: str) -> list[dict[str, Any]]:
    return [row for row in rows if row.get("experiment") == experiment]


def sequencing_table(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    table = []

    for row in sorted(rows, key=lambda item: (scenario_index(item["scenario"]), item["strategy"])):
        table.append(
            {
                "scenario": row["scenario"],
                "strategy": row["strategy"],
                "objective_average_cost_per_event": row["objective_average_cost_per_event"],
                "average_latency_ms": row["average_latency_ms"],
                "p95_latency_ms": row["p95_latency_ms"],
                "deadline_hit_rate": row["deadline_hit_rate"],
                "critical_deadline_hit_rate": row["critical_deadline_hit_rate"],
                "worker_utilization_fairness_jain_index": row[
                    "worker_utilization_fairness_jain_index"
                ],
                "makespan_ms": row["makespan_ms"],
                "throughput_events_per_second": row["throughput_events_per_second"],
            }
        )

    return table


def best_by_scenario(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    table = []

    for scenario, scenario_rows in group_by(rows, "scenario").items():
        ranked = sorted(scenario_rows, key=lambda row: row["objective_average_cost_per_event"])
        best_value = ranked[0]["objective_average_cost_per_event"]

        for rank, row in enumerate(ranked, start=1):
            value = row["objective_average_cost_per_event"]
            table.append(
                {
                    "scenario": scenario,
                    "rank": rank,
                    "strategy": row["strategy"],
                    "objective_average_cost_per_event": value,
                    "gap_to_best": round_number(value - best_value),
                    "gap_to_best_pct": percent_delta(value, best_value),
                    "deadline_hit_rate": row["deadline_hit_rate"],
                    "critical_deadline_hit_rate": row["critical_deadline_hit_rate"],
                    "average_latency_ms": row["average_latency_ms"],
                }
            )

    return sorted(table, key=lambda row: (scenario_index(row["scenario"]), row["rank"]))


def qubo_v0_v1_delta(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    table = []
    by_scenario = group_by(rows, "scenario")

    for scenario in sorted(by_scenario, key=scenario_index):
        indexed = {row["strategy"]: row for row in by_scenario[scenario]}

        if "qubo_batch_exact" not in indexed or "qubo_batch_exact_sequencing" not in indexed:
            continue

        v0 = indexed["qubo_batch_exact"]
        v1 = indexed["qubo_batch_exact_sequencing"]
        priority = indexed.get("priority_aware")
        shortest = indexed.get("shortest_queue")
        ranked = sorted(by_scenario[scenario], key=lambda row: row["objective_average_cost_per_event"])
        rank_by_strategy = {row["strategy"]: index + 1 for index, row in enumerate(ranked)}

        table.append(
            {
                "scenario": scenario,
                "qubo_v0_objective": v0["objective_average_cost_per_event"],
                "qubo_v1_objective": v1["objective_average_cost_per_event"],
                "qubo_v1_rank": rank_by_strategy["qubo_batch_exact_sequencing"],
                "qubo_v1_improvement_vs_v0": round_number(
                    v0["objective_average_cost_per_event"] - v1["objective_average_cost_per_event"]
                ),
                "qubo_v1_improvement_vs_v0_pct": percent_improvement(
                    v0["objective_average_cost_per_event"], v1["objective_average_cost_per_event"]
                ),
                "priority_aware_objective": value_or_none(priority, "objective_average_cost_per_event"),
                "qubo_v1_gap_vs_priority_aware": delta_or_none(
                    v1, priority, "objective_average_cost_per_event"
                ),
                "shortest_queue_objective": value_or_none(shortest, "objective_average_cost_per_event"),
                "qubo_v1_gap_vs_shortest_queue": delta_or_none(
                    v1, shortest, "objective_average_cost_per_event"
                ),
                "qubo_v1_critical_deadline_hit_rate": v1["critical_deadline_hit_rate"],
                "priority_aware_critical_deadline_hit_rate": value_or_none(
                    priority, "critical_deadline_hit_rate"
                ),
            }
        )

    return table


def sensitivity_rankings(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    table = []

    for scenario, scenario_rows in group_by(rows, "scenario").items():
        qbo_rows = [row for row in scenario_rows if row["strategy"] in SENSITIVITY_STRATEGIES]
        ranked = sorted(qbo_rows, key=lambda row: row["objective_average_cost_per_event"])
        best_value = ranked[0]["objective_average_cost_per_event"]

        for rank, row in enumerate(ranked, start=1):
            table.append(
                {
                    "scenario": scenario,
                    "rank": rank,
                    "strategy": row["strategy"],
                    "objective_average_cost_per_event": row["objective_average_cost_per_event"],
                    "gap_to_best_qubo_profile": round_number(
                        row["objective_average_cost_per_event"] - best_value
                    ),
                    "deadline_hit_rate": row["deadline_hit_rate"],
                    "critical_deadline_hit_rate": row["critical_deadline_hit_rate"],
                    "worker_utilization_fairness_jain_index": row[
                        "worker_utilization_fairness_jain_index"
                    ],
                }
            )

    return sorted(table, key=lambda row: (scenario_index(row["scenario"]), row["rank"]))


def qaoa_instances(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "instance_id": row["instance_id"],
            "scenario": row["scenario"],
            "variable_count": row["variable_count"],
            "best_reps": row["best_reps"],
            "best_seed": row["best_seed"],
            "exact_objective": row["exact_objective"],
            "qaoa_objective": row["qaoa_objective"],
            "objective_gap": row["objective_gap"],
            "relative_gap": row["relative_gap"],
            "feasible": row["feasible"],
            "exact_match": row["exact_match"],
            "same_assignment_as_exact": row["same_assignment_as_exact"],
            "elapsed_seconds": row["elapsed_seconds"],
        }
        for row in rows
    ]


def qaoa_aggregate(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not rows:
        return []

    exact_matches = sum(1 for row in rows if row["exact_match"])
    feasible = sum(1 for row in rows if row["feasible"])
    same_assignment = sum(1 for row in rows if row["same_assignment_as_exact"])

    return [
        {
            "instance_count": len(rows),
            "feasible_count": feasible,
            "feasible_rate": feasible / len(rows),
            "exact_match_count": exact_matches,
            "exact_match_rate": exact_matches / len(rows),
            "same_assignment_count": same_assignment,
            "same_assignment_rate": same_assignment / len(rows),
            "average_objective_gap": average(row["objective_gap"] for row in rows),
            "max_objective_gap": max(row["objective_gap"] for row in rows),
            "average_elapsed_seconds": average(row["elapsed_seconds"] for row in rows),
            "max_variable_count_completed": max(row["variable_count"] for row in rows),
        }
    ]


def write_figures(sequencing_rows: list[dict[str, Any]], qaoa_rows: list[dict[str, Any]]) -> None:
    for text in FIGURE_TEXT.values():
        write_figure_set(sequencing_rows, qaoa_rows, text)


def write_figure_set(
    sequencing_rows: list[dict[str, Any]],
    qaoa_rows: list[dict[str, Any]],
    text: dict[str, Any],
) -> None:
    objective_data = grouped_metric(
        sequencing_rows,
        PRIMARY_STRATEGIES,
        "objective_average_cost_per_event",
    )
    critical_deadline_data = grouped_metric(
        sequencing_rows,
        PRIMARY_STRATEGIES,
        "critical_deadline_hit_rate",
    )
    delta_rows = qubo_v0_v1_delta(sequencing_rows)
    suffix = text["suffix"]

    write_text(
        FIGURES_DIR / f"objective_cost_by_scenario{suffix}.svg",
        grouped_bar_svg(
            objective_data,
            title=text["objective_title"],
            y_label=text["objective_y"],
            max_value=None,
            value_formatter=lambda value: f"{value:.0f}",
            scenario_labels=text["scenario_labels"],
            series_labels=text["strategy_labels"],
        ),
    )
    write_text(
        FIGURES_DIR / f"critical_deadline_hit_rate_by_scenario{suffix}.svg",
        grouped_bar_svg(
            critical_deadline_data,
            title=text["critical_deadline_title"],
            y_label=text["critical_deadline_y"],
            max_value=1.0,
            value_formatter=lambda value: f"{value:.2f}",
            scenario_labels=text["scenario_labels"],
            series_labels=text["strategy_labels"],
        ),
    )
    write_text(
        FIGURES_DIR / f"qubo_v1_improvement_vs_v0{suffix}.svg",
        single_bar_svg(
            [
                {
                    "label": text["scenario_labels"].get(row["scenario"], row["scenario"]),
                    "value": row["qubo_v1_improvement_vs_v0_pct"],
                }
                for row in delta_rows
            ],
            title=text["improvement_title"],
            y_label=text["improvement_y"],
        ),
    )

    if qaoa_rows:
        write_text(
            FIGURES_DIR / f"qaoa_objective_gap_by_instance{suffix}.svg",
            single_bar_svg(
                [
                    {
                        "label": text["scenario_labels"].get(row["scenario"], row["scenario"]),
                        "value": row["objective_gap"],
                    }
                    for row in qaoa_rows
                ],
                title=text["qaoa_gap_title"],
                y_label=text["qaoa_gap_y"],
                value_formatter=lambda value: f"{value:.1e}",
            ),
        )


def write_key_findings(
    sequencing_rows: list[dict[str, Any]],
    sensitivity_rows: list[dict[str, Any]],
    qaoa_rows: list[dict[str, Any]],
) -> None:
    delta_rows = qubo_v0_v1_delta(sequencing_rows)
    best_rows = [row for row in best_by_scenario(sequencing_rows) if row["rank"] == 1]
    sensitivity_best = [row for row in sensitivity_rankings(sensitivity_rows) if row["rank"] == 1]
    qaoa_summary = qaoa_aggregate(qaoa_rows)

    v1_better_than_v0 = [
        row for row in delta_rows if row["qubo_v1_improvement_vs_v0"] > 0
    ]
    v1_best_scenarios = [
        row["scenario"]
        for row in best_rows
        if row["strategy"] == "qubo_batch_exact_sequencing"
    ]
    positive_improvements = [
        row["qubo_v1_improvement_vs_v0_pct"]
        for row in delta_rows
        if row["qubo_v1_improvement_vs_v0_pct"] > 0
    ]

    lines = [
        "# QUBO/QAOA Technical Findings",
        "",
        "This generated summary is a technical companion for the experiment outputs.",
        "It is not a peer-reviewed analysis by itself.",
        "",
        "## Main QUBO Comparison",
        "",
        f"- QUBO v1 sequencing improved over QUBO v0 in {len(v1_better_than_v0)}/{len(delta_rows)} scenarios.",
        f"- QUBO v1 sequencing was the best overall strategy in {len(v1_best_scenarios)}/{len(best_rows)} scenarios.",
    ]

    if v1_best_scenarios:
        lines.append(f"- Scenarios where QUBO v1 was best: {', '.join(v1_best_scenarios)}.")

    if positive_improvements:
        lines.append(
            "- Average positive improvement of QUBO v1 over QUBO v0: "
            f"{average(positive_improvements):.2f}%."
        )

    lines.extend(
        [
            "",
            "## Best Strategy By Scenario",
            "",
            "| scenario | best strategy | objective cost/event | critical deadline hit rate |",
            "| --- | --- | ---: | ---: |",
        ]
    )

    for row in best_rows:
        lines.append(
            "| {scenario} | {strategy} | {objective_average_cost_per_event:.4f} | "
            "{critical_deadline_hit_rate:.4f} |".format(**row)
        )

    lines.extend(
        [
            "",
            "## QUBO v1 vs QUBO v0",
            "",
            "| scenario | v0 | v1 | improvement | improvement % | v1 rank |",
            "| --- | ---: | ---: | ---: | ---: | ---: |",
        ]
    )

    for row in delta_rows:
        lines.append(
            "| {scenario} | {qubo_v0_objective:.4f} | {qubo_v1_objective:.4f} | "
            "{qubo_v1_improvement_vs_v0:.4f} | {qubo_v1_improvement_vs_v0_pct:.2f} | "
            "{qubo_v1_rank} |".format(**row)
        )

    lines.extend(
        [
            "",
            "## Sensitivity",
            "",
            "| scenario | best QUBO profile | objective cost/event | critical deadline hit rate |",
            "| --- | --- | ---: | ---: |",
        ]
    )

    for row in sensitivity_best:
        lines.append(
            "| {scenario} | {strategy} | {objective_average_cost_per_event:.4f} | "
            "{critical_deadline_hit_rate:.4f} |".format(**row)
        )

    if qaoa_summary:
        qaoa = qaoa_summary[0]
        lines.extend(
            [
                "",
                "## QAOA Validation",
                "",
                f"- Completed QAOA validation instances: {qaoa['instance_count']}.",
                f"- Feasible QAOA solutions: {qaoa['feasible_count']}/{qaoa['instance_count']}.",
                f"- Exact objective matches: {qaoa['exact_match_count']}/{qaoa['instance_count']}.",
                f"- Maximum completed variable count: {qaoa['max_variable_count_completed']}.",
                f"- Average elapsed time per completed instance: {qaoa['average_elapsed_seconds']:.2f} seconds.",
                "- The 12-variable steady-load instance is documented as an extended runtime limit.",
            ]
        )

    lines.extend(
        [
            "",
            "## Generated Assets",
            "",
            "- `results/processed/qubo_analysis/sequencing_strategy_comparison.csv`",
            "- `results/processed/qubo_analysis/sequencing_best_by_scenario.csv`",
            "- `results/processed/qubo_analysis/qubo_v0_v1_delta.csv`",
            "- `results/processed/qubo_analysis/qubo_sensitivity_rankings.csv`",
            "- `results/processed/qubo_analysis/qaoa_validation_aggregate.csv`",
            "- `results/figures/qubo_analysis/objective_cost_by_scenario.svg`",
            "- `results/figures/qubo_analysis/critical_deadline_hit_rate_by_scenario.svg`",
            "- `results/figures/qubo_analysis/qubo_v1_improvement_vs_v0.svg`",
            "- `results/figures/qubo_analysis/qaoa_objective_gap_by_instance.svg`",
            "- `results/figures/qubo_analysis/*_en.svg` English technical copies.",
        ]
    )

    write_text(PROCESSED_DIR / "key_findings.md", "\n".join(lines) + "\n")


def grouped_metric(
    rows: list[dict[str, Any]], strategies: list[str], metric: str
) -> list[dict[str, Any]]:
    indexed = {(row["scenario"], row["strategy"]): row for row in rows}
    groups = []

    for scenario in SCENARIO_ORDER:
        values = []

        for strategy in strategies:
            row = indexed.get((scenario, strategy))
            if row is not None:
                values.append({"series": strategy, "value": row[metric]})

        if values:
            groups.append({"label": scenario, "values": values})

    return groups


def grouped_bar_svg(
    groups: list[dict[str, Any]],
    title: str,
    y_label: str,
    max_value: float | None,
    value_formatter,
    scenario_labels: dict[str, str],
    series_labels: dict[str, str],
) -> str:
    width = 1280
    height = 720
    margin_left = 90
    margin_right = 30
    margin_top = 130
    margin_bottom = 175
    plot_width = width - margin_left - margin_right
    plot_height = height - margin_top - margin_bottom

    series = []
    for group in groups:
        for value in group["values"]:
            if value["series"] not in series:
                series.append(value["series"])

    values = [item["value"] for group in groups for item in group["values"]]
    y_max = max_value or nice_max(max(values) if values else 1)
    y_min = 0
    group_width = plot_width / max(len(groups), 1)
    bar_gap = 5
    bar_width = max(10, (group_width - 34) / max(len(series), 1) - bar_gap)

    parts = svg_header(width, height)
    parts.append(svg_text(width / 2, 34, title, size=22, anchor="middle", weight="700"))
    parts.extend(legend_parts(series, series_labels, x=180, y=68, columns=3, column_width=315))
    parts.append(svg_text(22, margin_top + plot_height / 2, y_label, size=14, rotate=-90))
    parts.extend(axis_parts(margin_left, margin_top, plot_width, plot_height, y_min, y_max))

    for group_index, group in enumerate(groups):
        x0 = margin_left + group_index * group_width + 16
        value_by_series = {item["series"]: item["value"] for item in group["values"]}

        for series_index, series_name in enumerate(series):
            if series_name not in value_by_series:
                continue

            value = value_by_series[series_name]
            bar_height = value_to_height(value, y_min, y_max, plot_height)
            x = x0 + series_index * (bar_width + bar_gap)
            y = margin_top + plot_height - bar_height
            color = COLORS.get(series_name, "#607080")

            parts.append(
                f'<rect x="{x:.2f}" y="{y:.2f}" width="{bar_width:.2f}" '
                f'height="{bar_height:.2f}" fill="{color}" rx="2" />'
            )

        label_x = margin_left + group_index * group_width + group_width / 2
        label = scenario_labels.get(group["label"], group["label"])
        parts.append(svg_text(label_x, height - 96, label, size=12, anchor="middle", rotate=-24))

    parts.extend(y_tick_labels(margin_left, margin_top, plot_height, y_min, y_max, value_formatter))
    parts.append("</svg>")
    return "\n".join(parts)


def single_bar_svg(
    rows: list[dict[str, Any]],
    title: str,
    y_label: str,
    value_formatter=lambda value: f"{value:.2f}",
) -> str:
    width = 980
    height = 540
    margin_left = 80
    margin_right = 30
    margin_top = 70
    margin_bottom = 130
    plot_width = width - margin_left - margin_right
    plot_height = height - margin_top - margin_bottom
    values = [row["value"] for row in rows] or [0]
    min_value = min(0, min(values))
    max_value = max(0, max(values))

    if math.isclose(min_value, max_value):
        max_value = max_value + 1

    y_min = nice_floor(min_value)
    y_max = nice_max(max_value)
    bar_width = max(18, plot_width / max(len(rows), 1) * 0.55)
    group_width = plot_width / max(len(rows), 1)
    zero_y = value_to_y(0, y_min, y_max, margin_top, plot_height)

    parts = svg_header(width, height)
    parts.append(svg_text(width / 2, 34, title, size=22, anchor="middle", weight="700"))
    parts.append(svg_text(22, margin_top + plot_height / 2, y_label, size=14, rotate=-90))
    parts.extend(axis_parts(margin_left, margin_top, plot_width, plot_height, y_min, y_max))
    parts.append(
        f'<line x1="{margin_left}" y1="{zero_y:.2f}" x2="{margin_left + plot_width}" '
        f'y2="{zero_y:.2f}" stroke="#4b5563" stroke-width="1" />'
    )

    for index, row in enumerate(rows):
        value = row["value"]
        x = margin_left + index * group_width + (group_width - bar_width) / 2
        y_value = value_to_y(value, y_min, y_max, margin_top, plot_height)
        y = min(y_value, zero_y)
        height_value = abs(zero_y - y_value)
        color = COLORS["positive"] if value >= 0 else COLORS["negative"]

        parts.append(
            f'<rect x="{x:.2f}" y="{y:.2f}" width="{bar_width:.2f}" '
            f'height="{height_value:.2f}" fill="{color}" rx="2" />'
        )
        parts.append(svg_text(x + bar_width / 2, height - 78, row["label"], size=12, anchor="middle", rotate=-25))

    parts.extend(y_tick_labels(margin_left, margin_top, plot_height, y_min, y_max, value_formatter))
    parts.append("</svg>")
    return "\n".join(parts)


def svg_header(width: int, height: int) -> list[str]:
    return [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" role="img">',
        '<rect width="100%" height="100%" fill="#ffffff" />',
        '<style>text{font-family:Arial,Helvetica,sans-serif;fill:#17202a}</style>',
    ]


def axis_parts(
    margin_left: float,
    margin_top: float,
    plot_width: float,
    plot_height: float,
    y_min: float,
    y_max: float,
) -> list[str]:
    parts = [
        f'<line x1="{margin_left}" y1="{margin_top}" x2="{margin_left}" '
        f'y2="{margin_top + plot_height}" stroke="#243241" stroke-width="1.2" />',
        f'<line x1="{margin_left}" y1="{margin_top + plot_height}" '
        f'x2="{margin_left + plot_width}" y2="{margin_top + plot_height}" '
        f'stroke="#243241" stroke-width="1.2" />',
    ]

    for index in range(6):
        value = y_min + (y_max - y_min) * index / 5
        y = value_to_y(value, y_min, y_max, margin_top, plot_height)
        parts.append(
            f'<line x1="{margin_left}" y1="{y:.2f}" x2="{margin_left + plot_width}" '
            f'y2="{y:.2f}" stroke="#e5e7eb" stroke-width="1" />'
        )

    return parts


def y_tick_labels(
    margin_left: float,
    margin_top: float,
    plot_height: float,
    y_min: float,
    y_max: float,
    formatter,
) -> list[str]:
    parts = []

    for index in range(6):
        value = y_min + (y_max - y_min) * index / 5
        y = value_to_y(value, y_min, y_max, margin_top, plot_height)
        parts.append(svg_text(margin_left - 10, y + 4, formatter(value), size=11, anchor="end"))

    return parts


def legend_parts(
    series: list[str],
    series_labels: dict[str, str],
    x: float,
    y: float,
    columns: int,
    column_width: float,
) -> list[str]:
    parts = []
    row_height = 24

    for index, series_name in enumerate(series):
        column = index % columns
        row = index // columns
        item_x = x + column * column_width
        item_y = y + row * row_height
        color = COLORS.get(series_name, "#607080")
        label = series_labels.get(series_name, series_name)
        parts.append(
            f'<rect x="{item_x}" y="{item_y - 11}" width="14" height="14" '
            f'fill="{color}" rx="2" />'
        )
        parts.append(svg_text(item_x + 22, item_y, label, size=12))

    return parts


def svg_text(
    x: float,
    y: float,
    text: str,
    size: int = 12,
    anchor: str = "start",
    weight: str = "400",
    rotate: float | None = None,
) -> str:
    escaped = escape_xml(text)
    transform = f' transform="rotate({rotate:.2f} {x:.2f} {y:.2f})"' if rotate is not None else ""
    return (
        f'<text x="{x:.2f}" y="{y:.2f}" font-size="{size}" '
        f'font-weight="{weight}" text-anchor="{anchor}"{transform}>{escaped}</text>'
    )


def group_by(rows: list[dict[str, Any]], key: str) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)

    for row in rows:
        grouped[row[key]].append(row)

    return dict(grouped)


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    if not rows:
        path.write_text("", encoding="utf-8")
        return

    fieldnames = list(rows[0].keys())

    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows({key: csv_value(value) for key, value in row.items()} for row in rows)


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def parse_number(value: str) -> int | float | None:
    if value == "":
        return None

    number = float(value)

    if number.is_integer():
        return int(number)

    return number


def percent_delta(value: float, baseline: float) -> float:
    if baseline == 0:
        return 0.0

    return round_number((value - baseline) / baseline * 100)


def percent_improvement(old_value: float, new_value: float) -> float:
    if old_value == 0:
        return 0.0

    return round_number((old_value - new_value) / old_value * 100)


def delta_or_none(left: dict[str, Any], right: dict[str, Any] | None, metric: str) -> float | None:
    if right is None:
        return None

    return round_number(left[metric] - right[metric])


def value_or_none(row: dict[str, Any] | None, key: str) -> Any:
    if row is None:
        return None

    return row[key]


def average(values: Any) -> float:
    materialized = list(values)

    if not materialized:
        return 0.0

    return sum(materialized) / len(materialized)


def round_number(value: float | int | None, digits: int = 6) -> float | int | None:
    if value is None:
        return None

    if isinstance(value, int):
        return value

    return round(value, digits)


def nice_max(value: float) -> float:
    if value <= 0:
        return 1.0

    magnitude = 10 ** math.floor(math.log10(value))
    normalized = value / magnitude

    if normalized <= 1:
        nice = 1
    elif normalized <= 2:
        nice = 2
    elif normalized <= 5:
        nice = 5
    else:
        nice = 10

    return nice * magnitude


def nice_floor(value: float) -> float:
    if value >= 0:
        return 0.0

    return -nice_max(abs(value))


def value_to_height(value: float, y_min: float, y_max: float, plot_height: float) -> float:
    return (value - y_min) / (y_max - y_min) * plot_height


def value_to_y(
    value: float,
    y_min: float,
    y_max: float,
    margin_top: float,
    plot_height: float,
) -> float:
    return margin_top + plot_height - value_to_height(value, y_min, y_max, plot_height)


def scenario_index(scenario: str) -> int:
    try:
        return SCENARIO_ORDER.index(scenario)
    except ValueError:
        return len(SCENARIO_ORDER)


def csv_value(value: Any) -> Any:
    if isinstance(value, (dict, list)):
        return json.dumps(value, sort_keys=True)

    return value


def escape_xml(value: str) -> str:
    return (
        str(value)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


if __name__ == "__main__":
    raise SystemExit(main())
