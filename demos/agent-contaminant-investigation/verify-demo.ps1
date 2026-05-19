#Requires -Version 5.1
<#
  Verify local demo stack quickly.
  - API health check
  - synthetic run smoke test
  - optional queue check
#>
param(
    [switch]$CheckQueue
)

$ErrorActionPreference = "Stop"
$Root = $PSScriptRoot
$SrcDir = Join-Path $Root "src"

Push-Location $SrcDir
try {
    Write-Host "Checking API health..."
    $health = Invoke-RestMethod -Uri "http://localhost:8000/healthz" -Method Get
    if ($health.status -ne "ok") {
        throw "Health check failed: $($health | ConvertTo-Json -Depth 5)"
    }
    Write-Host "Health check passed."

    Write-Host "Running smoke-test.ps1..."
    & ".\smoke-test.ps1" | Out-Host
    if ($LASTEXITCODE -ne 0) {
        throw "smoke-test.ps1 failed."
    }
    Write-Host "Smoke test passed."

    if ($CheckQueue) {
        Write-Host "Checking queue behavior with parallel submit..."
        & ".\submit-parallel-jobs.ps1" -Count 2 | Out-Host
        if ($LASTEXITCODE -ne 0) {
            throw "submit-parallel-jobs.ps1 failed."
        }
        Write-Host "Queue check completed. Confirm responses show status=queued."
    }
}
finally {
    Pop-Location
}

Write-Host ""
Write-Host "Verification complete."
