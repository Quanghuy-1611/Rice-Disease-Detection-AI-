@echo off
setlocal
cd /d "%~dp0"

if "%~1"=="" (
  echo Usage: TRAIN_11CLASS_3_SEEDS.bat MODEL
  echo Models: mobilenetv2 mobilenetv3large resnet18 efficientnetb0 shufflenetv2_1_0x densenet121
  exit /b 2
)

"model_benchmark\.venv312\Scripts\python.exe" "model_benchmark\src\run_model_3seeds_11class.py" --model "%~1" --workers 2 --device cuda
set "exit_code=%errorlevel%"
echo.
if not "%exit_code%"=="0" echo Training stopped with exit code %exit_code%.
if "%exit_code%"=="0" echo All configured seeds completed successfully.
pause
exit /b %exit_code%
