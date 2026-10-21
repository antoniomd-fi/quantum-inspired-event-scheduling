#!/usr/bin/env python
"""Analyze targeted multi-objective stress experiments."""

from __future__ import annotations

import csv
import math
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable


REPO_ROOT = Path(__file__).resolve().parents[1]
INPUT_DIR = REPO_ROOT / "results" / "raw" / "v3_targeted_stress_matrix"
RUNS_INPUT = INPUT_DIR / "runs.csv"
AGGREGATED_INPUT = INPUT_DIR / "aggregated.csv"
PROCESSED_DIR = REPO_ROOT / "results" / "processed" / "targeted_stress_matrix"
FIGURES_DIR = REPO_ROOT / "results" / "figures" / "targeted_stress_matrix"

PROFILES = [
    "burst_critical",
    "flooding_critical",
    "heterogeneous_pressure",
    "fairness_starvation",
]
LOADS = ["high", "overload"]
QUBO_V0 = "qubo_batch_exact"
QUBO_V1 = "qubo_batch_exact_sequencing"
CLASSICAL_STRATEGIES = [
    "priority_aware",
    "deadline_aware_dispatch",
    "shortest_queue",
    "min_cost_greedy",
    "duration_aware_dispatch",
]

LOWER_IS_BETTER = {
    "objective_average_cost_per_event",
    "p99_latency_ms",
    "starvation_count",
}
HIGHER_IS_BETTER = {
    "critical_deadline_hit_rate",
    "worker_utilization_fairness_jain_index",
    "event_count_fairness_jain_index",
}

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

TEXT = {
    "es": {
        "suffix": "",
        "profiles": {
            "burst_critical": "Ráfagas críticas",
            "flooding_critical": "Flooding crítico",
            "heterogeneous_pressure": "Presión heterogénea",
            "fairness_starvation": "Fairness/starvation",
        },
        "loads": {"high": "alta", "overload": "sobrecarga"},
        "hybrid_title": "Señal de activación híbrida por escenario",
        "hybrid_y": "Tasa de escenarios",
        "objective_title": "Brecha de QUBO v1 frente al mejor clásico",
        "objective_y": "Brecha media (%)",
        "critical_title": "Diferencia en cumplimiento crítico frente al clásico por objetivo",
        "critical_y": "Diferencia media",
        "p99_title": "Mejora p99 de QUBO v1 frente al clásico por objetivo",
        "p99_y": "Mejora media (%)",
    },
    "en": {
        "suffix": "_en",
        "profiles": {
            "burst_critical": "Critical bursts",
            "flooding_critical": "Critical flooding",
            "heterogeneous_pressure": "Heterogeneous pressure",
            "fairness_starvation": "Fairness/starvation",
        },
        "loads": {"high": "high", "overload": "overload"},
        "hybrid_title": "Hybrid activation signal by scenario",
        "hybrid_y": "Scenario rate",
        "objective_title": "QUBO v1 gap vs best classical strategy",
        "objective_y": "Mean gap (%)",
        "critical_title": "Critical hit-rate delta vs objective-best classical",
        "critical_y": "Mean delta",
        "p99_title": "QUBO v1 p99 improvement vs objective-best classical",
        "p99_y": "Mean improvement (%)",
    },
}

COLORS = {
    "positive": "#21745f",
    "negative": "#9b3b3b",
    "neutral": "#2f5f98",
    "accent": "#8f4f21",
    "axis": "#17212b",
    "grid": "#dfe5ea",
}


