#Requires -Version 5.1
<#
  Start the full local RNA-seq trust-and-DE learning loop.

  This launcher uses host uvicorn processes rather than Docker so the
  orchestrator and sub-agents can share demos/_shared_studies paths.
#>
param(
    [switch]$Install,
    [string]$Python = "python"
)

$ErrorActionPreference = "Stop"

$Root = $PSScriptRoot
$DemosRoot = Resolve-Path (Join-Path $Root "..")
$RepoRoot = Resolve-Path (Join-Path $Root "..\..")
$VenvDir = Join-Path $Root ".venv"
$VenvPython = Join-Path $VenvDir "Scripts\python.exe"

function Install-LoopDependencies {
    Write-Host "Installing shared learning-loop dependencies..."
    if (-not (Test-Path -LiteralPath $VenvPython)) {
        & $Python -m venv $VenvDir
    }
    & $VenvPython -m pip install --upgrade pip
    & $VenvPython -m pip install -r (Join-Path $DemosRoot "agent-accessible-workflows\requirements.txt")
    & $VenvPython -m pip install -r (Join-Path $DemosRoot "agent-contaminant-investigation\requirements.txt")
    & $VenvPython -m pip install -r (Join-Path $DemosRoot "repeatable-weekly-report\requirements-agent.txt")
    & $VenvPython -m pip install -r (Join-Path $Root "requirements.txt")
}

function Test-PythonModule {
    param([string]$Module)

    if (-not (Test-Path -LiteralPath $VenvPython)) {
        return $false
    }

    & $VenvPython -c "import $Module" *> $null
    return $LASTEXITCODE -eq 0
}

if ($Install -or -not (Test-Path -LiteralPath $VenvPython) -or -not (Test-PythonModule "redis") -or -not (Test-PythonModule "rq")) {
    Install-LoopDependencies
}

$PythonExe = if (Test-Path -LiteralPath $VenvPython) { $VenvPython } else { $Python }
$StudiesDir = Join-Path $DemosRoot "_shared_studies"

function Start-LoopService {
    param(
        [string]$Name,
        [string]$WorkingDirectory,
        [int]$Port,
        [hashtable]$Environment
    )

    $envLines = @("`$ErrorActionPreference = 'Stop'")
    foreach ($key in $Environment.Keys) {
        $value = [string]$Environment[$key]
        $envLines += "`$env:$key = '$($value.Replace("'", "''"))'"
    }
    $envLines += "& '$($PythonExe.Replace("'", "''"))' -m uvicorn api.main:app --port $Port"
    $command = $envLines -join "; "
    $encodedCommand = [Convert]::ToBase64String([Text.Encoding]::Unicode.GetBytes($command))

    Write-Host "Starting $Name on port $Port ..."
    Start-Process powershell -WorkingDirectory $WorkingDirectory -ArgumentList @(
        "-NoExit",
        "-ExecutionPolicy", "Bypass",
        "-EncodedCommand", $encodedCommand
    ) | Out-Null
}

Start-LoopService -Name "DESeq API" -WorkingDirectory (Join-Path $DemosRoot "agent-accessible-workflows\src") -Port 8000 -Environment @{
    PYTHONPATH = "."
    DESEQ_DEMO_MODE = "true"
}

Start-LoopService -Name "Contamination API" -WorkingDirectory (Join-Path $DemosRoot "agent-contaminant-investigation\src") -Port 8001 -Environment @{
    PYTHONPATH = "."
    CONTAM_DEMO_MODE = "true"
    ARTIFACT_STORAGE = "filesystem"
}

Start-LoopService -Name "Cycle report API" -WorkingDirectory (Join-Path $DemosRoot "repeatable-weekly-report\src") -Port 8002 -Environment @{
    PYTHONPATH = "."
    REPORT_DEMO_MODE = "true"
}

Start-LoopService -Name "Orchestrator API" -WorkingDirectory (Join-Path $Root "src") -Port 8003 -Environment @{
    PYTHONPATH = "."
    ORCHESTRATOR_DEMO_MODE = "true"
    DESEQ_API_BASE = "http://127.0.0.1:8000"
    CONTAM_API_BASE = "http://127.0.0.1:8001"
    REPORT_API_BASE = "http://127.0.0.1:8002"
    STUDIES_DIR = $StudiesDir
}

Write-Host ""
Write-Host "Learning loop services are starting in separate PowerShell windows."
Write-Host "Verify once the health checks are ready:"
Write-Host "  cd $Root"
Write-Host "  .\verify-demo.ps1"
