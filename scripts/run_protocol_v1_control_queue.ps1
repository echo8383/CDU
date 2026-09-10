param(
    [int]$BaselinePid = 0
)

$ErrorActionPreference = 'Stop'
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $ProjectRoot

function Invoke-CheckedPython {
    param([string[]]$Arguments)
    & python -u @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Python command failed ($LASTEXITCODE): python $($Arguments -join ' ')"
    }
}

if ($BaselinePid -gt 0) {
    Write-Output "Waiting for formal baseline PID=$BaselinePid"
    Wait-Process -Id $BaselinePid -ErrorAction SilentlyContinue
}

$baselineFile = Join-Path $ProjectRoot 'protocol_v1_results\controls\shared_baseline\BASELINE_PER_SERIES.csv'
if (-not (Test-Path -LiteralPath $baselineFile)) {
    throw 'Formal baseline did not complete; control queue stopped.'
}
$baselineRows = (Import-Csv -LiteralPath $baselineFile).Count
if ($baselineRows -ne 350) {
    throw "Formal baseline has $baselineRows rows instead of 350; control queue stopped."
}

Write-Output 'Phase A2: exact duplicate and independent noise'
Invoke-CheckedPython @('scripts\run_protocol_v1_controls.py', '--phase', 'negative')

Write-Output 'Phase A3: complementary alpha grid'
Invoke-CheckedPython @('scripts\run_protocol_v1_controls.py', '--phase', 'complementary')

Write-Output 'Phase A4: clean-vs-resume regression'
Invoke-CheckedPython @('scripts\verify_protocol_v1_resume_clean.py')

Write-Output 'Phase A5: formal acceptance audit'
Invoke-CheckedPython @('scripts\run_protocol_v1_controls.py', '--phase', 'audit')

Write-Output 'FORMAL CONTROL QUEUE COMPLETE'
