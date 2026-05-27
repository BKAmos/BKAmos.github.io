#Requires -Version 5.1
<#
  Verify orchestrator API against running sub-agents (or demo mode).
  Expects orchestrator on http://127.0.0.1:8003 by default.
#>
param(
    [int]$Port = 8003
)

$ErrorActionPreference = "Stop"
$Root = $PSScriptRoot
$SrcDir = Join-Path $Root "src"
$EnvPath = Join-Path $SrcDir ".env"
$Base = "http://127.0.0.1:$Port"

$headers = @{ "Content-Type" = "application/json" }
if (Test-Path $EnvPath) {
    $tokenLine = Select-String -Path $EnvPath -Pattern '^API_TOKEN=' | Select-Object -First 1
    if ($tokenLine) {
        $token = ($tokenLine.Line -replace '^API_TOKEN=', '').Trim()
        if ($token) {
            $headers["Authorization"] = "Bearer $token"
        }
    }
}

Write-Host "Checking orchestrator health at $Base ..."
$health = Invoke-RestMethod -Uri "$Base/healthz" -Method Get -Headers $headers
if ($health.status -ne "ok") {
    throw "Health check failed: $($health | ConvertTo-Json -Depth 5)"
}
Write-Host "Health check passed."

Write-Host "Starting trust-and-DE component (max 2 internal cycles)..."
$body = @{ max_internal_cycles = 2 } | ConvertTo-Json
$response = Invoke-RestMethod -Uri "$Base/tools/start_component" -Method Post -Headers $headers -Body $body
Write-Host ($response | ConvertTo-Json -Depth 8)

$action = $response.component_summary.parent_handoff.recommended_action
if (-not $action) {
    throw "Missing parent_handoff.recommended_action in response."
}
Write-Host "Handoff recommended_action=$action"

$studyId = $response.component_summary.study.study_id
if (-not $studyId) {
    throw "Missing component_summary.study.study_id in response."
}
Write-Host "Shared study_id=$studyId"

if ($response.component_run_id) {
    Write-Host "Fetching summary for $($response.component_run_id) ..."
    $summary = Invoke-RestMethod -Uri "$Base/components/$($response.component_run_id)/summary" -Method Get -Headers $headers
    Write-Host ($summary | ConvertTo-Json -Depth 6)
}

Write-Host "Verification complete."
