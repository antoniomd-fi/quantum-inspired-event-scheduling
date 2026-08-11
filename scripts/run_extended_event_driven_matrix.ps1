param(
    [string]$Profiles = "burst,saturation,critical_heavy,heterogeneous",
    [string]$Loads = "medium,high,overload",
    [string]$Seeds = "1..10",
    [string]$Strategies = "qubo_batch_exact,qubo_batch_exact_sequencing,priority_aware,shortest_queue,min_cost_greedy",
    [string]$OutDir = "/workspace/results/raw/v2_extended_event_driven_matrix",
    [string]$ImageName = "quantum-inspired-event-scheduling-sim"
)

$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$projectRoot = (Resolve-Path (Join-Path $repoRoot "code\event_scheduler_sim")).Path

docker build -t $ImageName $projectRoot
docker run --rm -v "${repoRoot}:/workspace" -w /workspace/code/event_scheduler_sim $ImageName mix deps.get
docker run --rm -v "${repoRoot}:/workspace" -w /workspace/code/event_scheduler_sim $ImageName mix sim.experiment --profiles $Profiles --loads $Loads --seeds $Seeds --strategies $Strategies --out $OutDir
