defmodule EventSchedulerSim.Objective do
  @moduledoc """
  Shared objective function for scheduling and resource-allocation experiments.

  The objective is intentionally explicit: each component is reported separately
  and then combined with stable default weights. This makes the score usable as
  a classical heuristic today and as a QUBO foundation later.
  """

  alias EventSchedulerSim.Assignment
  alias EventSchedulerSim.Event
  alias EventSchedulerSim.Scenario
  alias EventSchedulerSim.Scheduler
  alias EventSchedulerSim.Worker

  @default_weights %{
    latency_ms: 1.0,
    waiting_time_ms: 0.6,
    deadline_overrun_ms: 4.0,
    critical_waiting_time_ms: 1.5,
    starvation_overrun_ms: 3.0,
    utilization_imbalance: 1_000.0
  }

  def default_weights, do: @default_weights

  def run_cost(%Scenario{} = scenario, assignments, opts \\ []) when is_list(assignments) do
    components = run_components(scenario, assignments)
    build_cost(components, opts, length(assignments))
  end

  def candidate_cost(
        %Worker{} = worker,
        %Event{} = event,
        state,
        %Scenario{} = scenario,
        opts \\ []
      ) do
    start_time = Scheduler.projected_start_time(worker, event, state)
    processing_time = Worker.processing_time(worker, event)
    finish_time = start_time + processing_time
    assignment = Assignment.build(event, worker, start_time, finish_time, processing_time)

    components =
      assignment_components(scenario, assignment)
      |> Map.put(
        :utilization_imbalance,
        projected_utilization_imbalance(worker, assignment, state, scenario.workers)
      )

    build_cost(components, opts, 1)
  end

  def assignment_components(%Scenario{} = scenario, %Assignment{} = assignment) do
    %{
      latency_ms: assignment.latency,
      waiting_time_ms: assignment.waiting_time,
      deadline_overrun_ms: deadline_overrun(assignment),
      critical_waiting_time_ms: critical_waiting_time(assignment),
      starvation_overrun_ms: starvation_overrun(scenario, assignment),
      utilization_imbalance: 0.0
    }
  end

  defp run_components(%Scenario{} = scenario, assignments) do
    assignment_totals =
      assignments
      |> Enum.map(&assignment_components(scenario, &1))
      |> sum_component_maps()

    Map.put(
      assignment_totals,
      :utilization_imbalance,
      utilization_imbalance(scenario, assignments)
    )
  end

  defp build_cost(components, opts, event_count) do
    weights = weights(opts)
    rounded_components = round_map(components)

    weighted_components =
      Map.new(rounded_components, fn {component, value} ->
        {component, round_number(value * Map.fetch!(weights, component))}
      end)

    total_cost =
      weighted_components
      |> Map.values()
      |> Enum.sum()
      |> round_number()

    %{
      total_cost: total_cost,
      average_cost_per_event: round_number(safe_div(total_cost, event_count)),
      components: rounded_components,
      weighted_components: weighted_components,
      weights: weights
    }
  end

  defp weights(opts) do
    overrides = Keyword.get(opts, :weights, %{})
    Map.merge(@default_weights, overrides)
  end

  defp sum_component_maps([]) do
    Map.new(@default_weights, fn {component, _weight} -> {component, 0.0} end)
  end

  defp sum_component_maps(component_maps) do
    Enum.reduce(component_maps, sum_component_maps([]), fn components, acc ->
      Map.merge(acc, components, fn _component, left, right -> left + right end)
    end)
  end

  defp deadline_overrun(%Assignment{deadline_ms: nil}), do: 0

  defp deadline_overrun(%Assignment{deadline_ms: deadline_ms, latency: latency}) do
    max(0, latency - deadline_ms)
  end

  defp critical_waiting_time(%Assignment{} = assignment) do
    if critical?(assignment), do: assignment.waiting_time, else: 0
  end

  defp critical?(%Assignment{event_type: "critical"}), do: true
  defp critical?(%Assignment{priority: priority}), do: priority >= 8

  defp starvation_overrun(%Scenario{} = scenario, %Assignment{} = assignment) do
    max(0, assignment.waiting_time - scenario.starvation_threshold_ms)
  end

  defp utilization_imbalance(_scenario, []), do: 0.0

  defp utilization_imbalance(%Scenario{} = scenario, assignments) do
    worker_busy_time = worker_busy_time(scenario.workers, assignments)
    makespan = makespan(assignments)

    worker_busy_time
    |> Map.values()
    |> Enum.map(&safe_div(&1, makespan))
    |> jain_shortfall()
  end

  defp projected_utilization_imbalance(worker, assignment, state, workers) do
    busy_time =
      Map.update!(state.busy_time, worker.id, &(&1 + assignment.processing_time))

    availability =
      Map.put(state.availability, worker.id, assignment.finish_time)

    makespan = max_value(Map.values(availability))

    workers
    |> Enum.map(fn candidate_worker ->
      busy_time
      |> Map.fetch!(candidate_worker.id)
      |> safe_div(makespan)
    end)
    |> jain_shortfall()
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

  defp makespan(assignments) do
    first_arrival = assignments |> Enum.map(& &1.arrival_time) |> Enum.min()
    last_finish = assignments |> Enum.map(& &1.finish_time) |> Enum.max()
    last_finish - first_arrival
  end

  defp max_value([]), do: 0
  defp max_value(values), do: Enum.max(values)

  defp jain_shortfall(values), do: round_number(1.0 - jain_index(values))

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

  defp round_map(values) do
    Map.new(values, fn {key, value} -> {key, round_number(value)} end)
  end

  defp safe_div(_numerator, 0), do: 0.0
  defp safe_div(numerator, denominator), do: numerator / denominator

  defp round_number(value) when is_float(value), do: Float.round(value, 4)
  defp round_number(value), do: value
end
