defmodule EventSchedulerSim do
  alias EventSchedulerSim.Output
  alias EventSchedulerSim.Scenario
  alias EventSchedulerSim.Simulator
  alias EventSchedulerSim.Strategy

  def run(opts) do
    scenario_path = Keyword.fetch!(opts, :scenario_path)
    strategy_name = Keyword.get(opts, :strategy, :round_robin)
    output_dir = Keyword.get(opts, :output_dir, "results/baseline_round_robin")

    scenario = Scenario.load!(scenario_path)
    strategy = Strategy.resolve!(strategy_name)
    result = Simulator.run(scenario, strategy)

    Output.write!(result, output_dir)

    result
  end
end
