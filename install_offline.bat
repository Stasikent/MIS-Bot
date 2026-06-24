@echo off
setlocal

cd /d "%~dp0"

echo === Offline install started ===

python -m pip install --no-index --find-links="%~dp0offline_packages" pip setuptools wheel
if errorlevel 1 (
  echo ERROR: Failed to install pip/setuptools/wheel
  pause
  exit /b 1
)

python -m pip install --no-index --find-links="%~dp0offline_packages" -r "%~dp0project\requirements-offline.txt"
if errorlevel 1 (
  echo ERROR: Offline package install failed
  pause
  exit /b 1
)

echo === Offline install finished successfully ===
pause