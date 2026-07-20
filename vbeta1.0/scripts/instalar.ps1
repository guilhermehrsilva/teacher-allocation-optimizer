$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$Venv = Join-Path $Root ".venv"
$VenvPython = Join-Path $Venv "Scripts\python.exe"
$LockFile = Join-Path $Root "requirements.lock"
$PythonCheck = "import struct,sys; ok=sys.version_info.releaselevel=='final' and sys.version_info[:2] in ((3,12),(3,13)) and struct.calcsize('P')*8==64; raise SystemExit(0 if ok else 1)"

function Assert-NativeSuccess {
    param([Parameter(Mandatory = $true)][string]$Action)
    if ($LASTEXITCODE -ne 0) {
        throw "$Action falhou com código $LASTEXITCODE."
    }
}

function Test-SupportedPython {
    param(
        [Parameter(Mandatory = $true)][string]$Command,
        [string[]]$Prefix = @()
    )
    & $Command @Prefix -c $PythonCheck 2>$null
    return $LASTEXITCODE -eq 0
}

if (-not (Test-Path -LiteralPath $LockFile)) {
    throw "Arquivo de dependências travadas ausente: $LockFile"
}

if (-not (Test-Path -LiteralPath $VenvPython)) {
    $Launcher = Get-Command py -ErrorAction SilentlyContinue
    $Created = $false
    if ($Launcher) {
        foreach ($Version in @("-3.13", "-3.12")) {
            if (Test-SupportedPython -Command $Launcher.Source -Prefix @($Version)) {
                Write-Host "Criando ambiente virtual com Python $Version."
                & $Launcher.Source $Version -m venv $Venv
                Assert-NativeSuccess "Criação do ambiente virtual"
                $Created = $true
                break
            }
        }
    }
    if (-not $Created) {
        $Python = Get-Command python -ErrorAction SilentlyContinue
        if (-not $Python -or -not (Test-SupportedPython -Command $Python.Source)) {
            throw "Python 64 bits estável 3.12 ou 3.13 não encontrado. Instale uma versão homologada e execute novamente."
        }
        Write-Host "Criando ambiente virtual com $($Python.Source)."
        & $Python.Source -m venv $Venv
        Assert-NativeSuccess "Criação do ambiente virtual"
    }
}

if (-not (Test-SupportedPython -Command $VenvPython)) {
    throw "O ambiente .venv existente não usa Python 64 bits estável 3.12 ou 3.13. Recrie-o com uma versão homologada."
}

$PipModule = Join-Path $Venv "Lib\site-packages\pip\__init__.py"
if (-not (Test-Path -LiteralPath $PipModule)) {
    & $VenvPython -m ensurepip --upgrade
    Assert-NativeSuccess "Inicialização do pip"
}
& $VenvPython -m pip install --disable-pip-version-check --require-hashes -r $LockFile
Assert-NativeSuccess "Instalação das dependências"
& $VenvPython (Join-Path $Root "executar.py") --verificar
Assert-NativeSuccess "Verificação do pacote"

Write-Host "Instalação concluída. Use iniciar.ps1 para abrir a aplicação."
