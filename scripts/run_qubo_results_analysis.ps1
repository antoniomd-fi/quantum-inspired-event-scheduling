param(
    [string]$PythonCommand = "python"
)

$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$scriptPath = Join-Path $repoRoot "analysis\qubo_results_analysis.py"

& $PythonCommand $scriptPath
