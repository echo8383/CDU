param(
  [string]$Detectors = 'SubPCA,AnomalyTransformer,TimesNet,MOMENT_ZS,MOMENT_FT',
  [int]$Seed = 2024
)
$Root = Split-Path -Parent $PSScriptRoot
$DetectorList = $Detectors -split ',' | ForEach-Object { $_.Trim() } | Where-Object { $_ }
foreach ($Detector in $DetectorList) {
  Write-Host "`n========== START $Detector ==========" -ForegroundColor Cyan
  & python "$PSScriptRoot\run_detector_smoke.py" --detector $Detector --seed $Seed
  $SmokeExit = $LASTEXITCODE
  if ($SmokeExit -ne 0) {
    Write-Warning "========== $Detector SMOKE FAILED (exit=$SmokeExit); continuing next detector =========="
    continue
  }
  & python "$PSScriptRoot\run_detector_sweep.py" --detector $Detector --seed $Seed
  $Exit = $LASTEXITCODE
  if ($Exit -eq 0) { Write-Host "========== COMPLETE $Detector ==========" -ForegroundColor Green }
  else { Write-Warning "========== $Detector FINISHED WITH FAILURES (exit=$Exit); continuing next detector ==========" }
}
