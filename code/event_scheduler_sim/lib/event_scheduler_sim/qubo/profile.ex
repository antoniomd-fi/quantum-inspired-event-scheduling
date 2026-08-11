defmodule EventSchedulerSim.Qubo.Profile do
  @moduledoc """
  Configuration profiles for exact QUBO batch experiments.

  Profiles let us run sensitivity analysis without duplicating the QUBO builder
  or changing the global objective function used by the rest of the simulator.
  """

  @profiles %{
    default: %{
      name: "default",
      strategy_name: "qubo_batch_exact",
      assignment_penalty: 100_000.0,
      balance_weight: 0.02,
      objective_weights: %{
        utilization_imbalance: 0.0
      }
    },
    deadline_focused: %{
      name: "deadline_focused",
      strategy_name: "qubo_batch_exact_deadline_focused",
      assignment_penalty: 100_000.0,
      balance_weight: 0.01,
      objective_weights: %{
        deadline_overrun_ms: 12.0,
        critical_waiting_time_ms: 2.0,
        utilization_imbalance: 0.0
      }
    },
    critical_focused: %{
      name: "critical_focused",
      strategy_name: "qubo_batch_exact_critical_focused",
      assignment_penalty: 100_000.0,
      balance_weight: 0.005,
      objective_weights: %{
        waiting_time_ms: 1.0,
        deadline_overrun_ms: 10.0,
        critical_waiting_time_ms: 8.0,
        starvation_overrun_ms: 4.0,
        utilization_imbalance: 0.0
      }
    },
    sequencing: %{
      name: "sequencing",
      strategy_name: "qubo_batch_exact_sequencing",
      assignment_penalty: 100_000.0,
      balance_weight: 0.01,
      sequencing_wait_weight: 0.8,
      sequencing_deadline_weight: 8.0,
      sequencing_critical_weight: 4.0,
      batch_order: :priority_arrival,
      objective_weights: %{
        waiting_time_ms: 1.0,
        deadline_overrun_ms: 10.0,
        critical_waiting_time_ms: 8.0,
        starvation_overrun_ms: 4.0,
        utilization_imbalance: 0.0
      }
    },
    low_balance: %{
      name: "low_balance",
      strategy_name: "qubo_batch_exact_low_balance",
      assignment_penalty: 100_000.0,
      balance_weight: 0.0,
      objective_weights: %{
        utilization_imbalance: 0.0
      }
    }
  }

  def names do
    @profiles
    |> Map.values()
    |> Enum.map(& &1.name)
    |> Enum.sort()
  end

  def strategy_names do
    @profiles
    |> Map.values()
    |> Enum.map(& &1.strategy_name)
    |> Enum.sort()
  end

  def get!(profile) when is_atom(profile) do
    case Map.fetch(@profiles, profile) do
      {:ok, config} -> config
      :error -> unknown_profile!(profile)
    end
  end

  def get!(profile) when is_binary(profile) do
    @profiles
    |> Enum.find(fn {_key, config} ->
      config.name == profile or config.strategy_name == profile
    end)
    |> case do
      {_key, config} -> config
      nil -> unknown_profile!(profile)
    end
  end

  def builder_opts(profile) do
    config = get!(profile)

    [
      assignment_penalty: config.assignment_penalty,
      balance_weight: config.balance_weight,
      sequencing_wait_weight: Map.get(config, :sequencing_wait_weight, 0.0),
      sequencing_deadline_weight: Map.get(config, :sequencing_deadline_weight, 0.0),
      sequencing_critical_weight: Map.get(config, :sequencing_critical_weight, 0.0),
      objective_weights: config.objective_weights,
      qubo_profile: config.name
    ]
  end

  defp unknown_profile!(profile) do
    raise ArgumentError, "unknown QUBO profile: #{inspect(profile)}"
  end
end
