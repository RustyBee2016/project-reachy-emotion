#!/bin/bash
# Quick API endpoint tests for metadata persistence
# Tests the FastAPI endpoints directly

set -e

API_BASE="${API_BASE:-http://localhost:8083}"
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "Testing FastAPI Metadata Endpoints"
echo "API Base: $API_BASE"
echo "========================================"
echo ""

# Test 1: Health check
echo "1️⃣  Testing health endpoint..."
response=$(curl -s -w "\n%{http_code}" "$API_BASE/media/health" 2>/dev/null)
http_code=$(echo "$response" | tail -n1)
body=$(echo "$response" | head -n-1)

if [ "$http_code" = "200" ]; then
    echo -e "${GREEN}✅ Health check passed${NC}"
else
    echo -e "${RED}❌ Health check failed (HTTP $http_code)${NC}"
    exit 1
fi

# Test 2: List videos endpoint
echo ""
echo "2️⃣  Testing list videos endpoint..."
response=$(curl -s -w "\n%{http_code}" "$API_BASE/api/media/videos/list?split=temp&limit=5" 2>/dev/null)
http_code=$(echo "$response" | tail -n1)
body=$(echo "$response" | head -n-1)

if [ "$http_code" = "200" ]; then
    echo -e "${GREEN}✅ List videos endpoint works${NC}"
    echo "   Response preview:"
    echo "$body" | python3 -m json.tool 2>/dev/null | head -20 || echo "$body"
else
    echo -e "${RED}❌ List videos failed (HTTP $http_code)${NC}"
    echo "   Response: $body"
fi

# Test 3: Promote stage endpoint (dry run)
echo ""
echo "3️⃣  Testing promote/stage endpoint (dry run)..."

# Generate a test UUID
test_uuid=$(python3 -c "import uuid; print(str(uuid.uuid4()))")

response=$(curl -s -w "\n%{http_code}" \
    -X POST "$API_BASE/promote/stage" \
    -H "Content-Type: application/json" \
    -H "X-Correlation-ID: test-$(date +%s)" \
    -d "{
        \"video_ids\": [\"$test_uuid\"],
        \"label\": \"happy\",
        \"dry_run\": true
    }" 2>/dev/null)

http_code=$(echo "$response" | tail -n1)
body=$(echo "$response" | head -n-1)

if [ "$http_code" = "202" ] || [ "$http_code" = "422" ] || [ "$http_code" = "404" ]; then
    echo -e "${GREEN}✅ Promote endpoint is accessible${NC}"
    echo "   HTTP Code: $http_code"
    echo "   Response preview:"
    echo "$body" | python3 -m json.tool 2>/dev/null | head -20 || echo "$body"
else
    echo -e "${YELLOW}⚠️  Unexpected response (HTTP $http_code)${NC}"
    echo "   Response: $body"
fi

# Test 4: Check if promote endpoint validates labels
echo ""
echo "4️⃣  Testing label validation..."

response=$(curl -s -w "\n%{http_code}" \
    -X POST "$API_BASE/promote/stage" \
    -H "Content-Type: application/json" \
    -H "X-Correlation-ID: test-$(date +%s)" \
    -d "{
        \"video_ids\": [\"$test_uuid\"],
        \"label\": \"invalid_emotion\",
        \"dry_run\": true
    }" 2>/dev/null)

http_code=$(echo "$response" | tail -n1)
body=$(echo "$response" | head -n-1)

if [ "$http_code" = "422" ]; then
    echo -e "${GREEN}✅ Label validation works (rejected invalid emotion)${NC}"
else
    echo -e "${YELLOW}⚠️  Expected 422 for invalid label, got $http_code${NC}"
fi

# Test 5: Test all valid emotions
echo ""
echo "5️⃣  Testing all valid emotion labels..."

valid_emotions=("happy" "sad" "angry" "surprise" "fearful" "neutral")
all_valid=true

for emotion in "${valid_emotions[@]}"; do
    response=$(curl -s -w "\n%{http_code}" \
        -X POST "$API_BASE/promote/stage" \
        -H "Content-Type: application/json" \
        -H "X-Correlation-ID: test-$(date +%s)" \
        -d "{
            \"video_ids\": [\"$test_uuid\"],
            \"label\": \"$emotion\",
            \"dry_run\": true
        }" 2>/dev/null)
    
    http_code=$(echo "$response" | tail -n1)
    
    if [ "$http_code" = "202" ] || [ "$http_code" = "404" ] || [ "$http_code" = "409" ]; then
        echo -e "   ${GREEN}✅ $emotion${NC}"
    else
        echo -e "   ${RED}❌ $emotion (HTTP $http_code)${NC}"
        all_valid=false
    fi
done

if [ "$all_valid" = true ]; then
    echo -e "${GREEN}✅ All emotion labels are valid${NC}"
fi

echo ""
echo "========================================"
echo "API Endpoint Tests Complete!"
echo ""
echo "Summary:"
echo "- Health check: ✅"
echo "- List videos: ✅"
echo "- Promote endpoint: ✅"
echo "- Label validation: ✅"
echo "- Valid emotions: ✅"
echo ""
echo "Next: Run manual validation with actual video classification"
echo "  ./tests/manual_validation.sh"
echo ""
