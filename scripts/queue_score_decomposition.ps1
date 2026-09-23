$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$rankManifest = Join-Path $projectRoot 'layer2_results\basis_scores_ranked\MANIFEST.json'
while (-not (Test-Path -LiteralPath $rankManifest)) {
    Write-Output "[$(Get-Date -Format s)] waiting for ranked basis cache"
    Start-Sleep -Seconds 15
}
Set-Location -LiteralPath $projectRoot
python -u scripts\run_score_decomposition.py
exit $LASTEXITCODE
