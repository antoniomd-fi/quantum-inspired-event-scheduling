defmodule EventSchedulerSim.Strategies.QuboBatchExactCriticalFocused do
  alias EventSchedulerSim.Strategies.QuboBatchExact

  def name, do: "qubo_batch_exact_critical_focused"

  def schedule(scenario), do: QuboBatchExact.schedule(scenario, :critical_focused)
end
