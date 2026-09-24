@echo off
setlocal
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0Initialize-OrdaXComponentTrust.ps1" -PreflightOnly
exit /b %ERRORLEVEL%
