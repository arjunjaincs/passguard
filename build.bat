@echo off
echo ========================================
echo PassGuard - Build Executable
echo ========================================
echo.

REM Install PyInstaller if needed
python -c "import pyinstaller" 2>nul
if errorlevel 1 (
    echo Installing PyInstaller...
    pip install pyinstaller
    echo.
)

REM Build executable
echo Building PassGuard.exe...
echo.
pyinstaller --onefile --noconsole --name PassGuard --icon=assets/icon.ico main.py

if exist "dist\PassGuard.exe" (
    echo.
    echo ========================================
    echo SUCCESS! Build Complete!
    echo ========================================
    echo.
    echo Executable: dist\PassGuard.exe
    echo Size: 
    dir dist\PassGuard.exe | find "PassGuard.exe"
    echo.
    echo Ready to distribute!
    echo.
) else (
    echo.
    echo ========================================
    echo BUILD FAILED!
    echo ========================================
    echo.
)

pause
