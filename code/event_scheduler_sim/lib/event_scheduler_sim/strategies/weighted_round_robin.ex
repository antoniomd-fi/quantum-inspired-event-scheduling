defmodule EventSchedulerSim.Strategies.WeightedRoundRobin do
  alias EventSchedulerSim.Scheduler

  def name, do: "weighted_round_robin"

  def schedule(scenario) do
    sequence = weighted_sequence(scenario.workers)

    Scheduler.run(scenario,
      strategy_state: %{sequence: sequence, next_index: 0},
      selector: fn _event, _index, workers, _state, strategy_state ->
        worker_id =
          Enum.at(strategy_state.sequence, rem(strategy_state.next_index, length(sequence)))

        worker = Enum.find(workers, &(&1.id == worker_id))

        {worker, %{strategy_state | next_index: strategy_state.next_index + 1}}
      end
    )
  end

  defp weighted_sequence(workers) do
    Enum.flat_map(workers, fn worker ->
      List.duplicate(worker.id, worker.weight)
    end)
  end
end
