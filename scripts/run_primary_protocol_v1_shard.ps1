param(
    [int]$NoisePid = 0
)

$ErrorActionPreference = 'Stop'
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $ProjectRoot

if ($NoisePid -gt 0) {
    Write-Output "Waiting for independent-noise worker PID=$NoisePid"
    Wait-Process -Id $NoisePid -ErrorAction SilentlyContinue
}

$NoiseDir = Join-Path $ProjectRoot 'protocol_v1_results\controls\independent_noise\by_source'
$NoiseCount = (Get-ChildItem -LiteralPath $NoiseDir -Filter '*.json' -File -ErrorAction SilentlyContinue).Count
if ($NoiseCount -ne 23) {
    throw "Independent-noise control has $NoiseCount/23 source checkpoints; local complementary shard not started."
}

Write-Output 'Primary-machine complementary shard: alpha=0.25,1.0'
& python -u scripts\run_protocol_v1_complementary_shard.py --alphas 0.25 1
if ($LASTEXITCODE -ne 0) {
    throw "Primary complementary shard failed with exit code $LASTEXITCODE"
}
Write-Output 'PRIMARY PROTOCOL-V1 SHARD COMPLETE; waiting for collaborator results before acceptance.'
