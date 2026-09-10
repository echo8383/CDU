param(
  [int]$WaitPid = 42052,
  [int]$PollSeconds = 15
)
$ErrorActionPreference = 'Continue'
$Root = Split-Path -Parent $PSScriptRoot
$L2 = Join-Path $Root 'layer2_results'
function Wait-ForPid([int]$Pid) {
  while (Get-Process -Id $Pid -ErrorAction SilentlyContinue) {
    Start-Sleep -Seconds $PollSeconds
  }
}
function Run-Cdu([string]$Detector) {
  $log = Join-Path $L2 ("{0}_offline_metrics.log" -f $Detector)
  $err = "$log.err"
  Write-Output ("[CDU-QUEUE] START {0} {1}" -f $Detector,(Get-Date))
  & python -u (Join-Path $PSScriptRoot 'offline_one_detector.py') --detector $Detector *> $log
  $code = $LASTEXITCODE
  Write-Output ("[CDU-QUEUE] END {0} exit={1} {2}" -f $Detector,$code,(Get-Date))
}
if ($WaitPid -gt 0) { Wait-ForPid $WaitPid }
Run-Cdu 'M2N2'
Run-Cdu 'TranAD'
Write-Output ("[CDU-QUEUE] COMPLETE {0}" -f (Get-Date))