def main() -> int:
    if not RUNS_INPUT.exists() or not AGGREGATED_INPUT.exists():
        raise SystemExit(
            "Targeted stress inputs are missing. Run scripts/run_targeted_stress_matrix.ps1 first."
        )

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)

    runs = load_csv(RUNS_INPUT)
    aggregated = load_csv(AGGREGATED_INPUT)
    per_seed = per_seed_comparison(runs)
    profile_load = profile_load_summary(per_seed)
    overall = overall_summary(per_seed)
    sign_tests = sign_test_rows(per_seed)

    write_csv(PROCESSED_DIR / "runs_normalized.csv", runs)
    write_csv(PROCESSED_DIR / "aggregated_normalized.csv", aggregated)
    write_csv(PROCESSED_DIR / "per_seed_comparison.csv", per_seed)
    write_csv(PROCESSED_DIR / "profile_load_summary.csv", profile_load)
    write_csv(PROCESSED_DIR / "overall_summary.csv", overall)
    write_csv(PROCESSED_DIR / "sign_tests.csv", sign_tests)
    write_figures(profile_load)
    write_findings(per_seed, profile_load, overall, sign_tests)

    print(f"Targeted runs: {len(runs)}")
    print(f"Paired comparisons: {len(per_seed)}")
    print(f"Profile/load groups: {len(profile_load)}")
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
    rows = []

    for key, group in group_by(runs, ("profile", "load_level", "seed")).items():
        profile, load_level, seed = key
        indexed = {row["strategy"]: row for row in group}

        if QUBO_V1 not in indexed or QUBO_V0 not in indexed:
            continue

        classical_rows = [indexed[strategy] for strategy in CLASSICAL_STRATEGIES if strategy in indexed]

        if not classical_rows:
            continue

        v0 = indexed[QUBO_V0]
        v1 = indexed[QUBO_V1]
        best_objective_classical = best_row(
            classical_rows, "objective_average_cost_per_event", lower=True
        )
        best_critical_classical = best_row(classical_rows, "critical_deadline_hit_rate", lower=False)
        best_p99_classical = best_row(classical_rows, "p99_latency_ms", lower=True)
        best_starvation_classical = best_row(classical_rows, "starvation_count", lower=True)
        best_worker_fairness_classical = best_row(
            classical_rows, "worker_utilization_fairness_jain_index", lower=False
        )

        objective_gap_pct = percent_delta(
            v1["objective_average_cost_per_event"],
            best_objective_classical["objective_average_cost_per_event"],
        )
        objective_improvement_vs_v0_pct = percent_improvement(
            v0["objective_average_cost_per_event"],
            v1["objective_average_cost_per_event"],
        )
        critical_delta_vs_objective_classical = (
            v1["critical_deadline_hit_rate"]
            - best_objective_classical["critical_deadline_hit_rate"]
        )
        p99_improvement_vs_objective_classical_pct = percent_improvement(
            best_objective_classical["p99_latency_ms"],
            v1["p99_latency_ms"],
        )
        starvation_delta_vs_objective_classical = (
            v1["starvation_count"] - best_objective_classical["starvation_count"]
        )
        worker_fairness_delta_vs_objective_classical = (
            v1["worker_utilization_fairness_jain_index"]
            - best_objective_classical["worker_utilization_fairness_jain_index"]
        )
        resilience_gain_count = sum(
            [
                critical_delta_vs_objective_classical >= 0.02,
                p99_improvement_vs_objective_classical_pct >= 5.0,
                starvation_delta_vs_objective_classical < 0,
                worker_fairness_delta_vs_objective_classical >= 0.02,
            ]
        )
        objective_win = v1["objective_average_cost_per_event"] <= best_objective_classical[
            "objective_average_cost_per_event"
        ]
        within_5pct = objective_gap_pct <= 5.0
        hybrid_signal = objective_win or (within_5pct and resilience_gain_count >= 1)

        rows.append(
            {
                "profile": profile,
                "load_level": load_level,
                "seed": seed,
                "best_objective_classical_strategy": best_objective_classical["strategy"],
                "best_critical_classical_strategy": best_critical_classical["strategy"],
                "best_p99_classical_strategy": best_p99_classical["strategy"],
                "best_starvation_classical_strategy": best_starvation_classical["strategy"],
                "best_worker_fairness_classical_strategy": best_worker_fairness_classical[
                    "strategy"
                ],
                "qubo_v1_objective": v1["objective_average_cost_per_event"],
                "best_classical_objective": best_objective_classical[
                    "objective_average_cost_per_event"
                ],
                "qubo_v1_objective_gap_pct": round_number(objective_gap_pct),
                "qubo_v1_objective_win": objective_win,
                "qubo_v1_within_5pct_objective": within_5pct,
                "qubo_v1_objective_improvement_vs_v0_pct": round_number(
                    objective_improvement_vs_v0_pct
                ),
                "qubo_v1_better_than_v0": v1["objective_average_cost_per_event"]
                < v0["objective_average_cost_per_event"],
                "qubo_v1_critical_deadline_hit_rate": v1["critical_deadline_hit_rate"],
                "objective_classical_critical_deadline_hit_rate": best_objective_classical[
                    "critical_deadline_hit_rate"
                ],
                "best_classical_critical_deadline_hit_rate": best_critical_classical[
                    "critical_deadline_hit_rate"
                ],
                "critical_delta_vs_objective_classical": round_number(
                    critical_delta_vs_objective_classical
                ),
                "critical_delta_vs_best_critical_classical": round_number(
                    v1["critical_deadline_hit_rate"]
                    - best_critical_classical["critical_deadline_hit_rate"]
                ),
                "qubo_v1_p99_latency_ms": v1["p99_latency_ms"],
                "objective_classical_p99_latency_ms": best_objective_classical["p99_latency_ms"],
                "best_classical_p99_latency_ms": best_p99_classical["p99_latency_ms"],
                "p99_improvement_vs_objective_classical_pct": round_number(
                    p99_improvement_vs_objective_classical_pct
                ),
                "p99_improvement_vs_best_p99_classical_pct": round_number(
                    percent_improvement(best_p99_classical["p99_latency_ms"], v1["p99_latency_ms"])
                ),
                "qubo_v1_starvation_count": v1["starvation_count"],
                "objective_classical_starvation_count": best_objective_classical[
                    "starvation_count"
                ],
                "best_classical_starvation_count": best_starvation_classical["starvation_count"],
                "starvation_delta_vs_objective_classical": round_number(
                    starvation_delta_vs_objective_classical
                ),
                "starvation_delta_vs_best_starvation_classical": round_number(
                    v1["starvation_count"] - best_starvation_classical["starvation_count"]
                ),
                "worker_fairness_delta_vs_objective_classical": round_number(
                    worker_fairness_delta_vs_objective_classical
                ),
                "worker_fairness_delta_vs_best_fairness_classical": round_number(
                    v1["worker_utilization_fairness_jain_index"]
                    - best_worker_fairness_classical["worker_utilization_fairness_jain_index"]
                ),
                "resilience_gain_count_vs_objective_classical": resilience_gain_count,
                "hybrid_activation_signal": hybrid_signal,
            }
        )

    return sorted(rows, key=lambda row: (profile_index(row["profile"]), load_index(row["load_level"]), row["seed"]))


