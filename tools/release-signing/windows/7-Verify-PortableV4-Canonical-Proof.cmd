@echo off
setlocal
cd /d "%~dp0"
if "%~1"=="" exit /b 2
powershell.exe -NoProfile -File "%~dp07-Verify-PortableV4-Canonical-Proof.ps1" -ExpectedCommit "%~1"
exit /b %ERRORLEVEL%
