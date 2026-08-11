defmodule EventSchedulerSim.Simulator do
  alias EventSchedulerSim.Metrics
  alias EventSchedulerSim.Result
  alias EventSchedulerSim.Scenario

  def run(%Scenario{} = scenario, strategy) do
    assignments = strategy.schedule(scenario)
    metrics = Metrics.compute(scenario, assignments)

    %Result{
      scenario: scenario,
      strategy: strategy.name(),
      assignments: assignments,
      metrics: metrics
    }
  end
end
