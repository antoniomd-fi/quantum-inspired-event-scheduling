defmodule EventSchedulerSim.Worker do
  alias EventSchedulerSim.Event

  defstruct [
    :id,
    :speed,
    :weight
  ]

  def from_map(attrs) when is_map(attrs) do
    speed = attrs |> value(:speed, 1.0) |> to_float()
    weight = attrs |> value(:weight, default_weight(speed)) |> to_integer()

    if speed <= 0 do
      raise ArgumentError, "worker speed must be greater than zero"
    end

    if weight <= 0 do
      raise ArgumentError, "worker weight must be greater than zero"
    end

    %__MODULE__{
      id: attrs |> value(:id) |> to_string(),
      speed: speed,
      weight: weight
    }
  end

  def processing_time(%__MODULE__{speed: speed}, %Event{duration_ms: duration_ms}) do
    max(1, ceil(duration_ms / speed))
  end

  defp value(attrs, key, default \\ nil) do
    cond do
      Map.has_key?(attrs, key) -> Map.fetch!(attrs, key)
      Map.has_key?(attrs, Atom.to_string(key)) -> Map.fetch!(attrs, Atom.to_string(key))
      true -> default
    end
  end

  defp default_weight(speed), do: max(1, round(speed * 2))

  defp to_float(value) when is_float(value), do: value
  defp to_float(value) when is_integer(value), do: value / 1
  defp to_float(value) when is_binary(value), do: String.to_float(value)

  defp to_integer(value) when is_integer(value), do: value
  defp to_integer(value) when is_float(value), do: round(value)
  defp to_integer(value) when is_binary(value), do: String.to_integer(value)
end
