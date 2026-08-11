critical_every = 5

events =
  1..36
  |> Enum.map(fn index ->
    critical? = rem(index, critical_every) == 0

    %{
      id: "event_#{String.pad_leading(Integer.to_string(index), 3, "0")}",
      type: if(critical?, do: "critical", else: "standard"),
      arrival_time: (index - 1) * 80,
      duration_ms: if(critical?, do: 260, else: 140 + rem(index, 4) * 30),
      priority: if(critical?, do: 10, else: 2 + rem(index, 3)),
      deadline_ms: if(critical?, do: 450, else: 900)
    }
  end)

%{
  name: "baseline_small",
  description: "Small deterministic scenario for initial scheduling validation.",
  starvation_threshold_ms: 900,
  workers: [
    %{id: "worker_a", speed: 1.0},
    %{id: "worker_b", speed: 1.2},
    %{id: "worker_c", speed: 0.8}
  ],
  events: events
}
