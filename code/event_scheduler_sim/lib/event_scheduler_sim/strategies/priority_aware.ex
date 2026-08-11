defmodule EventSchedulerSim.Strategies.PriorityAware do
  alias EventSchedulerSim.Scheduler
  alias EventSchedulerSim.Worker

  def name, do: "priority_aware"

  def schedule(scenario) do
    Scheduler.run(scenario,
      event_order: :priority_arrival,
      selector: fn event, _index, workers, state, strategy_state ->
        worker =
          Enum.min_by(workers, fn worker ->
            if critical?(event) do
              {
                deadline_violation(worker, event, state),
                Scheduler.projected_finish_time(worker, event, state),
                Scheduler.queue_wait_time(worker, event, state),
                worker.id
              }
            else
              {
                Scheduler.queue_wait_time(worker, event, state),
                Scheduler.busy_time(worker, state),
                Scheduler.projected_finish_time(worker, event, state),
                worker.id
              }
            end
          end)

        {worker, strategy_state}
      end
    )
  end

  defp critical?(event), do: event.type == "critical" or event.priority >= 8

  defp deadline_violation(%Worker{} = worker, event, state) do
    case event.deadline_ms do
      nil ->
        0

      deadline_ms ->
        latency = Scheduler.projected_finish_time(worker, event, state) - event.arrival_time
        max(0, latency - deadline_ms)
    end
  end
end
