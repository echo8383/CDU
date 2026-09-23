param(
    [int]$WaitForPid = 53556,
    [string]$PythonExe = '',
    [switch]$DryRun
)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path $PSScriptRoot -Parent
Set-Location -LiteralPath $projectRoot
if (-not $PythonExe) { $PythonExe = (Get-Command python -ErrorAction Stop).Source }
$runner = Join-Path $PSScriptRoot 'run_protocol_fast.py'
$baseline = Join-Path $projectRoot 'protocol_fast_results\shared_baseline\PER_SERIES.csv'
if (-not (Test-Path -LiteralPath $baseline)) { throw 'Shared baseline is missing.' }
$rows = @(Import-Csv -LiteralPath $baseline)
if ($rows.Count -ne 350 -or @($rows.series_id | Sort-Object -Unique).Count -ne 350) {
    throw 'Shared baseline must contain 350 unique series.'
}
$parentRun = Get-Process -Id $WaitForPid -ErrorAction SilentlyContinue
if ($parentRun) {
    $command = (Get-CimInstance Win32_Process -Filter "ProcessId = $WaitForPid").CommandLine
    if ($command -notmatch 'run_protocol_fast.py') { throw "PID $WaitForPid is not the Fast evaluator." }
}
Write-Output ('[{0}] Queue: wait for PID {1}; then duplicate -> noise -> alpha2' -f (Get-Date -Format o), $WaitForPid)
if ($DryRun) {
    Write-Output 'DRY RUN: baseline valid; no jobs started and no waiting performed.'
    exit 0
}
# Capture the existing process object, rather than waiting on a reusable PID later.
if ($parentRun) { $parentRun | Wait-Process -ErrorAction SilentlyContinue }
Write-Output ('[{0}] Previous evaluator exited. Existing detector outputs are preserved.' -f (Get-Date -Format o))
foreach ($detector in @('SubPCA', 'POLY', 'MOMENT_FT')) {
    $summary = Join-Path $projectRoot "protocol_fast_results\main\$detector\SUMMARY.csv"
    Write-Output ("Previous {0}: summary_present={1}" -f $detector, (Test-Path -LiteralPath $summary))
}
$failureCount = 0
foreach ($control in @('duplicate', 'noise', 'alpha2')) {
    Write-Output ('[{0}] START control {1}' -f (Get-Date -Format o), $control)
    # One process per control frees memory and lets the next job run after a failure.
    $ErrorActionPreference = 'Continue'
    & $PythonExe -u $runner --controls $control --resume --continue-on-error
    $controlExit = $LASTEXITCODE
    $ErrorActionPreference = 'Stop'
    if ($controlExit -ne 0) { $failureCount += 1 }
    Write-Output ('[{0}] END control {1}: exit={2}' -f (Get-Date -Format o), $control, $controlExit)
}
Write-Output ('[{0}] QUEUE COMPLETE failed_controls={1}' -f (Get-Date -Format o), $failureCount)
if ($failureCount -gt 0) { exit 1 }
exit 0
