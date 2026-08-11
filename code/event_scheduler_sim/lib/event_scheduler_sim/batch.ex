defmodule EventSchedulerSim.Batch do
  alias EventSchedulerSim.Csv
  alias EventSchedulerSim.Json
  alias EventSchedulerSim.Strategy

  @summary_headers [
    "scenario",
    "strategy",
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
    "objective_average_cost_per_event",
    "output_dir"
  ]

  def default_scenarios do
    "scenarios/*.exs"
    |> Path.wildcard()
    |> Enum.sort()
  end

  def run(opts \\ []) do
    scenario_paths = Keyword.get(opts, :scenario_paths, default_scenarios())
    strategies = Keyword.get(opts, :strategies, Strategy.names())
    output_dir = Keyword.get(opts, :output_dir, "results/batch")

    File.mkdir_p!(output_dir)

    results =
      for scenario_path <- scenario_paths,
          strategy <- strategies do
        run_one(scenario_path, strategy, output_dir)
      end

    write_summary!(results, output_dir)

    results
  end

  defp run_one(scenario_path, strategy, output_dir) do
    scenario_slug = scenario_path |> Path.basename(".exs")
    strategy_name = Strategy.resolve!(strategy).name()
    run_output_dir = Path.join([output_dir, scenario_slug, strategy_name])

    result =
      EventSchedulerSim.run(
        scenario_path: scenario_path,
        strategy: strategy,
        output_dir: run_output_dir
      )

    %{
      scenario_path: scenario_path,
      output_dir: run_output_dir,
      strategy: strategy_name,
      metrics: result.metrics
    }
  end

  defp write_summary!(results, output_dir) do
    File.write!(Path.join(output_dir, "summary.csv"), summary_csv(results))
    File.write!(Path.join(output_dir, "summary.json"), summary_json(results))
  end

  defp summary_csv(results) do
    rows =
      Enum.map(results, fn result ->
        metrics = result.metrics

        [
          metrics.scenario,
          result.strategy,
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
          metrics.objective_average_cost_per_event,
          result.output_dir
        ]
      end)

    Csv.encode_rows(@summary_headers, rows)
  end

  defp summary_json(results) do
    encoded =
      Enum.map(results, fn result ->
        %{
          scenario_path: result.scenario_path,
          output_dir: result.output_dir,
          strategy: result.strategy,
          metrics: result.metrics
        }
      end)

    Json.encode(encoded) <> "\n"
  end
end
