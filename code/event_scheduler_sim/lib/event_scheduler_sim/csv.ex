defmodule EventSchedulerSim.Csv do
  def encode_rows(headers, rows) do
    ([encode_row(headers)] ++ Enum.map(rows, &encode_row/1))
    |> Enum.join("\n")
    |> Kernel.<>("\n")
  end

  def encode_row(values) do
    values
    |> Enum.map(&escape/1)
    |> Enum.join(",")
  end

  def escape(nil), do: ""
  def escape(true), do: "true"
  def escape(false), do: "false"

  def escape(value) do
    text = to_string(value)

    if String.contains?(text, [",", "\"", "\n", "\r"]) do
      "\"" <> String.replace(text, "\"", "\"\"") <> "\""
    else
      text
    end
  end
end
