#Requires -Version 5.1
<#
  Fire N concurrent POST /tools/run_deseq requests (synthetic dataset).
  Requires ENABLE_RQ=true in .env and multiple worker containers, e.g.:
    docker compose --env-file .env up -d --scale worker=4
#>
param(
    [int] $Count = 4,
    [string] $BaseUrl = "http://localhost:8000"
)

$ErrorActionPreference = "Stop"
$Root = $PSScriptRoot
$Fixture = Join-Path $Root (Join-Path "fixtures" "run-deseq-synthetic.json")

function Read-DotEnv {
    param([string]$Path)
    $map = @{}
    if (-not (Test-Path -LiteralPath $Path)) {
        throw "Missing $Path"
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

$envVars = Read-DotEnv (Join-Path $Root ".env")
$token = $envVars["API_TOKEN"]
if (-not $token) {
    throw "API_TOKEN missing in .env"
}
$rq = $envVars["ENABLE_RQ"]
if (-not $rq) { $rq = "" }
$rqNorm = $rq.Trim().ToLowerInvariant()
if ($rqNorm -ne "true" -and $rqNorm -ne "1" -and $rqNorm -ne "yes") {
    Write-Warning "ENABLE_RQ is not true in .env. Jobs run inline; set ENABLE_RQ=true and scale workers for queue parallelism."
}
if (-not (Test-Path -LiteralPath $Fixture)) {
    throw "Missing $Fixture"
}
$payload = Get-Content -LiteralPath $Fixture -Raw | ConvertFrom-Json
$payload.synthetic_profile = "large" # Force 10,000-gene run for queue stress runs.
$body = $payload | ConvertTo-Json -Depth 20

Write-Host "Submitting $Count jobs to $BaseUrl/tools/run_deseq ..."
$jobs = @( foreach ($i in 1..$Count) {
        Start-Job -Name "deseq-$i" -ScriptBlock {
            param($url, $json, $tok)
            $h = @{
                "Content-Type"  = "application/json"
                "Authorization" = "Bearer $tok"
            }
            try {
                Invoke-RestMethod -Uri "$url/tools/run_deseq" -Method Post -Headers $h -Body $json
            }
            catch {
                @{ error = $_.Exception.Message; inner = $_.ErrorDetails.Message }
            }
        } -ArgumentList $BaseUrl, $body, $token
    })

$jobs | Wait-Job | ForEach-Object {
    $n = $_.Name
    Write-Host "--- $n ---"
    Receive-Job $_
}
