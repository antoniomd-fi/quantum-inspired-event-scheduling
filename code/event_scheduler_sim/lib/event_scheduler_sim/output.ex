defmodule EventSchedulerSim.Output do
  alias EventSchedulerSim.Csv
  alias EventSchedulerSim.Json
  alias EventSchedulerSim.Result

  def write!(%Result{} = result, output_dir) do
    File.mkdir_p!(output_dir)

    File.write!(Path.join(output_dir, "assignments.csv"), assignments_csv(result.assignments))
    File.write!(Path.join(output_dir, "metrics.json"), Json.encode(result.metrics) <> "\n")
    File.write!(Path.join(output_dir, "summary.md"), summary(result))

    :ok
  end

  defp assignments_csv(assignments) do
    headers = [
      "event_id",
      "worker_id",
      "event_type",
      "priority",
      "arrival_time",
      "start_time",
      "finish_time",
      "processing_time",
      "waiting_time",
      "latency",
      "deadline_ms",
      "deadline_met"
    ]

    rows =
      Enum.map(assignments, fn assignment ->
        [
          assignment.event_id,
          assignment.worker_id,
          assignment.event_type,
          assignment.priority,
          assignment.arrival_time,
          assignment.start_time,
          assignment.finish_time,
          assignment.processing_time,
          assignment.waiting_time,
          assignment.latency,
          assignment.deadline_ms,
          assignment.deadline_met
        ]
      end)

    Csv.encode_rows(headers, rows)
  end

  defp summary(%Result{} = result) do
    metrics = result.metrics

    """
    # Simulation Summary

    Scenario: #{metrics.scenario}

    Strategy: #{result.strategy}

    Total events: #{metrics.total_events}

    Makespan ms: #{metrics.makespan_ms}

    Throughput events/s: #{metrics.throughput_events_per_second}

    Average latency ms: #{metrics.average_latency_ms}

    P95 latency ms: #{metrics.p95_latency_ms}

    P99 latency ms: #{metrics.p99_latency_ms}

    Deadline hit rate: #{metrics.deadline_hit_rate}

    Critical deadline hit rate: #{metrics.critical_deadline_hit_rate}

    Event-count fairness Jain index: #{metrics.event_count_fairness_jain_index}

    Worker-utilization fairness Jain index: #{metrics.worker_utilization_fairness_jain_index}

    Objective total cost: #{metrics.objective_total_cost}

    Objective average cost/event: #{metrics.objective_average_cost_per_event}
    """
  end
end
