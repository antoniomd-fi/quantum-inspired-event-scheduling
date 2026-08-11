{events, _next_arrival_time} =
  1..90
  |> Enum.map_reduce(0, fn index, arrival_time ->
    critical? = rem(index, 13) == 0
    phase = div(index - 1, 30)
    interval = Enum.at([95, 65, 40], phase)

    event = %{
      id: "event_#{String.pad_leading(Integer.to_string(index), 3, "0")}",
      type: if(critical?, do: "critical", else: "standard"),
      arrival_time: arrival_time,
      duration_ms: if(critical?, do: 320, else: 190 + rem(index, 5) * 30),
      priority: if(critical?, do: 10, else: 1 + rem(index, 5)),
      deadline_ms: if(critical?, do: 600, else: 1_300)
    }

    {event, arrival_time + interval}
  end)

%{
  name: "progressive_saturation",
  description: "Arrival intervals shrink over time to model progressive saturation.",
  starvation_threshold_ms: 1_300,
  workers: [
    %{id: "worker_a", speed: 1.0},
    %{id: "worker_b", speed: 0.95},
    %{id: "worker_c", speed: 0.9}
  ],
  events: events
}
