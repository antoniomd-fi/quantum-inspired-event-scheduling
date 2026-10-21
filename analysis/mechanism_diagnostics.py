from __future__ import annotations

import csv
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean


REPO_ROOT = Path(__file__).resolve().parents[1]
INPUT = REPO_ROOT / "results" / "processed" / "targeted_stress_matrix" / "per_seed_comparison.csv"
OUTPUT_DIR = REPO_ROOT / "results" / "processed" / "targeted_stress_matrix"

DIAGNOSTICS_CSV = OUTPUT_DIR / "mechanism_diagnostics.csv"
STRATEGY_COUNTS_CSV = OUTPUT_DIR / "mechanism_classical_strategy_counts.csv"
CASE_EXAMPLES_CSV = OUTPUT_DIR / "mechanism_case_examples.csv"
SUMMARY_MD = OUTPUT_DIR / "mechanism_diagnostics.md"

GROUP_ORDER = [
    ("burst_critical", "high"),
    ("burst_critical", "overload"),
    ("flooding_critical", "high"),
    ("flooding_critical", "overload"),
    ("heterogeneous_pressure", "high"),
    ("heterogeneous_pressure", "overload"),
    ("fairness_starvation", "high"),
    ("fairness_starvation", "overload"),
]

COUNT_FIELDS = [
    "best_objective_classical_strategy",
    "best_critical_classical_strategy",
    "best_p99_classical_strategy",
    "best_starvation_classical_strategy",
    "best_worker_fairness_classical_strategy",
]

METRIC_FIELDS = [
    "qubo_v1_objective_gap_pct",
    "qubo_v1_objective_improvement_vs_v0_pct",
    "critical_delta_vs_objective_classical",
    "p99_improvement_vs_objective_classical_pct",
    "starvation_delta_vs_objective_classical",
    "worker_fairness_delta_vs_objective_classical",
]


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def as_float(row: dict[str, str], key: str) -> float:
    return float(row[key])


def as_bool(row: dict[str, str], key: str) -> bool:
    return row[key].lower() == "true"


def pct(value: float) -> str:
    return f"{value:.2%}"


def rounded(value: float) -> float:
    return round(value, 6)


def dominant(counter: Counter[str]) -> tuple[str, int, float]:
    if not counter:
        return "", 0, 0.0

    strategy, count = counter.most_common(1)[0]
    return strategy, count, count / sum(counter.values())


def mechanism_label(profile: str, load: str) -> str:
    labels = {
        ("burst_critical", "high"): "local_batch_interaction_matches_qubo_v1",
        ("burst_critical", "overload"): "local_batch_signal_limited_by_global_saturation",
        ("flooding_critical", "high"): "critical_protection_with_tail_latency_tradeoff",
        ("flooding_critical", "overload"): "critical_protection_limited_by_overload",
        ("heterogeneous_pressure", "high"): "worker_queue_state_dominates_local_batch_terms",
        ("heterogeneous_pressure", "overload"): "heterogeneous_queue_pressure_dominates",
        ("fairness_starvation", "high"): "long_horizon_fairness_not_represented",
        ("fairness_starvation", "overload"): "starvation_memory_not_represented",
    }
    return labels[(profile, load)]


