events =
  0..7
  |> Enum.flat_map(fn burst_index ->
    burst_arrival = burst_index * 900

    1..8
    |> Enum.map(fn offset ->
      index = burst_index * 8 + offset
      critical? = offset in [7, 8]

      %{
        id: "event_#{String.pad_leading(Integer.to_string(index), 3, "0")}",
        type: if(critical?, do: "critical", else: "standard"),
        arrival_time: burst_arrival,
        duration_ms: if(critical?, do: 310, else: 170 + rem(index, 5) * 25),
        priority: if(critical?, do: 9 + rem(index, 2), else: 2 + rem(index, 4)),
        deadline_ms: if(critical?, do: 520, else: 1_200)
      }
    end)
  end)

%{
  name: "burst_load",
  description: "Events arrive in bursts to stress queueing and short-term backpressure.",
  starvation_threshold_ms: 1_100,
  workers: [
    %{id: "worker_a", speed: 1.0},
    %{id: "worker_b", speed: 1.1},
    %{id: "worker_c", speed: 0.9}
  ],
  events: events
}
