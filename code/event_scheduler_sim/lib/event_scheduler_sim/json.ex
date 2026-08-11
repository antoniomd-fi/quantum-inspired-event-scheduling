defmodule EventSchedulerSim.Json do
  def encode(value), do: do_encode(value)

  defp do_encode(value) when is_map(value) do
    entries =
      value
      |> Enum.sort_by(fn {key, _value} -> to_string(key) end)
      |> Enum.map(fn {key, item} ->
        do_encode(to_string(key)) <> ":" <> do_encode(item)
      end)

    "{" <> Enum.join(entries, ",") <> "}"
  end

  defp do_encode(value) when is_list(value) do
    "[" <> (value |> Enum.map(&do_encode/1) |> Enum.join(",")) <> "]"
  end

  defp do_encode(value) when is_binary(value) do
    escaped =
      value
      |> String.replace("\\", "\\\\")
      |> String.replace("\"", "\\\"")
      |> String.replace("\n", "\\n")
      |> String.replace("\r", "\\r")
      |> String.replace("\t", "\\t")

    "\"" <> escaped <> "\""
  end

  defp do_encode(value) when is_integer(value), do: Integer.to_string(value)

  defp do_encode(value) when is_float(value) do
    :erlang.float_to_binary(value, [:compact, decimals: 6])
  end

  defp do_encode(true), do: "true"
  defp do_encode(false), do: "false"
  defp do_encode(nil), do: "null"
end
