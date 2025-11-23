#!/bin/bash
# Quick test script for all Media Mover endpoints
# Tests Media Mover API on port 8083 (Ubuntu 1)

set -e

echo "========================================="
echo "Media Mover API Endpoint Tests"
echo "Host: 10.0.4.130"
echo "Port: 8083"
echo "========================================="
echo ""

# Check if jq is installed
if ! command -v jq &> /dev/null; then
    echo "⚠️  Warning: jq not installed. Output will not be formatted."
    echo "   Install with: sudo apt-get install jq"
    JQ_CMD="cat"
else
    JQ_CMD="jq"
fi

# Test counter
PASSED=0
FAILED=0

# Function to run test
run_test() {
    local test_name="$1"
    local url="$2"
    local expected_status="$3"
    
    echo "Testing: $test_name"
    echo "  URL: $url"
    
    response=$(curl -s -w "\n%{http_code}" "$url" 2>/dev/null)
    http_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | head -n-1)
    
    if [ "$http_code" = "$expected_status" ]; then
        echo "  ✅ PASS (HTTP $http_code)"
        if [ -n "$body" ]; then
            echo "$body" | $JQ_CMD '.' 2>/dev/null || echo "$body"
        fi
        ((PASSED++))
    else
        echo "  ❌ FAIL (Expected $expected_status, got $http_code)"
        echo "$body"
        ((FAILED++))
    fi
    echo ""
}

# Test 1: Health Check
run_test "Health Check" \
    "http://10.0.4.130:8083/api/v1/health" \
    "200"

# Test 2: Readiness Check
run_test "Readiness Check" \
    "http://10.0.4.130:8083/api/v1/ready" \
    "200"

# Test 3: List Videos (temp split)
run_test "List Videos (temp)" \
    "http://10.0.4.130:8083/api/v1/media/list?split=temp&limit=5" \
    "200"

# Test 4: List Videos (dataset_all split)
run_test "List Videos (dataset_all)" \
    "http://10.0.4.130:8083/api/v1/media/list?split=dataset_all&limit=5" \
    "200"

# Test 5: Video Metadata (luma_1)
run_test "Video Metadata (luma_1)" \
    "http://10.0.4.130:8083/api/v1/media/luma_1" \
    "200"

# Test 6: Video Thumbnail (luma_1)
echo "Testing: Video Thumbnail (luma_1)"
echo "  URL: http://10.0.4.130:8083/api/v1/media/luma_1/thumb"

response=$(curl -s -w "\n%{http_code}" "http://10.0.4.130:8083/api/v1/media/luma_1/thumb" 2>/dev/null)
http_code=$(echo "$response" | tail -n1)
body=$(echo "$response" | head -n-1)

if [ "$http_code" = "200" ]; then
    echo "  ✅ PASS (HTTP $http_code)"
    echo "$body" | $JQ_CMD '.' 2>/dev/null || echo "$body"
    ((PASSED++))
elif [ "$http_code" = "404" ]; then
    echo "  ⚠️  PENDING (HTTP 404 - Thumbnail not yet generated)"
    echo "     Wait 5-10 seconds for automatic generation"
    ((PASSED++))
else
    echo "  ❌ FAIL (Expected 200 or 404, got $http_code)"
    echo "$body"
    ((FAILED++))
fi
echo ""

# Test 7: Dialogue Health
run_test "Dialogue Health" \
    "http://10.0.4.130:8083/api/v1/dialogue/health" \
    "200"

# Test 8: Prometheus Metrics
echo "Testing: Prometheus Metrics"
echo "  URL: http://10.0.4.130:8083/metrics"

response=$(curl -s -w "\n%{http_code}" "http://10.0.4.130:8083/metrics" 2>/dev/null)
http_code=$(echo "$response" | tail -n1)
body=$(echo "$response" | head -n-1)

if [ "$http_code" = "200" ]; then
    echo "  ✅ PASS (HTTP $http_code)"
    # Show first few lines of metrics
    echo "$body" | head -n 5
    echo "  ... (truncated)"
    ((PASSED++))
else
    echo "  ❌ FAIL (Expected 200, got $http_code)"
    ((FAILED++))
fi
echo ""

# Test 9: Nginx Static Server
echo "Testing: Nginx Static Server"
echo "  URL: http://10.0.4.130:8082/"

response=$(curl -s -I "http://10.0.4.130:8082/" 2>/dev/null)
http_code=$(echo "$response" | grep "HTTP" | awk '{print $2}')

if [ "$http_code" = "200" ] || [ "$http_code" = "403" ]; then
    echo "  ✅ PASS (HTTP $http_code - Nginx is running)"
    ((PASSED++))
else
    echo "  ❌ FAIL (Expected 200 or 403, got $http_code)"
    ((FAILED++))
fi
echo ""

# Test 10: Thumbnail via Nginx (if luma_1 thumbnail exists)
echo "Testing: Thumbnail via Nginx"
echo "  URL: http://10.0.4.130:8082/thumbs/luma_1.jpg"

response=$(curl -s -I "http://10.0.4.130:8082/thumbs/luma_1.jpg" 2>/dev/null)
http_code=$(echo "$response" | grep "HTTP" | awk '{print $2}')

if [ "$http_code" = "200" ]; then
    echo "  ✅ PASS (HTTP $http_code - Thumbnail accessible)"
    ((PASSED++))
elif [ "$http_code" = "404" ]; then
    echo "  ⚠️  PENDING (HTTP 404 - Thumbnail not yet generated)"
    ((PASSED++))
else
    echo "  ❌ FAIL (Expected 200 or 404, got $http_code)"
    ((FAILED++))
fi
echo ""

# Summary
echo "========================================="
echo "Test Summary"
echo "========================================="
echo "Passed: $PASSED"
echo "Failed: $FAILED"
echo "Total:  $((PASSED + FAILED))"
echo ""

if [ $FAILED -eq 0 ]; then
    echo "✅ All tests passed!"
    exit 0
else
    echo "❌ Some tests failed"
    exit 1
fi
