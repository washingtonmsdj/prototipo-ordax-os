@echo off
setlocal
cd /d "%~dp0"
if "%~1"=="" exit /b 2
if "%~2"=="" exit /b 2
powershell.exe -NoProfile -File "%~dp06-Materialize-Verify-PortableV4-Canonical.ps1" -EnvelopeUrl "%~1" -ExpectedCommit "%~2"
exit /b %ERRORLEVEL%
