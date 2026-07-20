$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$VenvPython = Join-Path $Root ".venv\Scripts\python.exe"
$PythonCheck = "import struct,sys; ok=sys.version_info.releaselevel=='final' and sys.version_info[:2] in ((3,12),(3,13)) and struct.calcsize('P')*8==64; raise SystemExit(0 if ok else 1)"
$ApplicationArguments = @($args)

function Invoke-Application {
    param(
        [Parameter(Mandatory = $true)][string]$Command,
        [string[]]$Prefix = @()
    )
    & $Command @Prefix -c $PythonCheck 2>$null
    if ($LASTEXITCODE -ne 0) {
        return $false
    }
    & $Command @Prefix (Join-Path $Root "executar.py") @ApplicationArguments
    exit $LASTEXITCODE
}

if (Test-Path -LiteralPath $VenvPython) {
    Invoke-Application -Command $VenvPython
    throw "O ambiente .venv não usa Python 64 bits estável 3.12 ou 3.13. Execute scripts\instalar.ps1 após recriá-lo."
}

$Launcher = Get-Command py -ErrorAction SilentlyContinue
if ($Launcher) {
    foreach ($Version in @("-3.13", "-3.12")) {
        Invoke-Application -Command $Launcher.Source -Prefix @($Version)
    }
}

$Python = Get-Command python -ErrorAction SilentlyContinue
if ($Python) {
    Invoke-Application -Command $Python.Source
}

throw "Python 64 bits estável 3.12 ou 3.13 não encontrado. Execute scripts\instalar.ps1 antes de iniciar."