def build_diagnostics(rows: list[dict[str, str]]) -> list[dict[str, object]]:
    by_group: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        by_group[(row["profile"], row["load_level"])].append(row)

    diagnostics = []

    for profile, load in GROUP_ORDER:
        group = by_group[(profile, load)]
        comparisons = len(group)
        objective_counter = Counter(row["best_objective_classical_strategy"] for row in group)
        critical_counter = Counter(row["best_critical_classical_strategy"] for row in group)
        p99_counter = Counter(row["best_p99_classical_strategy"] for row in group)
        starvation_counter = Counter(row["best_starvation_classical_strategy"] for row in group)
        fairness_counter = Counter(row["best_worker_fairness_classical_strategy"] for row in group)

        objective_strategy, objective_count, objective_rate = dominant(objective_counter)
        critical_strategy, critical_count, critical_rate = dominant(critical_counter)
        p99_strategy, p99_count, p99_rate = dominant(p99_counter)
        starvation_strategy, starvation_count, starvation_rate = dominant(starvation_counter)
        fairness_strategy, fairness_count, fairness_rate = dominant(fairness_counter)

        diagnostics.append(
            {
                "profile": profile,
                "load_level": load,
                "comparisons": comparisons,
                "mechanism_label": mechanism_label(profile, load),
                "dominant_objective_classical_strategy": objective_strategy,
                "dominant_objective_classical_count": objective_count,
                "dominant_objective_classical_rate": rounded(objective_rate),
                "dominant_critical_classical_strategy": critical_strategy,
                "dominant_critical_classical_count": critical_count,
                "dominant_critical_classical_rate": rounded(critical_rate),
                "dominant_p99_classical_strategy": p99_strategy,
                "dominant_p99_classical_count": p99_count,
                "dominant_p99_classical_rate": rounded(p99_rate),
                "dominant_starvation_classical_strategy": starvation_strategy,
                "dominant_starvation_classical_count": starvation_count,
                "dominant_starvation_classical_rate": rounded(starvation_rate),
                "dominant_fairness_classical_strategy": fairness_strategy,
                "dominant_fairness_classical_count": fairness_count,
                "dominant_fairness_classical_rate": rounded(fairness_rate),
                "qubo_v1_objective_wins": sum(as_bool(row, "qubo_v1_objective_win") for row in group),
                "qubo_v1_within_5pct": sum(
                    as_bool(row, "qubo_v1_within_5pct_objective") for row in group
                ),
                "qubo_v1_better_than_v0": sum(as_bool(row, "qubo_v1_better_than_v0") for row in group),
                "hybrid_activation_signal": sum(
                    as_bool(row, "hybrid_activation_signal") for row in group
                ),
                **{
                    f"{field}_mean": rounded(mean(as_float(row, field) for row in group))
                    for field in METRIC_FIELDS
                },
            }
        )

    return diagnostics


def build_strategy_counts(rows: list[dict[str, str]]) -> list[dict[str, object]]:
    by_group: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        by_group[(row["profile"], row["load_level"])].append(row)

    output = []

    for profile, load in GROUP_ORDER:
        group = by_group[(profile, load)]

        for field in COUNT_FIELDS:
            counter = Counter(row[field] for row in group)

            for strategy, count in sorted(counter.items()):
                output.append(
                    {
                        "profile": profile,
                        "load_level": load,
                        "selection_metric": field,
                        "strategy": strategy,
                        "count": count,
                        "rate": rounded(count / len(group)),
                    }
                )

    return output


