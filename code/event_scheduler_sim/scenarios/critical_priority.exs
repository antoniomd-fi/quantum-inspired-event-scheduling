events =
  0..9
  |> Enum.flat_map(fn wave ->
    arrival_time = wave * 700

    standard_events =
      1..5
      |> Enum.map(fn offset ->
        index = wave * 7 + offset

        %{
          id: "event_#{String.pad_leading(Integer.to_string(index), 3, "0")}_standard",
          type: "standard",
          arrival_time: arrival_time,
          duration_ms: 210 + rem(index, 3) * 40,
          priority: 2 + rem(index, 3),
          deadline_ms: 1_100
        }
      end)

    critical_events =
      6..7
      |> Enum.map(fn offset ->
        index = wave * 7 + offset

        %{
          id: "event_#{String.pad_leading(Integer.to_string(index), 3, "0")}_critical",
          type: "critical",
          arrival_time: arrival_time,
          duration_ms: 260,
          priority: 10,
          deadline_ms: 420
        }
      end)

    standard_events ++ critical_events
  end)

%{
  name: "critical_priority",
  description:
    "Critical events share arrival windows with standard events and stricter deadlines.",
  starvation_threshold_ms: 1_000,
  workers: [
    %{id: "worker_a", speed: 1.0},
    %{id: "worker_b", speed: 1.0},
    %{id: "worker_c", speed: 1.0}
  ],
  events: events
}
