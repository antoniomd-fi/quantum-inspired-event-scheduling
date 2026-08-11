defmodule EventSchedulerSim.Strategies.DeadlineAwareDispatch do
  alias EventSchedulerSim.Scheduler

  def name, do: "deadline_aware_dispatch"

  def schedule(scenario) do
    Scheduler.run(scenario,
      event_order: :deadline_arrival,
      selector: fn event, _index, workers, state, strategy_state ->
        worker =
          Enum.min_by(workers, fn worker ->
            {
              deadline_violation(worker, event, state),
              Scheduler.projected_finish_time(worker, event, state),
              Scheduler.queue_wait_time(worker, event, state),
              worker.id
            }
          end)

        {worker, strategy_state}
      end
    )
  end

  defp deadline_violation(worker, event, state) do
    case event.deadline_ms do
      nil ->
        0

      deadline_ms ->
        latency = Scheduler.projected_finish_time(worker, event, state) - event.arrival_time
        max(0, latency - deadline_ms)
    end
  end
end
