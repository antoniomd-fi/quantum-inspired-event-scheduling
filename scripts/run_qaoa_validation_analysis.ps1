param(
    [string]$Python = "python"
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
Push-Location $repoRoot

try {
    & $Python analysis\qaoa_validation_analysis.py
}
finally {
    Pop-Location
}
