@echo off
chcp 65001 >nul
title AI Note Pipeline v2.7

echo ========================================
echo   AI Multi-Modal Note Pipeline v2.7
echo   Starting GUI ...
echo ========================================

REM 自动定位项目目录（%~dp0 = 本 bat 所在目录，任何机器可用）
pushd "%~dp0" || (
  echo [ERROR] Cannot locate project directory!
  pause
  exit /b 1
)

set "PYTHONPATH=%CD%;%CD%\src"

REM 优先使用 Hermes venv Python，否则系统 Python
set "PY=%LOCALAPPDATA%\hermes\hermes-agent\venv\Scripts\python.exe"
if exist "%PY%" (
  "%PY%" src\gui.py
) else (
  echo [WARN] Hermes Python not found, trying system Python...
  python src\gui.py
)

echo.
echo Pipeline exited. Press any key to close...
pause >nul
