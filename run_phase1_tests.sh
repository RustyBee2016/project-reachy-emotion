#!/bin/bash
# Phase 1 Test Runner
# This script runs tests for Phase 1 components
# Expected: Tests will fail initially (modules don't exist yet)

echo "========================================="
echo "   Phase 1: Test-Driven Development"
echo "========================================="
echo ""
echo "Following TDD practice:"
echo "1. Tests are written FIRST (✓ Complete)"
echo "2. Tests will FAIL initially (expected)"
echo "3. Implementation makes tests PASS"
echo ""
echo "========================================="
echo ""

# Ensure we're in the project root
cd "$(dirname "$0")"

# Install test dependencies if needed
echo "Installing test dependencies..."
pip install -q pytest pytest-asyncio pytest-cov mock psycopg2-binary

echo ""
echo "Running Phase 1 Tests..."
echo "========================"
echo ""

# Test 1: API Client
echo "1. Testing API Client (retry logic, idempotency)..."
python -m pytest tests/test_api_client.py -v --tb=short 2>&1 | grep -E "(PASSED|FAILED|ERROR|test_)"

echo ""

# Test 2: WebSocket Client  
echo "2. Testing WebSocket Client (auto-reconnection, events)..."
python -m pytest tests/test_websocket_client.py -v --tb=short 2>&1 | grep -E "(PASSED|FAILED|ERROR|test_)"

echo ""

# Test 3: Database Migrations
echo "3. Testing Database Migrations (schema, procedures)..."
if [ -z "$TEST_DB_NAME" ]; then
    echo "   ⚠️  Skipping DB tests - TEST_DB_NAME not set"
    echo "   To run: export TEST_DB_NAME=reachy_test"
else
    python -m pytest tests/test_database_migrations.py -v --tb=short 2>&1 | grep -E "(PASSED|FAILED|ERROR|test_)"
fi

echo ""
echo "========================================="
echo "Expected Result: Tests FAIL (no implementation)"
echo "Next Step: Implement code to make tests PASS"
echo "========================================="
