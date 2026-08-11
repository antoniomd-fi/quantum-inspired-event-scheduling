defmodule EventSchedulerSim.Strategies.RoundRobin do
  alias EventSchedulerSim.Scheduler

  def name, do: "round_robin"

  def schedule(scenario) do
    Scheduler.run(scenario,
      strategy_state: %{next_index: 0},
      selector: fn _event, _index, workers, _state, strategy_state ->
        worker = Enum.at(workers, rem(strategy_state.next_index, length(workers)))

        {worker, %{strategy_state | next_index: strategy_state.next_index + 1}}
      end
    )
  end
end
