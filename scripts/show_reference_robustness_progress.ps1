$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

$spec = @{
    'normalization/minmax' = 9 * 23
    'normalization/zscore_cdf' = 9 * 23
    'strength/variance' = 10 * 23
    'strength/variance_range' = 10 * 23
    'strength/local_deviation' = 10 * 23
    'strength/dispersion_change' = 10 * 23
}

foreach ($name in $spec.Keys) {
    $parts = $name.Split('/')
    $path = Join-Path 'protocol_reference_robustness' (Join-Path $parts[0] (Join-Path 'cap2048' $parts[1]))
    $done = @(Get-ChildItem -LiteralPath $path -Recurse -Filter '*.csv' -ErrorAction SilentlyContinue |
        Where-Object { $_.DirectoryName -like '*by_source' }).Count
    $total = $spec[$name]
    $state = if ($done -eq $total) { 'COMPLETE' } elseif ($done -gt 0) { 'RUNNING' } else { 'PENDING' }
    '{0,-38} {1,4}/{2,-4} {3}' -f $name, $done, $total, $state
}

Write-Host "`n--- normalization log ---"
Get-Content protocol_reference_robustness/logs/normalization.log -Tail 8 -ErrorAction SilentlyContinue
Write-Host "`n--- strength log ---"
Get-Content protocol_reference_robustness/logs/strength.log -Tail 8 -ErrorAction SilentlyContinue
