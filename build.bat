@echo off
chcp 65001 >nul
setlocal

cd /d "%~dp0"

echo ================================
echo   MIS Bot - сборка релиза
echo ================================
echo.

echo [1/5] Проверка PyInstaller...
py -m PyInstaller --version >nul 2>nul
if errorlevel 1 (
    echo PyInstaller не найден. Устанавливаю...
    py -m pip install pyinstaller
    if errorlevel 1 (
        echo Ошибка установки PyInstaller
        pause
        exit /b 1
    )
)

echo [2/5] Очистка старой сборки...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist

echo [3/5] Сборка EXE...
py -m PyInstaller --clean mis_bot_beta.spec
if errorlevel 1 (
    echo Ошибка сборки EXE
    pause
    exit /b 1
)

echo [4/5] Копирование runtime-папок рядом с EXE...

if not exist "dist\MIS_Bot_Beta\config" mkdir "dist\MIS_Bot_Beta\config"
xcopy "config" "dist\MIS_Bot_Beta\config" /E /I /Y >nul

if exist "project\templates" (
    if not exist "dist\MIS_Bot_Beta\project\templates" mkdir "dist\MIS_Bot_Beta\project\templates"
    xcopy "project\templates" "dist\MIS_Bot_Beta\project\templates" /E /I /Y >nul
)

if exist "tesseract" (
    if not exist "dist\MIS_Bot_Beta\tesseract" mkdir "dist\MIS_Bot_Beta\tesseract"
    xcopy "tesseract" "dist\MIS_Bot_Beta\tesseract" /E /I /Y >nul
)

if not exist "dist\MIS_Bot_Beta\project\logs" mkdir "dist\MIS_Bot_Beta\project\logs"
if not exist "dist\MIS_Bot_Beta\config\runtime" mkdir "dist\MIS_Bot_Beta\config\runtime"

echo [5/5] Готово.
echo.
echo EXE:
echo %cd%\dist\MIS_Bot_Beta\MIS_Bot_Beta.exe
echo.

pause