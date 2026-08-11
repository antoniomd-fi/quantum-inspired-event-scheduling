defmodule EventSchedulerSim.Qubo.Export do
  @moduledoc """
  Exports small QUBO validation instances for external solvers.

  The exporter follows the same batch construction used by the exact QUBO
  strategy, then stores each model with its exact reference solution. External
  tools such as Qiskit can use these artifacts to validate whether an
  approximate optimizer is recovering the same assignment decisions.
  """

  alias EventSchedulerSim.Qubo.Builder
  alias EventSchedulerSim.Qubo.ExactSolver
  alias EventSchedulerSim.Qubo.Model
  alias EventSchedulerSim.Qubo.Profile
  alias EventSchedulerSim.Scenario
  alias EventSchedulerSim.Scheduler

  @schema_version "qubo-validation-v1"
  @default_batch_size 3
  @default_batch_limit 1
  @default_max_variables 20

  def build_instances(opts \\ []) do
    scenario_paths = Keyword.fetch!(opts, :scenario_paths)
    profile = Keyword.get(opts, :profile, "sequencing")
    batch_size = Keyword.get(opts, :batch_size, @default_batch_size)
    batch_limit = Keyword.get(opts, :batch_limit, @default_batch_limit)
    max_variables = Keyword.get(opts, :max_variables, @default_max_variables)

    validate_positive_integer!(batch_size, "batch_size")
    validate_positive_integer!(batch_limit, "batch_limit")

    Enum.flat_map(scenario_paths, fn scenario_path ->
      scenario = Scenario.load!(scenario_path)

      build_scenario_instances(
        scenario,
        scenario_path,
        profile,
        batch_size,
        batch_limit,
        max_variables
      )
    end)
  end

  def write!(instances, output_dir) when is_list(instances) do
    File.mkdir_p!(output_dir)

    manifest_entries =
      Enum.map(instances, fn instance ->
        file_name = instance.instance_id <> ".json"
        path = Path.join(output_dir, file_name)

        File.write!(path, EventSchedulerSim.Json.encode(instance) <> "\n")

        %{
          instance_id: instance.instance_id,
          scenario: instance.scenario,
          profile: instance.profile,
          variable_count: instance.variable_count,
          file: file_name
        }
      end)

    manifest = %{
      schema_version: @schema_version,
      generated_by: "mix sim.qubo.export",
      instance_count: length(instances),
      instances: manifest_entries
    }

    File.write!(
      Path.join(output_dir, "manifest.json"),
      EventSchedulerSim.Json.encode(manifest) <> "\n"
    )

    :ok
  end

  defp build_scenario_instances(
         %Scenario{} = scenario,
         scenario_path,
         profile,
         batch_size,
         batch_limit,
         max_variables
       ) do
    config = Profile.get!(profile)
    builder_opts = Profile.builder_opts(profile)
    event_order = Map.get(config, :batch_order, :arrival)

    scenario.events
    |> order_events(event_order)
    |> Enum.chunk_every(batch_size)
    |> Enum.take(batch_limit)
    |> Enum.with_index(1)
    |> Enum.reduce({Scheduler.initial_state(scenario.workers), []}, fn {batch, batch_index},
                                                                       {state, instances} ->
      model = Builder.build(scenario, batch, scenario.workers, state, builder_opts)
      solution = ExactSolver.solve!(model, max_variables: max_variables)

      if solution.constraint_violations > 0 do
        raise ArgumentError,
              "exact QUBO reference solution is infeasible for #{scenario.name} batch #{batch_index}"
      end

      instance =
        instance_map(
          scenario,
          scenario_path,
          config,
          batch,
          batch_index,
          state,
          model,
          solution
        )

      next_state = apply_solution(scenario, batch, state, solution)
      {next_state, instances ++ [instance]}
    end)
    |> elem(1)
  end

  defp instance_map(scenario, scenario_path, config, batch, batch_index, state, model, solution) do
    instance_id =
      [
        scenario.name,
        config.name,
        "batch",
        batch_index |> Integer.to_string() |> String.pad_leading(2, "0")
      ]
      |> Enum.join("_")
      |> slug()

    %{
      schema_version: @schema_version,
      instance_id: instance_id,
      scenario: scenario.name,
      scenario_path: scenario_path,
      profile: config.name,
      strategy: config.strategy_name,
      batch_index: batch_index,
      batch_size: length(batch),
      event_count: length(batch),
      worker_count: length(scenario.workers),
      variable_count: length(model.variables),
      state_before: state,
      events: Enum.map(batch, &event_map/1),
      workers: Enum.map(scenario.workers, &worker_map/1),
      variables: Enum.map(model.variables, &variable_map/1),
      constant: model.constant,
      linear: linear_terms(model),
      quadratic: quadratic_terms(model),
      metadata: model.metadata,
      exact_solution: solution_map(model, solution)
    }
  end

  defp apply_solution(scenario, batch, state, solution) do
    batch
    |> application_order()
    |> Enum.reduce(state, fn event, current_state ->
      worker_id =
        solution.selected_worker_by_event
        |> Map.fetch!(event.id)
        |> List.first()

      worker = Enum.find(scenario.workers, &(&1.id == worker_id))
      assignment = Scheduler.assign(event, worker, current_state)

      Scheduler.update_state(current_state, worker, assignment)
    end)
  end

  defp solution_map(%Model{} = model, solution) do
    %{
      objective_value: solution.objective_value,
      constraint_violations: solution.constraint_violations,
      selected_variable_count: solution.selected_variable_count,
      selected_worker_by_event: solution.selected_worker_by_event,
      assignment_vector:
        Enum.map(model.variables, fn variable ->
          Map.get(solution.assignment, variable.index, 0)
        end),
      selected_variables: Enum.map(solution.selected_variables, &variable_map/1)
    }
  end

  defp event_map(event) do
    %{
      id: event.id,
      type: event.type,
      arrival_time: event.arrival_time,
      duration_ms: event.duration_ms,
      priority: event.priority,
      deadline_ms: event.deadline_ms
    }
  end

  defp worker_map(worker) do
    %{
      id: worker.id,
      speed: worker.speed,
      weight: worker.weight
    }
  end

  defp variable_map(variable) do
    %{
      index: variable.index,
      name: "x_#{variable.index}",
      event_id: variable.event_id,
      worker_id: variable.worker_id
    }
  end

  defp linear_terms(%Model{} = model) do
    model.linear
    |> Enum.sort_by(fn {index, _coefficient} -> index end)
    |> Enum.map(fn {index, coefficient} ->
      %{index: index, coefficient: coefficient}
    end)
  end

  defp quadratic_terms(%Model{} = model) do
    model.quadratic
    |> Enum.sort_by(fn {{left_index, right_index}, _coefficient} -> {left_index, right_index} end)
    |> Enum.map(fn {{left_index, right_index}, coefficient} ->
      %{left: left_index, right: right_index, coefficient: coefficient}
    end)
  end

  defp order_events(events, :arrival), do: Enum.sort_by(events, &{&1.arrival_time, &1.id})
  defp order_events(events, :priority_arrival), do: application_order(events)

  defp application_order(events) do
    Enum.sort_by(events, fn event ->
      {event.arrival_time, -event.priority, deadline_value(event), event.id}
    end)
  end

  defp deadline_value(%{deadline_ms: nil}), do: 9_999_999_999
  defp deadline_value(%{deadline_ms: deadline_ms}), do: deadline_ms

  defp validate_positive_integer!(value, _name) when is_integer(value) and value > 0, do: :ok

  defp validate_positive_integer!(value, name) do
    raise ArgumentError, "#{name} must be a positive integer, got #{inspect(value)}"
  end

  defp slug(value) do
    value
    |> String.downcase()
    |> String.replace(~r/[^a-z0-9_]+/, "_")
    |> String.trim("_")
  end
end
