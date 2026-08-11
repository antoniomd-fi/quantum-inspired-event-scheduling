defmodule EventSchedulerSim.Strategies.ShortestQueue do
  alias EventSchedulerSim.Scheduler

  def name, do: "shortest_queue"

  def schedule(scenario) do
    Scheduler.run(scenario,
      selector: fn event, _index, workers, state, strategy_state ->
        worker =
          Enum.min_by(workers, fn worker ->
            {
              Scheduler.queue_wait_time(worker, event, state),
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
