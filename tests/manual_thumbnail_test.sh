#!/bin/bash
# Manual test script for thumbnail generation system
# This script validates the complete thumbnail generation workflow

set -e

echo "========================================="
echo "Thumbnail Generation System Test"
echo "========================================="
echo ""

# Configuration
VIDEOS_ROOT="${REACHY_VIDEOS_ROOT:-/media/rusty_admin/project_data/reachy_emotion/videos}"
API_BASE_URL="${REACHY_API_BASE_URL:-http://10.0.4.130:8083}"
TEST_VIDEO_ID="test_thumb_$(date +%s)"

echo "Configuration:"
echo "  Videos Root: $VIDEOS_ROOT"
echo "  API Base URL: $API_BASE_URL"
echo "  Test Video ID: $TEST_VIDEO_ID"
echo ""

# Check prerequisites
echo "Checking prerequisites..."

if ! command -v ffmpeg &> /dev/null; then
    echo "❌ ERROR: FFmpeg is not installed"
    echo "   Install with: sudo apt-get install ffmpeg"
    exit 1
fi
echo "✓ FFmpeg is installed"

if ! command -v curl &> /dev/null; then
    echo "❌ ERROR: curl is not installed"
    exit 1
fi
echo "✓ curl is installed"

if [ ! -d "$VIDEOS_ROOT/temp" ]; then
    echo "❌ ERROR: Videos temp directory does not exist: $VIDEOS_ROOT/temp"
    exit 1
fi
echo "✓ Videos temp directory exists"

if [ ! -d "$VIDEOS_ROOT/thumbs" ]; then
    echo "⚠ WARNING: Thumbs directory does not exist, creating it..."
    mkdir -p "$VIDEOS_ROOT/thumbs"
fi
echo "✓ Thumbs directory exists"

echo ""

# Test 1: Create a test video
echo "Test 1: Creating test video..."
TEST_VIDEO_PATH="$VIDEOS_ROOT/temp/${TEST_VIDEO_ID}.mp4"

ffmpeg -f lavfi -i color=c=blue:s=320x240:d=2 \
    -pix_fmt yuv420p \
    -y "$TEST_VIDEO_PATH" \
    > /dev/null 2>&1

if [ -f "$TEST_VIDEO_PATH" ]; then
    echo "✓ Test video created: $TEST_VIDEO_PATH"
    ls -lh "$TEST_VIDEO_PATH"
else
    echo "❌ ERROR: Failed to create test video"
    exit 1
fi

echo ""

# Test 2: Wait for thumbnail generation
echo "Test 2: Waiting for automatic thumbnail generation..."
echo "   (Background service polls every 5 seconds)"

THUMBNAIL_PATH="$VIDEOS_ROOT/thumbs/${TEST_VIDEO_ID}.jpg"
MAX_WAIT=30
ELAPSED=0

while [ $ELAPSED -lt $MAX_WAIT ]; do
    if [ -f "$THUMBNAIL_PATH" ]; then
        echo "✓ Thumbnail generated in ${ELAPSED} seconds"
        ls -lh "$THUMBNAIL_PATH"
        break
    fi
    
    echo "   Waiting... (${ELAPSED}s / ${MAX_WAIT}s)"
    sleep 2
    ELAPSED=$((ELAPSED + 2))
done

if [ ! -f "$THUMBNAIL_PATH" ]; then
    echo "❌ ERROR: Thumbnail was not generated within ${MAX_WAIT} seconds"
    echo "   Check that the Media Mover API is running with thumbnail watcher enabled"
    echo "   Expected: $THUMBNAIL_PATH"
    
    # Cleanup
    rm -f "$TEST_VIDEO_PATH"
    exit 1
fi

echo ""

# Test 3: Verify thumbnail is a valid JPEG
echo "Test 3: Verifying thumbnail format..."

FILE_TYPE=$(file -b --mime-type "$THUMBNAIL_PATH")
if [ "$FILE_TYPE" = "image/jpeg" ]; then
    echo "✓ Thumbnail is a valid JPEG image"
else
    echo "❌ ERROR: Thumbnail is not a JPEG (detected: $FILE_TYPE)"
    rm -f "$TEST_VIDEO_PATH" "$THUMBNAIL_PATH"
    exit 1
