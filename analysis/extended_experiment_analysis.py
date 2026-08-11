#!/usr/bin/env python
"""Analyze repeated event-driven experiments across profiles, loads, and seeds."""

from __future__ import annotations

import csv
import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
INPUT_DIR = REPO_ROOT / "results" / "raw" / "v2_extended_event_driven_matrix"
RUNS_INPUT = INPUT_DIR / "runs.csv"
AGGREGATED_INPUT = INPUT_DIR / "aggregated.csv"
PROCESSED_DIR = REPO_ROOT / "results" / "processed" / "extended_event_driven_matrix"
FIGURES_DIR = REPO_ROOT / "results" / "figures" / "extended_event_driven_matrix"

PROFILES = ["burst", "saturation", "critical_heavy", "heterogeneous"]
LOADS = ["medium", "high", "overload"]
CLASSICAL_STRATEGIES = ["priority_aware", "shortest_queue", "min_cost_greedy"]
QUBO_V0 = "qubo_batch_exact"
QUBO_V1 = "qubo_batch_exact_sequencing"
STRATEGIES = [QUBO_V0, QUBO_V1] + CLASSICAL_STRATEGIES

NUMERIC_PREFIXES = (
    "target_utilization",
    "estimated_interarrival_ms",
    "actual_critical_ratio",
    "actual_average_duration_ms",
    "actual_average_deadline_ms",
    "worker_count",
    "total_worker_speed",
    "total_worker_weight",
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
)

FIGURE_TEXT = {
    "es": {
        "suffix": "",
        "profiles": {
            "burst": "Ráfagas",
            "saturation": "Saturación",
            "critical_heavy": "Críticos",
            "heterogeneous": "Heterogéneo",
        },
        "loads": {
            "medium": "Media",
            "high": "Alta",
            "overload": "Sobrecarga",
        },
        "strategies": {
            QUBO_V0: "QUBO v0",
            QUBO_V1: "QUBO v1",
            "priority_aware": "Prioridad",
            "shortest_queue": "Cola más corta",
            "min_cost_greedy": "Costo mínimo",
        },
        "wins_title": "Victorias por estrategia en escenarios generados",
        "wins_y": "Cantidad de escenarios",
        "v1_v0_title": "Mejora de QUBO v1 frente a QUBO v0",
        "v1_v0_y": "Mejora (%)",
        "gap_title": "Brecha de QUBO v1 frente al mejor clásico",
        "gap_y": "Brecha (%)",
        "critical_title": "Cumplimiento de plazos críticos en la matriz extendida",
        "critical_y": "Tasa media",
    },
    "en": {
        "suffix": "_en",
        "profiles": {
            "burst": "Burst",
            "saturation": "Saturation",
            "critical_heavy": "Critical-heavy",
            "heterogeneous": "Heterogeneous",
        },
        "loads": {
            "medium": "Medium",
            "high": "High",
            "overload": "Overload",
        },
        "strategies": {
            QUBO_V0: "QUBO v0",
            QUBO_V1: "QUBO v1",
            "priority_aware": "Priority aware",
            "shortest_queue": "Shortest queue",
            "min_cost_greedy": "Min-cost greedy",
        },
        "wins_title": "Strategy wins across generated scenarios",
        "wins_y": "Scenario count",
        "v1_v0_title": "QUBO v1 improvement vs QUBO v0",
        "v1_v0_y": "Improvement (%)",
        "gap_title": "QUBO v1 gap vs best classical strategy",
        "gap_y": "Gap (%)",
        "critical_title": "Critical deadline hit rate in the extended matrix",
        "critical_y": "Mean hit rate",
    },
}

COLORS = {
    QUBO_V0: "#2f5f98",
    QUBO_V1: "#21745f",
    "priority_aware": "#8f4f21",
    "shortest_queue": "#3d6b8f",
    "min_cost_greedy": "#9b3b3b",
    "positive": "#21745f",
    "negative": "#9b3b3b",
    "neutral": "#5f6b73",
}


