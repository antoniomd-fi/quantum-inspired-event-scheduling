defmodule EventSchedulerSim.Experiment.Runner do
  alias EventSchedulerSim.Csv
  alias EventSchedulerSim.Experiment.Matrix
  alias EventSchedulerSim.Experiment.ScenarioGenerator
  alias EventSchedulerSim.Json
  alias EventSchedulerSim.Simulator
  alias EventSchedulerSim.Stats
  alias EventSchedulerSim.Strategy

  @run_headers [
    "profile",
    "load_level",
    "seed",
    "scenario",
    "strategy",
    "target_utilization",
    "estimated_interarrival_ms",
    "actual_critical_ratio",
    "actual_average_duration_ms",
    "actual_average_deadline_ms",
    "worker_count",
    "total_worker_speed",
    "total_worker_weight",
    "total_events",
    "makespan_ms",
    "throughput_events_per_second",
    "average_latency_ms",
    "p95_latency_ms",
    "p99_latency_ms",
    "max_latency_ms",
    "average_waiting_time_ms",
    "max_waiting_time_ms",
    "deadline_hit_rate",
    "critical_deadline_hit_rate",
    "starvation_count",
    "event_count_fairness_jain_index",
    "worker_utilization_fairness_jain_index",
    "objective_total_cost",
    "objective_average_cost_per_event"
  ]

  @workload_metrics [
    :target_utilization,
    :estimated_interarrival_ms,
    :actual_critical_ratio,
    :actual_average_duration_ms,
    :actual_average_deadline_ms,
    :worker_count,
    :total_worker_speed,
    :total_worker_weight
  ]

  @aggregate_metrics [
    :makespan_ms,
    :throughput_events_per_second,
    :average_latency_ms,
    :p95_latency_ms,
    :p99_latency_ms,
    :max_latency_ms,
    :average_waiting_time_ms,
    :max_waiting_time_ms,
    :deadline_hit_rate,
    :critical_deadline_hit_rate,
    :starvation_count,
    :event_count_fairness_jain_index,
    :worker_utilization_fairness_jain_index,
    :objective_total_cost,
    :objective_average_cost_per_event
  ]

  def run(opts \\ []) do
    matrix = Matrix.build(opts)
    output_dir = Keyword.get(opts, :output_dir, "results/experimental_matrix")
    File.mkdir_p!(output_dir)

    runs =
      Enum.map(matrix, fn experiment ->
        run_one(experiment)
      end)

    aggregates = aggregate(runs)

    File.write!(Path.join(output_dir, "runs.csv"), runs_csv(runs))
    File.write!(Path.join(output_dir, "runs.json"), Json.encode(runs_json(runs)) <> "\n")
    File.write!(Path.join(output_dir, "aggregated.csv"), aggregated_csv(aggregates))
    File.write!(Path.join(output_dir, "aggregated.json"), Json.encode(aggregates) <> "\n")

    %{
      output_dir: output_dir,
      run_count: length(runs),
      aggregate_count: length(aggregates),
      runs: runs,
      aggregates: aggregates
    }
  end

  defp run_one(experiment) do
    scenario =
      ScenarioGenerator.build(
        profile: experiment.profile,
        load_level: experiment.load_level,
        seed: experiment.seed
      )

    strategy = Strategy.resolve!(experiment.strategy)
    result = Simulator.run(scenario, strategy)

    %{
      profile: experiment.profile,
      load_level: experiment.load_level,
      seed: experiment.seed,
      scenario: scenario.name,
      strategy: strategy.name(),
      workload_metadata: scenario.metadata,
      metrics: result.metrics
    }
  end

  defp aggregate(runs) do
    runs
    |> Enum.group_by(fn run -> {run.profile, run.load_level, run.strategy} end)
    |> Enum.map(fn {{profile, load_level, strategy}, group} ->
      metric_summary =
        (@workload_metrics ++ @aggregate_metrics)
        |> Enum.flat_map(fn metric ->
          values = Enum.map(group, &metric_value(&1, metric))
          summary = Stats.summary(values)

          [
            {:"#{metric}_mean", summary.mean},
            {:"#{metric}_stddev", summary.stddev},
            {:"#{metric}_min", summary.min},
            {:"#{metric}_max", summary.max}
          ]
        end)
        |> Map.new()

      %{
        profile: profile,
        load_level: load_level,
        strategy: strategy,
        repetitions: length(group)
      }
      |> Map.merge(metric_summary)
    end)
    |> Enum.sort_by(&{&1.profile, &1.load_level, &1.strategy})
  end

  defp runs_csv(runs) do
    rows =
      Enum.map(runs, fn run ->
        metrics = run.metrics

        [
          run.profile,
          run.load_level,
          run.seed,
          run.scenario,
          run.strategy,
          metadata_value(run, :target_utilization),
          metadata_value(run, :estimated_interarrival_ms),
          metadata_value(run, :actual_critical_ratio),
          metadata_value(run, :actual_average_duration_ms),
          metadata_value(run, :actual_average_deadline_ms),
          metadata_value(run, :worker_count),
          metadata_value(run, :total_worker_speed),
          metadata_value(run, :total_worker_weight),
          metrics.total_events,
          metrics.makespan_ms,
          metrics.throughput_events_per_second,
          metrics.average_latency_ms,
          metrics.p95_latency_ms,
          metrics.p99_latency_ms,
          metrics.max_latency_ms,
          metrics.average_waiting_time_ms,
          metrics.max_waiting_time_ms,
          metrics.deadline_hit_rate,
          metrics.critical_deadline_hit_rate,
          metrics.starvation_count,
          metrics.event_count_fairness_jain_index,
          metrics.worker_utilization_fairness_jain_index,
          metrics.objective_total_cost,
          metrics.objective_average_cost_per_event
        ]
      end)

    Csv.encode_rows(@run_headers, rows)
  end

  defp runs_json(runs) do
    Enum.map(runs, fn run ->
      %{
        profile: run.profile,
        load_level: run.load_level,
        seed: run.seed,
        scenario: run.scenario,
        strategy: run.strategy,
        workload_metadata: run.workload_metadata,
        metrics: run.metrics
      }
    end)
  end

  defp aggregated_csv(aggregates) do
    headers = aggregate_headers()

    rows =
      Enum.map(aggregates, fn aggregate ->
        Enum.map(headers, &Map.fetch!(aggregate, String.to_atom(&1)))
      end)

    Csv.encode_rows(headers, rows)
  end

  defp aggregate_headers do
    base_headers = ["profile", "load_level", "strategy", "repetitions"]

    metric_headers =
      Enum.flat_map(@workload_metrics ++ @aggregate_metrics, fn metric ->
        [
          "#{metric}_mean",
          "#{metric}_stddev",
          "#{metric}_min",
          "#{metric}_max"
        ]
      end)

    base_headers ++ metric_headers
  end

  defp metric_value(run, metric) do
    case Map.fetch(run.metrics, metric) do
      {:ok, value} -> value
      :error -> metadata_value(run, metric)
    end
  end

  defp metadata_value(run, metric) do
    Map.fetch!(run.workload_metadata, metric)
  end
end
