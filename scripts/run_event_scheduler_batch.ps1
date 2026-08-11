param(
    [string]$Scenarios = "",
    [string]$Strategies = "",
    [string]$OutDir = "../../results/raw/v1_classical_baselines",
    [string]$ImageName = "quantum-inspired-event-scheduling-sim"
)

$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$projectRoot = (Resolve-Path (Join-Path $repoRoot "code\event_scheduler_sim")).Path

$taskArgs = @("mix", "sim.batch", "--out", $OutDir)

if ($Scenarios -ne "") {
    $taskArgs += @("--scenarios", $Scenarios)
}

if ($Strategies -ne "") {
    $taskArgs += @("--strategies", $Strategies)
}

docker build -t $ImageName $projectRoot
docker run --rm -v "${repoRoot}:/workspace" -w /workspace/code/event_scheduler_sim $ImageName mix deps.get
docker run --rm -v "${repoRoot}:/workspace" -w /workspace/code/event_scheduler_sim $ImageName $taskArgs
