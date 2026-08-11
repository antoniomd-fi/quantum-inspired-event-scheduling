defmodule EventSchedulerSim.Strategies.LeastLoaded do
  alias EventSchedulerSim.Scheduler

  def name, do: "least_loaded"

  def schedule(scenario) do
    Scheduler.run(scenario,
      selector: fn event, _index, workers, state, strategy_state ->
        worker =
          Enum.min_by(workers, fn worker ->
            {
              Scheduler.busy_time(worker, state),
              Scheduler.projected_finish_time(worker, event, state),
              Scheduler.event_count(worker, state),
              worker.id
            }
          end)

        {worker, strategy_state}
      end
    )
  end
end
