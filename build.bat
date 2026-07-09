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
echo [3/4] Building app folder with PyInstaller (onedir mode, not onefile)...
pyinstaller --windowed --icon=assets\icon.ico --add-data "assets;assets" --name HSSwitch --contents-directory HSSwitch_files main.py
if errorlevel 1 (
    echo.
    echo [FAILED] Build failed. Check the log above.
    pause
    exit /b 1
)

echo.
echo [4/4] Zipping dist\HSSwitch folder for distribution/auto-update...
if exist dist\HSSwitch.zip del /q dist\HSSwitch.zip
powershell -NoProfile -Command "Compress-Archive -Path 'dist\HSSwitch\*' -DestinationPath 'dist\HSSwitch.zip' -Force"
if errorlevel 1 (
    echo.
    echo [FAILED] Zip step failed.
    pause
    exit /b 1
)

echo.
echo ============================================
echo  Build complete: dist\HSSwitch\HSSwitch.exe
echo  Distribution zip:  dist\HSSwitch.zip
echo ============================================
pause
