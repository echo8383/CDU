$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$detectors = @('SubPCA','POLY','MOMENT_FT','MOMENT_ZS','M2N2','TranAD','TimesNet','FITS','AnomalyTransformer')
while ($true) {
    $symmetric = Test-Path (Join-Path $projectRoot 'protocol_basis_results\cap2048\drop_symmetric_rank\QUEUE_STATUS.json')
    $controls = Test-Path (Join-Path $projectRoot 'protocol_basis_results\cap2048\drop_symmetric_rank_controls\QUEUE_STATUS.json')
    $bridge = Test-Path (Join-Path $projectRoot 'protocol_basis_bridge\cap2048\QUEUE_STATUS.json')
    $decomposition = Test-Path (Join-Path $projectRoot 'protocol_score_decomposition\cap2048\QUEUE_STATUS.json')
    $vusComplete = 0
    foreach ($detectorName in $detectors) {
        if (Test-Path (Join-Path $projectRoot "protocol_score_decomposition\cap2048\vus\${detectorName}_SUMMARY.csv")) {
            $vusComplete++
        }
    }
    Write-Output "[$(Get-Date -Format s)] symmetric=$symmetric controls=$controls bridge=$bridge decomposition=$decomposition VUS=$vusComplete/9"
    if ($symmetric -and $controls -and $bridge -and $decomposition -and $vusComplete -eq 9) { break }
    Start-Sleep -Seconds 20
}
Set-Location -LiteralPath $projectRoot
python scripts\summarize_score_decomposition.py
exit $LASTEXITCODE
