#Requires -Version 5.1
<#
  Regenerate outputs for the 12 simple portfolio demos (not agent-accessible-workflows).
  Requires Python 3.11+ with demos/requirements.txt installed.
#>
$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
$DemosRoot = Join-Path $RepoRoot "demos"

$Slugs = @(
    "forecasting-uncertainty",
    "ab-testing-decisions",
    "segmentation-explainable",
    "margin-whatif",
    "multimodal-support-signals",
    "repeatable-weekly-report",
    "scientific-bioinformatics-de",
    "scientific-cheminformatics-similarity",
    "scientific-predictive-dose-response",
    "scientific-structural-contacts",
    "scientific-generative-sequences",
    "scientific-multimodal-biology"
)

function Get-Python {
    if ($env:PORTFOLIO_PYTHON) { return $env:PORTFOLIO_PYTHON }
    foreach ($cmd in @("python3", "python")) {
        try {
            $ver = & $cmd -c "import sys; print(sys.version_info[:2] >= (3, 11))" 2>$null
            if ($ver -eq "True") { return $cmd }
        } catch { }
    }
    throw "Python 3.11+ required. Set PORTFOLIO_PYTHON to your interpreter."
}

$Python = Get-Python
Write-Host "Using $Python"

foreach ($slug in $Slugs) {
    $dir = Join-Path $DemosRoot $slug
    Write-Host "=== $slug ==="
    Push-Location $dir
    & $Python data/generate.py
    if ($LASTEXITCODE -ne 0) { throw "generate failed: $slug" }
    & $Python src/run.py
    if ($LASTEXITCODE -ne 0) { throw "run failed: $slug" }
    Pop-Location
}

Write-Host "Done. Commit PNG/CSV files under demos/*/outputs/"
