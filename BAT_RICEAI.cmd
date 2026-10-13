@echo off
title RiceAI - Start local server
echo Starting RiceAI. Please wait until both API and Web are ready.
echo Do not close this window while it is starting.
echo.
powershell.exe -NoProfile -ExecutionPolicy RemoteSigned -File "%~dp0scripts\start_riceai_demo.ps1"
if errorlevel 1 (
  echo.
  echo RiceAI could not start. Send a screenshot of this window for help.
) else (
  echo.
  echo RiceAI is running. You can close this window now.
)
echo.
pause
