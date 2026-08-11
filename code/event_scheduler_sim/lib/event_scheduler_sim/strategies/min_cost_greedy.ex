defmodule EventSchedulerSim.Strategies.MinCostGreedy do
  alias EventSchedulerSim.Objective
  alias EventSchedulerSim.Scheduler

  def name, do: "min_cost_greedy"

  def schedule(scenario) do
    Scheduler.run(scenario,
      selector: fn event, _index, workers, state, strategy_state ->
        worker =
          Enum.min_by(workers, fn worker ->
            {
              Objective.candidate_cost(worker, event, state, scenario).total_cost,
              Scheduler.projected_finish_time(worker, event, state),
              worker.id
            }
          end)

        {worker, strategy_state}
      end
    )
  end
end
