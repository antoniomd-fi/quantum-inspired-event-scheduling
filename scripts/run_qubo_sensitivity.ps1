param(
    [string]$OutDir = "../../results/raw/v1_qubo_sensitivity",
    [string]$ImageName = "quantum-inspired-event-scheduling-sim"
)

$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$projectRoot = (Resolve-Path (Join-Path $repoRoot "code\event_scheduler_sim")).Path

$scenarios = @(
    "scenarios/baseline.exs",
    "scenarios/steady_load.exs",
    "scenarios/burst_load.exs",
    "scenarios/critical_priority.exs",
    "scenarios/heterogeneous_workers.exs"
) -join ","

$strategies = @(
    "qubo_batch_exact",
    "qubo_batch_exact_deadline_focused",
    "qubo_batch_exact_critical_focused",
    "qubo_batch_exact_low_balance",
    "priority_aware",
    "shortest_queue"
) -join ","

docker build -t $ImageName $projectRoot
docker run --rm -v "${repoRoot}:/workspace" -w /workspace/code/event_scheduler_sim $ImageName mix deps.get
docker run --rm -v "${repoRoot}:/workspace" -w /workspace/code/event_scheduler_sim $ImageName mix sim.batch --scenarios $scenarios --strategies $strategies --out $OutDir
