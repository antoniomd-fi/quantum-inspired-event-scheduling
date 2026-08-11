# Event Scheduler Simulation

This is the Elixir simulation core for quantum-inspired event-driven scheduling experiments.

The initial version focuses on deterministic classical baselines so the experimental contract is clear before adding Broadway, GenStage, QUBO, or QAOA integrations.

## Contract

Inputs:

- Scenario files in `scenarios/*.exs`.
- Scheduling strategy name.
- Optional batch strategy and scenario lists.
- Parameterized experiment profiles, load levels, and seeds.

Outputs:

- `assignments.csv`
- `metrics.json`
- `summary.md`
- `summary.csv` for batch comparisons
- `runs.csv` and `aggregated.csv` for repeated experimental matrices

The main technical model is documented in:

- `../../docs/problem_model.md`
- `../../docs/objective_function.md`
- `../../docs/qubo_formulation.md`
- `../../docs/qaoa_validation.md`
- `../../docs/results_analysis.md`
- `../../docs/targeted_stress_experiments.md`

## Run With Docker

From the repository root:

```powershell
docker build -t quantum-inspired-event-scheduling-sim .\code\event_scheduler_sim
docker run --rm -v "${PWD}:/workspace" -w /workspace/code/event_scheduler_sim quantum-inspired-event-scheduling-sim mix deps.get
docker run --rm -v "${PWD}:/workspace" -w /workspace/code/event_scheduler_sim quantum-inspired-event-scheduling-sim mix test
docker run --rm -v "${PWD}:/workspace" -w /workspace/code/event_scheduler_sim quantum-inspired-event-scheduling-sim mix sim.run --scenario scenarios/baseline.exs --strategy round_robin --out ../../results/raw/baseline_round_robin
docker run --rm -v "${PWD}:/workspace" -w /workspace/code/event_scheduler_sim quantum-inspired-event-scheduling-sim mix sim.batch --out ../../results/raw/v1_classical_baselines
docker run --rm -v "${PWD}:/workspace" -w /workspace/code/event_scheduler_sim quantum-inspired-event-scheduling-sim mix sim.experiment --seeds 1..5 --out ../../results/raw/v1_experimental_matrix
```

Or use the helper script:

```powershell
.\scripts\run_event_scheduler.ps1
.\scripts\run_event_scheduler_batch.ps1
.\scripts\run_event_scheduler_experiment.ps1
.\scripts\run_qubo_reduced_comparison.ps1
.\scripts\run_qubo_sensitivity.ps1
.\scripts\run_qubo_sequencing_comparison.ps1
.\scripts\run_qaoa_validation.ps1
.\scripts\run_qubo_results_analysis.ps1
.\scripts\run_extended_event_driven_matrix.ps1
python analysis\extended_experiment_analysis.py
.\scripts\run_qaoa_validation_analysis.ps1
.\scripts\run_targeted_stress_matrix.ps1
.\scripts\run_targeted_stress_analysis.ps1
```

## Run Without Docker

This requires Elixir and Erlang/OTP on the host:

```powershell
mix test
mix sim.run --scenario scenarios/baseline.exs --strategy round_robin --out results/baseline_round_robin
mix sim.batch --out results/v1_classical_baselines
mix sim.experiment --seeds 1..5 --out results/v1_experimental_matrix
```

## Strategies

- `round_robin`
- `weighted_round_robin`
- `shortest_queue`
- `least_loaded`
- `priority_aware`
- `deadline_aware_dispatch`
- `duration_aware_dispatch`
- `min_cost_greedy`

`min_cost_greedy` uses the shared objective function implemented in
`EventSchedulerSim.Objective`.

Experimental strategy:

- `qubo_batch_exact`
- `qubo_batch_exact_deadline_focused`
- `qubo_batch_exact_critical_focused`
- `qubo_batch_exact_low_balance`
- `qubo_batch_exact_sequencing`

`qubo_batch_exact` builds and solves small QUBO batches exactly. It is useful
for validation runs, but it is not included in default full-matrix experiments.

The reduced comparison setup is documented in:

- `../../docs/qubo_reduced_comparison.md`
- `../../docs/qubo_sensitivity.md`
- `../../docs/qubo_v1_sequencing.md`
- `../../docs/qaoa_validation.md`

## Scenarios

- `baseline`
- `steady_load`
- `burst_load`
- `progressive_saturation`
- `critical_priority`
- `heterogeneous_workers`

## Parameterized Experiment Profiles

- `steady`
- `burst`
- `saturation`
- `critical_heavy`
- `heterogeneous`
- `burst_critical`
- `flooding_critical`
- `heterogeneous_pressure`
- `fairness_starvation`

## Next Technical Milestones

- Add Broadway/GenStage pipelines for event production, processing, and backpressure.
- Add analysis notebooks or Livebooks for the finalized result slices.
