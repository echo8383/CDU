param([Parameter(Mandatory=$true)][int]$RunProcessId)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path $PSScriptRoot -Parent
Set-Location -LiteralPath $projectRoot
$python = (Get-Command python).Source
$run = Get-Process -Id $RunProcessId -ErrorAction SilentlyContinue
if ($run) {
    $cmd = (Get-CimInstance Win32_Process -Filter "ProcessId = $RunProcessId").CommandLine
    if ($cmd -notmatch 'run_protocol_fast.py') { throw 'Refusing to watch an unrelated process.' }
}
$previous = ''
do {
    $summaries = @('duplicate_Var-96','independent_noise','complementary_alpha_2') | ForEach-Object {
        Get-Item -LiteralPath "protocol_fast_results/main/$_/SUMMARY.csv" -ErrorAction SilentlyContinue
    }
    $state = ($summaries | ForEach-Object { $_.FullName + ':' + $_.LastWriteTimeUtc.Ticks }) -join '|'
    $alive = $run -and -not $run.HasExited
    if ($state -ne $previous -or -not $alive) {
        & $python scripts/sync_fast_controls_paper.py
        if ($LASTEXITCODE -ne 0) { throw 'Control validation failed; paper not updated.' }
        # Separate builds: failure to overwrite an open PDF must not stop experiments.
        foreach ($build in @('icassp/build.ps1','icassp/build_zh.ps1')) {
            & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $build
            Write-Output ("[{0}] build={1} exit={2}" -f (Get-Date -Format o),$build,$LASTEXITCODE)
        }
        $previous = $state
    }
    if ($alive) { Start-Sleep -Seconds 30 }
} while ($alive)
Write-Output 'Experiment process exited. Final available evidence synchronized; inspect PROGRESS.csv for completeness.'
