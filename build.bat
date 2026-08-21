@echo off
setlocal

echo ========================================
echo   MyDesktopClock Build Script
echo ========================================
echo.

REM ---- Check Python ----
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found. Please install Python 3.10+ and add to PATH.
    pause
    exit /b 1
)

REM ---- Install dependencies ----
echo [1/4] Installing PyQt6 ...
pip install "PyQt6>=6.5.0"
if errorlevel 1 (
    echo [ERROR] PyQt6 installation failed. Please check network or pip source.
    pause
    exit /b 1
)

echo [2/4] Installing PyInstaller ...
pip install "pyinstaller>=6.0"
if errorlevel 1 (
    echo [ERROR] PyInstaller installation failed.
    pause
    exit /b 1
)

REM ---- Clean old builds ----
echo [3/4] Cleaning old build artifacts ...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist MyDesktopClock.spec del /q MyDesktopClock.spec

REM ---- Build ----
echo [4/4] Building (may take 1-3 minutes) ...
pyinstaller --onefile --windowed --name DesktopClock --clean --noconfirm --icon=icon.ico clock.py
if errorlevel 1 (
    echo.
    echo [ERROR] Build failed. Please check error messages above.
    pause
    exit /b 1
)

echo.
echo ========================================
echo   Build successful!
echo   Output: dist\DesktopClock.exe
echo ========================================
echo.
echo Copy dist\DesktopClock.exe to any location to use.
echo First run may be scanned by Windows Defender - this is normal.
pause
