param(
    [string]$Scenario = "scenarios/baseline.exs",
    [string]$Strategy = "round_robin",
    [string]$OutDir = "../../results/raw/baseline_round_robin",
    [string]$ImageName = "quantum-inspired-event-scheduling-sim"
)

$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$projectRoot = (Resolve-Path (Join-Path $repoRoot "code\event_scheduler_sim")).Path

docker build -t $ImageName $projectRoot
docker run --rm -v "${repoRoot}:/workspace" -w /workspace/code/event_scheduler_sim $ImageName mix deps.get
docker run --rm -v "${repoRoot}:/workspace" -w /workspace/code/event_scheduler_sim $ImageName mix sim.run --scenario $Scenario --strategy $Strategy --out $OutDir