def build_case_examples(rows: list[dict[str, str]]) -> list[dict[str, object]]:
    by_group: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        by_group[(row["profile"], row["load_level"])].append(row)

    examples = []

    for profile, load in GROUP_ORDER:
        group = by_group[(profile, load)]
        mean_gap = mean(as_float(row, "qubo_v1_objective_gap_pct") for row in group)
        selected = {
            "representative_gap": min(
                group, key=lambda row: abs(as_float(row, "qubo_v1_objective_gap_pct") - mean_gap)
            ),
            "strongest_qubo_v1_case": min(group, key=lambda row: as_float(row, "qubo_v1_objective_gap_pct")),
            "strongest_classical_case": max(group, key=lambda row: as_float(row, "qubo_v1_objective_gap_pct")),
        }

        for case_type, row in selected.items():
            examples.append(
                {
                    "case_type": case_type,
                    "profile": profile,
                    "load_level": load,
                    "seed": row["seed"],
                    "best_objective_classical_strategy": row["best_objective_classical_strategy"],
                    "objective_win": row["qubo_v1_objective_win"],
                    "within_5pct": row["qubo_v1_within_5pct_objective"],
                    "better_than_v0": row["qubo_v1_better_than_v0"],
                    "hybrid_signal": row["hybrid_activation_signal"],
                    "objective_gap_pct": row["qubo_v1_objective_gap_pct"],
                    "improvement_vs_v0_pct": row["qubo_v1_objective_improvement_vs_v0_pct"],
                    "critical_delta": row["critical_delta_vs_objective_classical"],
                    "p99_improvement_pct": row["p99_improvement_vs_objective_classical_pct"],
                    "starvation_delta": row["starvation_delta_vs_objective_classical"],
                    "worker_fairness_delta": row["worker_fairness_delta_vs_objective_classical"],
                }
            )

    return examples


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    if not rows:
        raise ValueError(f"No rows to write for {path}")

    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def write_summary(path: Path, diagnostics: list[dict[str, object]]) -> None:
    lines = [
        "# Mechanism diagnostics for QUBO v1",
        "",
        "This file summarizes diagnostic evidence extracted from the already generated targeted stress matrix.",
        "It is intended to support the mechanism-oriented rewrite of Section 5.5, not to replace the formal result tables.",
        "",
        "## What the diagnostics show",
        "",
    ]

    for row in diagnostics:
        profile = row["profile"]
        load = row["load_level"]
        objective_strategy = row["dominant_objective_classical_strategy"]
        objective_rate = pct(float(row["dominant_objective_classical_rate"]))
        v0_count = row["qubo_v1_better_than_v0"]
        wins = row["qubo_v1_objective_wins"]
        gap = row["qubo_v1_objective_gap_pct_mean"]
        critical = row["critical_delta_vs_objective_classical_mean"]
        p99 = row["p99_improvement_vs_objective_classical_pct_mean"]
        starvation = row["starvation_delta_vs_objective_classical_mean"]
        label = row["mechanism_label"]

        lines.extend(
            [
                f"### `{profile}` / `{load}`",
                "",
                f"- Mechanism label: `{label}`.",
                f"- Dominant objective-best classical strategy: `{objective_strategy}` ({objective_rate} of seeds).",
                f"- QUBO v1 objective wins vs best classical: {wins}/30.",
                f"- QUBO v1 improves over QUBO v0: {v0_count}/30.",
                f"- Mean objective gap vs best classical: {gap:.2f}%.",
                f"- Mean critical deadline delta: {critical:.4f}.",
                f"- Mean p99 latency improvement: {p99:.2f}%.",
                f"- Mean starvation delta: {starvation:.2f}.",
                "",
            ]
        )

    lines.extend(
        [
            "## Benchmark candidates for the next round",
            "",
            "These candidates are derived from the mechanism analysis and should only be added if they directly support the next delivery.",
            "",
            "1. QUBO v1 without intra-batch sequencing terms.",
            "2. QUBO v1 without critical/deadline reinforcement.",
            "3. Load sweep over the critical burst scenario to locate where saturation cancels the local QUBO advantage.",
            "4. Heterogeneity sweep to test whether worker-state pressure dominates the current balance term.",
            "5. Starvation-focused scenario with exported assignments to inspect whether a long-horizon fairness term is needed.",
            "",
        ]
    )

    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    rows = read_rows(INPUT)
    diagnostics = build_diagnostics(rows)
    strategy_counts = build_strategy_counts(rows)
    case_examples = build_case_examples(rows)

    write_csv(DIAGNOSTICS_CSV, diagnostics)
    write_csv(STRATEGY_COUNTS_CSV, strategy_counts)
    write_csv(CASE_EXAMPLES_CSV, case_examples)
    write_summary(SUMMARY_MD, diagnostics)

    print(f"Wrote {DIAGNOSTICS_CSV.relative_to(REPO_ROOT)}")
    print(f"Wrote {STRATEGY_COUNTS_CSV.relative_to(REPO_ROOT)}")
    print(f"Wrote {CASE_EXAMPLES_CSV.relative_to(REPO_ROOT)}")
    print(f"Wrote {SUMMARY_MD.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