def main() -> int:
    if not RUNS_INPUT.exists() or not AGGREGATED_INPUT.exists():
        raise SystemExit(
            "Extended matrix inputs are missing. Run scripts/run_extended_event_driven_matrix.ps1 first."
        )

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)

    runs = load_csv(RUNS_INPUT)
    aggregated = load_csv(AGGREGATED_INPUT)
    per_seed = per_seed_comparison(runs)
    profile_load = profile_load_comparison(aggregated)
    best_counts = best_strategy_counts(per_seed)
    summary = summary_rows(per_seed, profile_load)

    write_csv(PROCESSED_DIR / "runs_normalized.csv", runs)
    write_csv(PROCESSED_DIR / "aggregated_normalized.csv", aggregated)
    write_csv(PROCESSED_DIR / "per_seed_comparison.csv", per_seed)
    write_csv(PROCESSED_DIR / "profile_load_comparison.csv", profile_load)
    write_csv(PROCESSED_DIR / "best_strategy_counts.csv", best_counts)
    write_csv(PROCESSED_DIR / "summary.csv", summary)
    write_figures(per_seed, profile_load)
    write_findings(per_seed, profile_load, best_counts, summary)

    print(f"Extended runs: {len(runs)}")
    print(f"Generated scenario comparisons: {len(per_seed)}")
    print(f"Profile/load aggregates: {len(profile_load)}")
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
        if key == "seed" or key == "repetitions":
            normalized[key] = int(value)
        elif is_numeric_key(key):
            normalized[key] = parse_number(value)
        else:
            normalized[key] = value

    return normalized


def is_numeric_key(key: str) -> bool:
    return any(key == prefix or key.startswith(prefix + "_") for prefix in NUMERIC_PREFIXES)


