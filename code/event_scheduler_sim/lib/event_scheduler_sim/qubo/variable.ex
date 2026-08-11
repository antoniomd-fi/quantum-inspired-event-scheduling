defmodule EventSchedulerSim.Qubo.Variable do
  @moduledoc """
  Binary assignment variable for a QUBO event-worker model.
  """

  defstruct [
    :index,
    :name,
    :event_id,
    :worker_id
  ]

  def new(index, event, worker) do
    event_id = to_string(event.id)
    worker_id = to_string(worker.id)

    %__MODULE__{
      index: index,
      name: "x:#{event_id}:#{worker_id}",
      event_id: event_id,
      worker_id: worker_id
    }
  end
end
