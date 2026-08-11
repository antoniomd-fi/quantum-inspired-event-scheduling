defmodule EventSchedulerSim.Qubo.Builder do
  @moduledoc """
  Builds small QUBO assignment models from event batches.
  """

  alias EventSchedulerSim.Objective
  alias EventSchedulerSim.Qubo.Model
  alias EventSchedulerSim.Qubo.Variable
  alias EventSchedulerSim.Scenario
  alias EventSchedulerSim.Scheduler
  alias EventSchedulerSim.Worker

  @default_assignment_penalty 100_000.0
  @default_balance_weight 0.02
  @default_sequencing_wait_weight 0.0
  @default_sequencing_deadline_weight 0.0
  @default_sequencing_critical_weight 0.0

  def build(%Scenario{} = scenario, events, workers, state, opts \\ [])
      when is_list(events) and is_list(workers) do
    variables = variables(events, workers)

    metadata = %{
      event_count: length(events),
      worker_count: length(workers),
      variable_count: length(variables),
      qubo_profile: Keyword.get(opts, :qubo_profile, "custom"),
      assignment_penalty: Keyword.get(opts, :assignment_penalty, @default_assignment_penalty),
      balance_weight: Keyword.get(opts, :balance_weight, @default_balance_weight),
      sequencing_wait_weight:
        Keyword.get(opts, :sequencing_wait_weight, @default_sequencing_wait_weight),
      sequencing_deadline_weight:
        Keyword.get(opts, :sequencing_deadline_weight, @default_sequencing_deadline_weight),
      sequencing_critical_weight:
        Keyword.get(opts, :sequencing_critical_weight, @default_sequencing_critical_weight),
      objective_weights: Keyword.get(opts, :objective_weights, %{utilization_imbalance: 0.0}),
      target_load_ms: target_load(events, workers, state)
    }

    variables
    |> Model.new(metadata)
    |> add_assignment_quality_terms(scenario, events, workers, state, opts)
    |> add_exactly_one_worker_terms(events, opts)
    |> add_load_balance_terms(events, workers, state, opts)
    |> add_intra_batch_sequencing_terms(events, workers, state, opts)
  end

  defp variables(events, workers) do
    events
    |> Enum.flat_map(fn event ->
      Enum.map(workers, fn worker -> {event, worker} end)
    end)
    |> Enum.with_index()
    |> Enum.map(fn {{event, worker}, index} -> Variable.new(index, event, worker) end)
  end

  defp add_assignment_quality_terms(model, scenario, events, workers, state, opts) do
    event_by_id = Map.new(events, &{to_string(&1.id), &1})
    worker_by_id = Map.new(workers, &{to_string(&1.id), &1})
    objective_weights = Keyword.get(opts, :objective_weights, %{utilization_imbalance: 0.0})

    Enum.reduce(model.variables, model, fn variable, acc ->
      event = Map.fetch!(event_by_id, variable.event_id)
      worker = Map.fetch!(worker_by_id, variable.worker_id)

      cost =
        worker
        |> Objective.candidate_cost(event, state, scenario, weights: objective_weights)
        |> Map.fetch!(:total_cost)

      Model.add_linear(acc, variable.index, cost)
    end)
  end

  defp add_exactly_one_worker_terms(model, events, opts) do
    assignment_penalty = Keyword.get(opts, :assignment_penalty, @default_assignment_penalty)

    Enum.reduce(events, model, fn event, acc ->
      variables = Model.variables_for_event(acc, event.id)

      acc
      |> Model.add_constant(assignment_penalty)
      |> add_linear_terms(variables, -assignment_penalty)
      |> add_pair_terms(variables, 2 * assignment_penalty)
    end)
  end

  defp add_load_balance_terms(model, events, workers, state, opts) do
    balance_weight = Keyword.get(opts, :balance_weight, @default_balance_weight)

    if balance_weight == 0 do
      model
    else
      event_by_id = Map.new(events, &{to_string(&1.id), &1})
      worker_by_id = Map.new(workers, &{to_string(&1.id), &1})
      target = model.metadata.target_load_ms

      Enum.reduce(workers, model, fn worker, acc ->
        worker_variables = Model.variables_for_worker(acc, worker.id)
        current_busy_time = Map.fetch!(state.busy_time, worker.id)
        offset = current_busy_time - target

        acc
        |> Model.add_constant(balance_weight * offset * offset)
        |> add_load_linear_terms(
          worker_variables,
          worker_by_id,
          event_by_id,
          balance_weight,
          offset
        )
        |> add_load_pair_terms(worker_variables, worker_by_id, event_by_id, balance_weight)
      end)
    end
  end

  defp add_linear_terms(model, variables, coefficient) do
    Enum.reduce(variables, model, fn variable, acc ->
      Model.add_linear(acc, variable.index, coefficient)
    end)
  end

  defp add_pair_terms(model, variables, coefficient) do
    variables
    |> pairs()
    |> Enum.reduce(model, fn {left_variable, right_variable}, acc ->
      Model.add_quadratic(acc, left_variable.index, right_variable.index, coefficient)
    end)
  end

  defp add_load_linear_terms(
         model,
         variables,
         worker_by_id,
         event_by_id,
         balance_weight,
         offset
       ) do
    Enum.reduce(variables, model, fn variable, acc ->
      processing_time = processing_time(variable, worker_by_id, event_by_id)

      coefficient =
        balance_weight * (2 * offset * processing_time + processing_time * processing_time)

      Model.add_linear(acc, variable.index, coefficient)
    end)
  end

  defp add_load_pair_terms(model, variables, worker_by_id, event_by_id, balance_weight) do
    variables
    |> pairs()
    |> Enum.reduce(model, fn {left_variable, right_variable}, acc ->
      left_processing_time = processing_time(left_variable, worker_by_id, event_by_id)
      right_processing_time = processing_time(right_variable, worker_by_id, event_by_id)
      coefficient = 2 * balance_weight * left_processing_time * right_processing_time

      Model.add_quadratic(acc, left_variable.index, right_variable.index, coefficient)
    end)
  end

  defp add_intra_batch_sequencing_terms(model, events, workers, state, opts) do
    wait_weight = Keyword.get(opts, :sequencing_wait_weight, @default_sequencing_wait_weight)

    deadline_weight =
      Keyword.get(opts, :sequencing_deadline_weight, @default_sequencing_deadline_weight)

    critical_weight =
      Keyword.get(opts, :sequencing_critical_weight, @default_sequencing_critical_weight)

    if wait_weight == 0 and deadline_weight == 0 and critical_weight == 0 do
      model
    else
      ordered_events = sequence_order(events)
      variables_by_pair = Map.new(model.variables, &{{&1.event_id, &1.worker_id}, &1})

      Enum.reduce(workers, model, fn worker, acc ->
        ordered_events
        |> ordered_pairs()
        |> Enum.reduce(acc, fn {previous_event, later_event}, pair_acc ->
          previous_variable =
            Map.fetch!(variables_by_pair, {to_string(previous_event.id), worker.id})

          later_variable = Map.fetch!(variables_by_pair, {to_string(later_event.id), worker.id})
          coefficient = sequencing_coefficient(worker, later_event, previous_event, state, opts)

          Model.add_quadratic(
            pair_acc,
            previous_variable.index,
            later_variable.index,
            coefficient
          )
        end)
      end)
    end
  end

  defp sequencing_coefficient(worker, later_event, previous_event, state, opts) do
    wait_weight = Keyword.get(opts, :sequencing_wait_weight, @default_sequencing_wait_weight)

    deadline_weight =
      Keyword.get(opts, :sequencing_deadline_weight, @default_sequencing_deadline_weight)

    critical_weight =
      Keyword.get(opts, :sequencing_critical_weight, @default_sequencing_critical_weight)

    additional_wait = Worker.processing_time(worker, previous_event)

    base_latency =
      Scheduler.projected_finish_time(worker, later_event, state) - later_event.arrival_time

    deadline_delta =
      deadline_overrun(later_event, base_latency + additional_wait) -
        deadline_overrun(later_event, base_latency)

    wait_weight * additional_wait +
      deadline_weight * deadline_delta +
      critical_weight * critical_multiplier(later_event) * additional_wait
  end

  defp processing_time(variable, worker_by_id, event_by_id) do
    worker = Map.fetch!(worker_by_id, variable.worker_id)
    event = Map.fetch!(event_by_id, variable.event_id)

    Worker.processing_time(worker, event)
  end

  defp sequence_order(events) do
    Enum.sort_by(events, fn event ->
      {event.arrival_time, -event.priority, deadline_value(event), event.id}
    end)
  end

  defp ordered_pairs([]), do: []
  defp ordered_pairs([_single]), do: []

  defp ordered_pairs([head | tail]) do
    Enum.map(tail, &{head, &1}) ++ ordered_pairs(tail)
  end

  defp deadline_overrun(%{deadline_ms: nil}, _latency), do: 0

  defp deadline_overrun(%{deadline_ms: deadline_ms}, latency) do
    max(0, latency - deadline_ms)
  end

  defp critical_multiplier(%{type: "critical"}), do: 1
  defp critical_multiplier(%{priority: priority}) when priority >= 8, do: 1
  defp critical_multiplier(_event), do: 0

  defp deadline_value(%{deadline_ms: nil}), do: 9_999_999_999
  defp deadline_value(%{deadline_ms: deadline_ms}), do: deadline_ms

  defp target_load(events, workers, state) do
    current_busy_time =
      workers
      |> Enum.map(&Map.fetch!(state.busy_time, &1.id))
      |> Enum.sum()

    estimated_batch_processing_time =
      events
      |> Enum.map(&average_processing_time(&1, workers))
      |> Enum.sum()

    safe_div(current_busy_time + estimated_batch_processing_time, length(workers))
  end

  defp average_processing_time(event, workers) do
    processing_times = Enum.map(workers, &Worker.processing_time(&1, event))

    safe_div(Enum.sum(processing_times), length(processing_times))
  end

  defp pairs([]), do: []
  defp pairs([_single]), do: []

  defp pairs([head | tail]) do
    Enum.map(tail, &{head, &1}) ++ pairs(tail)
  end

  defp safe_div(_numerator, 0), do: 0.0
  defp safe_div(numerator, denominator), do: numerator / denominator
end
