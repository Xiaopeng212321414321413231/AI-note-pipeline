@echo off
chcp 65001 >nul
cd /d "G:\ai软件\git\zhipu manage"
C:\Users\13312\AppData\Local\hermes\hermes-agent\venv\Scripts\python.exe src\main.py --watch >> logs\watcher.log 2>&1