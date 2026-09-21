@echo off
setlocal
cd /d "%~dp0"
title OrdaX - Verificar toolkit de confianca
echo.
echo ============================================================
echo   OrdaX - Verificar toolkit de confianca
echo ============================================================
echo.
echo Este passo e SOMENTE LEITURA.
echo Nenhuma chave privada sera criada, alterada ou copiada.
echo Nenhum arquivo de revisao sera criado.
echo.
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0Initialize-OrdaXReleaseTrust.ps1" -PreflightOnly
if errorlevel 1 goto :error
echo.
echo TOOLKIT=ELEGIVEL
echo Proximo passo: 2-Initialize-OrdaXTrust.cmd
goto :end

:error
echo.
echo TOOLKIT=NAO_ELEGIVEL
echo Nao execute a cerimonia com este pacote.

:end
echo.
pause
endlocal
