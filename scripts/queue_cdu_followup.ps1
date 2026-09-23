param([ValidateSet('metric','seeds','basis')][string]$Track)
$ErrorActionPreference='Stop'
$projectRoot=Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $projectRoot
$failures=@()
if ($Track -eq 'metric') {
    foreach($kind in @('spline','linear','hgb')) {
        python -u scripts/run_cdu_followup.py --mode detector_only --probe $kind --resume
        if($LASTEXITCODE -ne 0){$failures+=$kind}
    }
} elseif($Track -eq 'seeds') {
    foreach($replicate in 1..4) {
        python -u scripts/run_cdu_followup.py --mode seed --probe spline --sample-seed $replicate --resume
        if($LASTEXITCODE -ne 0){$failures+="seed$replicate"}
    }
} else {
    foreach($family in @('variance','range','next_difference','centered_placement','absolute_difference','mad','spectral_entropy')) {
        python -u scripts/run_cdu_followup.py --mode basis --probe spline --drop-family $family --resume
        if($LASTEXITCODE -ne 0){$failures+=$family}
    }
}
if($failures.Count -gt 0){throw "Failed experiments: $($failures -join ', ')"}
Write-Output "[$Track] ALL COMPLETE"
