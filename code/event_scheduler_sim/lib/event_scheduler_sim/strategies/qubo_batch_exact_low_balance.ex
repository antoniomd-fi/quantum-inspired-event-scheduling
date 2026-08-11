defmodule EventSchedulerSim.Strategies.QuboBatchExactLowBalance do
  alias EventSchedulerSim.Strategies.QuboBatchExact

  def name, do: "qubo_batch_exact_low_balance"

  def schedule(scenario), do: QuboBatchExact.schedule(scenario, :low_balance)
end
