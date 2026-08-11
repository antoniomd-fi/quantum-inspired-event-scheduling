param(
    [string]$Python = "python"
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
Push-Location $repoRoot

try {
    & $Python analysis\targeted_stress_analysis.py
}
finally {
    Pop-Location
}
