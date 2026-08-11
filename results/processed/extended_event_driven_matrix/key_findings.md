# Extended Event-Driven Matrix Findings

This generated summary is a technical companion for the experiment outputs.
It is not a peer-reviewed analysis by itself.

## Experimental Scope

- Generated scenario instances: 120.
- Profile/load groups: 12.
- Profiles: burst, saturation, critical_heavy, heterogeneous.
- Loads: medium, high, overload.
- Seeds: 1..10.
- Strategies: QUBO v0, QUBO v1 sequencing, priority_aware, shortest_queue, min_cost_greedy.

## Main Results

- QUBO v1 beat the best classical strategy in 9/120 generated scenarios (7.50%).
- QUBO v1 was within 5% of the best classical strategy in 50/120 generated scenarios (41.67%).
- QUBO v1 improved over QUBO v0 in 97/120 generated scenarios (80.83%).
- Average QUBO v1 gap vs best classical: 8.27%.
- Average QUBO v1 improvement vs QUBO v0: 2.75%.

## Best Strategy Counts

| strategy | win count | win rate |
| --- | ---: | ---: |
| qubo_batch_exact | 0 | 0.00% |
| qubo_batch_exact_sequencing | 9 | 7.50% |
| priority_aware | 61 | 50.83% |
| shortest_queue | 35 | 29.17% |
| min_cost_greedy | 15 | 12.50% |

## Profile/Load Summary

| profile | load | best overall | QUBO v1 gap vs best classical % | QUBO v1 improvement vs v0 % |
| --- | --- | --- | ---: | ---: |
| burst | medium | priority_aware | 1.24 | 4.44 |
| burst | high | priority_aware | 5.74 | 5.91 |
| burst | overload | priority_aware | 0.96 | 2.28 |
| saturation | medium | shortest_queue | 14.65 | 2.02 |
| saturation | high | priority_aware | 10.17 | 0.85 |
| saturation | overload | priority_aware | 9.53 | -0.39 |
| critical_heavy | medium | priority_aware | 4.01 | 6.16 |
| critical_heavy | high | priority_aware | 13.12 | 5.46 |
| critical_heavy | overload | priority_aware | 2.21 | 2.32 |
| heterogeneous | medium | min_cost_greedy | 13.09 | 2.42 |
| heterogeneous | high | shortest_queue | 18.18 | 0.99 |
| heterogeneous | overload | priority_aware | 1.03 | 0.70 |

## Interpretation Notes

- QUBO v1 was the best mean strategy in 0/12 profile/load groups.
- QUBO v1 improved over QUBO v0 in 11/12 profile/load groups.
- QUBO v1 stayed within 5% of the best classical mean result in 5/12 profile/load groups.
- These results reinforce QUBO v1 as a useful specialist formulation under complex event-driven pressure, but not as a universal replacement for classical heuristics.