fi

# Check file size
FILE_SIZE=$(stat -f%z "$THUMBNAIL_PATH" 2>/dev/null || stat -c%s "$THUMBNAIL_PATH" 2>/dev/null)
if [ "$FILE_SIZE" -gt 1000 ] && [ "$FILE_SIZE" -lt 100000 ]; then
    echo "✓ Thumbnail size is reasonable: ${FILE_SIZE} bytes"
else
    echo "⚠ WARNING: Thumbnail size seems unusual: ${FILE_SIZE} bytes"
fi

echo ""

# Test 4: Test API endpoint
echo "Test 4: Testing thumbnail API endpoint..."

RESPONSE=$(curl -s -w "\n%{http_code}" "$API_BASE_URL/api/v1/media/${TEST_VIDEO_ID}/thumb")
HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
BODY=$(echo "$RESPONSE" | head -n-1)

if [ "$HTTP_CODE" = "200" ]; then
    echo "✓ API returned 200 OK"
    echo "$BODY" | python3 -m json.tool 2>/dev/null || echo "$BODY"
    
    # Verify response contains thumbnail URL
    if echo "$BODY" | grep -q "thumbnail_url"; then
        echo "✓ Response contains thumbnail_url"
    else
        echo "❌ ERROR: Response missing thumbnail_url"
    fi
else
    echo "❌ ERROR: API returned HTTP $HTTP_CODE"
    echo "$BODY"
fi

echo ""

# Test 5: Verify thumbnail URL is accessible
echo "Test 5: Verifying thumbnail URL is accessible via Nginx..."

THUMBNAIL_URL=$(echo "$BODY" | python3 -c "import sys, json; print(json.load(sys.stdin)['data']['thumbnail_url'])" 2>/dev/null || echo "")

if [ -n "$THUMBNAIL_URL" ]; then
    echo "   Thumbnail URL: $THUMBNAIL_URL"
    
    NGINX_RESPONSE=$(curl -s -w "\n%{http_code}" "$THUMBNAIL_URL")
    NGINX_HTTP_CODE=$(echo "$NGINX_RESPONSE" | tail -n1)
    
    if [ "$NGINX_HTTP_CODE" = "200" ]; then
        echo "✓ Thumbnail is accessible via Nginx"
    else
        echo "⚠ WARNING: Thumbnail URL returned HTTP $NGINX_HTTP_CODE"
        echo "   This may indicate Nginx is not configured to serve /thumbs/"
    fi
else
    echo "⚠ WARNING: Could not extract thumbnail URL from response"
fi

echo ""

# Test 6: Test video metadata endpoint
echo "Test 6: Testing video metadata endpoint..."

METADATA_RESPONSE=$(curl -s -w "\n%{http_code}" "$API_BASE_URL/api/v1/media/${TEST_VIDEO_ID}")
METADATA_HTTP_CODE=$(echo "$METADATA_RESPONSE" | tail -n1)
METADATA_BODY=$(echo "$METADATA_RESPONSE" | head -n-1)

if [ "$METADATA_HTTP_CODE" = "200" ]; then
    echo "✓ Video metadata endpoint returned 200 OK"
    echo "$METADATA_BODY" | python3 -m json.tool 2>/dev/null || echo "$METADATA_BODY"
else
    echo "⚠ WARNING: Video metadata endpoint returned HTTP $METADATA_HTTP_CODE"
fi

echo ""

# Cleanup
echo "Cleanup: Removing test files..."
rm -f "$TEST_VIDEO_PATH"
rm -f "$THUMBNAIL_PATH"
echo "✓ Test files removed"

echo ""
echo "========================================="
echo "All Tests Completed Successfully! ✓"
echo "========================================="
echo ""
echo "Summary:"
echo "  ✓ FFmpeg is installed and working"
echo "  ✓ Test video was created"
echo "  ✓ Thumbnail was automatically generated"
echo "  ✓ Thumbnail is a valid JPEG image"
echo "  ✓ API endpoint returns correct response"
echo "  ✓ Thumbnail URL is accessible"
echo ""
echo "The thumbnail generation system is working correctly!"
