defmodule EventSchedulerSimTest do
  use ExUnit.Case

  test "runs the baseline round-robin scenario" do
    output_dir = Path.join(System.tmp_dir!(), "event_scheduler_sim_test")
    File.rm_rf!(output_dir)

    result =
      EventSchedulerSim.run(
        scenario_path: "scenarios/baseline.exs",
        strategy: "round_robin",
        output_dir: output_dir
      )

    assert result.strategy == "round_robin"
    assert result.metrics.scenario == "baseline_small"
    assert result.metrics.total_events == 36
    assert result.metrics.throughput_events_per_second > 0
    assert result.metrics.objective_total_cost > 0
    assert result.metrics.objective_average_cost_per_event > 0
    assert File.exists?(Path.join(output_dir, "assignments.csv"))
    assert File.exists?(Path.join(output_dir, "metrics.json"))
    assert File.exists?(Path.join(output_dir, "summary.md"))
  end

  test "runs all bundled scenarios with all classical strategies" do
    for scenario_path <- EventSchedulerSim.Batch.default_scenarios(),
        strategy <- EventSchedulerSim.Strategy.names() do
      output_dir =
        Path.join([
          System.tmp_dir!(),
          "event_scheduler_sim_all_strategies",
          Path.basename(scenario_path, ".exs"),
          strategy
        ])

      File.rm_rf!(output_dir)

      result =
        EventSchedulerSim.run(
          scenario_path: scenario_path,
          strategy: strategy,
          output_dir: output_dir
        )

      assert result.strategy == strategy
      assert result.metrics.total_events > 0
      assert result.metrics.throughput_events_per_second >= 0
      assert Map.has_key?(result.metrics, :event_count_fairness_jain_index)
      assert Map.has_key?(result.metrics, :worker_utilization_fairness_jain_index)
      assert Map.has_key?(result.metrics, :objective_total_cost)
      assert Map.has_key?(result.metrics, :objective_average_cost_per_event)
    end
  end

  test "uses precise strategy names while keeping legacy aliases resolvable" do
    strategy_names = EventSchedulerSim.Strategy.names()

    assert "deadline_aware_dispatch" in strategy_names
    assert "duration_aware_dispatch" in strategy_names
    refute "earliest_deadline_first" in strategy_names
    refute "shortest_processing_time" in strategy_names
    refute "qubo_batch_exact" in strategy_names
    assert "qubo_batch_exact" in EventSchedulerSim.Strategy.experimental_names()
    assert "qubo_batch_exact_deadline_focused" in EventSchedulerSim.Strategy.experimental_names()
    assert "qubo_batch_exact_critical_focused" in EventSchedulerSim.Strategy.experimental_names()
    assert "qubo_batch_exact_low_balance" in EventSchedulerSim.Strategy.experimental_names()
    assert "qubo_batch_exact_sequencing" in EventSchedulerSim.Strategy.experimental_names()

    assert EventSchedulerSim.Strategy.resolve!("earliest_deadline_first").name() ==
             "deadline_aware_dispatch"

    assert EventSchedulerSim.Strategy.resolve!("shortest_processing_time").name() ==
             "duration_aware_dispatch"

    assert EventSchedulerSim.Strategy.resolve!("qubo_batch_exact").name() == "qubo_batch_exact"

    assert EventSchedulerSim.Strategy.resolve!("qubo_batch_exact_deadline_focused").name() ==
             "qubo_batch_exact_deadline_focused"

    assert EventSchedulerSim.Strategy.resolve!("qubo_batch_exact_sequencing").name() ==
             "qubo_batch_exact_sequencing"
  end

  test "writes a batch summary" do
    output_dir = Path.join(System.tmp_dir!(), "event_scheduler_sim_batch_test")
    File.rm_rf!(output_dir)

    results =
      EventSchedulerSim.Batch.run(
        scenario_paths: ["scenarios/baseline.exs"],
        strategies: ["round_robin", "least_loaded"],
        output_dir: output_dir
      )

    assert length(results) == 2
    assert File.exists?(Path.join(output_dir, "summary.csv"))
    assert File.exists?(Path.join(output_dir, "summary.json"))

    summary_csv = File.read!(Path.join(output_dir, "summary.csv"))

    assert summary_csv =~ "baseline_small,round_robin"
    assert summary_csv =~ "baseline_small,least_loaded"
    assert summary_csv =~ "event_count_fairness_jain_index"
    assert summary_csv =~ "worker_utilization_fairness_jain_index"
    assert summary_csv =~ "objective_total_cost"
    assert summary_csv =~ "objective_average_cost_per_event"
  end

  test "generates deterministic scenarios from profile, load level, and seed" do
    first =
      EventSchedulerSim.Experiment.ScenarioGenerator.build(
        profile: "steady",
        load_level: "medium",
        seed: 42
      )

    second =
      EventSchedulerSim.Experiment.ScenarioGenerator.build(
        profile: "steady",
        load_level: "medium",
        seed: 42
      )

    different =
      EventSchedulerSim.Experiment.ScenarioGenerator.build(
        profile: "steady",
        load_level: "medium",
        seed: 43
      )

    assert first.name == "steady_medium_seed_42"
    assert first.events == second.events
    assert first.metadata.target_utilization == 0.75
    assert first.metadata.actual_critical_ratio >= 0
    assert first.metadata.total_worker_speed == 4.0
    refute first.events == different.events
  end

  test "runs a repeated experimental matrix and writes aggregated outputs" do
    output_dir = Path.join(System.tmp_dir!(), "event_scheduler_sim_experiment_test")
    File.rm_rf!(output_dir)

    result =
      EventSchedulerSim.Experiment.Runner.run(
        profiles: ["steady"],
        load_levels: ["low"],
        seeds: [1, 2],
        strategies: ["round_robin", "shortest_queue"],
        output_dir: output_dir
      )

    assert result.run_count == 4
    assert result.aggregate_count == 2
    assert File.exists?(Path.join(output_dir, "runs.csv"))
    assert File.exists?(Path.join(output_dir, "runs.json"))
    assert File.exists?(Path.join(output_dir, "aggregated.csv"))
    assert File.exists?(Path.join(output_dir, "aggregated.json"))

    aggregated_csv = File.read!(Path.join(output_dir, "aggregated.csv"))
    runs_csv = File.read!(Path.join(output_dir, "runs.csv"))

    assert aggregated_csv =~ "steady,low,round_robin,2"
    assert aggregated_csv =~ "steady,low,shortest_queue,2"
    assert aggregated_csv =~ "target_utilization_mean"
    assert aggregated_csv =~ "objective_average_cost_per_event_mean"
    assert runs_csv =~ "actual_critical_ratio"
    assert runs_csv =~ "objective_total_cost"
  end

  test "separates event-count fairness from worker-utilization fairness" do
    scenario =
      EventSchedulerSim.Experiment.ScenarioGenerator.build(
        profile: "heterogeneous",
        load_level: "high",
        seed: 1
      )

    result =
      EventSchedulerSim.Simulator.run(
        scenario,
        EventSchedulerSim.Strategy.resolve!("round_robin")
      )

    assert result.metrics.event_count_fairness_jain_index >
             result.metrics.worker_utilization_fairness_jain_index
  end

  test "generates targeted stress profiles for multi-objective pressure" do
    scenario =
      EventSchedulerSim.Experiment.ScenarioGenerator.build(
        profile: "burst_critical",
        load_level: "overload",
        seed: 7
      )

    assert scenario.name == "burst_critical_overload_seed_7"
    assert scenario.metadata.target_utilization == 1.15
    assert scenario.metadata.worker_count == 3
    assert scenario.metadata.actual_critical_ratio > 0.20
    assert scenario.starvation_threshold_ms == 900
  end

  test "computes objective cost components for realized assignments" do
    worker = %EventSchedulerSim.Worker{id: "w1", speed: 1.0, weight: 1}

    scenario = %EventSchedulerSim.Scenario{
      name: "objective_test",
      starvation_threshold_ms: 5,
      workers: [worker],
      events: []
    }

    event = %EventSchedulerSim.Event{
      id: "e1",
      type: "critical",
      arrival_time: 0,
      duration_ms: 5,
      priority: 9,
      deadline_ms: 10
    }

    assignment = EventSchedulerSim.Assignment.build(event, worker, 7, 12, 5)
    objective = EventSchedulerSim.Objective.run_cost(scenario, [assignment])

    assert objective.components == %{
             latency_ms: 12,
             waiting_time_ms: 7,
             deadline_overrun_ms: 2,
             critical_waiting_time_ms: 7,
             starvation_overrun_ms: 2,
             utilization_imbalance: 0.0
           }

    assert objective.total_cost == 40.7
    assert objective.average_cost_per_event == 40.7
  end

  test "candidate objective prefers lower projected deadline overrun" do
    slow_worker = %EventSchedulerSim.Worker{id: "slow", speed: 1.0, weight: 1}
    fast_worker = %EventSchedulerSim.Worker{id: "fast", speed: 2.0, weight: 2}

    scenario = %EventSchedulerSim.Scenario{
      name: "candidate_objective_test",
      starvation_threshold_ms: 50,
      workers: [slow_worker, fast_worker],
      events: []
    }

    event = %EventSchedulerSim.Event{
      id: "e1",
      type: "standard",
      arrival_time: 0,
      duration_ms: 20,
      priority: 1,
      deadline_ms: 10
    }

    state = %{
      availability: %{"slow" => 0, "fast" => 0},
      busy_time: %{"slow" => 0, "fast" => 0},
      event_count: %{"slow" => 0, "fast" => 0}
    }

    slow_cost = EventSchedulerSim.Objective.candidate_cost(slow_worker, event, state, scenario)
    fast_cost = EventSchedulerSim.Objective.candidate_cost(fast_worker, event, state, scenario)

    assert slow_cost.components.deadline_overrun_ms > fast_cost.components.deadline_overrun_ms
    assert fast_cost.total_cost < slow_cost.total_cost
  end

  test "builds and solves a tiny QUBO assignment model" do
    slow_worker = %EventSchedulerSim.Worker{id: "slow", speed: 1.0, weight: 1}
    fast_worker = %EventSchedulerSim.Worker{id: "fast", speed: 2.0, weight: 2}

    scenario = %EventSchedulerSim.Scenario{
      name: "tiny_qubo_test",
      starvation_threshold_ms: 50,
      workers: [slow_worker, fast_worker],
      events: []
    }

    event = %EventSchedulerSim.Event{
      id: "e1",
      type: "standard",
      arrival_time: 0,
      duration_ms: 20,
      priority: 1,
      deadline_ms: 10
    }

    state = EventSchedulerSim.Scheduler.initial_state(scenario.workers)

    model =
      EventSchedulerSim.Qubo.Builder.build(
        scenario,
        [event],
        scenario.workers,
        state,
        balance_weight: 0.0
      )

    solution = EventSchedulerSim.Qubo.ExactSolver.solve!(model)

    assert model.metadata.variable_count == 2
    assert solution.constraint_violations == 0
    assert solution.selected_worker_by_event == %{"e1" => ["fast"]}
  end

  test "applies QUBO sensitivity profiles to model metadata" do
    worker = %EventSchedulerSim.Worker{id: "w1", speed: 1.0, weight: 1}

    scenario = %EventSchedulerSim.Scenario{
      name: "qubo_profile_test",
      starvation_threshold_ms: 50,
      workers: [worker],
      events: []
    }

    event = %EventSchedulerSim.Event{
      id: "e1",
      type: "critical",
      arrival_time: 0,
      duration_ms: 20,
      priority: 9,
      deadline_ms: 10
    }

    state = EventSchedulerSim.Scheduler.initial_state(scenario.workers)

    default_model =
      EventSchedulerSim.Qubo.Builder.build(
        scenario,
        [event],
        scenario.workers,
        state,
        EventSchedulerSim.Qubo.Profile.builder_opts(:default)
      )

    critical_model =
      EventSchedulerSim.Qubo.Builder.build(
        scenario,
        [event],
        scenario.workers,
        state,
        EventSchedulerSim.Qubo.Profile.builder_opts(:critical_focused)
      )

    assert default_model.metadata.qubo_profile == "default"
    assert critical_model.metadata.qubo_profile == "critical_focused"
    assert critical_model.metadata.objective_weights.critical_waiting_time_ms == 8.0
    assert critical_model.metadata.balance_weight < default_model.metadata.balance_weight
    assert EventSchedulerSim.Qubo.Profile.get!(:sequencing).batch_order == :priority_arrival
  end

  test "sequencing QUBO profile adds intra-batch pair penalties" do
    worker = %EventSchedulerSim.Worker{id: "w1", speed: 1.0, weight: 1}

    scenario = %EventSchedulerSim.Scenario{
      name: "qubo_sequencing_test",
      starvation_threshold_ms: 50,
      workers: [worker],
      events: []
    }

    events = [
      %EventSchedulerSim.Event{
        id: "critical",
        type: "critical",
        arrival_time: 0,
        duration_ms: 20,
        priority: 10,
        deadline_ms: 25
      },
      %EventSchedulerSim.Event{
        id: "standard",
        type: "standard",
        arrival_time: 0,
        duration_ms: 20,
        priority: 1,
        deadline_ms: 60
      }
    ]

    state = EventSchedulerSim.Scheduler.initial_state(scenario.workers)

    default_model =
      EventSchedulerSim.Qubo.Builder.build(
        scenario,
        events,
        scenario.workers,
        state,
        balance_weight: 0.0,
        sequencing_wait_weight: 0.0
      )

    sequencing_model =
      EventSchedulerSim.Qubo.Builder.build(
        scenario,
        events,
        scenario.workers,
        state,
        EventSchedulerSim.Qubo.Profile.builder_opts(:sequencing)
      )

    assert default_model.metadata.qubo_profile == "custom"
    assert sequencing_model.metadata.qubo_profile == "sequencing"
    assert map_size(default_model.quadratic) == 0
    assert map_size(sequencing_model.quadratic) == 1
    assert sequencing_model.quadratic[{0, 1}] > 0
  end

  test "exports small QUBO validation instances" do
    output_dir = Path.join(System.tmp_dir!(), "event_scheduler_sim_qubo_export_test")
    File.rm_rf!(output_dir)

    instances =
      EventSchedulerSim.Qubo.Export.build_instances(
        scenario_paths: ["scenarios/baseline.exs"],
        profile: "sequencing",
        batch_size: 2,
        batch_limit: 1
      )

    [instance] = instances

    assert instance.schema_version == "qubo-validation-v1"
    assert instance.scenario == "baseline_small"
    assert instance.profile == "sequencing"
    assert instance.event_count == 2
    assert instance.worker_count == 3
    assert instance.variable_count == 6
    assert length(instance.variables) == 6
    assert length(instance.exact_solution.assignment_vector) == 6
    assert instance.exact_solution.constraint_violations == 0

    EventSchedulerSim.Qubo.Export.write!(instances, output_dir)

    assert File.exists?(Path.join(output_dir, "manifest.json"))
    assert File.exists?(Path.join(output_dir, instance.instance_id <> ".json"))
  end

  test "runs the experimental exact QUBO batch strategy on a small scenario" do
    workers = [
      %EventSchedulerSim.Worker{id: "w1", speed: 1.0, weight: 1},
      %EventSchedulerSim.Worker{id: "w2", speed: 1.5, weight: 2}
    ]

    events = [
      %EventSchedulerSim.Event{
        id: "e1",
        type: "standard",
        arrival_time: 0,
        duration_ms: 20,
        priority: 1,
        deadline_ms: 30
      },
      %EventSchedulerSim.Event{
        id: "e2",
        type: "critical",
        arrival_time: 5,
        duration_ms: 30,
        priority: 9,
        deadline_ms: 35
      },
      %EventSchedulerSim.Event{
        id: "e3",
        type: "standard",
        arrival_time: 10,
        duration_ms: 10,
        priority: 2,
        deadline_ms: 25
      }
    ]

    scenario = %EventSchedulerSim.Scenario{
      name: "small_qubo_strategy_test",
      starvation_threshold_ms: 100,
      workers: workers,
      events: events
    }

    result =
      EventSchedulerSim.Simulator.run(
        scenario,
        EventSchedulerSim.Strategy.resolve!("qubo_batch_exact")
      )

    assert result.strategy == "qubo_batch_exact"
    assert result.metrics.total_events == 3
    assert Enum.all?(result.assignments, &(&1.worker_id in ["w1", "w2"]))
    assert result.metrics.objective_total_cost > 0
  end
end
