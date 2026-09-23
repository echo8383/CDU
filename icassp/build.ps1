param([ValidatePattern('^[a-zA-Z0-9_-]+$')][string]$JobName = 'main')
$ErrorActionPreference = 'Stop'
Push-Location $PSScriptRoot
try {
    & pdflatex "-jobname=$JobName" -interaction=nonstopmode -halt-on-error main.tex
    if ($LASTEXITCODE -ne 0) { throw 'First LaTeX pass failed' }
    & bibtex $JobName
    if ($LASTEXITCODE -ne 0) { throw 'BibTeX failed' }
    & pdflatex "-jobname=$JobName" -interaction=nonstopmode -halt-on-error main.tex
    if ($LASTEXITCODE -ne 0) { throw 'Second LaTeX pass failed' }
    & pdflatex "-jobname=$JobName" -interaction=nonstopmode -halt-on-error main.tex
    if ($LASTEXITCODE -ne 0) { throw 'Final LaTeX pass failed' }
} finally { Pop-Location }
