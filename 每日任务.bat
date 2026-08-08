@echo off
chcp 65001 >nul
title AI 每日笔记任务 v2.7

echo ========================================
echo   AI 每日笔记任务 --daily
echo   1. 扫描 RSS 源
echo   2. 下载队列文章
echo   3. 处理本地 input 文件
echo ========================================

REM 自动定位项目目录（%~dp0 = 本 bat 所在目录，任何机器可用）
pushd "%~dp0" || (
  echo [ERROR] Cannot locate project directory!
  pause
  exit /b 1
)

set "PYTHONPATH=%CD%;%CD%\src"

python src\main.py --daily

echo.
echo ========================================
echo   Daily task completed
echo ========================================
pause
