defmodule EventSchedulerSim.Stats do
  def summary([]) do
    %{mean: 0.0, stddev: 0.0, min: 0.0, max: 0.0}
  end

  def summary(values) do
    numeric_values = Enum.map(values, &to_float/1)
    mean = mean(numeric_values)

    %{
      mean: round_float(mean),
      stddev: round_float(stddev(numeric_values, mean)),
      min: round_float(Enum.min(numeric_values)),
      max: round_float(Enum.max(numeric_values))
    }
  end

  def mean([]), do: 0.0
  def mean(values), do: Enum.sum(values) / length(values)

  def stddev([], _mean), do: 0.0
  def stddev([_value], _mean), do: 0.0

  def stddev(values, mean) do
    variance =
      values
      |> Enum.map(&:math.pow(&1 - mean, 2))
      |> Enum.sum()
      |> Kernel./(length(values) - 1)

    :math.sqrt(variance)
  end

  defp to_float(value) when is_integer(value), do: value / 1
  defp to_float(value) when is_float(value), do: value

  defp round_float(value), do: Float.round(value, 4)
end
