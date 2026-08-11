#!/usr/bin/env python
"""Validate exported QUBO instances with Qiskit QAOA.

The script intentionally keeps Elixir as the source of truth for the scheduling
model. It only consumes exported QUBO coefficients, runs QAOA on tiny instances,
and compares the approximate result against the exact reference solution stored
with each instance.
"""

from __future__ import annotations

import argparse
import csv
import importlib.metadata
import json
import math
import sys
import time
from pathlib import Path
from typing import Any


REQUIRED_PACKAGES = ("qiskit", "qiskit-algorithms", "qiskit-optimization")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--instances",
        default="results/raw/v1_qaoa_validation_instances",
        help="Directory containing exported QUBO JSON instances or one JSON instance file.",
    )
    parser.add_argument(
        "--out",
        default="results/raw/v1_qaoa_validation",
        help="Directory where QAOA validation outputs will be written.",
    )
    parser.add_argument("--reps", default="1,2", help="Comma-separated QAOA depths.")
    parser.add_argument("--seeds", default="7,13", help="Comma-separated deterministic seeds.")
    parser.add_argument("--shots", type=int, default=2048, help="Sampler shots per QAOA evaluation.")
    parser.add_argument("--maxiter", type=int, default=80, help="COBYLA maximum iterations.")
    parser.add_argument(
        "--max-instances",
        type=int,
        default=None,
        help="Optional cap for quick smoke runs.",
    )
    parser.add_argument(
        "--max-variables",
        type=int,
        default=None,
        help="Optional cap by QUBO variable count.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    instances = load_instances(Path(args.instances))

    if args.max_variables is not None:
        skipped = [
            instance
            for instance in instances
            if int(instance["variable_count"]) > args.max_variables
        ]
        instances = [
            instance
            for instance in instances
            if int(instance["variable_count"]) <= args.max_variables
        ]

        for instance in skipped:
            print(
                "Skipping {instance_id}: {variable_count} variables exceeds --max-variables "
                "{max_variables}".format(
                    instance_id=instance["instance_id"],
                    variable_count=instance["variable_count"],
                    max_variables=args.max_variables,
                ),
                flush=True,
            )

    if args.max_instances is not None:
        instances = instances[: args.max_instances]

    if not instances:
        raise SystemExit(f"No QUBO instances found in {args.instances}")

    try:
        qiskit_api = import_qiskit()
    except ImportError as error:
        print(missing_dependency_message(error), file=sys.stderr)
        return 2

    reps_values = parse_int_list(args.reps, "reps")
    seed_values = parse_int_list(args.seeds, "seeds")
    output_dir = Path(args.out)
    output_dir.mkdir(parents=True, exist_ok=True)

    attempts: list[dict[str, Any]] = []
    summaries: list[dict[str, Any]] = []
    started_at = time.time()

    for instance in instances:
        instance_attempts: list[dict[str, Any]] = []

        for reps in reps_values:
            for seed in seed_values:
                print(
                    "Running {instance_id} with reps={reps}, seed={seed}, shots={shots}, "
                    "maxiter={maxiter}".format(
                        instance_id=instance["instance_id"],
                        reps=reps,
                        seed=seed,
                        shots=args.shots,
                        maxiter=args.maxiter,
                    ),
                    flush=True,
                )
                attempt = run_attempt(
                    qiskit_api=qiskit_api,
                    instance=instance,
                    reps=reps,
                    seed=seed,
                    shots=args.shots,
                    maxiter=args.maxiter,
                )
                attempts.append(attempt)
                instance_attempts.append(attempt)

        best_attempt = min(instance_attempts, key=attempt_sort_key)
        summaries.append(summary_row(instance, best_attempt))
        write_outputs(output_dir, summaries, attempts, time.time() - started_at)

    elapsed_seconds = round(time.time() - started_at, 3)
    write_outputs(output_dir, summaries, attempts, elapsed_seconds)

    print(f"QAOA validation instances: {len(instances)}")
    print(f"QAOA attempts: {len(attempts)}")
    print(f"Output: {output_dir}")
    print(f"Summary CSV: {output_dir / 'summary.csv'}")
    return 0


def import_qiskit() -> dict[str, Any]:
    from qiskit.primitives import StatevectorSampler
    from qiskit_algorithms import QAOA
    from qiskit_algorithms.optimizers import COBYLA
    from qiskit_algorithms.utils import algorithm_globals
    from qiskit_optimization.algorithms import MinimumEigenOptimizer
    from qiskit_optimization.problems import QuadraticProgram

    return {
        "COBYLA": COBYLA,
        "MinimumEigenOptimizer": MinimumEigenOptimizer,
        "QAOA": QAOA,
        "QuadraticProgram": QuadraticProgram,
        "StatevectorSampler": StatevectorSampler,
        "algorithm_globals": algorithm_globals,
    }


def missing_dependency_message(error: ImportError) -> str:
    packages = ", ".join(REQUIRED_PACKAGES)
    return (
        f"Missing Qiskit dependency: {error}. "
        f"Install {packages}, or run scripts/run_qaoa_validation.ps1 to use Docker."
    )


def load_instances(path: Path) -> list[dict[str, Any]]:
    if path.is_file():
        return [json.loads(path.read_text(encoding="utf-8"))]

    manifest_path = path / "manifest.json"

    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        files = [path / entry["file"] for entry in manifest["instances"]]
    else:
        files = sorted(item for item in path.glob("*.json") if item.name != "manifest.json")

    return [json.loads(file_path.read_text(encoding="utf-8")) for file_path in files]


def run_attempt(
    qiskit_api: dict[str, Any],
    instance: dict[str, Any],
    reps: int,
    seed: int,
    shots: int,
    maxiter: int,
) -> dict[str, Any]:
    qiskit_api["algorithm_globals"].random_seed = seed

    scale_factor = coefficient_scale(instance)
    problem = build_quadratic_program(qiskit_api["QuadraticProgram"], instance, scale_factor)
    sampler = qiskit_api["StatevectorSampler"](default_shots=shots, seed=seed)
    optimizer = qiskit_api["COBYLA"](maxiter=maxiter)
    qaoa = qiskit_api["QAOA"](sampler=sampler, optimizer=optimizer, reps=reps)
    solver = qiskit_api["MinimumEigenOptimizer"](qaoa)

    started_at = time.time()
    result = solver.solve(problem)
    elapsed_seconds = round(time.time() - started_at, 3)

    vectors = candidate_vectors(result)
    evaluated = [evaluate_candidate(instance, vector) for vector in vectors]
    best_candidate = min(evaluated, key=candidate_sort_key)
    exact_objective = float(instance["exact_solution"]["objective_value"])
    gap = best_candidate["objective_value"] - exact_objective
    relative_gap = gap / max(abs(exact_objective), 1.0)

    return {
        "instance_id": instance["instance_id"],
        "scenario": instance["scenario"],
        "profile": instance["profile"],
        "batch_index": instance["batch_index"],
        "variable_count": instance["variable_count"],
        "reps": reps,
        "seed": seed,
        "shots": shots,
        "maxiter": maxiter,
        "scale_factor": scale_factor,
        "elapsed_seconds": elapsed_seconds,
        "exact_objective": exact_objective,
        "qaoa_objective": best_candidate["objective_value"],
        "objective_gap": gap,
        "relative_gap": relative_gap,
        "feasible": best_candidate["feasible"],
        "exact_match": best_candidate["feasible"] and abs(gap) <= 1.0e-6,
        "constraint_violations": best_candidate["constraint_violations"],
        "selected_worker_by_event": best_candidate["selected_worker_by_event"],
        "assignment_vector": best_candidate["assignment_vector"],
        "assignment_bitstring": best_candidate["assignment_bitstring"],
        "qiskit_fval_scaled": safe_float(getattr(result, "fval", math.nan)),
        "qiskit_status": str(getattr(result, "status", "UNKNOWN")),
        "qiskit_sample_count": len(getattr(result, "samples", []) or []),
    }


def write_outputs(
    output_dir: Path,
    summaries: list[dict[str, Any]],
    attempts: list[dict[str, Any]],
    elapsed_seconds: float,
) -> None:
    elapsed_seconds = round(elapsed_seconds, 3)
    write_csv(output_dir / "attempts.csv", attempts)
    write_csv(output_dir / "summary.csv", summaries)
    write_json(
        output_dir / "summary.json",
        {
            "schema_version": "qaoa-validation-v1",
            "elapsed_seconds": elapsed_seconds,
            "qiskit_versions": package_versions(),
            "instance_count": len(summaries),
            "attempt_count": len(attempts),
            "summaries": summaries,
            "attempts": attempts,
        },
    )
    write_markdown(output_dir / "analysis.md", summaries, attempts, elapsed_seconds)


def build_quadratic_program(
    quadratic_program_type: Any, instance: dict[str, Any], scale_factor: float
) -> Any:
    problem = quadratic_program_type(name=instance["instance_id"])

    for variable in instance["variables"]:
        problem.binary_var(name=variable["name"])

    variable_names = {variable["index"]: variable["name"] for variable in instance["variables"]}

    linear = {
        variable_names[term["index"]]: term["coefficient"] * scale_factor
        for term in instance["linear"]
    }

    quadratic = {
        (variable_names[term["left"]], variable_names[term["right"]]): term["coefficient"]
        * scale_factor
        for term in instance["quadratic"]
    }

    problem.minimize(
        constant=instance["constant"] * scale_factor,
        linear=linear,
        quadratic=quadratic,
    )

    return problem


def candidate_vectors(result: Any) -> list[list[int]]:
    vectors: list[list[int]] = []

    if getattr(result, "x", None) is not None:
        vectors.append(normalize_vector(result.x))

    for sample in getattr(result, "samples", []) or []:
        if getattr(sample, "x", None) is not None:
            vectors.append(normalize_vector(sample.x))

    deduplicated: list[list[int]] = []
    seen: set[tuple[int, ...]] = set()

    for vector in vectors:
        key = tuple(vector)
        if key not in seen:
            deduplicated.append(vector)
            seen.add(key)

    if not deduplicated:
        raise RuntimeError("Qiskit did not return any candidate assignment vector.")

    return deduplicated


def normalize_vector(raw_vector: Any) -> list[int]:
    return [1 if float(value) >= 0.5 else 0 for value in list(raw_vector)]


def evaluate_candidate(instance: dict[str, Any], vector: list[int]) -> dict[str, Any]:
    objective_value = evaluate_objective(instance, vector)
    selected_worker_by_event = selected_workers(instance, vector)
    constraint_violations = count_constraint_violations(instance, selected_worker_by_event)

    return {
        "objective_value": objective_value,
        "assignment_vector": vector,
        "assignment_bitstring": "".join(str(bit) for bit in vector),
        "selected_worker_by_event": selected_worker_by_event,
        "constraint_violations": constraint_violations,
        "feasible": constraint_violations == 0,
    }


def evaluate_objective(instance: dict[str, Any], vector: list[int]) -> float:
    value = float(instance["constant"])

    for term in instance["linear"]:
        value += float(term["coefficient"]) * vector[int(term["index"])]

    for term in instance["quadratic"]:
        left = int(term["left"])
        right = int(term["right"])
        value += float(term["coefficient"]) * vector[left] * vector[right]

    return round(value, 6)


def selected_workers(instance: dict[str, Any], vector: list[int]) -> dict[str, list[str]]:
    selected = {event["id"]: [] for event in instance["events"]}

    for variable in instance["variables"]:
        if vector[int(variable["index"])] == 1:
            selected[variable["event_id"]].append(variable["worker_id"])

    return selected


def count_constraint_violations(
    instance: dict[str, Any], selected_worker_by_event: dict[str, list[str]]
) -> int:
    return sum(
        1
        for event in instance["events"]
        if len(selected_worker_by_event.get(event["id"], [])) != 1
    )


def coefficient_scale(instance: dict[str, Any]) -> float:
    coefficients = [abs(float(term["coefficient"])) for term in instance["linear"]]
    coefficients.extend(abs(float(term["coefficient"])) for term in instance["quadratic"])
    max_abs = max(coefficients) if coefficients else 1.0

    if max_abs == 0:
        return 1.0

    return 1.0 / max_abs


def candidate_sort_key(candidate: dict[str, Any]) -> tuple[int, float, int]:
    feasible_rank = 0 if candidate["feasible"] else 1
    return (feasible_rank, candidate["objective_value"], candidate["constraint_violations"])


def attempt_sort_key(attempt: dict[str, Any]) -> tuple[int, float, int]:
    feasible_rank = 0 if attempt["feasible"] else 1
    return (feasible_rank, attempt["qaoa_objective"], attempt["constraint_violations"])


def summary_row(instance: dict[str, Any], best_attempt: dict[str, Any]) -> dict[str, Any]:
    exact_vector = instance["exact_solution"]["assignment_vector"]
    same_assignment = exact_vector == best_attempt["assignment_vector"]

    return {
        "instance_id": instance["instance_id"],
        "scenario": instance["scenario"],
        "profile": instance["profile"],
        "batch_index": instance["batch_index"],
        "event_count": instance["event_count"],
        "worker_count": instance["worker_count"],
        "variable_count": instance["variable_count"],
        "best_reps": best_attempt["reps"],
        "best_seed": best_attempt["seed"],
        "exact_objective": best_attempt["exact_objective"],
        "qaoa_objective": best_attempt["qaoa_objective"],
        "objective_gap": best_attempt["objective_gap"],
        "relative_gap": best_attempt["relative_gap"],
        "feasible": best_attempt["feasible"],
        "exact_match": best_attempt["exact_match"],
        "same_assignment_as_exact": same_assignment,
        "constraint_violations": best_attempt["constraint_violations"],
        "elapsed_seconds": best_attempt["elapsed_seconds"],
        "assignment_bitstring": best_attempt["assignment_bitstring"],
    }


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return

    fieldnames = list(rows[0].keys())

    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows({key: csv_value(value) for key, value in row.items()} for row in rows)


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(to_jsonable(payload), indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_markdown(
    path: Path,
    summaries: list[dict[str, Any]],
    attempts: list[dict[str, Any]],
    elapsed_seconds: float,
) -> None:
    exact_matches = sum(1 for row in summaries if row["exact_match"])
    feasible = sum(1 for row in summaries if row["feasible"])
    average_gap = sum(float(row["objective_gap"]) for row in summaries) / len(summaries)

    lines = [
        "# QAOA Validation Summary",
        "",
        "This file is generated by `analysis/qaoa_validation/qaoa_validate_qubo.py`.",
        "",
        f"- Instances: {len(summaries)}",
        f"- Attempts: {len(attempts)}",
        f"- Feasible best attempts: {feasible}/{len(summaries)}",
        f"- Exact objective matches: {exact_matches}/{len(summaries)}",
        f"- Average objective gap: {average_gap:.6f}",
        f"- Elapsed seconds: {elapsed_seconds}",
        "",
        "## Best Attempt By Instance",
        "",
        "| instance | vars | reps | seed | exact | qaoa | gap | feasible | exact match |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |",
    ]

    for row in summaries:
        lines.append(
            "| {instance_id} | {variable_count} | {best_reps} | {best_seed} | "
            "{exact_objective:.6f} | {qaoa_objective:.6f} | {objective_gap:.6f} | "
            "{feasible} | {exact_match} |".format(**row)
        )

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_int_list(value: str, name: str) -> list[int]:
    parsed = [int(item.strip()) for item in value.split(",") if item.strip()]

    if not parsed:
        raise ValueError(f"{name} must contain at least one integer")

    return parsed


def package_versions() -> dict[str, str]:
    versions = {}

    for package in REQUIRED_PACKAGES:
        try:
            versions[package] = importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError:
            versions[package] = "not-installed"

    return versions


def safe_float(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None

    if math.isnan(number) or math.isinf(number):
        return None

    return number


def csv_value(value: Any) -> Any:
    if isinstance(value, (dict, list)):
        return json.dumps(to_jsonable(value), sort_keys=True)

    return value


def to_jsonable(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): to_jsonable(item) for key, item in value.items()}

    if isinstance(value, list):
        return [to_jsonable(item) for item in value]

    if isinstance(value, tuple):
        return [to_jsonable(item) for item in value]

    if hasattr(value, "item"):
        return value.item()

    return value


if __name__ == "__main__":
    raise SystemExit(main())
