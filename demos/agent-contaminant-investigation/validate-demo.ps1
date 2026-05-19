#Requires -Version 5.1
<#
  Run focused validation without requiring the local API stack:
  - Python unit/API tests for scoring and status flow
  - Cloudflare gateway TypeScript typecheck
#>
param(
    [switch]$SkipGatewayInstall
)

$ErrorActionPreference = "Stop"
$Root = $PSScriptRoot
$GatewayDir = Join-Path $Root "src\gateway"

Push-Location $Root
try {
    Write-Host "Running Python validation tests..."
    python -m pytest tests
    if ($LASTEXITCODE -ne 0) {
        throw "Python validation tests failed."
    }
}
finally {
    Pop-Location
}

Push-Location $GatewayDir
try {
    if (-not $SkipGatewayInstall -and -not (Test-Path -LiteralPath "node_modules")) {
        Write-Host "Installing gateway dependencies with npm ci..."
        npm ci
        if ($LASTEXITCODE -ne 0) {
            throw "npm ci failed."
        }
    }

    Write-Host "Running gateway typecheck..."
    npm run typecheck
    if ($LASTEXITCODE -ne 0) {
        throw "Gateway typecheck failed."
    }
}
finally {
    Pop-Location
}

Write-Host ""
Write-Host "Validation complete."
