@echo off
setlocal
cd /d "%~dp0"
title OrdaX - Assinar primeira release
echo.
echo Esta etapa NAO copia a chave privada para o pacote.
echo Ela gera somente release-envelope.json a partir do manifesto verificado.
echo.
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp04-Sign-Initial-OrdaXRelease.ps1"
if errorlevel 1 (
  echo.
  echo ASSINATURA_INICIAL=FALHOU
  pause
  exit /b 1
)
echo.
echo ASSINATURA_INICIAL=CONCLUIDA
echo O release-envelope.json deve permanecer junto dos tres artefatos v4 exatos apos revisao.
echo Proximo passo: execute 5-Verify-PortableV4-SignedHandoff.cmd antes de qualquer publicacao/materializacao.
echo A chave privada NAO deve ser publicada.
echo.
pause
endlocal
