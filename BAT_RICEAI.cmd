@echo off
title RiceAI - Start local server
powershell.exe -NoProfile -ExecutionPolicy RemoteSigned -File "%~dp0scripts\start_riceai_demo.ps1"
if errorlevel 1 (
  echo.
  echo RiceAI could not start. Send a screenshot of this window for help.
)
echo.
pause
