defmodule EventSchedulerSim.Strategies.QuboBatchExact do
  @moduledoc """
  Experimental QUBO batch strategy solved by brute force.

  This strategy is meant for small validation runs. It should not be used as a
  default full-matrix strategy because exact QUBO solving grows exponentially.
  """

  alias EventSchedulerSim.Qubo.Builder
  alias EventSchedulerSim.Qubo.ExactSolver
  alias EventSchedulerSim.Qubo.Profile
  alias EventSchedulerSim.Scheduler

  @batch_size 4

  def name, do: "qubo_batch_exact"

  def schedule(scenario, profile \\ :default) do
    config = Profile.get!(profile)
    builder_opts = Profile.builder_opts(profile)
    initial_state = Scheduler.initial_state(scenario.workers)

    scenario.events
    |> event_order(Map.get(config, :batch_order, :arrival))
    |> Enum.chunk_every(@batch_size)
    |> Enum.reduce({initial_state, []}, fn batch, {state, assignments} ->
      {next_state, batch_assignments} = assign_batch(scenario, batch, state, builder_opts)
      {next_state, assignments ++ batch_assignments}
    end)
    |> elem(1)
  end

  defp assign_batch(scenario, batch, state, builder_opts) do
    model = Builder.build(scenario, batch, scenario.workers, state, builder_opts)
    solution = ExactSolver.solve!(model)

    if solution.constraint_violations > 0 do
      raise ArgumentError, "QUBO exact solver returned an infeasible assignment"
    end

    batch
    |> application_order()
    |> Enum.reduce({state, []}, fn event, {current_state, assignments} ->
      worker_id =
        solution.selected_worker_by_event
        |> Map.fetch!(event.id)
        |> List.first()

      worker = Enum.find(scenario.workers, &(&1.id == worker_id))
      assignment = Scheduler.assign(event, worker, current_state)
      next_state = Scheduler.update_state(current_state, worker, assignment)

      {next_state, assignments ++ [assignment]}
    end)
  end

  defp event_order(events, :arrival), do: Enum.sort_by(events, &{&1.arrival_time, &1.id})
  defp event_order(events, :priority_arrival), do: application_order(events)

  defp application_order(events) do
    Enum.sort_by(events, fn event ->
      {event.arrival_time, -event.priority, deadline_value(event), event.id}
    end)
  end

  defp deadline_value(%{deadline_ms: nil}), do: 9_999_999_999
  defp deadline_value(%{deadline_ms: deadline_ms}), do: deadline_ms
end