def per_seed_comparison(runs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped = group_by(runs, ("profile", "load_level", "seed"))
    rows = []

    for key, group in grouped.items():
        profile, load_level, seed = key
        indexed = {row["strategy"]: row for row in group}

        if QUBO_V1 not in indexed or QUBO_V0 not in indexed:
            continue

        classical_rows = [indexed[strategy] for strategy in CLASSICAL_STRATEGIES if strategy in indexed]
        best_classical = min(classical_rows, key=lambda row: row["objective_average_cost_per_event"])
        best_overall = min(group, key=lambda row: row["objective_average_cost_per_event"])
        v0 = indexed[QUBO_V0]
        v1 = indexed[QUBO_V1]

        v1_objective = v1["objective_average_cost_per_event"]
        v0_objective = v0["objective_average_cost_per_event"]
        best_classical_objective = best_classical["objective_average_cost_per_event"]

        rows.append(
            {
                "profile": profile,
                "load_level": load_level,
                "seed": seed,
                "best_overall_strategy": best_overall["strategy"],
                "best_overall_objective": best_overall["objective_average_cost_per_event"],
                "best_classical_strategy": best_classical["strategy"],
                "best_classical_objective": best_classical_objective,
                "qubo_v0_objective": v0_objective,
                "qubo_v1_objective": v1_objective,
                "qubo_v1_gap_vs_best_classical": round_number(
                    v1_objective - best_classical_objective
                ),
                "qubo_v1_gap_vs_best_classical_pct": percent_delta(
                    v1_objective, best_classical_objective
                ),
                "qubo_v1_improvement_vs_v0": round_number(v0_objective - v1_objective),
                "qubo_v1_improvement_vs_v0_pct": percent_improvement(v0_objective, v1_objective),
                "qubo_v1_wins_best_classical": v1_objective <= best_classical_objective,
                "qubo_v1_within_5pct_best_classical": percent_delta(
                    v1_objective, best_classical_objective
                )
                <= 5,
                "qubo_v1_better_than_v0": v1_objective < v0_objective,
                "qubo_v1_deadline_hit_rate": v1["deadline_hit_rate"],
                "qubo_v1_critical_deadline_hit_rate": v1["critical_deadline_hit_rate"],
                "best_classical_critical_deadline_hit_rate": best_classical[
                    "critical_deadline_hit_rate"
                ],
            }
        )

    return sorted(rows, key=lambda row: (profile_index(row["profile"]), load_index(row["load_level"]), row["seed"]))


def profile_load_comparison(aggregated: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped = group_by(aggregated, ("profile", "load_level"))
    rows = []

    for key, group in grouped.items():
        profile, load_level = key
        indexed = {row["strategy"]: row for row in group}

        if QUBO_V1 not in indexed or QUBO_V0 not in indexed:
            continue

        classical_rows = [indexed[strategy] for strategy in CLASSICAL_STRATEGIES if strategy in indexed]
        best_classical = min(classical_rows, key=lambda row: row["objective_average_cost_per_event_mean"])
        best_overall = min(group, key=lambda row: row["objective_average_cost_per_event_mean"])
        v0 = indexed[QUBO_V0]
        v1 = indexed[QUBO_V1]
        v1_objective = v1["objective_average_cost_per_event_mean"]
        v0_objective = v0["objective_average_cost_per_event_mean"]
        best_classical_objective = best_classical["objective_average_cost_per_event_mean"]

        rows.append(
            {
                "profile": profile,
                "load_level": load_level,
                "repetitions": v1["repetitions"],
                "best_overall_strategy": best_overall["strategy"],
                "best_overall_objective_mean": best_overall["objective_average_cost_per_event_mean"],
                "best_classical_strategy": best_classical["strategy"],
                "best_classical_objective_mean": best_classical_objective,
                "qubo_v0_objective_mean": v0_objective,
                "qubo_v1_objective_mean": v1_objective,
                "qubo_v1_objective_stddev": v1["objective_average_cost_per_event_stddev"],
                "qubo_v1_gap_vs_best_classical_mean": round_number(
                    v1_objective - best_classical_objective
                ),
                "qubo_v1_gap_vs_best_classical_pct": percent_delta(
                    v1_objective, best_classical_objective
                ),
                "qubo_v1_improvement_vs_v0_mean": round_number(v0_objective - v1_objective),
                "qubo_v1_improvement_vs_v0_pct": percent_improvement(v0_objective, v1_objective),
                "qubo_v1_deadline_hit_rate_mean": v1["deadline_hit_rate_mean"],
                "qubo_v1_critical_deadline_hit_rate_mean": v1["critical_deadline_hit_rate_mean"],
                "best_classical_critical_deadline_hit_rate_mean": best_classical[
                    "critical_deadline_hit_rate_mean"
                ],
            }
        )

    return sorted(rows, key=lambda row: (profile_index(row["profile"]), load_index(row["load_level"])))


def best_strategy_counts(per_seed: list[dict[str, Any]]) -> list[dict[str, Any]]:
    counter = Counter(row["best_overall_strategy"] for row in per_seed)

    return [
        {
            "strategy": strategy,
            "win_count": counter.get(strategy, 0),
            "win_rate": counter.get(strategy, 0) / len(per_seed) if per_seed else 0,
        }
        for strategy in STRATEGIES
    ]


def summary_rows(per_seed: list[dict[str, Any]], profile_load: list[dict[str, Any]]) -> list[dict[str, Any]]:
    total = len(per_seed)

    if total == 0:
        return []

    return [
        {
            "generated_scenario_count": total,
            "profile_load_group_count": len(profile_load),
            "qubo_v1_wins_best_classical_count": count_true(
                per_seed, "qubo_v1_wins_best_classical"
            ),
            "qubo_v1_wins_best_classical_rate": rate_true(
                per_seed, "qubo_v1_wins_best_classical"
            ),
            "qubo_v1_within_5pct_best_classical_count": count_true(
                per_seed, "qubo_v1_within_5pct_best_classical"
            ),
            "qubo_v1_within_5pct_best_classical_rate": rate_true(
                per_seed, "qubo_v1_within_5pct_best_classical"
            ),
            "qubo_v1_better_than_v0_count": count_true(per_seed, "qubo_v1_better_than_v0"),
            "qubo_v1_better_than_v0_rate": rate_true(per_seed, "qubo_v1_better_than_v0"),
            "average_qubo_v1_gap_vs_best_classical_pct": average(
                row["qubo_v1_gap_vs_best_classical_pct"] for row in per_seed
            ),
            "average_qubo_v1_improvement_vs_v0_pct": average(
                row["qubo_v1_improvement_vs_v0_pct"] for row in per_seed
            ),
            "average_qubo_v1_critical_deadline_hit_rate": average(
                row["qubo_v1_critical_deadline_hit_rate"] for row in per_seed
            ),
            "average_best_classical_critical_deadline_hit_rate": average(
                row["best_classical_critical_deadline_hit_rate"] for row in per_seed
            ),
        }
    ]


def write_figures(per_seed: list[dict[str, Any]], profile_load: list[dict[str, Any]]) -> None:
    for text in FIGURE_TEXT.values():
        suffix = text["suffix"]
        write_text(
            FIGURES_DIR / f"best_strategy_counts{suffix}.svg",
            single_bar_svg(
                [
                    {
                        "label": text["strategies"].get(row["strategy"], row["strategy"]),
                        "value": row["win_count"],
                    }
                    for row in best_strategy_counts(per_seed)
                ],
                title=text["wins_title"],
                y_label=text["wins_y"],
                value_formatter=lambda value: f"{value:.0f}",
            ),
        )
        write_text(
            FIGURES_DIR / f"qubo_v1_improvement_vs_v0_by_profile_load{suffix}.svg",
            single_bar_svg(
                [
                    {
                        "label": profile_load_label(row, text),
                        "value": row["qubo_v1_improvement_vs_v0_pct"],
                    }
                    for row in profile_load
                ],
                title=text["v1_v0_title"],
                y_label=text["v1_v0_y"],
            ),
        )
        write_text(
            FIGURES_DIR / f"qubo_v1_gap_vs_best_classical{suffix}.svg",
            single_bar_svg(
                [
                    {
                        "label": profile_load_label(row, text),
                        "value": row["qubo_v1_gap_vs_best_classical_pct"],
                    }
                    for row in profile_load
                ],
                title=text["gap_title"],
                y_label=text["gap_y"],
            ),
        )
        write_text(
            FIGURES_DIR / f"critical_deadline_rate_extended{suffix}.svg",
            grouped_bar_svg(
                [
                    {
                        "label": profile_load_label(row, text),
                        "values": [
                            {
                                "series": QUBO_V1,
                                "value": row["qubo_v1_critical_deadline_hit_rate_mean"],
                            },
                            {
                                "series": "best_classical",
                                "value": row["best_classical_critical_deadline_hit_rate_mean"],
                            },
                        ],
                    }
                    for row in profile_load
                ],
                title=text["critical_title"],
                y_label=text["critical_y"],
                series_labels={
                    QUBO_V1: text["strategies"][QUBO_V1],
                    "best_classical": "Mejor clásico"
                    if text["suffix"] == ""
                    else "Best classical",
                },
                max_value=1.0,
                value_formatter=lambda value: f"{value:.2f}",
            ),
        )


def write_findings(
    per_seed: list[dict[str, Any]],
    profile_load: list[dict[str, Any]],
    best_counts: list[dict[str, Any]],
    summary: list[dict[str, Any]],
) -> None:
    overall = summary[0]
    v1_best_groups = [
        row
        for row in profile_load
        if row["best_overall_strategy"] == QUBO_V1
    ]
    v1_better_v0_groups = [
        row
        for row in profile_load
        if row["qubo_v1_improvement_vs_v0_pct"] > 0
    ]
    within_5_groups = [
        row
        for row in profile_load
        if row["qubo_v1_gap_vs_best_classical_pct"] <= 5
    ]

    lines = [
        "# Extended Event-Driven Matrix Findings",
        "",
        "This generated summary is a technical companion for the experiment outputs.",
        "It is not a peer-reviewed analysis by itself.",
        "",
        "## Experimental Scope",
        "",
        f"- Generated scenario instances: {overall['generated_scenario_count']}.",
        f"- Profile/load groups: {overall['profile_load_group_count']}.",
        "- Profiles: burst, saturation, critical_heavy, heterogeneous.",
        "- Loads: medium, high, overload.",
        "- Seeds: 1..10.",
        "- Strategies: QUBO v0, QUBO v1 sequencing, priority_aware, shortest_queue, min_cost_greedy.",
        "",
        "## Main Results",
        "",
        "- QUBO v1 beat the best classical strategy in "
        f"{overall['qubo_v1_wins_best_classical_count']}/{overall['generated_scenario_count']} generated scenarios "
        f"({overall['qubo_v1_wins_best_classical_rate']:.2%}).",
        "- QUBO v1 was within 5% of the best classical strategy in "
        f"{overall['qubo_v1_within_5pct_best_classical_count']}/{overall['generated_scenario_count']} generated scenarios "
        f"({overall['qubo_v1_within_5pct_best_classical_rate']:.2%}).",
        "- QUBO v1 improved over QUBO v0 in "
        f"{overall['qubo_v1_better_than_v0_count']}/{overall['generated_scenario_count']} generated scenarios "
        f"({overall['qubo_v1_better_than_v0_rate']:.2%}).",
        "- Average QUBO v1 gap vs best classical: "
        f"{overall['average_qubo_v1_gap_vs_best_classical_pct']:.2f}%.",
        "- Average QUBO v1 improvement vs QUBO v0: "
        f"{overall['average_qubo_v1_improvement_vs_v0_pct']:.2f}%.",
        "",
        "## Best Strategy Counts",
        "",
        "| strategy | win count | win rate |",
        "| --- | ---: | ---: |",
    ]

    for row in best_counts:
        lines.append(
            f"| {row['strategy']} | {row['win_count']} | {row['win_rate']:.2%} |"
        )

    lines.extend(
        [
            "",
            "## Profile/Load Summary",
            "",
            "| profile | load | best overall | QUBO v1 gap vs best classical % | QUBO v1 improvement vs v0 % |",
            "| --- | --- | --- | ---: | ---: |",
        ]
    )

    for row in profile_load:
        lines.append(
            "| {profile} | {load_level} | {best_overall_strategy} | "
            "{qubo_v1_gap_vs_best_classical_pct:.2f} | "
            "{qubo_v1_improvement_vs_v0_pct:.2f} |".format(**row)
        )

    lines.extend(
        [
            "",
            "## Interpretation Notes",
            "",
            f"- QUBO v1 was the best mean strategy in {len(v1_best_groups)}/{len(profile_load)} profile/load groups.",
            f"- QUBO v1 improved over QUBO v0 in {len(v1_better_v0_groups)}/{len(profile_load)} profile/load groups.",
            f"- QUBO v1 stayed within 5% of the best classical mean result in {len(within_5_groups)}/{len(profile_load)} profile/load groups.",
            "- These results reinforce QUBO v1 as a useful specialist formulation under complex event-driven pressure, but not as a universal replacement for classical heuristics.",
        ]
    )

    write_text(PROCESSED_DIR / "key_findings.md", "\n".join(lines) + "\n")


def single_bar_svg(
    rows: list[dict[str, Any]],
    title: str,
    y_label: str,
    value_formatter=lambda value: f"{value:.2f}",
) -> str:
    width = 1280
    height = 720
    margin_left = 90
    margin_right = 30
    margin_top = 80
    margin_bottom = 210
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
        parts.append(
            svg_text(x + bar_width / 2, height - 120, row["label"], size=11, anchor="middle", rotate=-35)
        )

    parts.extend(y_tick_labels(margin_left, margin_top, plot_height, y_min, y_max, value_formatter))
    parts.append("</svg>")
    return "\n".join(parts)


def grouped_bar_svg(
    groups: list[dict[str, Any]],
    title: str,
    y_label: str,
    series_labels: dict[str, str],
    max_value: float,
    value_formatter,
) -> str:
    width = 1280
    height = 720
    margin_left = 90
    margin_right = 30
    margin_top = 130
    margin_bottom = 210
    plot_width = width - margin_left - margin_right
    plot_height = height - margin_top - margin_bottom
    series = []

    for group in groups:
        for value in group["values"]:
            if value["series"] not in series:
                series.append(value["series"])

    y_min = 0
    y_max = max_value
    group_width = plot_width / max(len(groups), 1)
    bar_gap = 5
    bar_width = max(10, (group_width - 24) / max(len(series), 1) - bar_gap)
    parts = svg_header(width, height)
    parts.append(svg_text(width / 2, 34, title, size=22, anchor="middle", weight="700"))
    parts.extend(legend_parts(series, series_labels, 360, 70, columns=2, column_width=260))
    parts.append(svg_text(22, margin_top + plot_height / 2, y_label, size=14, rotate=-90))
    parts.extend(axis_parts(margin_left, margin_top, plot_width, plot_height, y_min, y_max))

    for group_index, group in enumerate(groups):
        x0 = margin_left + group_index * group_width + 12

        for series_index, item in enumerate(group["values"]):
            value = item["value"]
            series_name = item["series"]
            bar_height = value_to_height(value, y_min, y_max, plot_height)
            x = x0 + series_index * (bar_width + bar_gap)
            y = margin_top + plot_height - bar_height
            color = COLORS.get(series_name, COLORS["neutral"])
            parts.append(
                f'<rect x="{x:.2f}" y="{y:.2f}" width="{bar_width:.2f}" '
                f'height="{bar_height:.2f}" fill="{color}" rx="2" />'
            )

        label_x = margin_left + group_index * group_width + group_width / 2
        parts.append(
            svg_text(label_x, height - 120, group["label"], size=10, anchor="middle", rotate=-35)
        )

    parts.extend(y_tick_labels(margin_left, margin_top, plot_height, y_min, y_max, value_formatter))
    parts.append("</svg>")
    return "\n".join(parts)


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
        color = COLORS.get(series_name, COLORS["neutral"])
        label = series_labels.get(series_name, series_name)
        parts.append(
            f'<rect x="{item_x}" y="{item_y - 11}" width="14" height="14" '
            f'fill="{color}" rx="2" />'
        )
        parts.append(svg_text(item_x + 22, item_y, label, size=12))

    return parts


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


def svg_text(
    x: float,
    y: float,
    text: str,
    size: int = 12,
    anchor: str = "start",
    weight: str = "400",
    rotate: float | None = None,
) -> str:
    transform = f' transform="rotate({rotate:.2f} {x:.2f} {y:.2f})"' if rotate is not None else ""
    return (
        f'<text x="{x:.2f}" y="{y:.2f}" font-size="{size}" '
        f'font-weight="{weight}" text-anchor="{anchor}"{transform}>{escape_xml(text)}</text>'
    )


def profile_load_label(row: dict[str, Any], text: dict[str, Any]) -> str:
    profile = text["profiles"].get(row["profile"], row["profile"])
    load = text["loads"].get(row["load_level"], row["load_level"])
    return f"{profile} / {load}"


def group_by(rows: list[dict[str, Any]], keys: tuple[str, ...]) -> dict[tuple[Any, ...], list[dict[str, Any]]]:
    grouped: dict[tuple[Any, ...], list[dict[str, Any]]] = defaultdict(list)

    for row in rows:
        grouped[tuple(row[key] for key in keys)].append(row)

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


def count_true(rows: list[dict[str, Any]], key: str) -> int:
    return sum(1 for row in rows if row[key])


def rate_true(rows: list[dict[str, Any]], key: str) -> float:
    if not rows:
        return 0.0

    return count_true(rows, key) / len(rows)


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


def profile_index(profile: str) -> int:
    try:
        return PROFILES.index(profile)
    except ValueError:
        return len(PROFILES)


def load_index(load: str) -> int:
    try:
        return LOADS.index(load)
    except ValueError:
        return len(LOADS)


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
