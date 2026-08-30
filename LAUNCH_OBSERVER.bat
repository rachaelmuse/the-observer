@echo off
cd /d "%~dp0"
if not exist "data" mkdir data
if not exist "data\archive" mkdir data\archive
echo Stopping any previous Observer on 127.0.0.1:8730 ...
for /f "tokens=5" %%P in ('netstat -ano ^| findstr ":8730" ^| findstr "LISTENING"') do (
  taskkill /PID %%P /F >nul 2>&1
)
ping 127.0.0.1 -n 2 >nul
echo Starting The Observer at http://127.0.0.1:8730/
python -m uvicorn observer.api:app --host 127.0.0.1 --port 8730
