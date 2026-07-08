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
echo [3/4] Building app folder with PyInstaller (onedir)...
rem --onefile를 쓰지 않는다: 실행할 때마다 임시 폴더에 압축을 풀었다가 지우는
rem 방식이 백신 실시간 검사와 자꾸 충돌해서 "Failed to load Python DLL" 류의
rem 오류가 반복됐다. onedir는 압축 해제 과정 자체가 없어서 이 문제가 구조적으로 없어진다.
pyinstaller --windowed --icon=assets\icon.ico --name HSSwitch main.py
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
