defmodule EventSchedulerSim.Strategies.QuboBatchExactSequencing do
  alias EventSchedulerSim.Strategies.QuboBatchExact

  def name, do: "qubo_batch_exact_sequencing"

  def schedule(scenario), do: QuboBatchExact.schedule(scenario, :sequencing)
end
