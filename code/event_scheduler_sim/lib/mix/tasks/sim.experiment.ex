defmodule Mix.Tasks.Sim.Experiment do
  use Mix.Task

  alias EventSchedulerSim.Experiment.Matrix
  alias EventSchedulerSim.Experiment.Runner

  @shortdoc "Runs the parameterized experimental matrix"

  @impl Mix.Task
  def run(args) do
    Mix.Task.run("app.start")

    {opts, _rest, invalid} =
      OptionParser.parse(args,
        strict: [
          profiles: :string,
          loads: :string,
          seeds: :string,
          strategies: :string,
          out: :string
        ]
      )

    if invalid != [] do
      Mix.raise("Invalid options: #{inspect(invalid)}")
    end

    result =
      Runner.run(
        profiles: split_list(Keyword.get(opts, :profiles), Matrix.profiles()),
        load_levels: split_list(Keyword.get(opts, :loads), Matrix.load_levels()),
        seeds: parse_seeds(Keyword.get(opts, :seeds), Matrix.seeds()),
        strategies: split_list(Keyword.get(opts, :strategies), Matrix.strategies()),
        output_dir: Keyword.get(opts, :out, "results/experimental_matrix")
      )

    Mix.shell().info("Experimental runs: #{result.run_count}")
    Mix.shell().info("Aggregate rows: #{result.aggregate_count}")
    Mix.shell().info("Output: #{result.output_dir}")
    Mix.shell().info("Runs CSV: #{Path.join(result.output_dir, "runs.csv")}")
    Mix.shell().info("Aggregated CSV: #{Path.join(result.output_dir, "aggregated.csv")}")
  end

  defp split_list(nil, default), do: default

  defp split_list(value, _default) do
    value
    |> String.split(",", trim: true)
    |> Enum.map(&String.trim/1)
    |> Enum.reject(&(&1 == ""))
  end

  defp parse_seeds(nil, default), do: default

  defp parse_seeds(value, _default) do
    case String.split(value, "..", parts: 2) do
      [first, last] ->
        String.to_integer(first)..String.to_integer(last)
        |> Enum.to_list()

      [_single] ->
        value
        |> split_list([])
        |> Enum.map(&String.to_integer/1)
    end
  end
end
