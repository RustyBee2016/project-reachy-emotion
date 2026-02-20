@echo off
REM Web UI Test Runner for Windows
REM Run from project root: tests\run_web_ui_tests.bat

echo ============================================
echo Reachy Emotion - Web UI Test Suite
echo ============================================

REM Check if pytest is available
python -m pytest --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: pytest not found. Install with: pip install pytest
    exit /b 1
)

echo.
echo Available test modes:
echo   1. Offline (mock tests only)
echo   2. Integration (requires Ubuntu machines online)
echo   3. Full E2E (all tests)
echo.

set /p MODE="Select mode [1/2/3]: "

if "%MODE%"=="1" (
    echo Running offline tests...
    python -m pytest tests/test_web_ui.py -v --offline -m "not integration and not e2e"
) else if "%MODE%"=="2" (
    echo Running integration tests...
    python -m pytest tests/test_web_ui.py -v -m "integration"
) else if "%MODE%"=="3" (
    echo Running full test suite...
    python -m pytest tests/test_web_ui.py -v
) else (
    echo Invalid selection. Running offline tests by default...
    python -m pytest tests/test_web_ui.py -v --offline
)

echo.
echo ============================================
echo Test run complete
echo ============================================
pause
