defmodule EventSchedulerSim.Strategies.QuboBatchExactDeadlineFocused do
  alias EventSchedulerSim.Strategies.QuboBatchExact

  def name, do: "qubo_batch_exact_deadline_focused"

  def schedule(scenario), do: QuboBatchExact.schedule(scenario, :deadline_focused)
end
