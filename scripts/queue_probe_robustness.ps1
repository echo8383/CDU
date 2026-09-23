param(
    [Parameter(Mandatory=$true)][int]$WaitForPid,
    [int]$TrainingCap = 2048
)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path $PSScriptRoot -Parent
Set-Location -LiteralPath $projectRoot
$python = (Get-Command python).Source
$parentRun = Get-Process -Id $WaitForPid -ErrorAction SilentlyContinue
if ($parentRun) {
    $command = (Get-CimInstance Win32_Process -Filter "ProcessId = $WaitForPid").CommandLine
    if ($command -notmatch 'run_protocol_fast.py') { throw 'Wait target is not the control evaluator.' }
    Write-Output ('[{0}] WAIT controls PID={1}; next=HGB training-cap={2}' -f (Get-Date -Format o),$WaitForPid,$TrainingCap)
    $parentRun | Wait-Process -ErrorAction SilentlyContinue
}
$minimumGB = if ($TrainingCap -gt 0) { 3 } else { 12 }
do {
    $freeGB = (Get-CimInstance Win32_OperatingSystem).FreePhysicalMemory / 1MB
    if ($freeGB -lt $minimumGB) {
        Write-Output ('[{0}] WAIT memory available={1:N1}GB required={2}GB' -f (Get-Date -Format o),$freeGB,$minimumGB)
        Start-Sleep -Seconds 30
    }
} while ($freeGB -lt $minimumGB)
$other = @(Get-CimInstance Win32_Process | Where-Object {
    $_.Name -match '^python' -and $_.CommandLine -match 'run_probe_robustness.py'
})
if ($other.Count) { throw 'A robustness runner is already active; refusing duplicate.' }
Write-Output ('[{0}] START second-probe run' -f (Get-Date -Format o))
& $python -u scripts/run_probe_robustness.py --training-cap $TrainingCap --resume
$runExit = $LASTEXITCODE
& $python scripts/summarize_probe_robustness.py --training-cap $TrainingCap
Write-Output ('[{0}] END second-probe exit={1}' -f (Get-Date -Format o),$runExit)
exit $runExit
