param(
    [string]$InstancesDir = "results/raw/v1_qaoa_validation_instances",
    [string]$OutDir = "results/raw/v1_qaoa_validation",
    [string]$ElixirImageName = "quantum-inspired-event-scheduling-sim",
    [string]$QaoaImageName = "qaoa-validation",
    [int]$BatchSize = 3,
    [int]$Batches = 1,
    [string]$Reps = "1",
    [string]$Seeds = "7",
    [int]$Shots = 512,
    [int]$MaxIter = 25,
    [int]$MaxVariables = 9
)

$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$projectRoot = (Resolve-Path (Join-Path $repoRoot "code\event_scheduler_sim")).Path
$qaoaDockerfile = Join-Path $repoRoot "analysis\qaoa_validation\Dockerfile"

$scenarios = @(
    "scenarios/baseline.exs",
    "scenarios/steady_load.exs",
    "scenarios/burst_load.exs",
    "scenarios/critical_priority.exs",
    "scenarios/heterogeneous_workers.exs"
) -join ","

function Convert-ToContainerPath([string]$PathValue) {
    $normalized = $PathValue.Replace("\", "/").TrimStart(".").TrimStart("/")
    return "/workspace/$normalized"
}

$containerInstancesDir = Convert-ToContainerPath $InstancesDir
$containerOutDir = Convert-ToContainerPath $OutDir

docker build -t $ElixirImageName $projectRoot
docker run --rm -v "${repoRoot}:/workspace" -w /workspace/code/event_scheduler_sim $ElixirImageName mix deps.get
docker run --rm -v "${repoRoot}:/workspace" -w /workspace/code/event_scheduler_sim $ElixirImageName mix sim.qubo.export --scenarios $scenarios --profile sequencing --batch-size $BatchSize --batches $Batches --out $containerInstancesDir

docker build -t $QaoaImageName -f $qaoaDockerfile $repoRoot
docker run --rm -v "${repoRoot}:/workspace" -w /workspace $QaoaImageName python analysis/qaoa_validation/qaoa_validate_qubo.py --instances $containerInstancesDir --out $containerOutDir --reps $Reps --seeds $Seeds --shots $Shots --maxiter $MaxIter --max-variables $MaxVariables
