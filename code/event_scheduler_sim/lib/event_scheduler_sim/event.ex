defmodule EventSchedulerSim.Event do
  defstruct [
    :id,
    :type,
    :arrival_time,
    :duration_ms,
    :priority,
    :deadline_ms
  ]

  def from_map(attrs) when is_map(attrs) do
    %__MODULE__{
      id: attrs |> value(:id) |> to_string(),
      type: attrs |> value(:type, "standard") |> to_string(),
      arrival_time: attrs |> value(:arrival_time, 0) |> to_integer(),
      duration_ms: attrs |> value(:duration_ms) |> to_integer(),
      priority: attrs |> value(:priority, 1) |> to_integer(),
      deadline_ms: attrs |> value(:deadline_ms, nil) |> nullable_integer()
    }
  end

  defp value(attrs, key, default \\ nil) do
    cond do
      Map.has_key?(attrs, key) -> Map.fetch!(attrs, key)
      Map.has_key?(attrs, Atom.to_string(key)) -> Map.fetch!(attrs, Atom.to_string(key))
      true -> default
    end
  end

  defp nullable_integer(nil), do: nil
  defp nullable_integer(value), do: to_integer(value)

  defp to_integer(value) when is_integer(value), do: value
  defp to_integer(value) when is_float(value), do: round(value)
  defp to_integer(value) when is_binary(value), do: String.to_integer(value)
end
