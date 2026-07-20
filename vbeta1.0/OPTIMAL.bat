@echo off
title OPTIMAL - Ferramenta de Alocacao Docente v1.0
echo.
echo   ============================================
echo       OPTIMAL - Alocacao Docente v1.0
echo   ============================================
echo.
echo   Iniciando a aplicacao...
echo.
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0iniciar.ps1" %*
if %ERRORLEVEL% neq 0 (
    echo.
    echo   [ERRO] A aplicacao encerrou com codigo %ERRORLEVEL%.
    echo   Consulte docs\09_TROUBLESHOOTING.md para solucoes.
    echo.
    pause
)
