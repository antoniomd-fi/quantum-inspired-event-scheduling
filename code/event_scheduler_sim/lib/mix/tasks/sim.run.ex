defmodule Mix.Tasks.Sim.Run do
  use Mix.Task

  @shortdoc "Runs a scheduling simulation"

  @impl Mix.Task
  def run(args) do
    Mix.Task.run("app.start")

    {opts, _rest, invalid} =
      OptionParser.parse(args,
        strict: [
          scenario: :string,
          strategy: :string,
          out: :string
        ]
      )

    if invalid != [] do
      Mix.raise("Invalid options: #{inspect(invalid)}")
    end

    scenario_path = Keyword.get(opts, :scenario, "scenarios/baseline.exs")
    strategy = Keyword.get(opts, :strategy, "round_robin")
    output_dir = Keyword.get(opts, :out, "results/baseline_round_robin")

    result =
      EventSchedulerSim.run(
        scenario_path: scenario_path,
        strategy: strategy,
        output_dir: output_dir
      )

    Mix.shell().info("Scenario: #{result.metrics.scenario}")
    Mix.shell().info("Strategy: #{result.strategy}")
    Mix.shell().info("Total events: #{result.metrics.total_events}")
    Mix.shell().info("Average latency ms: #{result.metrics.average_latency_ms}")
    Mix.shell().info("Output: #{output_dir}")
  end
end
