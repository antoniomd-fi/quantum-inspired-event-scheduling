defmodule EventSchedulerSim.Scenario do
  alias EventSchedulerSim.Event
  alias EventSchedulerSim.Worker

  defstruct [
    :name,
    :description,
    :starvation_threshold_ms,
    metadata: %{},
    events: [],
    workers: []
  ]

  def load!(path) do
    {raw, _binding} = Code.eval_file(path)
    from_map(raw)
  end

  def from_map(attrs) when is_map(attrs) do
    %__MODULE__{
      name: attrs |> value(:name, "unnamed_scenario") |> to_string(),
      description: attrs |> value(:description, "") |> to_string(),
      starvation_threshold_ms: attrs |> value(:starvation_threshold_ms, 1_000) |> to_integer(),
      metadata: attrs |> value(:metadata, %{}),
      workers: attrs |> value(:workers, []) |> Enum.map(&Worker.from_map/1),
      events: attrs |> value(:events, []) |> Enum.map(&Event.from_map/1)
    }
  end

  defp value(attrs, key, default) do
    cond do
      Map.has_key?(attrs, key) -> Map.fetch!(attrs, key)
      Map.has_key?(attrs, Atom.to_string(key)) -> Map.fetch!(attrs, Atom.to_string(key))
      true -> default
    end
  end

  defp to_integer(value) when is_integer(value), do: value
  defp to_integer(value) when is_float(value), do: round(value)
  defp to_integer(value) when is_binary(value), do: String.to_integer(value)
end
