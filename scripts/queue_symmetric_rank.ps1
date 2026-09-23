$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $projectRoot

python -u scripts\build_ranked_basis_cache.py --resume
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

python -u scripts\run_symmetric_rank.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Output '[symmetric-rank] PIPELINE COMPLETE'
