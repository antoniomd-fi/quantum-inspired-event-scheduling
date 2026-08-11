defmodule EventSchedulerSim.Assignment do
  alias EventSchedulerSim.Event
  alias EventSchedulerSim.Worker

  defstruct [
    :event_id,
    :event_type,
    :worker_id,
    :priority,
    :arrival_time,
    :start_time,
    :finish_time,
    :processing_time,
    :waiting_time,
    :latency,
    :deadline_ms,
    :deadline_met
  ]

  def build(%Event{} = event, %Worker{} = worker, start_time, finish_time, processing_time) do
    latency = finish_time - event.arrival_time

    %__MODULE__{
      event_id: event.id,
      event_type: event.type,
      worker_id: worker.id,
      priority: event.priority,
      arrival_time: event.arrival_time,
      start_time: start_time,
      finish_time: finish_time,
      processing_time: processing_time,
      waiting_time: start_time - event.arrival_time,
      latency: latency,
      deadline_ms: event.deadline_ms,
      deadline_met: deadline_met?(latency, event.deadline_ms)
    }
  end

  defp deadline_met?(_latency, nil), do: true
  defp deadline_met?(latency, deadline_ms), do: latency <= deadline_ms
end
