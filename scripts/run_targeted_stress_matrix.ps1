param(
    [string]$Profiles = "burst_critical,flooding_critical,heterogeneous_pressure,fairness_starvation",
    [string]$Loads = "high,overload",
    [string]$Seeds = "1..30",
    [string]$Strategies = "qubo_batch_exact,qubo_batch_exact_sequencing,priority_aware,deadline_aware_dispatch,shortest_queue,min_cost_greedy,duration_aware_dispatch",
    [string]$OutDir = "/workspace/results/raw/v3_targeted_stress_matrix",
    [string]$ImageName = "quantum-inspired-event-scheduling-sim"
)

$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$projectRoot = (Resolve-Path (Join-Path $repoRoot "code\event_scheduler_sim")).Path

docker build -t $ImageName $projectRoot
docker run --rm -v "${repoRoot}:/workspace" -w /workspace/code/event_scheduler_sim $ImageName mix deps.get
docker run --rm -v "${repoRoot}:/workspace" -w /workspace/code/event_scheduler_sim $ImageName mix sim.experiment --profiles $Profiles --loads $Loads --seeds $Seeds --strategies $Strategies --out $OutDir
