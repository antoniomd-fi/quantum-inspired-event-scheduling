events =
  1..70
  |> Enum.map(fn index ->
    critical? = rem(index, 11) == 0

    %{
      id: "event_#{String.pad_leading(Integer.to_string(index), 3, "0")}",
      type: if(critical?, do: "critical", else: "standard"),
      arrival_time: (index - 1) * 70,
      duration_ms: if(critical?, do: 300, else: 180 + rem(index, 6) * 25),
      priority: if(critical?, do: 10, else: 2 + rem(index, 5)),
      deadline_ms: if(critical?, do: 520, else: 1_000)
    }
  end)

%{
  name: "heterogeneous_workers",
  description: "Workers have different processing capacities and explicit scheduling weights.",
  starvation_threshold_ms: 1_200,
  workers: [
    %{id: "worker_fast", speed: 1.8, weight: 4},
    %{id: "worker_standard", speed: 1.0, weight: 2},
    %{id: "worker_slow", speed: 0.6, weight: 1}
  ],
  events: events
}
