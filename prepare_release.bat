@echo off
setlocal

cd /d "%~dp0"

set RELEASE_DIR=release_bundle

if exist "%RELEASE_DIR%" rmdir /s /q "%RELEASE_DIR%"

mkdir "%RELEASE_DIR%"
mkdir "%RELEASE_DIR%\project"
mkdir "%RELEASE_DIR%\project\templates"
mkdir "%RELEASE_DIR%\offline_packages"
mkdir "%RELEASE_DIR%\installers"

echo Copying project files...
copy /y "project\bot.py" "%RELEASE_DIR%\project\" >nul 2>nul
copy /y "project\bot_safe.py" "%RELEASE_DIR%\project\" >nul 2>nul
copy /y "project\bot_search_only.py" "%RELEASE_DIR%\project\" >nul 2>nul
copy /y "project\check_env.py" "%RELEASE_DIR%\project\" >nul 2>nul
copy /y "project\check_mouse.py" "%RELEASE_DIR%\project\" >nul 2>nul
copy /y "project\check_region_ocr.py" "%RELEASE_DIR%\project\" >nul 2>nul
copy /y "project\make_screenshot.py" "%RELEASE_DIR%\project\" >nul 2>nul
copy /y "project\requirements-offline.txt" "%RELEASE_DIR%\project\" >nul 2>nul
copy /y "project\capture_templates_guide.txt" "%RELEASE_DIR%\project\" >nul 2>nul

echo Copying templates...
xcopy /e /i /y "project\templates" "%RELEASE_DIR%\project\templates" >nul

echo Copying offline packages...
xcopy /e /i /y "offline_packages" "%RELEASE_DIR%\offline_packages" >nul

echo Copying installers...
xcopy /e /i /y "installers" "%RELEASE_DIR%\installers" >nul

echo Copying batch files...
copy /y "install_offline.bat" "%RELEASE_DIR%\" >nul 2>nul
copy /y "run_bot.bat" "%RELEASE_DIR%\" >nul 2>nul

echo.
echo Release prepared in:
echo %cd%\%RELEASE_DIR%
echo.
pause