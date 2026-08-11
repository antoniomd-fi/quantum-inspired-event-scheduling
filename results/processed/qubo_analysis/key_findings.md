# QUBO/QAOA Technical Findings

This generated summary is a technical companion for the experiment outputs.
It is not a peer-reviewed analysis by itself.

## Main QUBO Comparison

- QUBO v1 sequencing improved over QUBO v0 in 4/5 scenarios.
- QUBO v1 sequencing was the best overall strategy in 1/5 scenarios.
- Scenarios where QUBO v1 was best: burst_load.
- Average positive improvement of QUBO v1 over QUBO v0: 12.70%.

## Best Strategy By Scenario

| scenario | best strategy | objective cost/event | critical deadline hit rate |
| --- | --- | ---: | ---: |
| baseline_small | shortest_queue | 202.1444 | 1.0000 |
| steady_load | shortest_queue | 196.2389 | 1.0000 |
| burst_load | qubo_batch_exact_sequencing | 600.7891 | 1.0000 |
| critical_priority | priority_aware | 563.3743 | 1.0000 |
| heterogeneous_workers | shortest_queue | 367.2571 | 1.0000 |

## QUBO v1 vs QUBO v0

| scenario | v0 | v1 | improvement | improvement % | v1 rank |
| --- | ---: | ---: | ---: | ---: | ---: |
| baseline_small | 230.4472 | 227.9528 | 2.4944 | 1.08 | 3 |
| steady_load | 201.1125 | 201.1125 | 0.0000 | 0.00 | 5 |
| burst_load | 744.3125 | 600.7891 | 143.5234 | 19.28 | 1 |
| critical_priority | 856.4457 | 599.4586 | 256.9871 | 30.01 | 2 |
| heterogeneous_workers | 440.8000 | 438.9500 | 1.8500 | 0.42 | 3 |

## Sensitivity

| scenario | best QUBO profile | objective cost/event | critical deadline hit rate |
| --- | --- | ---: | ---: |
| baseline_small | qubo_batch_exact | 230.4472 | 1.0000 |
| steady_load | qubo_batch_exact_critical_focused | 201.0833 | 1.0000 |
| burst_load | qubo_batch_exact_critical_focused | 716.3875 | 0.4375 |
| critical_priority | qubo_batch_exact_critical_focused | 801.0543 | 0.3500 |
| heterogeneous_workers | qubo_batch_exact | 440.8000 | 1.0000 |

## QAOA Validation

- Completed QAOA validation instances: 4.
- Feasible QAOA solutions: 4/4.
- Exact objective matches: 4/4.
- Maximum completed variable count: 9.
- Average elapsed time per completed instance: 70.69 seconds.
- The 12-variable steady-load instance is documented as an extended runtime limit.

## Generated Assets

- `results/processed/qubo_analysis/sequencing_strategy_comparison.csv`
- `results/processed/qubo_analysis/sequencing_best_by_scenario.csv`
- `results/processed/qubo_analysis/qubo_v0_v1_delta.csv`
- `results/processed/qubo_analysis/qubo_sensitivity_rankings.csv`
- `results/processed/qubo_analysis/qaoa_validation_aggregate.csv`
- `results/figures/qubo_analysis/objective_cost_by_scenario.svg`
- `results/figures/qubo_analysis/critical_deadline_hit_rate_by_scenario.svg`
- `results/figures/qubo_analysis/qubo_v1_improvement_vs_v0.svg`
- `results/figures/qubo_analysis/qaoa_objective_gap_by_instance.svg`
- `results/figures/qubo_analysis/*_en.svg` English technical copies.
