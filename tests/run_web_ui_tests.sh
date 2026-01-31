#!/bin/bash
# Web UI Test Runner for Linux/Ubuntu
# Run from project root: bash tests/run_web_ui_tests.sh

echo "============================================"
echo "Reachy Emotion - Web UI Test Suite"
echo "============================================"

# Check if pytest is available
if ! python -m pytest --version &>/dev/null; then
    echo "ERROR: pytest not found. Install with: pip install pytest"
    exit 1
fi

# Parse arguments
OFFLINE=false
INTEGRATION=false
E2E=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --offline)
            OFFLINE=true
            shift
            ;;
        --integration)
            INTEGRATION=true
            shift
            ;;
        --e2e)
            E2E=true
            shift
            ;;
        *)
            echo "Unknown option: $1"
            echo "Usage: $0 [--offline|--integration|--e2e]"
            exit 1
            ;;
    esac
done

echo ""
if [ "$OFFLINE" = true ]; then
    echo "Running offline tests (mock only)..."
    python -m pytest tests/test_web_ui.py -v --offline -m "not integration and not e2e"
elif [ "$INTEGRATION" = true ]; then
    echo "Running integration tests..."
    python -m pytest tests/test_web_ui.py -v -m "integration"
elif [ "$E2E" = true ]; then
    echo "Running full E2E test suite..."
    python -m pytest tests/test_web_ui.py -v
else
    echo "Running all tests (default)..."
    python -m pytest tests/test_web_ui.py -v
fi

echo ""
echo "============================================"
echo "Test run complete"
echo "============================================"
