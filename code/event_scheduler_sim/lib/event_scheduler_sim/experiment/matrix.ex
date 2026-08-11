defmodule EventSchedulerSim.Experiment.Matrix do
  alias EventSchedulerSim.Strategy

  @profiles [
    "steady",
    "burst",
    "saturation",
    "critical_heavy",
    "heterogeneous"
  ]

  @load_levels [
    "low",
    "medium",
    "high",
    "overload"
  ]

  def profiles, do: @profiles
  def load_levels, do: @load_levels
  def seeds, do: 1..5 |> Enum.to_list()
  def strategies, do: Strategy.names()

  def build(opts \\ []) do
    profiles = Keyword.get(opts, :profiles, profiles())
    load_levels = Keyword.get(opts, :load_levels, load_levels())
    seeds = Keyword.get(opts, :seeds, seeds())
    strategies = Keyword.get(opts, :strategies, strategies())

    for profile <- profiles,
        load_level <- load_levels,
        seed <- seeds,
        strategy <- strategies do
      %{
        profile: profile,
        load_level: load_level,
        seed: seed,
        strategy: strategy
      }
    end
  end
end
