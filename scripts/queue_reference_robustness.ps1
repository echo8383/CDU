param(
    [ValidateSet('normalization','strength')]
    [string]$Experiment,
    [int]$Threads = 2
)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

$variants = if ($Experiment -eq 'normalization') {
    @('minmax', 'zscore_cdf')
} else {
    @('variance', 'variance_range', 'local_deviation', 'dispersion_change')
}

foreach ($variant in $variants) {
    Write-Host "[$Experiment/$variant] START"
    & python -u scripts/run_reference_robustness.py `
        --experiment $Experiment `
        --variant $variant `
        --training-cap 2048 `
        --threads $Threads `
        --resume
    if ($LASTEXITCODE -ne 0) {
        throw "$Experiment/$variant failed with exit code $LASTEXITCODE"
    }
    Write-Host "[$Experiment/$variant] COMPLETE"
}

& python scripts/summarize_reference_robustness.py
