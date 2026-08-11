# QAOA Validation

This folder contains the Python/Qiskit validation layer for small QUBO
instances exported by the Elixir simulator.

The intended flow is:

1. Export tiny QUBO instances from Elixir.
2. Solve each instance with Qiskit QAOA using one or more depths and seeds.
3. Compare QAOA's best sampled solution against the exact reference solution
   produced by the Elixir brute-force solver.

The validation is deliberately limited to small batches. It is not meant to
replace the full event-driven simulation; it validates whether the QUBO
formulation can be consumed by a quantum variational optimizer and whether the
approximate solution recovers the exact assignment on controlled instances.

Run from the repository root:

```powershell
.\scripts\run_qaoa_validation.ps1
```

Main outputs:

- `results/raw/v1_qaoa_validation_instances`: exported QUBO JSON instances.
- `results/raw/v1_qaoa_validation/attempts.csv`: all QAOA attempts.
- `results/raw/v1_qaoa_validation/summary.csv`: best attempt per instance.
- `results/raw/v1_qaoa_validation/analysis.md`: generated human-readable summary.

The default PowerShell script runs a fast validation mode:

- QAOA depth `reps=1`;
- one deterministic seed;
- 512 sampler shots;
- 25 COBYLA iterations;
- at most 9 QUBO variables per instance.

Use the script parameters to launch extended runs once the quick path is
confirmed.

The current observed extended-run note is stored in:

```text
results/raw/v1_qaoa_validation/extended_attempt_notes.md
```
