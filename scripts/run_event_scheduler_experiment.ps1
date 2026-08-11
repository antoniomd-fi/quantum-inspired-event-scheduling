param(
    [string]$Profiles = "",
    [string]$Loads = "",
    [string]$Seeds = "1..5",
    [string]$Strategies = "",
    [string]$OutDir = "../../results/raw/v1_experimental_matrix",
    [string]$ImageName = "quantum-inspired-event-scheduling-sim"
)

$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$projectRoot = (Resolve-Path (Join-Path $repoRoot "code\event_scheduler_sim")).Path

$taskArgs = @("mix", "sim.experiment", "--seeds", $Seeds, "--out", $OutDir)

if ($Profiles -ne "") {
    $taskArgs += @("--profiles", $Profiles)
}

if ($Loads -ne "") {
    $taskArgs += @("--loads", $Loads)
}

if ($Strategies -ne "") {
    $taskArgs += @("--strategies", $Strategies)
}

docker build -t $ImageName $projectRoot
docker run --rm -v "${repoRoot}:/workspace" -w /workspace/code/event_scheduler_sim $ImageName mix deps.get
docker run --rm -v "${repoRoot}:/workspace" -w /workspace/code/event_scheduler_sim $ImageName $taskArgs
