@echo off
chcp 65001 >nul
title AI笔记流水线 - 全栈启动器
echo ========================================
echo   AI笔记流水线 - 全栈启动
echo ========================================
echo.

:: 1. 启动 n8n（后台）
echo [1/3] 启动 n8n 自动化工作流...
start /B "" "C:\Users\13312\.workbuddy\binaries\node\versions\22.22.2\node.exe" ^
  "C:\Users\13312\.workbuddy\binaries\node\workspace\node_modules\n8n\bin\n8n" start > "%USERPROFILE%\n8n.log" 2>&1
timeout /t 10 /nobreak >nul

:: 2. 启动 Webhook 桥
echo [2/3] 启动 Webhook 桥（端口 9876）...
start /B "" "%USERPROFILE%\AppData\Roaming\uv\python\cpython-3.11-windows-x86_64-none\python.exe" ^
  "G:\ai软件\git\zhipu manage\src\webhook_bridge.py" > "%USERPROFILE%\bridge.log" 2>&1
timeout /t 2 /nobreak >nul

:: 3. 启动流水线 GUI
echo [3/3] 启动流水线 GUI...
start "" "G:\ai软件\git\zhipu manage\一键启动.bat"

echo.
echo ✅ 全部启动完成！
echo    n8n:       http://localhost:5678
echo    Webhook桥: http://127.0.0.1:9876/ping
echo    流水线GUI: 已打开
echo.
pause
