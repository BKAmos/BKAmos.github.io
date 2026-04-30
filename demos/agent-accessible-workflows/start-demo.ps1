#Requires -Version 5.1
<#
  Start local demo stack for Track B packaging.
  - Creates src/.env from .env.example when missing
  - Generates API_TOKEN if placeholder is present
  - Starts docker compose services
#>
param(
    [switch]$EnableQueue,
    [int]$WorkerScale = 2
)

$ErrorActionPreference = "Stop"
$Root = $PSScriptRoot
$SrcDir = Join-Path $Root "src"
$EnvPath = Join-Path $SrcDir ".env"
$EnvExamplePath = Join-Path $SrcDir ".env.example"

function Read-DotEnv {
    param([string]$Path)
    $map = @{}
    if (-not (Test-Path -LiteralPath $Path)) { return $map }
    foreach ($line in [System.IO.File]::ReadAllLines($Path)) {
        $t = $line.Trim()
        if (-not $t -or $t.StartsWith("#")) { continue }
        $eq = $t.IndexOf("=")
        if ($eq -lt 1) { continue }
        $k = $t.Substring(0, $eq).Trim()
        $v = $t.Substring($eq + 1).Trim()
        $map[$k] = $v
    }
    return $map
}

function Upsert-EnvVar {
    param(
        [string]$Path,
        [string]$Key,
        [string]$Value
    )
    $lines = @()
    if (Test-Path -LiteralPath $Path) {
        $lines = [System.IO.File]::ReadAllLines($Path)
    }
    $found = $false
    for ($i = 0; $i -lt $lines.Count; $i++) {
        if ($lines[$i] -match "^\s*$([regex]::Escape($Key))=") {
            $lines[$i] = "$Key=$Value"
            $found = $true
        }
    }
    if (-not $found) {
        $lines += "$Key=$Value"
    }
    [System.IO.File]::WriteAllLines($Path, $lines)
}

if (-not (Test-Path -LiteralPath $EnvPath)) {
    if (-not (Test-Path -LiteralPath $EnvExamplePath)) {
        throw "Missing $EnvExamplePath"
    }
    Copy-Item -LiteralPath $EnvExamplePath -Destination $EnvPath
    Write-Host "Created $EnvPath from .env.example"
}

$envMap = Read-DotEnv -Path $EnvPath
$token = $envMap["API_TOKEN"]
if (-not $token -or $token -eq "change-me-to-a-long-random-secret" -or $token -eq "dev-token") {
    $token = -join ((48..57 + 65..90 + 97..122) | Get-Random -Count 48 | ForEach-Object { [char]$_ })
    Upsert-EnvVar -Path $EnvPath -Key "API_TOKEN" -Value $token
    Write-Host "Generated API_TOKEN in src/.env"
}

if ($EnableQueue) {
    Upsert-EnvVar -Path $EnvPath -Key "ENABLE_RQ" -Value "true"
} else {
    Upsert-EnvVar -Path $EnvPath -Key "ENABLE_RQ" -Value "false"
}

Push-Location $SrcDir
try {
    if ($EnableQueue) {
        docker compose --env-file .env up -d --build --scale "worker=$WorkerScale"
    } else {
        docker compose --env-file .env up -d --build
    }
    docker compose ps
}
finally {
    Pop-Location
}

Write-Host ""
Write-Host "Demo is up."
Write-Host "API health: http://localhost:8000/healthz"
Write-Host "Run smoke test: cd demos\agent-accessible-workflows\src; .\smoke-test.ps1"
Write-Host "Portfolio page (if Jekyll running): http://127.0.0.1:4000/portfolio/agent-accessible-workflows.html"
Write-Host "API_TOKEN (use for UI/CLI/gateway): $token"
