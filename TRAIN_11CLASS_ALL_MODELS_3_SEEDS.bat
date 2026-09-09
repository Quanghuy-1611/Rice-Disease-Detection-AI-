@echo off
setlocal
cd /d "%~dp0"

set "PYTHONUTF8=1"
"model_benchmark\.venv312\Scripts\python.exe" "model_benchmark\src\run_campaign_11class_continuous.py" --workers 2 --device cuda
set "exit_code=%errorlevel%"
echo.
if not "%exit_code%"=="0" echo Campaign stopped safely with exit code %exit_code%. Review the log before running this file again.
if "%exit_code%"=="0" echo All 6 models x 3 seeds completed successfully. Test sets remain unevaluated.
pause
exit /b %exit_code%
