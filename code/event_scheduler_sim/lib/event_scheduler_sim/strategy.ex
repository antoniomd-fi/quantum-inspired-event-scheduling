defmodule EventSchedulerSim.Strategy do
  alias EventSchedulerSim.Strategies.DeadlineAwareDispatch
  alias EventSchedulerSim.Strategies.DurationAwareDispatch
  alias EventSchedulerSim.Strategies.LeastLoaded
  alias EventSchedulerSim.Strategies.MinCostGreedy
  alias EventSchedulerSim.Strategies.PriorityAware
  alias EventSchedulerSim.Strategies.QuboBatchExact
  alias EventSchedulerSim.Strategies.QuboBatchExactCriticalFocused
  alias EventSchedulerSim.Strategies.QuboBatchExactDeadlineFocused
  alias EventSchedulerSim.Strategies.QuboBatchExactLowBalance
  alias EventSchedulerSim.Strategies.QuboBatchExactSequencing
  alias EventSchedulerSim.Strategies.RoundRobin
  alias EventSchedulerSim.Strategies.ShortestQueue
  alias EventSchedulerSim.Strategies.WeightedRoundRobin

  @strategies %{
    "deadline_aware_dispatch" => DeadlineAwareDispatch,
    "duration_aware_dispatch" => DurationAwareDispatch,
    "least_loaded" => LeastLoaded,
    "min_cost_greedy" => MinCostGreedy,
    "priority_aware" => PriorityAware,
    "round_robin" => RoundRobin,
    "shortest_queue" => ShortestQueue,
    "weighted_round_robin" => WeightedRoundRobin
  }

  @experimental_strategies %{
    "qubo_batch_exact" => QuboBatchExact,
    "qubo_batch_exact_critical_focused" => QuboBatchExactCriticalFocused,
    "qubo_batch_exact_deadline_focused" => QuboBatchExactDeadlineFocused,
    "qubo_batch_exact_low_balance" => QuboBatchExactLowBalance,
    "qubo_batch_exact_sequencing" => QuboBatchExactSequencing
  }

  @legacy_names %{
    "earliest_deadline_first" => "deadline_aware_dispatch",
    "shortest_processing_time" => "duration_aware_dispatch"
  }

  def names, do: @strategies |> Map.keys() |> Enum.sort()
  def experimental_names, do: @experimental_strategies |> Map.keys() |> Enum.sort()

  def all_names,
    do: @strategies |> Map.merge(@experimental_strategies) |> Map.keys() |> Enum.sort()

  def resolve!(strategy) when is_atom(strategy) do
    strategy
    |> Atom.to_string()
    |> resolve!()
  end

  def resolve!(strategy) when is_binary(strategy) do
    normalized_strategy = Map.get(@legacy_names, strategy, strategy)

    case Map.fetch(all_strategies(), normalized_strategy) do
      {:ok, module} -> module
      :error -> unknown_strategy!(strategy)
    end
  end

  defp all_strategies, do: Map.merge(@strategies, @experimental_strategies)

  defp unknown_strategy!(strategy) do
    raise ArgumentError, "unknown strategy: #{inspect(strategy)}"
  end
end
