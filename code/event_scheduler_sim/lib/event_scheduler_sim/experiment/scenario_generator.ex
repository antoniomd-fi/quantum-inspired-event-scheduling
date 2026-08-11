defmodule EventSchedulerSim.Experiment.ScenarioGenerator do
  alias EventSchedulerSim.Scenario

  @load_utilization %{
    "low" => 0.55,
    "medium" => 0.75,
    "high" => 0.95,
    "overload" => 1.15
  }

  @profiles %{
    "steady" => %{
      event_count: 120,
      pattern: :steady,
      critical_ratio: 0.10,
      standard_duration: {170, 55},
      critical_duration: {260, 60},
      standard_deadline_ms: 950,
      critical_deadline_ms: 520,
      starvation_threshold_ms: 1_000,
      workers: [
        %{id: "worker_a", speed: 1.0, weight: 2},
        %{id: "worker_b", speed: 1.1, weight: 2},
        %{id: "worker_c", speed: 0.9, weight: 2},
        %{id: "worker_d", speed: 1.0, weight: 2}
      ]
    },
    "burst" => %{
      event_count: 144,
      pattern: :burst,
      burst_size: 9,
      critical_ratio: 0.18,
      standard_duration: {190, 70},
      critical_duration: {300, 80},
      standard_deadline_ms: 1_100,
      critical_deadline_ms: 560,
      starvation_threshold_ms: 1_200,
      workers: [
        %{id: "worker_a", speed: 1.0, weight: 2},
        %{id: "worker_b", speed: 1.05, weight: 2},
        %{id: "worker_c", speed: 0.95, weight: 2}
      ]
    },
    "saturation" => %{
      event_count: 150,
      pattern: :saturation,
      critical_ratio: 0.14,
      standard_duration: {205, 75},
      critical_duration: {320, 90},
      standard_deadline_ms: 1_250,
      critical_deadline_ms: 620,
      starvation_threshold_ms: 1_450,
      workers: [
        %{id: "worker_a", speed: 1.0, weight: 2},
        %{id: "worker_b", speed: 0.95, weight: 2},
        %{id: "worker_c", speed: 0.9, weight: 2}
      ]
    },
    "critical_heavy" => %{
      event_count: 132,
      pattern: :burst,
      burst_size: 6,
      critical_ratio: 0.35,
      standard_duration: {180, 65},
      critical_duration: {280, 70},
      standard_deadline_ms: 1_000,
      critical_deadline_ms: 430,
      starvation_threshold_ms: 1_100,
      workers: [
        %{id: "worker_a", speed: 1.0, weight: 2},
        %{id: "worker_b", speed: 1.0, weight: 2},
        %{id: "worker_c", speed: 1.0, weight: 2}
      ]
    },
    "heterogeneous" => %{
      event_count: 140,
      pattern: :steady,
      critical_ratio: 0.12,
      standard_duration: {200, 80},
      critical_duration: {310, 85},
      standard_deadline_ms: 1_050,
      critical_deadline_ms: 560,
      starvation_threshold_ms: 1_250,
      workers: [
        %{id: "worker_fast", speed: 1.8, weight: 4},
        %{id: "worker_standard", speed: 1.0, weight: 2},
        %{id: "worker_slow", speed: 0.6, weight: 1}
      ]
    },
    "burst_critical" => %{
      event_count: 156,
      pattern: :burst,
      burst_size: 12,
      critical_ratio: 0.32,
      standard_duration: {190, 75},
      critical_duration: {290, 80},
      standard_deadline_ms: 1_000,
      critical_deadline_ms: 380,
      starvation_threshold_ms: 900,
      workers: [
        %{id: "worker_a", speed: 1.05, weight: 2},
        %{id: "worker_b", speed: 1.0, weight: 2},
        %{id: "worker_c", speed: 0.9, weight: 2}
      ]
    },
    "flooding_critical" => %{
      event_count: 180,
      pattern: :burst,
      burst_size: 15,
      critical_ratio: 0.08,
      standard_duration: {165, 65},
      critical_duration: {270, 70},
      standard_deadline_ms: 1_300,
      critical_deadline_ms: 360,
      starvation_threshold_ms: 800,
      workers: [
        %{id: "worker_a", speed: 1.0, weight: 2},
        %{id: "worker_b", speed: 0.95, weight: 2},
        %{id: "worker_c", speed: 0.9, weight: 2}
      ]
    },
    "heterogeneous_pressure" => %{
      event_count: 156,
      pattern: :saturation,
      critical_ratio: 0.20,
      standard_duration: {205, 90},
      critical_duration: {315, 90},
      standard_deadline_ms: 1_100,
      critical_deadline_ms: 500,
      starvation_threshold_ms: 1_000,
      workers: [
        %{id: "worker_fast", speed: 1.9, weight: 5},
        %{id: "worker_standard", speed: 0.95, weight: 2},
        %{id: "worker_constrained", speed: 0.55, weight: 1}
      ]
    },
    "fairness_starvation" => %{
      event_count: 168,
      pattern: :saturation,
      critical_ratio: 0.18,
      standard_duration: {220, 95},
      critical_duration: {340, 100},
      standard_deadline_ms: 1_250,
      critical_deadline_ms: 580,
      starvation_threshold_ms: 700,
      workers: [
        %{id: "worker_fast", speed: 1.4, weight: 3},
        %{id: "worker_regular", speed: 1.0, weight: 2},
        %{id: "worker_slow", speed: 0.75, weight: 1}
      ]
    }
  }

  def profiles, do: @profiles |> Map.keys() |> Enum.sort()
  def load_levels, do: @load_utilization |> Map.keys() |> Enum.sort()

  def build(opts) do
    profile_name = Keyword.fetch!(opts, :profile)
    load_level = Keyword.fetch!(opts, :load_level)
    seed = Keyword.fetch!(opts, :seed)

    profile = Map.fetch!(@profiles, profile_name)
    utilization = Map.fetch!(@load_utilization, load_level)
    rng = seed_rng(seed)
    interarrival_ms = interarrival_ms(profile, utilization)
    {events, _rng} = build_events(profile, profile_name, load_level, seed, interarrival_ms, rng)

    Scenario.from_map(%{
      name: "#{profile_name}_#{load_level}_seed_#{seed}",
      description: "#{profile_name} generated scenario at #{load_level} load with seed #{seed}.",
      starvation_threshold_ms: profile.starvation_threshold_ms,
      metadata:
        metadata(
          profile,
          profile_name,
          load_level,
          seed,
          utilization,
          interarrival_ms,
          events
        ),
      workers: profile.workers,
      events: events
    })
  end

  defp metadata(profile, profile_name, load_level, seed, utilization, interarrival_ms, events) do
    event_count = length(events)
    critical_count = Enum.count(events, &(&1.type == "critical"))

    %{
      profile: profile_name,
      load_level: load_level,
      seed: seed,
      target_utilization: round_float(utilization),
      estimated_interarrival_ms: round_float(interarrival_ms),
      event_count: event_count,
      actual_critical_ratio: round_float(safe_div(critical_count, event_count)),
      actual_average_duration_ms: round_float(average(events, :duration_ms)),
      actual_average_deadline_ms: round_float(average(events, :deadline_ms)),
      worker_count: length(profile.workers),
      total_worker_speed: round_float(profile.workers |> Enum.map(& &1.speed) |> Enum.sum()),
      total_worker_weight: profile.workers |> Enum.map(& &1.weight) |> Enum.sum()
    }
  end

  defp build_events(profile, profile_name, load_level, seed, interarrival_ms, rng) do
    arrival_times = arrival_times(profile, interarrival_ms)

    1..profile.event_count
    |> Enum.zip(arrival_times)
    |> Enum.map_reduce(rng, fn {index, arrival_time}, current_rng ->
      {critical?, next_rng} = critical_event?(profile.critical_ratio, current_rng)
      {duration_ms, duration_rng} = duration(profile, critical?, next_rng)
      {priority, priority_rng} = priority(critical?, duration_rng)
      {deadline_ms, deadline_rng} = deadline(profile, critical?, priority_rng)

      event = %{
        id:
          [
            profile_name,
            load_level,
            "seed",
            seed,
            "event",
            String.pad_leading(Integer.to_string(index), 4, "0")
          ]
          |> Enum.join("_"),
        type: if(critical?, do: "critical", else: "standard"),
        arrival_time: arrival_time,
        duration_ms: duration_ms,
        priority: priority,
        deadline_ms: deadline_ms
      }

      {event, deadline_rng}
    end)
  end

  defp arrival_times(%{pattern: :steady, event_count: event_count}, interarrival_ms) do
    0..(event_count - 1)
    |> Enum.map(&round(&1 * interarrival_ms))
  end

  defp arrival_times(
         %{pattern: :burst, event_count: event_count, burst_size: burst_size},
         interarrival_ms
       ) do
    burst_gap = interarrival_ms * burst_size

    0..(event_count - 1)
    |> Enum.map(fn index ->
      burst_index = div(index, burst_size)
      offset = rem(index, burst_size)

      round(burst_index * burst_gap + min(offset, 2) * interarrival_ms * 0.08)
    end)
  end

  defp arrival_times(%{pattern: :saturation, event_count: event_count}, interarrival_ms) do
    {times, _arrival} =
      0..(event_count - 1)
      |> Enum.map_reduce(0.0, fn index, arrival ->
        pressure = index / max(event_count - 1, 1)
        interval = interarrival_ms * (1.25 - 0.55 * pressure)

        {round(arrival), arrival + interval}
      end)

    times
  end

  defp interarrival_ms(profile, utilization) do
    total_speed =
      profile.workers
      |> Enum.map(& &1.speed)
      |> Enum.sum()

    average_work_ms =
      average_duration(
        profile.standard_duration,
        profile.critical_duration,
        profile.critical_ratio
      )

    max(1, average_work_ms / (total_speed * utilization))
  end

  defp average_duration({standard_mean, _}, {critical_mean, _}, critical_ratio) do
    standard_mean * (1.0 - critical_ratio) + critical_mean * critical_ratio
  end

  defp critical_event?(critical_ratio, rng) do
    {value, next_rng} = uniform(rng)
    {value <= critical_ratio, next_rng}
  end

  defp duration(profile, true, rng), do: bounded_jitter(profile.critical_duration, 80, 700, rng)
  defp duration(profile, false, rng), do: bounded_jitter(profile.standard_duration, 60, 650, rng)

  defp priority(true, rng) do
    {value, next_rng} = uniform_int(8, 10, rng)
    {value, next_rng}
  end

  defp priority(false, rng) do
    {value, next_rng} = uniform_int(1, 5, rng)
    {value, next_rng}
  end

  defp deadline(profile, true, rng),
    do: bounded_jitter({profile.critical_deadline_ms, 80}, 250, 1_100, rng)

  defp deadline(profile, false, rng),
    do: bounded_jitter({profile.standard_deadline_ms, 160}, 450, 2_000, rng)

  defp bounded_jitter({mean, spread}, min_value, max_value, rng) do
    {jitter, next_rng} = uniform_int(-spread, spread, rng)

    value =
      mean
      |> Kernel.+(jitter)
      |> max(min_value)
      |> min(max_value)

    {value, next_rng}
  end

  defp seed_rng(seed) do
    a = seed |> abs() |> Kernel.+(101)
    b = seed |> abs() |> Kernel.*(3) |> Kernel.+(211)
    c = seed |> abs() |> Kernel.*(7) |> Kernel.+(307)

    :rand.seed_s(:exsss, {a, b, c})
  end

  defp uniform(rng), do: :rand.uniform_s(rng)

  defp uniform_int(min_value, max_value, rng) do
    {value, next_rng} = uniform(rng)
    range = max_value - min_value + 1
    generated = min_value + floor(value * range)

    {min(generated, max_value), next_rng}
  end

  defp average(events, key) do
    values = Enum.map(events, &Map.fetch!(&1, key))
    safe_div(Enum.sum(values), length(values))
  end

  defp safe_div(_numerator, 0), do: 0.0
  defp safe_div(numerator, denominator), do: numerator / denominator

  defp round_float(value) when is_float(value), do: Float.round(value, 4)
  defp round_float(value), do: value
end
