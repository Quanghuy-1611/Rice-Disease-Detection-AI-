@echo off
chcp 65001 >nul
set "PORT=8015"
echo Kiem tra va giai phong cong %PORT% neu bi chiem...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :%PORT%') do (
    echo Tim thay tien trinh %%a dang su dung cong %PORT%...
    taskkill /F /PID %%a >nul 2>&1
)

cd /d "%~dp0backend"
if exist "%~dp0.venv\Scripts\python.exe" (
    "%~dp0.venv\Scripts\python.exe" -m uvicorn app.main:app --host 127.0.0.1 --port %PORT%
) else (
    python -m uvicorn app.main:app --host 127.0.0.1 --port %PORT%
)
pause
