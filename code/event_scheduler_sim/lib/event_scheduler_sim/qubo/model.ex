defmodule EventSchedulerSim.Qubo.Model do
  @moduledoc """
  Minimal QUBO model representation.

  The objective is evaluated as:

      constant + sum(linear_i * x_i) + sum(quadratic_i_j * x_i * x_j)

  where each `x_i` is binary.
  """

  defstruct variables: [],
            linear: %{},
            quadratic: %{},
            constant: 0.0,
            metadata: %{}

  def new(variables, metadata \\ %{}) do
    %__MODULE__{variables: variables, metadata: metadata}
  end

  def add_constant(%__MODULE__{} = model, coefficient) do
    %{model | constant: model.constant + coefficient}
  end

  def add_linear(%__MODULE__{} = model, variable_index, coefficient) do
    %{model | linear: Map.update(model.linear, variable_index, coefficient, &(&1 + coefficient))}
  end

  def add_quadratic(%__MODULE__{} = model, left_index, right_index, coefficient)
      when left_index == right_index do
    add_linear(model, left_index, coefficient)
  end

  def add_quadratic(%__MODULE__{} = model, left_index, right_index, coefficient) do
    key = ordered_pair(left_index, right_index)

    %{
      model
      | quadratic: Map.update(model.quadratic, key, coefficient, &(&1 + coefficient))
    }
  end

  def evaluate(%__MODULE__{} = model, assignment) when is_map(assignment) do
    linear_value =
      Enum.reduce(model.linear, 0.0, fn {variable_index, coefficient}, acc ->
        acc + coefficient * bit(assignment, variable_index)
      end)

    quadratic_value =
      Enum.reduce(model.quadratic, 0.0, fn {{left_index, right_index}, coefficient}, acc ->
        acc + coefficient * bit(assignment, left_index) * bit(assignment, right_index)
      end)

    round_number(model.constant + linear_value + quadratic_value)
  end

  def variables_for_event(%__MODULE__{} = model, event_id) do
    event_id = to_string(event_id)
    Enum.filter(model.variables, &(&1.event_id == event_id))
  end

  def variables_for_worker(%__MODULE__{} = model, worker_id) do
    worker_id = to_string(worker_id)
    Enum.filter(model.variables, &(&1.worker_id == worker_id))
  end

  defp ordered_pair(left_index, right_index) when left_index < right_index do
    {left_index, right_index}
  end

  defp ordered_pair(left_index, right_index), do: {right_index, left_index}

  defp bit(assignment, variable_index), do: Map.get(assignment, variable_index, 0)

  defp round_number(value) when is_float(value), do: Float.round(value, 6)
  defp round_number(value), do: value
end
