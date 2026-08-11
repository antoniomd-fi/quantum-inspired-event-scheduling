defmodule EventSchedulerSim.Strategies.DurationAwareDispatch do
  alias EventSchedulerSim.Scheduler
  alias EventSchedulerSim.Worker

  def name, do: "duration_aware_dispatch"

  def schedule(scenario) do
    Scheduler.run(scenario,
      event_order: :duration_arrival,
      selector: fn event, _index, workers, state, strategy_state ->
        worker =
          Enum.min_by(workers, fn worker ->
            {
              Scheduler.projected_finish_time(worker, event, state),
              Scheduler.queue_wait_time(worker, event, state),
              Worker.processing_time(worker, event),
              worker.id
            }
          end)

        {worker, strategy_state}
      end
    )
  end
end
