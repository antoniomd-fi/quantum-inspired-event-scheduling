# Quantum-Inspired Event Scheduling

Experimental artifact for evaluating quantum-inspired scheduling strategies in
event-driven distributed systems.

The repository contains:

- an Elixir/Docker simulator for event-driven scheduling scenarios;
- classical scheduling baselines;
- exact QUBO batch strategies used as quantum-inspired optimizers;
- Python analysis scripts for processed tables and SVG figures;
- small-instance QAOA validation with Qiskit;
- curated raw and processed experiment outputs;
- bilingual Livebooks for reproducible result inspection.

## Main Result

The experiments do not claim universal quantum advantage. The strongest finding
is contextual:

```text
QUBO-based scheduling is most useful as a specialist optimizer in selected
multi-objective pressure windows, especially critical burst scenarios.
```

In the targeted stress matrix:

- QUBO v1 beat the best objective-based classical strategy in 44/240 paired
  comparisons.
- QUBO v1 stayed within 5% of the best objective-based classical strategy in
  147/240 comparisons.
- The hybrid activation signal appeared in 120/240 comparisons.
- The strongest case was `burst_critical/high`, where QUBO v1 won in 90% of
  seeds and produced a hybrid activation signal in 100% of seeds.

## Repository Layout

```text
code/event_scheduler_sim/     Elixir simulator and scheduling strategies
analysis/                     Python analysis and QAOA validation scripts
scripts/                      Reproducible PowerShell commands
notebooks/livebook/           English and Spanish Livebooks
results/raw/                  Curated raw experiment outputs
results/processed/            Processed CSV summaries
results/figures/              Generated SVG figures
```

## Run The Simulator

Build the Docker image:

```powershell
docker build -t quantum-inspired-event-scheduling-sim .\code\event_scheduler_sim
```

Run tests:

```powershell
docker run --rm -v "${PWD}:/workspace" -w /workspace/code/event_scheduler_sim quantum-inspired-event-scheduling-sim mix test
```

Run the targeted stress matrix:

```powershell
.\scripts\run_targeted_stress_matrix.ps1
```

Process targeted results:

```powershell
.\scripts\run_targeted_stress_analysis.ps1
```

## Open The Livebooks

Start Livebook with Docker:

```powershell
docker run --rm -p 8080:8080 -v "${PWD}:/workspace" ghcr.io/livebook-dev/livebook:latest
```

Then open:

```text
http://localhost:8080
```

Available notebooks:

- `/workspace/notebooks/livebook/results_exploration_en.livemd`
- `/workspace/notebooks/livebook/results_exploration_es.livemd`

## Reproduce Processed Outputs

```powershell
python analysis\extended_experiment_analysis.py
python analysis\qaoa_validation_analysis.py
python analysis\targeted_stress_analysis.py
```

The QAOA validation dependencies are isolated in:

```text
analysis/qaoa_validation/
```

## Interpretation Boundary

This artifact supports an experimental, quantum-inspired scheduling study. It
does not demonstrate scalable quantum advantage and should not be interpreted as
a production scheduler.

The intended interpretation is a hybrid architecture:

- classical heuristics as the default low-latency path;
- QUBO-based optimization for selected high-pressure windows;
- QAOA as small-instance validation of the QUBO-to-quantum-optimizer path.
