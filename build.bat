@echo off
setlocal

echo ============================================
echo  HSSwitch Build
echo ============================================

echo.
echo [1/3] Cleaning previous build output...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist HSSwitch.spec del /q HSSwitch.spec

echo.
echo [2/3] Installing dependencies...
pip install -r requirements.txt
if errorlevel 1 (
    echo.
    echo [FAILED] Could not install dependencies.
    pause
    exit /b 1
)

echo.
echo [3/3] Building exe with PyInstaller...
pyinstaller --onefile --windowed --icon=assets\icon.ico --name HSSwitch main.py
if errorlevel 1 (
    echo.
    echo [FAILED] Build failed. Check the log above.
    pause
    exit /b 1
)

echo.
echo ============================================
echo  Build complete: dist\HSSwitch.exe
echo ============================================
pause
