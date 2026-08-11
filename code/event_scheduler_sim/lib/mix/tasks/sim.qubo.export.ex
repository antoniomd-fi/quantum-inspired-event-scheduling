defmodule Mix.Tasks.Sim.Qubo.Export do
  use Mix.Task

  @shortdoc "Exports small QUBO instances for external validation"

  @default_scenarios [
    "scenarios/baseline.exs",
    "scenarios/steady_load.exs",
    "scenarios/burst_load.exs",
    "scenarios/critical_priority.exs",
    "scenarios/heterogeneous_workers.exs"
  ]

  @impl Mix.Task
  def run(args) do
    Mix.Task.run("app.start")

    {opts, _rest, invalid} =
      OptionParser.parse(args,
        strict: [
          scenarios: :string,
          profile: :string,
          batch_size: :integer,
          batches: :integer,
          max_variables: :integer,
          out: :string
        ]
      )

    if invalid != [] do
      Mix.raise("Invalid options: #{inspect(invalid)}")
    end

    scenario_paths =
      opts
      |> Keyword.get(:scenarios)
      |> split_list(@default_scenarios)

    profile = Keyword.get(opts, :profile, "sequencing")
    batch_size = Keyword.get(opts, :batch_size, 3)
    batch_limit = Keyword.get(opts, :batches, 1)
    max_variables = Keyword.get(opts, :max_variables, 20)
    output_dir = Keyword.get(opts, :out, "../../results/raw/v1_qaoa_validation_instances")

    instances =
      EventSchedulerSim.Qubo.Export.build_instances(
        scenario_paths: scenario_paths,
        profile: profile,
        batch_size: batch_size,
        batch_limit: batch_limit,
        max_variables: max_variables
      )

    EventSchedulerSim.Qubo.Export.write!(instances, output_dir)

    Mix.shell().info("QUBO validation instances: #{length(instances)}")
    Mix.shell().info("Profile: #{profile}")
    Mix.shell().info("Batch size: #{batch_size}")
    Mix.shell().info("Batches per scenario: #{batch_limit}")
    Mix.shell().info("Output: #{output_dir}")
    Mix.shell().info("Manifest: #{Path.join(output_dir, "manifest.json")}")
  end

  defp split_list(nil, default), do: default

  defp split_list(value, _default) do
    value
    |> String.split(",", trim: true)
    |> Enum.map(&String.trim/1)
    |> Enum.reject(&(&1 == ""))
  end
end
