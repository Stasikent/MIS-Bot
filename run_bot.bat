@echo off
setlocal

cd /d "%~dp0project"

echo === Starting MIS bot ===
python bot.py

echo.
echo === Bot finished ===
pause