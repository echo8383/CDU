$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$decompStatus = Join-Path $projectRoot 'protocol_score_decomposition\cap2048\QUEUE_STATUS.json'
while (-not (Test-Path -LiteralPath $decompStatus)) {
    Write-Output "[$(Get-Date -Format s)] waiting for score decomposition"
    Start-Sleep -Seconds 20
}

$detectors = @('SubPCA','POLY','MOMENT_FT','MOMENT_ZS','M2N2','TranAD','TimesNet','FITS','AnomalyTransformer')
$logRoot = Join-Path $projectRoot 'protocol_score_decomposition\logs'
$processes = @()
foreach ($detectorName in $detectors) {
    $stdout = Join-Path $logRoot "vus_$detectorName.stdout.log"
    $stderr = Join-Path $logRoot "vus_$detectorName.stderr.log"
    $arguments = "-u scripts\compute_decomposition_vus.py --detector $detectorName --resume"
    $processes += Start-Process -FilePath python -ArgumentList $arguments -WorkingDirectory $projectRoot `
        -WindowStyle Hidden -RedirectStandardOutput $stdout -RedirectStandardError $stderr -PassThru
}
$processes | Wait-Process
$failed = @($processes | Where-Object { $_.ExitCode -ne 0 })
if ($failed.Count -gt 0) { throw "VUS workers failed: $($failed.Id -join ',')" }
Write-Output '[decomposition/VUS] ALL DETECTORS COMPLETE'
