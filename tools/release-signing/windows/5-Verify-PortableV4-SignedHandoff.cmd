@echo off
setlocal
cd /d "%~dp0"
title OrdaX - Verificar release Portable v4 assinada
echo.
echo Esta etapa verifica assinatura, manifesto e os tres artefatos v4 locais.
echo NAO publica, NAO ativa, NAO seleciona pendrive e NAO escreve midia fisica.
echo.
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp05-Verify-PortableV4-SignedHandoff.ps1"
if errorlevel 1 (
  echo.
  echo VERIFICACAO_PORTABLE_V4=FALHOU
  pause
  exit /b 1
)
echo.
echo VERIFICACAO_PORTABLE_V4=CONCLUIDA
echo Revise signed-handoff-verification.json antes da publicacao.
echo Depois da publicacao HTTPS revisada, execute 6-Materialize-Verify-PortableV4-Canonical.cmd.
echo.
pause
endlocal
