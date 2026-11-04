@echo off
setlocal
cd /d "%~dp0"

echo =========================================================
echo  Audio Extractor - construction Windows autonome
 echo =========================================================
echo.
echo Requires: Windows 10/11, Python installed on THIS computer,
echo           internet connection for the first build.
echo Recipients do NOT need Python or FFmpeg.
echo.
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0build_windows.ps1"
if errorlevel 1 (
    echo.
    echo [ERROR] Build failed. Scroll up to see the error.
    pause
    exit /b 1
)
echo.
echo [OK] Build complete. See the RELEASE folder.
start "" "%~dp0RELEASE"
pause
