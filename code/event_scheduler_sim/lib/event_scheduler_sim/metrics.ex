defmodule EventSchedulerSim.Metrics do
  alias EventSchedulerSim.Assignment
  alias EventSchedulerSim.Objective
  alias EventSchedulerSim.Scenario

  def compute(%Scenario{} = scenario, assignments) do
    latencies = Enum.map(assignments, & &1.latency)
    waiting_times = Enum.map(assignments, & &1.waiting_time)
    makespan = makespan(assignments)
    worker_counts = worker_counts(scenario.workers, assignments)
    worker_busy_time = worker_busy_time(scenario.workers, assignments)
    worker_utilization = worker_utilization(worker_busy_time, makespan)
    objective = Objective.run_cost(scenario, assignments)

    %{
      scenario: scenario.name,
      total_events: length(assignments),
      makespan_ms: makespan,
      throughput_events_per_second: round_float(safe_div(length(assignments) * 1000, makespan)),
      average_latency_ms: round_float(mean(latencies)),
      p95_latency_ms: percentile(latencies, 0.95),
      p99_latency_ms: percentile(latencies, 0.99),
      max_latency_ms: max_value(latencies),
      average_waiting_time_ms: round_float(mean(waiting_times)),
      max_waiting_time_ms: max_value(waiting_times),
      deadline_hit_rate: round_float(deadline_hit_rate(assignments)),
      critical_deadline_hit_rate: round_float(critical_deadline_hit_rate(assignments)),
      starvation_count: starvation_count(assignments, scenario.starvation_threshold_ms),
      event_count_fairness_jain_index: round_float(jain_index(Map.values(worker_counts))),
      worker_utilization_fairness_jain_index:
        round_float(jain_index(Map.values(worker_utilization))),
      objective_total_cost: objective.total_cost,
      objective_average_cost_per_event: objective.average_cost_per_event,
      objective_components: objective.components,
      objective_weighted_components: objective.weighted_components,
      objective_weights: objective.weights,
      worker_event_counts: worker_counts,
      worker_busy_time_ms: worker_busy_time,
      worker_utilization: worker_utilization
    }
  end

  defp makespan([]), do: 0

  defp makespan(assignments) do
    first_arrival = assignments |> Enum.map(& &1.arrival_time) |> Enum.min()
    last_finish = assignments |> Enum.map(& &1.finish_time) |> Enum.max()
    last_finish - first_arrival
  end

  defp worker_counts(workers, assignments) do
    Map.new(workers, fn worker ->
      count = Enum.count(assignments, &(&1.worker_id == worker.id))
      {worker.id, count}
    end)
  end

  defp worker_busy_time(workers, assignments) do
    Map.new(workers, fn worker ->
      busy_time =
        assignments
        |> Enum.filter(&(&1.worker_id == worker.id))
        |> Enum.map(& &1.processing_time)
        |> Enum.sum()

      {worker.id, busy_time}
    end)
  end

  defp worker_utilization(worker_busy_time, makespan) do
    Map.new(worker_busy_time, fn {worker_id, busy_time} ->
      {worker_id, round_float(safe_div(busy_time, makespan))}
    end)
  end

  defp deadline_hit_rate(assignments) do
    measured = Enum.filter(assignments, &measured_deadline?/1)
    safe_div(Enum.count(measured, & &1.deadline_met), length(measured))
  end

  defp critical_deadline_hit_rate(assignments) do
    critical =
      assignments
      |> Enum.filter(&critical?/1)
      |> Enum.filter(&measured_deadline?/1)

    safe_div(Enum.count(critical, & &1.deadline_met), length(critical))
  end

  defp starvation_count(assignments, threshold_ms) do
    Enum.count(assignments, &(&1.waiting_time > threshold_ms))
  end

  defp critical?(%Assignment{event_type: "critical"}), do: true
  defp critical?(%Assignment{priority: priority}), do: priority >= 8

  defp measured_deadline?(%Assignment{deadline_ms: nil}), do: false
  defp measured_deadline?(%Assignment{}), do: true

  defp mean([]), do: 0.0
  defp mean(values), do: Enum.sum(values) / length(values)

  defp percentile([], _quantile), do: 0

  defp percentile(values, quantile) do
    sorted = Enum.sort(values)
    index = ceil(quantile * length(sorted)) - 1
    bounded_index = index |> max(0) |> min(length(sorted) - 1)
    Enum.at(sorted, bounded_index)
  end

  defp max_value([]), do: 0
  defp max_value(values), do: Enum.max(values)

  defp jain_index([]), do: 0.0

  defp jain_index(values) do
    sum = Enum.sum(values)
    square_sum = values |> Enum.map(&(&1 * &1)) |> Enum.sum()

    if sum == 0 or square_sum == 0 do
      0.0
    else
      sum * sum / (length(values) * square_sum)
    end
  end

  defp safe_div(_numerator, 0), do: 0.0
  defp safe_div(numerator, denominator), do: numerator / denominator

  defp round_float(value) when is_float(value), do: Float.round(value, 4)
  defp round_float(value), do: value
end
