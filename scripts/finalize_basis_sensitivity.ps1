$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$families = @(
    'variance', 'range', 'next_difference', 'centered_placement',
    'absolute_difference', 'mad', 'spectral_entropy'
)
$resultRoot = Join-Path $projectRoot 'protocol_basis_results\cap2048'
$logRoot = Join-Path $projectRoot 'protocol_basis_results\logs'

while ($true) {
    $complete = 0
    foreach ($familyName in $families) {
        $statusPath = Join-Path $resultRoot "drop_$familyName\QUEUE_STATUS.json"
        if (Test-Path -LiteralPath $statusPath) {
            $status = Get-Content -LiteralPath $statusPath -Raw | ConvertFrom-Json
            if ($status.status -eq 'COMPLETE') { $complete++ }
        }
    }
    Write-Output "[$(Get-Date -Format s)] completed=$complete/7"
    if ($complete -eq 7) { break }
    Start-Sleep -Seconds 30
}

python (Join-Path $PSScriptRoot 'summarize_basis_sensitivity.py') *>&1 |
    Tee-Object -FilePath (Join-Path $logRoot 'summary.log')
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Output "[$(Get-Date -Format s)] basis sensitivity summarized"
