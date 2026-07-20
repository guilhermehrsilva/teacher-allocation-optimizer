$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$VenvPython = Join-Path $Root ".venv\Scripts\python.exe"
$Python = if (Test-Path -LiteralPath $VenvPython) { $VenvPython } else { (Get-Command python -ErrorAction Stop).Source }
$env:PYTHONDONTWRITEBYTECODE = "1"

function Invoke-CheckedPython {
    param([Parameter(ValueFromRemainingArguments = $true)][string[]]$Arguments)
    & $Python @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Comando Python falhou com código ${LASTEXITCODE}: $($Arguments -join ' ')"
    }
}

Push-Location (Join-Path $Root "backend")
try { Invoke-CheckedPython -m unittest discover -s tests -p "test_*.py" -v } finally { Pop-Location }

Push-Location (Join-Path $Root "engines\primary")
try { Invoke-CheckedPython -m unittest discover -s tests -p "test_*.py" -v } finally { Pop-Location }

Push-Location (Join-Path $Root "engines\scenarios")
try { Invoke-CheckedPython -m unittest discover -s tests -p "test_*.py" -v } finally { Pop-Location }

Push-Location $Root
try { Invoke-CheckedPython -m unittest discover -s "scripts\tests" -p "test_*.py" -v } finally { Pop-Location }

Invoke-CheckedPython (Join-Path $Root "executar.py") --verificar
if (Test-Path -LiteralPath (Join-Path $Root "MANIFESTO_RELEASE.json")) {
    Invoke-CheckedPython (Join-Path $Root "scripts\integridade_release.py") --verificar
}
Write-Host "Todas as verificações automatizadas foram concluídas."
