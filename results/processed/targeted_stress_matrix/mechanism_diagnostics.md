# Mechanism diagnostics for QUBO v1

This file summarizes diagnostic evidence extracted from the already generated targeted stress matrix.
It is intended to support the mechanism-oriented rewrite of Section 5.5, not to replace the formal result tables.

## What the diagnostics show

### `burst_critical` / `high`

- Mechanism label: `local_batch_interaction_matches_qubo_v1`.
- Dominant objective-best classical strategy: `deadline_aware_dispatch` (96.67% of seeds).
- QUBO v1 objective wins vs best classical: 27/30.
- QUBO v1 improves over QUBO v0: 30/30.
- Mean objective gap vs best classical: -1.61%.
- Mean critical deadline delta: 0.1649.
- Mean p99 latency improvement: 0.98%.
- Mean starvation delta: 0.40.

### `burst_critical` / `overload`

- Mechanism label: `local_batch_signal_limited_by_global_saturation`.
- Dominant objective-best classical strategy: `duration_aware_dispatch` (86.67% of seeds).
- QUBO v1 objective wins vs best classical: 5/30.
- QUBO v1 improves over QUBO v0: 20/30.
- Mean objective gap vs best classical: 2.06%.
- Mean critical deadline delta: 0.0362.
- Mean p99 latency improvement: 1.66%.
- Mean starvation delta: 5.83.

### `flooding_critical` / `high`

- Mechanism label: `critical_protection_with_tail_latency_tradeoff`.
- Dominant objective-best classical strategy: `priority_aware` (63.33% of seeds).
- QUBO v1 objective wins vs best classical: 3/30.
- QUBO v1 improves over QUBO v0: 30/30.
- Mean objective gap vs best classical: 3.09%.
- Mean critical deadline delta: 0.0714.
- Mean p99 latency improvement: -4.62%.
- Mean starvation delta: 2.70.

### `flooding_critical` / `overload`

- Mechanism label: `critical_protection_limited_by_overload`.
- Dominant objective-best classical strategy: `duration_aware_dispatch` (100.00% of seeds).
- QUBO v1 objective wins vs best classical: 0/30.
- QUBO v1 improves over QUBO v0: 28/30.
- Mean objective gap vs best classical: 4.86%.
- Mean critical deadline delta: 0.0727.
- Mean p99 latency improvement: -0.67%.
- Mean starvation delta: 9.40.

### `heterogeneous_pressure` / `high`

- Mechanism label: `worker_queue_state_dominates_local_batch_terms`.
- Dominant objective-best classical strategy: `shortest_queue` (73.33% of seeds).
- QUBO v1 objective wins vs best classical: 5/30.
- QUBO v1 improves over QUBO v0: 16/30.
- Mean objective gap vs best classical: 6.47%.
- Mean critical deadline delta: 0.0829.
- Mean p99 latency improvement: -2.26%.
- Mean starvation delta: 0.30.

### `heterogeneous_pressure` / `overload`

- Mechanism label: `heterogeneous_queue_pressure_dominates`.
- Dominant objective-best classical strategy: `shortest_queue` (73.33% of seeds).
- QUBO v1 objective wins vs best classical: 4/30.
- QUBO v1 improves over QUBO v0: 16/30.
- Mean objective gap vs best classical: 4.89%.
- Mean critical deadline delta: 0.0365.
- Mean p99 latency improvement: 1.09%.
- Mean starvation delta: 1.70.

### `fairness_starvation` / `high`

- Mechanism label: `long_horizon_fairness_not_represented`.
- Dominant objective-best classical strategy: `shortest_queue` (70.00% of seeds).
- QUBO v1 objective wins vs best classical: 0/30.
- QUBO v1 improves over QUBO v0: 16/30.
- Mean objective gap vs best classical: 11.96%.
- Mean critical deadline delta: 0.0574.
- Mean p99 latency improvement: -7.09%.
- Mean starvation delta: 3.63.

### `fairness_starvation` / `overload`

- Mechanism label: `starvation_memory_not_represented`.
- Dominant objective-best classical strategy: `shortest_queue` (56.67% of seeds).
- QUBO v1 objective wins vs best classical: 0/30.
- QUBO v1 improves over QUBO v0: 11/30.
- Mean objective gap vs best classical: 6.72%.
- Mean critical deadline delta: 0.0236.
- Mean p99 latency improvement: -2.90%.
- Mean starvation delta: 4.57.

## Benchmark candidates for the next round

These candidates are derived from the mechanism analysis and should only be added if they directly support the next delivery.

1. QUBO v1 without intra-batch sequencing terms.
2. QUBO v1 without critical/deadline reinforcement.
3. Load sweep over the critical burst scenario to locate where saturation cancels the local QUBO advantage.
4. Heterogeneity sweep to test whether worker-state pressure dominates the current balance term.
5. Starvation-focused scenario with exported assignments to inspect whether a long-horizon fairness term is needed.