def profile_load_summary(per_seed: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []

    for key, group in group_by(per_seed, ("profile", "load_level")).items():
        profile, load_level = key
        objective_stats = metric_stats(row["qubo_v1_objective_gap_pct"] for row in group)
        v0_stats = metric_stats(row["qubo_v1_objective_improvement_vs_v0_pct"] for row in group)
        critical_stats = metric_stats(row["critical_delta_vs_objective_classical"] for row in group)
        p99_stats = metric_stats(row["p99_improvement_vs_objective_classical_pct"] for row in group)
        starvation_stats = metric_stats(row["starvation_delta_vs_objective_classical"] for row in group)
        fairness_stats = metric_stats(row["worker_fairness_delta_vs_objective_classical"] for row in group)

        rows.append(
            {
                "profile": profile,
                "load_level": load_level,
                "comparisons": len(group),
                "objective_win_count": count_true(group, "qubo_v1_objective_win"),
                "objective_win_rate": round_number(rate_true(group, "qubo_v1_objective_win")),
                "within_5pct_objective_count": count_true(
                    group, "qubo_v1_within_5pct_objective"
                ),
                "within_5pct_objective_rate": round_number(
                    rate_true(group, "qubo_v1_within_5pct_objective")
                ),
                "better_than_v0_count": count_true(group, "qubo_v1_better_than_v0"),
                "better_than_v0_rate": round_number(rate_true(group, "qubo_v1_better_than_v0")),
                "hybrid_activation_signal_count": count_true(group, "hybrid_activation_signal"),
                "hybrid_activation_signal_rate": round_number(
                    rate_true(group, "hybrid_activation_signal")
                ),
                **prefixed_stats("objective_gap_pct", objective_stats),
                **prefixed_stats("improvement_vs_v0_pct", v0_stats),
                **prefixed_stats("critical_delta", critical_stats),
                **prefixed_stats("p99_improvement_pct", p99_stats),
                **prefixed_stats("starvation_delta", starvation_stats),
                **prefixed_stats("worker_fairness_delta", fairness_stats),
            }
        )

    return sorted(rows, key=lambda row: (profile_index(row["profile"]), load_index(row["load_level"])))


def overall_summary(per_seed: list[dict[str, Any]]) -> list[dict[str, Any]]:
    objective_stats = metric_stats(row["qubo_v1_objective_gap_pct"] for row in per_seed)
    critical_stats = metric_stats(row["critical_delta_vs_objective_classical"] for row in per_seed)
    p99_stats = metric_stats(row["p99_improvement_vs_objective_classical_pct"] for row in per_seed)

    return [
        {
            "comparisons": len(per_seed),
            "objective_win_count": count_true(per_seed, "qubo_v1_objective_win"),
            "objective_win_rate": round_number(rate_true(per_seed, "qubo_v1_objective_win")),
            "within_5pct_objective_count": count_true(per_seed, "qubo_v1_within_5pct_objective"),
            "within_5pct_objective_rate": round_number(
                rate_true(per_seed, "qubo_v1_within_5pct_objective")
            ),
            "better_than_v0_count": count_true(per_seed, "qubo_v1_better_than_v0"),
            "better_than_v0_rate": round_number(rate_true(per_seed, "qubo_v1_better_than_v0")),
            "hybrid_activation_signal_count": count_true(per_seed, "hybrid_activation_signal"),
            "hybrid_activation_signal_rate": round_number(
                rate_true(per_seed, "hybrid_activation_signal")
            ),
            **prefixed_stats("objective_gap_pct", objective_stats),
            **prefixed_stats("critical_delta", critical_stats),
            **prefixed_stats("p99_improvement_pct", p99_stats),
        }
    ]


def sign_test_rows(per_seed: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []

    for key, group in group_by(per_seed, ("profile", "load_level")).items():
        profile, load_level = key
        objective_wins = count_true(group, "qubo_v1_objective_win")
        objective_losses = sum(1 for row in group if row["qubo_v1_objective_gap_pct"] > 0)
        v0_wins = count_true(group, "qubo_v1_better_than_v0")
        v0_losses = sum(1 for row in group if not row["qubo_v1_better_than_v0"])

        rows.append(
            {
                "profile": profile,
                "load_level": load_level,
                "test": "objective_vs_best_classical",
                "wins": objective_wins,
                "losses": objective_losses,
                "ties": len(group) - objective_wins - objective_losses,
                "two_sided_sign_test_p": sign_test_p(objective_wins, objective_losses),
            }
        )
        rows.append(
            {
                "profile": profile,
                "load_level": load_level,
                "test": "objective_vs_qubo_v0",
                "wins": v0_wins,
                "losses": v0_losses,
                "ties": len(group) - v0_wins - v0_losses,
                "two_sided_sign_test_p": sign_test_p(v0_wins, v0_losses),
            }
        )

    adjusted_rows = add_holm_adjustment(rows)
    return sorted(
        adjusted_rows,
        key=lambda row: (
            profile_index(row["profile"]),
            load_index(row["load_level"]),
            row["test"],
        ),
    )


def add_holm_adjustment(rows: list[dict[str, Any]], alpha: float = 0.05) -> list[dict[str, Any]]:
    """Add Holm-adjusted p-values across one family of hypothesis tests."""
    ordered = sorted(
        enumerate(rows),
        key=lambda item: item[1]["two_sided_sign_test_p"],
    )
    adjusted_by_index = [1.0] * len(rows)
    running_max = 0.0

    for rank, (original_index, row) in enumerate(ordered):
        remaining_hypotheses = len(rows) - rank
        scaled_p = min(1.0, row["two_sided_sign_test_p"] * remaining_hypotheses)
        running_max = max(running_max, scaled_p)
        adjusted_by_index[original_index] = running_max

    return [
        {
            **row,
            "holm_adjusted_p": adjusted_by_index[index],
            "holm_reject_0_05": adjusted_by_index[index] <= alpha,
        }
        for index, row in enumerate(rows)
    ]


def write_figures(profile_load: list[dict[str, Any]]) -> None:
    for language, text in TEXT.items():
        suffix = text["suffix"]
        write_rate_chart(
            FIGURES_DIR / f"hybrid_activation_signal{suffix}.svg",
            profile_load,
            "hybrid_activation_signal_rate",
            text,
            text["hybrid_title"],
            text["hybrid_y"],
        )
        write_ci_chart(
            FIGURES_DIR / f"objective_gap_ci{suffix}.svg",
            profile_load,
            "objective_gap_pct_mean",
            "objective_gap_pct_ci95_low",
            "objective_gap_pct_ci95_high",
            text,
            text["objective_title"],
            text["objective_y"],
            invert_colors=True,
        )
        write_ci_chart(
            FIGURES_DIR / f"critical_deadline_delta_ci{suffix}.svg",
            profile_load,
            "critical_delta_mean",
            "critical_delta_ci95_low",
            "critical_delta_ci95_high",
            text,
            text["critical_title"],
            text["critical_y"],
        )
        write_ci_chart(
            FIGURES_DIR / f"p99_latency_improvement_ci{suffix}.svg",
            profile_load,
            "p99_improvement_pct_mean",
            "p99_improvement_pct_ci95_low",
            "p99_improvement_pct_ci95_high",
            text,
            text["p99_title"],
            text["p99_y"],
        )


def write_rate_chart(
    path: Path,
    rows: list[dict[str, Any]],
    value_key: str,
    text: dict[str, Any],
    title: str,
    y_label: str,
) -> None:
    write_bar_chart(
        path=path,
        rows=rows,
        value_key=value_key,
        low_key=None,
        high_key=None,
        text=text,
        title=title,
        y_label=y_label,
        y_min=0.0,
        y_max=1.0,
        percent_axis=True,
        invert_colors=False,
    )


def write_ci_chart(
    path: Path,
    rows: list[dict[str, Any]],
    value_key: str,
    low_key: str,
    high_key: str,
    text: dict[str, Any],
    title: str,
    y_label: str,
    invert_colors: bool = False,
) -> None:
    values = [row[value_key] for row in rows] + [row[low_key] for row in rows] + [row[high_key] for row in rows]
    y_min = min(values + [0.0])
    y_max = max(values + [0.0])
    padding = max((y_max - y_min) * 0.18, 0.05 if max(abs(y_min), abs(y_max)) <= 1 else 2.0)

    write_bar_chart(
        path=path,
        rows=rows,
        value_key=value_key,
        low_key=low_key,
        high_key=high_key,
        text=text,
        title=title,
        y_label=y_label,
        y_min=y_min - padding,
        y_max=y_max + padding,
        percent_axis=False,
        invert_colors=invert_colors,
    )


def write_bar_chart(
    path: Path,
    rows: list[dict[str, Any]],
    value_key: str,
    low_key: str | None,
    high_key: str | None,
    text: dict[str, Any],
    title: str,
    y_label: str,
    y_min: float,
    y_max: float,
    percent_axis: bool,
    invert_colors: bool,
) -> None:
    width = 1280
    height = 660
    margin_left = 92
    margin_right = 40
    margin_top = 82
    margin_bottom = 150
    plot_width = width - margin_left - margin_right
    plot_height = height - margin_top - margin_bottom
    slot_width = plot_width / max(len(rows), 1)
    bar_width = min(74, slot_width * 0.58)
    zero_y = y_position(0, y_min, y_max, margin_top, plot_height)
    ticks = axis_ticks(y_min, y_max, percent_axis)

    svg = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#ffffff"/>',
        f'<text x="{width / 2}" y="44" text-anchor="middle" font-family="Arial, sans-serif" font-size="24" font-weight="700" fill="{COLORS["axis"]}">{escape_xml(title)}</text>',
        f'<text x="24" y="{margin_top + plot_height / 2}" transform="rotate(-90 24 {margin_top + plot_height / 2})" text-anchor="middle" font-family="Arial, sans-serif" font-size="15" fill="{COLORS["axis"]}">{escape_xml(y_label)}</text>',
    ]

    for tick in ticks:
        y = y_position(tick, y_min, y_max, margin_top, plot_height)
        label = f"{tick * 100:.0f}%" if percent_axis else f"{tick:.2f}" if abs(tick) < 1 else f"{tick:.1f}"
        svg.extend(
            [
                f'<line x1="{margin_left}" y1="{y:.2f}" x2="{width - margin_right}" y2="{y:.2f}" stroke="{COLORS["grid"]}" stroke-width="1"/>',
                f'<text x="{margin_left - 12}" y="{y + 5:.2f}" text-anchor="end" font-family="Arial, sans-serif" font-size="12" fill="{COLORS["axis"]}">{label}</text>',
            ]
        )

    svg.append(
        f'<line x1="{margin_left}" y1="{zero_y:.2f}" x2="{width - margin_right}" y2="{zero_y:.2f}" stroke="{COLORS["axis"]}" stroke-width="1.2"/>'
    )

    for index, row in enumerate(rows):
        value = row[value_key]
        x_center = margin_left + slot_width * index + slot_width / 2
        y_value = y_position(value, y_min, y_max, margin_top, plot_height)
        bar_y = min(y_value, zero_y)
        bar_height = max(abs(zero_y - y_value), 1.0)
        color = value_color(value, invert_colors)
        x = x_center - bar_width / 2
        label = scenario_label(row, text)
        value_label = f"{value * 100:.0f}%" if percent_axis else f"{value:.2f}" if abs(value) < 1 else f"{value:.1f}"

        svg.append(
            f'<rect x="{x:.2f}" y="{bar_y:.2f}" width="{bar_width:.2f}" height="{bar_height:.2f}" rx="3" fill="{color}"/>'
        )

        if low_key and high_key:
            y_low = y_position(row[low_key], y_min, y_max, margin_top, plot_height)
            y_high = y_position(row[high_key], y_min, y_max, margin_top, plot_height)
            svg.extend(
                [
                    f'<line x1="{x_center:.2f}" y1="{y_high:.2f}" x2="{x_center:.2f}" y2="{y_low:.2f}" stroke="{COLORS["axis"]}" stroke-width="1.4"/>',
                    f'<line x1="{x_center - 8:.2f}" y1="{y_high:.2f}" x2="{x_center + 8:.2f}" y2="{y_high:.2f}" stroke="{COLORS["axis"]}" stroke-width="1.4"/>',
                    f'<line x1="{x_center - 8:.2f}" y1="{y_low:.2f}" x2="{x_center + 8:.2f}" y2="{y_low:.2f}" stroke="{COLORS["axis"]}" stroke-width="1.4"/>',
                ]
            )

        label_y = y_value - 8 if value >= 0 else y_value + 18
        svg.extend(
            [
                f'<text x="{x_center:.2f}" y="{label_y:.2f}" text-anchor="middle" font-family="Arial, sans-serif" font-size="12" fill="{COLORS["axis"]}">{escape_xml(value_label)}</text>',
                f'<text x="{x_center:.2f}" y="{margin_top + plot_height + 42}" transform="rotate(-35 {x_center:.2f} {margin_top + plot_height + 42})" text-anchor="end" font-family="Arial, sans-serif" font-size="12" fill="{COLORS["axis"]}">{escape_xml(label)}</text>',
            ]
        )

    svg.extend(
        [
            f'<line x1="{margin_left}" y1="{margin_top}" x2="{margin_left}" y2="{margin_top + plot_height}" stroke="{COLORS["axis"]}" stroke-width="1"/>',
            "</svg>",
        ]
    )
    path.write_text("\n".join(svg), encoding="utf-8")


def write_findings(
    per_seed: list[dict[str, Any]],
    profile_load: list[dict[str, Any]],
    overall: list[dict[str, Any]],
    sign_tests: list[dict[str, Any]],
) -> None:
    summary = overall[0]
    best_hybrid = max(profile_load, key=lambda row: row["hybrid_activation_signal_rate"])
    best_objective = min(profile_load, key=lambda row: row["objective_gap_pct_mean"])
    best_critical = max(profile_load, key=lambda row: row["critical_delta_mean"])
    strongest_v0 = max(profile_load, key=lambda row: row["improvement_vs_v0_pct_mean"])

    lines = [
        "# Targeted Stress Matrix Findings",
        "",
        "This generated summary is a technical companion for the experiment outputs.",
        "It is not a peer-reviewed analysis by itself.",
        "",
        "## Experimental Scope",
        "",
        f"- Paired generated scenarios: {len(per_seed)}.",
        f"- Profile/load groups: {len(profile_load)}.",
        "- Profiles: burst_critical, flooding_critical, heterogeneous_pressure, fairness_starvation.",
        "- Loads: high, overload.",
        "- Seeds: 1..30.",
        "- Strategies: QUBO v0, QUBO v1 sequencing, priority_aware, deadline_aware_dispatch, shortest_queue, min_cost_greedy, duration_aware_dispatch.",
        "",
        "## Overall Results",
        "",
        f"- QUBO v1 beat the best objective-based classical strategy in {summary['objective_win_count']}/{summary['comparisons']} scenarios ({percent(summary['objective_win_rate'])}).",
        f"- QUBO v1 was within 5% of the best objective-based classical strategy in {summary['within_5pct_objective_count']}/{summary['comparisons']} scenarios ({percent(summary['within_5pct_objective_rate'])}).",
        f"- QUBO v1 improved over QUBO v0 in {summary['better_than_v0_count']}/{summary['comparisons']} scenarios ({percent(summary['better_than_v0_rate'])}).",
        f"- Hybrid activation signal appeared in {summary['hybrid_activation_signal_count']}/{summary['comparisons']} scenarios ({percent(summary['hybrid_activation_signal_rate'])}).",
        f"- Mean objective gap vs best classical: {summary['objective_gap_pct_mean']:.2f}% (95% CI {summary['objective_gap_pct_ci95_low']:.2f}% to {summary['objective_gap_pct_ci95_high']:.2f}%).",
        f"- Mean critical hit-rate delta vs the objective-best classical strategy: {summary['critical_delta_mean']:.4f} (95% CI {summary['critical_delta_ci95_low']:.4f} to {summary['critical_delta_ci95_high']:.4f}).",
        f"- Mean p99 latency improvement vs the objective-best classical strategy: {summary['p99_improvement_pct_mean']:.2f}% (95% CI {summary['p99_improvement_pct_ci95_low']:.2f}% to {summary['p99_improvement_pct_ci95_high']:.2f}%).",
        "",
        "## Strongest Signals",
        "",
        f"- Highest hybrid activation rate: {best_hybrid['profile']} / {best_hybrid['load_level']} ({percent(best_hybrid['hybrid_activation_signal_rate'])}).",
        f"- Lowest mean objective gap: {best_objective['profile']} / {best_objective['load_level']} ({best_objective['objective_gap_pct_mean']:.2f}%).",
        f"- Strongest critical-deadline delta: {best_critical['profile']} / {best_critical['load_level']} ({best_critical['critical_delta_mean']:.4f}).",
        f"- Strongest improvement vs QUBO v0: {strongest_v0['profile']} / {strongest_v0['load_level']} ({strongest_v0['improvement_vs_v0_pct_mean']:.2f}%).",
        "",
        "## Profile/Load Summary",
        "",
        "| profile | load | objective win rate | within 5% | hybrid signal | objective gap % mean | critical delta mean | p99 improvement % mean |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]

    for row in profile_load:
        lines.append(
            f"| {row['profile']} | {row['load_level']} | {percent(row['objective_win_rate'])} | "
            f"{percent(row['within_5pct_objective_rate'])} | {percent(row['hybrid_activation_signal_rate'])} | "
            f"{row['objective_gap_pct_mean']:.2f} | {row['critical_delta_mean']:.4f} | "
            f"{row['p99_improvement_pct_mean']:.2f} |"
        )

    lines.extend(
        [
            "",
            "## Sign Tests",
            "",
            "The 16 tests are treated as one family and adjusted with Holm's procedure.",
            "",
            "| profile | load | test | wins | losses | raw p-value | Holm-adjusted p-value | reject at 0.05 |",
            "| --- | --- | --- | ---: | ---: | ---: | ---: | --- |",
        ]
    )

    for row in sign_tests:
        lines.append(
            f"| {row['profile']} | {row['load_level']} | {row['test']} | "
            f"{row['wins']} | {row['losses']} | "
            f"{format_p_value(row['two_sided_sign_test_p'])} | "
            f"{format_p_value(row['holm_adjusted_p'])} | "
            f"{'yes' if row['holm_reject_0_05'] else 'no'} |"
        )

    lines.extend(
        [
            "",
            "## Interpretation Boundary",
            "",
            "- The hybrid activation signal is a decision-support indicator, not a production scheduler.",
            "- QUBO v1 should be interpreted as a candidate specialist optimizer for selected pressure windows.",
            "- These results still do not demonstrate quantum advantage; they deepen the evidence for a hybrid quantum-inspired architecture.",
            "",
        ]
    )

    (PROCESSED_DIR / "key_findings.md").write_text("\n".join(lines), encoding="utf-8")


def best_row(rows: list[dict[str, Any]], metric: str, lower: bool) -> dict[str, Any]:
    if lower:
        return min(rows, key=lambda row: row[metric])

    return max(rows, key=lambda row: row[metric])


def metric_stats(values: Iterable[float]) -> dict[str, float]:
    materialized = [float(value) for value in values]
    n = len(materialized)

    if n == 0:
        return {
            "mean": 0.0,
            "stddev": 0.0,
            "ci95_low": 0.0,
            "ci95_high": 0.0,
            "min": 0.0,
            "max": 0.0,
        }

    mean_value = mean(materialized)
    stddev_value = sample_stddev(materialized, mean_value)
    half_width = 1.96 * stddev_value / math.sqrt(n) if n > 1 else 0.0

    return {
        "mean": round_number(mean_value),
        "stddev": round_number(stddev_value),
        "ci95_low": round_number(mean_value - half_width),
        "ci95_high": round_number(mean_value + half_width),
        "min": round_number(min(materialized)),
        "max": round_number(max(materialized)),
    }


def prefixed_stats(prefix: str, stats: dict[str, float]) -> dict[str, float]:
    return {f"{prefix}_{key}": value for key, value in stats.items()}


def sign_test_p(wins: int, losses: int) -> float:
    n = wins + losses

    if n == 0:
        return 1.0

    tail = min(wins, losses)
    probability = sum(combination(n, k) for k in range(tail + 1)) / (2**n)
    return min(1.0, 2 * probability)


def combination(n: int, k: int) -> int:
    return math.factorial(n) // (math.factorial(k) * math.factorial(n - k))


def group_by(rows: list[dict[str, Any]], keys: tuple[str, ...]) -> dict[tuple[Any, ...], list[dict[str, Any]]]:
    grouped: dict[tuple[Any, ...], list[dict[str, Any]]] = defaultdict(list)

    for row in rows:
        grouped[tuple(row[key] for key in keys)].append(row)

    return grouped


def count_true(rows: list[dict[str, Any]], key: str) -> int:
    return sum(1 for row in rows if row[key])


def rate_true(rows: list[dict[str, Any]], key: str) -> float:
    return count_true(rows, key) / len(rows) if rows else 0.0


def mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def sample_stddev(values: list[float], mean_value: float) -> float:
    if len(values) <= 1:
        return 0.0

    variance = sum((value - mean_value) ** 2 for value in values) / (len(values) - 1)
    return math.sqrt(variance)


def percent_delta(candidate: float, baseline: float) -> float:
    return ((candidate - baseline) / max(abs(baseline), 1.0)) * 100


def percent_improvement(baseline: float, candidate: float) -> float:
    return ((baseline - candidate) / max(abs(baseline), 1.0)) * 100


def axis_ticks(y_min: float, y_max: float, percent_axis: bool) -> list[float]:
    if percent_axis:
        return [0.0, 0.25, 0.5, 0.75, 1.0]

    step = (y_max - y_min) / 4
    return [y_min + step * index for index in range(5)]


def y_position(value: float, y_min: float, y_max: float, margin_top: int, plot_height: int) -> float:
    if y_max == y_min:
        return margin_top + plot_height / 2

    ratio = (value - y_min) / (y_max - y_min)
    return margin_top + plot_height - ratio * plot_height


def value_color(value: float, invert: bool) -> str:
    if value == 0:
        return COLORS["neutral"]

    positive_is_good = not invert
    is_good = value > 0 if positive_is_good else value < 0
    return COLORS["positive"] if is_good else COLORS["negative"]


def scenario_label(row: dict[str, Any], text: dict[str, Any]) -> str:
    profile = text["profiles"].get(row["profile"], row["profile"])
    load = text["loads"].get(row["load_level"], row["load_level"])
    return f"{profile} / {load}"


def profile_index(profile: str) -> int:
    try:
        return PROFILES.index(profile)
    except ValueError:
        return len(PROFILES)


def load_index(load_level: str) -> int:
    try:
        return LOADS.index(load_level)
    except ValueError:
        return len(LOADS)


def parse_number(value: str) -> float:
    if value == "":
        return 0.0

    number = float(value)
    return int(number) if number.is_integer() else number


def round_number(value: float) -> float:
    return round(value, 6)


def format_p_value(value: float) -> str:
    if value < 0.000001:
        return "<0.000001"

    return f"{value:.6f}"


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
