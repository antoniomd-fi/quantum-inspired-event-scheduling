events =
  1..72
  |> Enum.map(fn index ->
    critical? = rem(index, 12) == 0

    %{
      id: "event_#{String.pad_leading(Integer.to_string(index), 3, "0")}",
      type: if(critical?, do: "critical", else: "standard"),
      arrival_time: (index - 1) * 125,
      duration_ms: if(critical?, do: 240, else: 140 + rem(index, 4) * 35),
      priority: if(critical?, do: 9, else: 2 + rem(index, 4)),
      deadline_ms: if(critical?, do: 500, else: 950)
    }
  end)

%{
  name: "steady_load",
  description: "Stable workload with moderate utilization and occasional critical events.",
  starvation_threshold_ms: 900,
  workers: [
    %{id: "worker_a", speed: 1.0},
    %{id: "worker_b", speed: 1.1},
    %{id: "worker_c", speed: 0.9},
    %{id: "worker_d", speed: 1.0}
  ],
  events: events
}
