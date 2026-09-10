param(
    [Parameter(Mandatory=$true)]
    [string]$Destination
)

$ErrorActionPreference = 'Stop'
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$ResolvedProject = (Resolve-Path -LiteralPath $ProjectRoot).Path
$Target = [System.IO.Path]::GetFullPath($Destination)

if ($Target.StartsWith($ResolvedProject, [System.StringComparison]::OrdinalIgnoreCase)) {
    throw 'Destination must be outside the project repository.'
}
if (Test-Path -LiteralPath $Target) {
    throw "Destination already exists; choose a new empty path: $Target"
}

$BasisSource = Join-Path $ProjectRoot 'layer2_results\basis_scores'
$ControlsSource = Join-Path $ProjectRoot 'protocol_v1_results\controls'
$Required = @(
    $BasisSource,
    (Join-Path $ControlsSource 'shared_baseline'),
    (Join-Path $ControlsSource 'FOLD_AUDIT.csv'),
    (Join-Path $ControlsSource 'SPLIT_MANIFEST.json'),
    (Join-Path $ControlsSource 'RUN_SIGNATURE.json')
)
foreach ($Path in $Required) {
    if (-not (Test-Path -LiteralPath $Path)) { throw "Required asset missing: $Path" }
}

New-Item -ItemType Directory -Path (Join-Path $Target 'layer2_results\basis_scores') -Force | Out-Null
New-Item -ItemType Directory -Path (Join-Path $Target 'protocol_v1_results\controls') -Force | Out-Null
Copy-Item -Path (Join-Path $BasisSource '*') -Destination (Join-Path $Target 'layer2_results\basis_scores') -Recurse
Copy-Item -LiteralPath (Join-Path $ControlsSource 'shared_baseline') -Destination (Join-Path $Target 'protocol_v1_results\controls') -Recurse
Copy-Item -LiteralPath (Join-Path $ControlsSource 'FOLD_AUDIT.csv') -Destination (Join-Path $Target 'protocol_v1_results\controls')
Copy-Item -LiteralPath (Join-Path $ControlsSource 'SPLIT_MANIFEST.json') -Destination (Join-Path $Target 'protocol_v1_results\controls')
Copy-Item -LiteralPath (Join-Path $ControlsSource 'RUN_SIGNATURE.json') -Destination (Join-Path $Target 'protocol_v1_results\controls')

$BasisCount = (Get-ChildItem -LiteralPath (Join-Path $Target 'layer2_results\basis_scores') -Filter '*.npz' -File).Count
if ($BasisCount -ne 350) { throw "Exported basis count is $BasisCount instead of 350" }
Write-Output "COLLABORATOR ASSET EXPORT COMPLETE: $Target"
Write-Output "Basis cache: $BasisCount files (approximately 1.7 GB)"
