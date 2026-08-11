defmodule EventSchedulerSim.Qubo.ExactSolver do
  @moduledoc """
  Brute-force solver for small QUBO models.

  This solver is intentionally limited. Its role is to validate QUBO
  formulations on tiny instances before adding approximate or external solvers.
  """

  import Bitwise

  alias EventSchedulerSim.Qubo.Model

  @default_max_variables 20

  def solve!(%Model{} = model, opts \\ []) do
    variable_count = length(model.variables)
    max_variables = Keyword.get(opts, :max_variables, @default_max_variables)

    if variable_count > max_variables do
      raise ArgumentError,
            "exact QUBO solver supports at most #{max_variables} variables, got #{variable_count}"
    end

    best =
      masks(variable_count)
      |> Enum.reduce(nil, fn mask, current_best ->
        assignment = assignment_from_mask(variable_count, mask)
        objective_value = Model.evaluate(model, assignment)
        candidate = solution(model, assignment, objective_value, mask)

        better_solution(candidate, current_best)
      end)

    Map.delete(best, :mask)
  end

  defp masks(0), do: [0]
  defp masks(variable_count), do: 0..((1 <<< variable_count) - 1)

  defp assignment_from_mask(0, _mask), do: %{}

  defp assignment_from_mask(variable_count, mask) do
    0..(variable_count - 1)
    |> Enum.map(fn index ->
      value = if (mask &&& 1 <<< index) == 0, do: 0, else: 1
      {index, value}
    end)
    |> Map.new()
  end

  defp solution(%Model{} = model, assignment, objective_value, mask) do
    selected_variables =
      model.variables
      |> Enum.filter(&(Map.fetch!(assignment, &1.index) == 1))

    selected_worker_by_event =
      selected_variables
      |> Enum.group_by(& &1.event_id)
      |> Map.new(fn {event_id, variables} ->
        {event_id, Enum.map(variables, & &1.worker_id)}
      end)

    %{
      assignment: assignment,
      objective_value: objective_value,
      selected_variables: selected_variables,
      selected_worker_by_event: selected_worker_by_event,
      constraint_violations: constraint_violations(model, selected_worker_by_event),
      selected_variable_count: length(selected_variables),
      mask: mask
    }
  end

  defp constraint_violations(%Model{} = model, selected_worker_by_event) do
    model.variables
    |> Enum.map(& &1.event_id)
    |> Enum.uniq()
    |> Enum.count(fn event_id ->
      selected_count =
        selected_worker_by_event
        |> Map.get(event_id, [])
        |> length()

      selected_count != 1
    end)
  end

  defp better_solution(candidate, nil), do: candidate

  defp better_solution(candidate, current_best) do
    candidate_key = solution_key(candidate)
    current_key = solution_key(current_best)

    if candidate_key < current_key, do: candidate, else: current_best
  end

  defp solution_key(solution) do
    {
      solution.objective_value,
      solution.constraint_violations,
      solution.selected_variable_count,
      solution.mask
    }
  end
end
