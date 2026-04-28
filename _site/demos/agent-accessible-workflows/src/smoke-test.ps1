#Requires -Version 5.1
<#
  POST /tools/run_deseq using Invoke-RestMethod (avoids PowerShell/curl JSON quoting issues).
  Reads API_TOKEN from .env next to this script. Optional: $env:API_BASE_URL (default http://localhost:8000).
#>
$ErrorActionPreference = 'Stop'

$Root = $PSScriptRoot
$EnvFile = Join-Path $Root '.env'
$Fixture = Join-Path $Root (Join-Path 'fixtures' 'run-deseq-synthetic.json')
$BaseUrl = ($env:API_BASE_URL, 'http://localhost:8000' | Where-Object { $_ } | Select-Object -First 1).TrimEnd('/')

function Read-DotEnv {
    param([string]$Path)
    $map = @{}
    if (-not (Test-Path -LiteralPath $Path)) {
        throw "Missing $Path. Copy .env.example to .env and set API_TOKEN."
    }
    $raw = [System.IO.File]::ReadAllText($Path)
    if ($raw.Length -gt 0 -and [int][char]$raw[0] -eq 0xFEFF) {
        $raw = $raw.Substring(1)
    }
    foreach ($line in $raw -split "`r?`n") {
        $t = $line.Trim()
        if (-not $t -or $t[0] -eq [char]'#') { continue }
        $eq = $t.IndexOf('=')
        if ($eq -lt 1) { continue }
        $k = $t.Substring(0, $eq).Trim()
        $v = $t.Substring($eq + 1).Trim()
        $map[$k] = $v
    }
    $map
}

$envVars = Read-DotEnv -Path $EnvFile
$dmFlag = $envVars['DESEQ_DEMO_MODE']
if ([string]::IsNullOrWhiteSpace($dmFlag)) { $dmFlag = 'false' }
$demoMode = $dmFlag.ToLower() -eq 'true'
$token = $envVars['API_TOKEN']

if (-not $demoMode) {
    if (-not $token) {
        throw 'DESEQ_DEMO_MODE is not true and API_TOKEN is missing from .env'
    }
}

if (-not (Test-Path -LiteralPath $Fixture)) {
    throw "Missing fixture: $Fixture"
}

$body = [System.IO.File]::ReadAllText($Fixture, [System.Text.UTF8Encoding]::new($false)).Trim()
$headers = @{ 'Content-Type' = 'application/json' }
if (-not $demoMode) {
    $headers['Authorization'] = "Bearer $token"
}

Write-Host "POST $BaseUrl/tools/run_deseq"
$resp = Invoke-RestMethod -Uri "$BaseUrl/tools/run_deseq" -Method Post -Headers $headers -Body $body
$resp | ConvertTo-Json -Depth 12
$jobId = $resp.job_id

if ($resp.status -eq 'queued' -and $jobId) {
    Write-Host "`nPolling /jobs/$jobId ..."
    $pollHeaders = @{}
    if (-not $demoMode) { $pollHeaders['Authorization'] = "Bearer $token" }
    $deadline = (Get-Date).AddMinutes(15)
    while ((Get-Date) -lt $deadline) {
        $st = Invoke-RestMethod -Uri "$BaseUrl/jobs/$jobId" -Headers $pollHeaders
        Write-Host "Status: $($st.status)"
        if ($st.status -in 'completed', 'failed') {
            $st | ConvertTo-Json -Depth 12
            break
        }
        Start-Sleep -Seconds 2
    }
}
