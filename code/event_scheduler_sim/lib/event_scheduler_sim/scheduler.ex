defmodule EventSchedulerSim.Scheduler do
  alias EventSchedulerSim.Assignment
  alias EventSchedulerSim.Scenario
  alias EventSchedulerSim.Worker

  def run(%Scenario{workers: []}, _opts) do
    raise ArgumentError, "scenario must include at least one worker"
  end

  def run(%Scenario{} = scenario, opts) do
    selector = Keyword.fetch!(opts, :selector)
    event_order = Keyword.get(opts, :event_order, :arrival)
    strategy_state = Keyword.get(opts, :strategy_state, %{})
    initial_state = initial_state(scenario.workers)

    {_state, _strategy_state, assignments} =
      scenario.events
      |> ordered_events(event_order)
      |> Enum.with_index()
      |> Enum.reduce({initial_state, strategy_state, []}, fn {event, index},
                                                             {state, current_strategy_state, acc} ->
        {worker, next_strategy_state} =
          selector.(event, index, scenario.workers, state, current_strategy_state)

        assignment = assign(event, worker, state)
        next_state = update_state(state, worker, assignment)

        {next_state, next_strategy_state, [assignment | acc]}
      end)

    Enum.reverse(assignments)
  end

  def projected_finish_time(worker, event, state) do
    projected_start_time(worker, event, state) + Worker.processing_time(worker, event)
  end

  def projected_start_time(worker, event, state) do
    worker
    |> available_at(state)
    |> max(event.arrival_time)
  end

  def queue_wait_time(worker, event, state) do
    max(0, available_at(worker, state) - event.arrival_time)
  end

  def busy_time(worker, state), do: Map.fetch!(state.busy_time, worker.id)
  def event_count(worker, state), do: Map.fetch!(state.event_count, worker.id)
  def available_at(worker, state), do: Map.fetch!(state.availability, worker.id)

  def initial_state(workers) do
    %{
      availability: Map.new(workers, &{&1.id, 0}),
      busy_time: Map.new(workers, &{&1.id, 0}),
      event_count: Map.new(workers, &{&1.id, 0})
    }
  end

  defp ordered_events(events, :arrival) do
    Enum.sort_by(events, &{&1.arrival_time, &1.id})
  end

  defp ordered_events(events, :priority_arrival) do
    Enum.sort_by(events, fn event ->
      {event.arrival_time, -event.priority, deadline_value(event), event.id}
    end)
  end

  defp ordered_events(events, :deadline_arrival) do
    Enum.sort_by(events, fn event ->
      {event.arrival_time, deadline_value(event), -event.priority, event.id}
    end)
  end

  defp ordered_events(events, :duration_arrival) do
    Enum.sort_by(events, fn event ->
      {event.arrival_time, event.duration_ms, deadline_value(event), event.id}
    end)
  end

  defp deadline_value(%{deadline_ms: nil}), do: 9_999_999_999
  defp deadline_value(%{deadline_ms: deadline_ms}), do: deadline_ms

  def assign(event, worker, state) do
    start_time = projected_start_time(worker, event, state)
    processing_time = Worker.processing_time(worker, event)
    finish_time = start_time + processing_time

    Assignment.build(event, worker, start_time, finish_time, processing_time)
  end

  def update_state(state, worker, assignment) do
    %{
      state
      | availability: Map.put(state.availability, worker.id, assignment.finish_time),
        busy_time: Map.update!(state.busy_time, worker.id, &(&1 + assignment.processing_time)),
        event_count: Map.update!(state.event_count, worker.id, &(&1 + 1))
    }
  end
end
