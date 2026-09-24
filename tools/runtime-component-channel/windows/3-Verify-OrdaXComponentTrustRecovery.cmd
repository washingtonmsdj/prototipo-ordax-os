@echo off
setlocal
if "%~1"=="" (
  echo Usage: %~nx0 ^<recovered-private-key-path^>
  exit /b 2
)
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0Complete-OrdaXComponentTrust.ps1" -RecoveredPrivateKeyPath "%~1"
exit /b %ERRORLEVEL%
