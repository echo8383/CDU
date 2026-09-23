$ErrorActionPreference = 'Stop'
Push-Location $PSScriptRoot
try {
    & xelatex -interaction=nonstopmode -halt-on-error main_zh.tex
    if ($LASTEXITCODE -ne 0) { throw 'Chinese XeLaTeX pass failed' }
    & bibtex main_zh
    if ($LASTEXITCODE -ne 0) { throw 'Chinese bibliography pass failed' }
    1..2 | ForEach-Object {
        & xelatex -interaction=nonstopmode -halt-on-error main_zh.tex
        if ($LASTEXITCODE -ne 0) { throw 'Chinese XeLaTeX pass failed' }
    }
} finally {
    Pop-Location
}
