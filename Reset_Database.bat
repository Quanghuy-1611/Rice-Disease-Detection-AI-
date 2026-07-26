@echo off
chcp 65001 >nul
echo ===================================================
echo     CONG CU RESET DATABASE Nhanh (By Antigravity)
echo ===================================================
echo.
echo Dang xoa sach du lieu cu va tao tai khoan Admin...
echo.

cd /d "%~dp0\backend"
"C:\Users\Quang Huy\AppData\Local\Programs\Python\Python311\python.exe" -X utf8 reset_db.py

echo.
echo ===================================================
echo Hoan tat! Nhan phim bat ky de thoat...
pause >nul
