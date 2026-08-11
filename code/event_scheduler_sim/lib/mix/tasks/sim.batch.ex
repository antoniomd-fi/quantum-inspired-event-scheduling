defmodule Mix.Tasks.Sim.Batch do
  use Mix.Task

  @shortdoc "Runs a batch of scheduling simulations"

  @impl Mix.Task
  def run(args) do
    Mix.Task.run("app.start")

    {opts, _rest, invalid} =
      OptionParser.parse(args,
        strict: [
          scenarios: :string,
          strategies: :string,
          out: :string
        ]
      )

    if invalid != [] do
      Mix.raise("Invalid options: #{inspect(invalid)}")
    end

    scenario_paths =
      opts
      |> Keyword.get(:scenarios)
      |> split_list(EventSchedulerSim.Batch.default_scenarios())

    strategies =
      opts
      |> Keyword.get(:strategies)
      |> split_list(EventSchedulerSim.Strategy.names())

    output_dir = Keyword.get(opts, :out, "results/batch")

    results =
      EventSchedulerSim.Batch.run(
        scenario_paths: scenario_paths,
        strategies: strategies,
        output_dir: output_dir
      )

    Mix.shell().info("Batch simulations: #{length(results)}")
    Mix.shell().info("Output: #{output_dir}")
    Mix.shell().info("Summary CSV: #{Path.join(output_dir, "summary.csv")}")
  end

  defp split_list(nil, default), do: default

  defp split_list(value, _default) do
    value
    |> String.split(",", trim: true)
    |> Enum.map(&String.trim/1)
    |> Enum.reject(&(&1 == ""))
  end
end
