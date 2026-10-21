# Targeted Stress Matrix Findings

This generated summary is a technical companion for the experiment outputs.
It is not a peer-reviewed analysis by itself.

## Experimental Scope

- Paired generated scenarios: 240.
- Profile/load groups: 8.
- Profiles: burst_critical, flooding_critical, heterogeneous_pressure, fairness_starvation.
- Loads: high, overload.
- Seeds: 1..30.
- Strategies: QUBO v0, QUBO v1 sequencing, priority_aware, deadline_aware_dispatch, shortest_queue, min_cost_greedy, duration_aware_dispatch.

## Overall Results

- QUBO v1 beat the best objective-based classical strategy in 44/240 scenarios (18.33%).
- QUBO v1 was within 5% of the best objective-based classical strategy in 147/240 scenarios (61.25%).
- QUBO v1 improved over QUBO v0 in 167/240 scenarios (69.58%).
- Hybrid activation signal appeared in 120/240 scenarios (50.00%).
- Mean objective gap vs best classical: 4.81% (95% CI 4.12% to 5.49%).
- Mean critical hit-rate delta vs the objective-best classical strategy: 0.0682 (95% CI 0.0575 to 0.0789).
- Mean p99 latency improvement vs the objective-best classical strategy: -1.73% (95% CI -2.35% to -1.11%).

## Strongest Signals

- Highest hybrid activation rate: burst_critical / high (100.00%).
- Lowest mean objective gap: burst_critical / high (-1.61%).
- Strongest critical-deadline delta: burst_critical / high (0.1649).
- Strongest improvement vs QUBO v0: burst_critical / high (17.35%).

## Profile/Load Summary

| profile | load | objective win rate | within 5% | hybrid signal | objective gap % mean | critical delta mean | p99 improvement % mean |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| burst_critical | high | 90.00% | 100.00% | 100.00% | -1.61 | 0.1649 | 0.98 |
| burst_critical | overload | 16.67% | 100.00% | 66.67% | 2.06 | 0.0362 | 1.66 |
| flooding_critical | high | 10.00% | 83.33% | 60.00% | 3.09 | 0.0714 | -4.62 |
| flooding_critical | overload | 0.00% | 60.00% | 53.33% | 4.86 | 0.0727 | -0.67 |
| heterogeneous_pressure | high | 16.67% | 40.00% | 36.67% | 6.47 | 0.0829 | -2.26 |
| heterogeneous_pressure | overload | 13.33% | 50.00% | 40.00% | 4.89 | 0.0365 | 1.09 |
| fairness_starvation | high | 0.00% | 16.67% | 16.67% | 11.96 | 0.0574 | -7.09 |
| fairness_starvation | overload | 0.00% | 40.00% | 26.67% | 6.72 | 0.0236 | -2.90 |

## Sign Tests

The 16 tests are treated as one family and adjusted with Holm's procedure.

| profile | load | test | wins | losses | raw p-value | Holm-adjusted p-value | reject at 0.05 |
| --- | --- | --- | ---: | ---: | ---: | ---: | --- |
| burst_critical | high | objective_vs_best_classical | 27 | 3 | 0.000008 | 0.000084 | yes |
| burst_critical | high | objective_vs_qubo_v0 | 30 | 0 | <0.000001 | <0.000001 | yes |
| burst_critical | overload | objective_vs_best_classical | 5 | 25 | 0.000325 | 0.002274 | yes |
| burst_critical | overload | objective_vs_qubo_v0 | 20 | 10 | 0.098737 | 0.493686 | no |
| flooding_critical | high | objective_vs_best_classical | 3 | 27 | 0.000008 | 0.000084 | yes |
| flooding_critical | high | objective_vs_qubo_v0 | 30 | 0 | <0.000001 | <0.000001 | yes |
| flooding_critical | overload | objective_vs_best_classical | 0 | 30 | <0.000001 | <0.000001 | yes |
| flooding_critical | overload | objective_vs_qubo_v0 | 28 | 2 | <0.000001 | 0.000010 | yes |
| heterogeneous_pressure | high | objective_vs_best_classical | 5 | 25 | 0.000325 | 0.002274 | yes |
| heterogeneous_pressure | high | objective_vs_qubo_v0 | 16 | 14 | 0.855536 | 1.000000 | no |
| heterogeneous_pressure | overload | objective_vs_best_classical | 4 | 26 | 0.000059 | 0.000476 | yes |
| heterogeneous_pressure | overload | objective_vs_qubo_v0 | 16 | 14 | 0.855536 | 1.000000 | no |
| fairness_starvation | high | objective_vs_best_classical | 0 | 30 | <0.000001 | <0.000001 | yes |
| fairness_starvation | high | objective_vs_qubo_v0 | 16 | 14 | 0.855536 | 1.000000 | no |
| fairness_starvation | overload | objective_vs_best_classical | 0 | 30 | <0.000001 | <0.000001 | yes |
| fairness_starvation | overload | objective_vs_qubo_v0 | 11 | 19 | 0.200488 | 0.801954 | no |

## Interpretation Boundary

- The hybrid activation signal is a decision-support indicator, not a production scheduler.
- QUBO v1 should be interpreted as a candidate specialist optimizer for selected pressure windows.
- These results still do not demonstrate quantum advantage; they deepen the evidence for a hybrid quantum-inspired architecture.
