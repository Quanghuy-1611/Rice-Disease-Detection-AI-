@echo off
chcp 65001 >nul
title RiceAI Launcher
color 0A

echo ============================================
echo   RiceAI - He Thong Nhan Dien Benh Cay Lua
echo ============================================
echo.

echo Buoc 1: Khoi dong Backend AI Server...
start "BackendAI" "%~dp0start_backend.bat"
echo   Da khoi dong Backend tai http://localhost:8015
echo.

ping 127.0.0.1 -n 4 >nul

echo Buoc 2: Khoi dong Frontend Web...
start "FrontendWeb" "%~dp0start_frontend.bat"
echo   Da khoi dong Frontend tai http://localhost:5173
echo.

ping 127.0.0.1 -n 3 >nul

echo ============================================
echo   KHOI DONG THANH CONG!
echo ============================================
echo.
echo   Truy cap: http://localhost:5173
echo   Dang nhap bang email da xac minh de mo khu vuc quan tri.
echo ============================================

ping 127.0.0.1 -n 3 >nul
start http://localhost:5173

pause
