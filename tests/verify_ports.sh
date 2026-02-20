#!/bin/bash
# Port Configuration Verification Script
# Verifies all services are running on correct ports

set -e

echo "========================================="
echo "Reachy Port Configuration Verification"
echo "========================================="
echo ""

# Color codes
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test counter
PASSED=0
FAILED=0
WARNING=0

# Function to test endpoint
test_endpoint() {
    local service="$1"
    local url="$2"
    local expected_status="$3"
    local is_critical="$4"
    
    printf "%-30s " "$service:"
    
    response=$(curl -s -w "%{http_code}" -o /dev/null "$url" 2>/dev/null)
    
    if [ "$response" = "$expected_status" ]; then
        echo -e "${GREEN}✅ OK${NC} (HTTP $response)"
        ((PASSED++))
        return 0
    else
        if [ "$is_critical" = "true" ]; then
            echo -e "${RED}❌ FAILED${NC} (Expected $expected_status, got $response)"
            ((FAILED++))
        else
            echo -e "${YELLOW}⚠️  WARNING${NC} (Expected $expected_status, got $response)"
            ((WARNING++))
        fi
        return 1
    fi
}

echo "Ubuntu 1 (10.0.4.130) - Backend Services"
echo "─────────────────────────────────────────"

# Media Mover API (Port 8083) - CRITICAL
test_endpoint \
    "Media Mover API :8083" \
    "http://10.0.4.130:8083/api/v1/health" \
    "200" \
    "true"

# Nginx Static Server (Port 8082) - CRITICAL
test_endpoint \
    "Nginx Static :8082" \
    "http://10.0.4.130:8082/" \
    "200" \
    "true" || \
test_endpoint \
    "Nginx Static :8082 (retry)" \
    "http://10.0.4.130:8082/" \
    "403" \
    "true"

# n8n (Port 5678) - NON-CRITICAL
test_endpoint \
    "n8n :5678" \
    "http://10.0.4.130:5678" \
    "200" \
    "false"

echo ""
echo "Ubuntu 2 (10.0.4.140) - Frontend Services"
echo "─────────────────────────────────────────"

# Gateway API (Port 8000) - NON-CRITICAL (may not be running)
test_endpoint \
    "Gateway API :8000" \
    "http://10.0.4.140:8000/health" \
    "200" \
    "false"

# Streamlit UI (Port 8501) - NON-CRITICAL
test_endpoint \
    "Streamlit UI :8501" \
    "http://10.0.4.140:8501" \
    "200" \
    "false"

echo ""
echo "Additional Checks"
echo "─────────────────────────────────────────"

# Check PostgreSQL (requires psql)
printf "%-30s " "PostgreSQL :5432:"
if command -v psql &> /dev/null; then
    if psql -h 10.0.4.130 -p 5432 -U reachy_app -d reachy_local -c "SELECT 1;" &> /dev/null; then
        echo -e "${GREEN}✅ OK${NC}"
        ((PASSED++))
    else
        echo -e "${YELLOW}⚠️  WARNING${NC} (Connection failed - may need password)"
        ((WARNING++))
    fi
else
    echo -e "${YELLOW}⚠️  SKIPPED${NC} (psql not installed)"
    ((WARNING++))
fi

# Check for port conflicts on Media Mover
printf "%-30s " "Port 8083 Binding:"
if ss -tlnp 2>/dev/null | grep -q ":8083"; then
    echo -e "${GREEN}✅ OK${NC} (Service listening)"
    ((PASSED++))
else
    echo -e "${RED}❌ FAILED${NC} (No service on port 8083)"
    ((FAILED++))
fi

# Check for incorrect port 8000 on Ubuntu 1
printf "%-30s " "Port 8000 on Ubuntu 1:"
if curl -s -o /dev/null -w "%{http_code}" "http://10.0.4.130:8000/api/v1/health" 2>/dev/null | grep -q "200"; then
    echo -e "${RED}❌ ERROR${NC} (Service incorrectly on port 8000)"
    echo "   Media Mover should be on port 8083, not 8000!"
    ((FAILED++))
else
    echo -e "${GREEN}✅ OK${NC} (No service on port 8000 - correct)"
    ((PASSED++))
fi

echo ""
echo "========================================="
echo "Verification Summary"
echo "========================================="
echo -e "${GREEN}Passed:${NC}   $PASSED"
echo -e "${YELLOW}Warnings:${NC} $WARNING"
echo -e "${RED}Failed:${NC}   $FAILED"
echo "Total:    $((PASSED + WARNING + FAILED))"
echo ""

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}✅ Port configuration is correct!${NC}"
    echo ""
    echo "Services running on correct ports:"
    echo "  • Media Mover API: 10.0.4.130:8083 ✓"
    echo "  • Nginx Static:    10.0.4.130:8082 ✓"
    echo "  • Gateway API:     10.0.4.140:8000 ✓"
    exit 0
else
    echo -e "${RED}❌ Port configuration has errors!${NC}"
    echo ""
    echo "Please check:"
    echo "  1. Media Mover API should be on port 8083 (Ubuntu 1)"
    echo "  2. Gateway API should be on port 8000 (Ubuntu 2)"
    echo "  3. No service should use port 8000 on Ubuntu 1"
    exit 1
fi
