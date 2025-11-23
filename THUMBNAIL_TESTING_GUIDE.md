# Thumbnail Generation Testing Guide

## Quick Start

### Prerequisites

```bash
# 1. Install FFmpeg (required)
sudo apt-get update && sudo apt-get install -y ffmpeg

# 2. Verify installation
ffmpeg -version

# 3. Ensure API is running
ps aux | grep uvicorn
```

### Run All Tests

```bash
cd /home/rusty_admin/projects/reachy_08.4.2

# Run unit tests (fast, no FFmpeg required for most)
pytest tests/test_thumbnail_generator.py -v
pytest tests/test_thumbnail_watcher.py -v

# Run integration tests (requires FFmpeg)
pytest tests/test_thumbnail_integration.py -m integration -v

# Run manual validation script
./tests/manual_thumbnail_test.sh
```

## Test Scenarios

### Scenario 1: Test with Existing Video (luma_1)

```bash
# 1. Check if video exists
ls -lh /media/rusty_admin/project_data/reachy_emotion/videos/temp/luma_1.mp4

# 2. Remove old thumbnail if exists
rm -f /media/rusty_admin/project_data/reachy_emotion/videos/thumbs/luma_1.jpg

# 3. Restart API to trigger watcher
pkill -f "uvicorn.*app.main:app"
cd /home/rusty_admin/projects/reachy_08.4.2/apps/api
uvicorn app.main:app --host 0.0.0.0 --port 8083 &

# 4. Wait 10 seconds for thumbnail generation
sleep 10

# 5. Check thumbnail was created
ls -lh /media/rusty_admin/project_data/reachy_emotion/videos/thumbs/luma_1.jpg

# 6. Test API endpoint
curl -i http://10.0.4.130:8083/api/v1/media/luma_1/thumb

# Expected: 200 OK with thumbnail_url
```

### Scenario 2: Test with New Video

```bash
# 1. Create a test video
ffmpeg -f lavfi -i color=c=red:s=640x480:d=3 \
    -pix_fmt yuv420p \
    -y /media/rusty_admin/project_data/reachy_emotion/videos/temp/test_new.mp4

# 2. Wait for automatic thumbnail generation (max 10 seconds)
for i in {1..10}; do
    if [ -f /media/rusty_admin/project_data/reachy_emotion/videos/thumbs/test_new.jpg ]; then
        echo "✓ Thumbnail generated in ${i} seconds"
        break
    fi
    echo "Waiting... ${i}s"
    sleep 1
done

# 3. Verify thumbnail
file /media/rusty_admin/project_data/reachy_emotion/videos/thumbs/test_new.jpg
ls -lh /media/rusty_admin/project_data/reachy_emotion/videos/thumbs/test_new.jpg

# 4. Test API
curl http://10.0.4.130:8083/api/v1/media/test_new/thumb | jq

# 5. Cleanup
rm -f /media/rusty_admin/project_data/reachy_emotion/videos/temp/test_new.mp4
rm -f /media/rusty_admin/project_data/reachy_emotion/videos/thumbs/test_new.jpg
```

### Scenario 3: Test Multiple Videos

```bash
# Create 3 test videos
for i in {1..3}; do
    ffmpeg -f lavfi -i color=c=blue:s=320x240:d=1 \
        -pix_fmt yuv420p \
        -y /media/rusty_admin/project_data/reachy_emotion/videos/temp/batch_test_${i}.mp4
done

# Wait for all thumbnails
sleep 15

# Check all were generated
ls -lh /media/rusty_admin/project_data/reachy_emotion/videos/thumbs/batch_test_*.jpg

# Test each endpoint
for i in {1..3}; do
    echo "Testing batch_test_${i}..."
    curl -s http://10.0.4.130:8083/api/v1/media/batch_test_${i}/thumb | jq -r '.data.thumbnail_url'
done

# Cleanup
rm -f /media/rusty_admin/project_data/reachy_emotion/videos/temp/batch_test_*.mp4
rm -f /media/rusty_admin/project_data/reachy_emotion/videos/thumbs/batch_test_*.jpg
```

## Automated Test Script

The comprehensive automated test is available:

```bash
./tests/manual_thumbnail_test.sh
```

This script tests:
- ✓ FFmpeg installation
- ✓ Directory structure
- ✓ Video creation
- ✓ Automatic thumbnail generation
- ✓ JPEG format validation
- ✓ API endpoint response
- ✓ Nginx accessibility
- ✓ Cleanup

## Expected Results

### Successful Thumbnail Generation

**API Response (200 OK):**
```json
{
  "status": "success",
  "data": {
    "video_id": "luma_1",
    "thumbnail_url": "http://10.0.4.130:8082/thumbs/luma_1.jpg"
  },
  "meta": {
    "correlation_id": "460bc20f-2247-4dd9-98c8-22321a103769",
    "timestamp": "2025-11-19T08:40:08.256293Z",
    "version": "v1"
  }
}
```

**File System:**
```bash
$ ls -lh /media/rusty_admin/project_data/reachy_emotion/videos/thumbs/luma_1.jpg
-rw-r--r-- 1 rusty_admin rusty_admin 12K Nov 19 08:40 luma_1.jpg

$ file /media/rusty_admin/project_data/reachy_emotion/videos/thumbs/luma_1.jpg
luma_1.jpg: JPEG image data, JFIF standard 1.01
```

### Thumbnail Not Yet Generated (404)

If queried too quickly after video ingestion:

```json
{
  "detail": {
    "error": "not_found",
    "message": "Thumbnail not found for video: luma_1"
  }
}
```

**Solution:** Wait 5-10 seconds and retry.

## Troubleshooting Tests

### Test Fails: FFmpeg Not Found

```bash
# Install FFmpeg
sudo apt-get update
sudo apt-get install -y ffmpeg

# Verify
ffmpeg -version
```

### Test Fails: Permission Denied

```bash
# Check directory permissions
ls -ld /media/rusty_admin/project_data/reachy_emotion/videos/thumbs/

# Fix if needed
sudo chown -R rusty_admin:rusty_admin /media/rusty_admin/project_data/reachy_emotion/videos/thumbs/
chmod 755 /media/rusty_admin/project_data/reachy_emotion/videos/thumbs/
```

### Test Fails: Service Not Running

```bash
# Check if API is running
ps aux | grep uvicorn

# Check logs for watcher service
# Should see: "Thumbnail watcher service started"

# Restart API
cd /home/rusty_admin/projects/reachy_08.4.2/apps/api
uvicorn app.main:app --host 0.0.0.0 --port 8083
```

### Test Fails: Thumbnail Not Generated

```bash
# Check API logs for errors
# Look for:
#   - "Thumbnail watcher service started"
#   - "Generated thumbnail for: {video_id}"
#   - Any error messages

# Manually test FFmpeg
ffmpeg -ss 00:00:01 \
    -i /media/rusty_admin/project_data/reachy_emotion/videos/temp/luma_1.mp4 \
    -vframes 1 -q:v 2 \
    /tmp/manual_test_thumb.jpg

# If this works, the issue is with the service
# If this fails, check FFmpeg installation and video file
```

## Unit Test Details

### Test Thumbnail Generator (18 tests)

```bash
pytest tests/test_thumbnail_generator.py -v

# Tests cover:
# - FFmpeg validation
# - Successful thumbnail generation
# - Error handling (missing video, FFmpeg failure, timeout)
# - Overwrite behavior
# - Directory creation
# - Video ID lookup with multiple extensions
```

### Test Thumbnail Watcher (15 tests)

```bash
pytest tests/test_thumbnail_watcher.py -v

# Tests cover:
# - Service initialization
# - Video scanning and detection
# - Thumbnail generation
# - Start/stop lifecycle
# - Error recovery
# - Statistics tracking
```

### Integration Tests (7 tests)

```bash
pytest tests/test_thumbnail_integration.py -m integration -v

# Tests cover:
# - Real video thumbnail generation
# - Automatic watcher processing
# - Multiple video handling
# - Existing thumbnail skip behavior
# - Thumbnail quality validation
# - Different video format support
```

## Performance Benchmarks

Expected performance on typical hardware:

- **Detection Time:** 0-5 seconds (poll interval)
- **Generation Time:** 0.5-2 seconds per video
- **Total Time:** 0.5-7 seconds from video arrival to thumbnail availability

## Success Criteria

All tests should pass with:
- ✓ 0 failures
- ✓ 0 errors
- ✓ All assertions passing
- ✓ Thumbnails generated within 10 seconds
- ✓ Valid JPEG files created
- ✓ API endpoints returning 200 OK

## Next Steps After Testing

Once all tests pass:

1. **Update n8n workflows** (if needed - see `n8n/THUMBNAIL_GENERATION_NOTES.md`)
2. **Monitor production** for thumbnail generation events
3. **Verify disk space** in `/videos/thumbs/` directory
4. **Set up alerts** for thumbnail generation failures (optional)

## Quick Reference Commands

```bash
# Check service status
ps aux | grep uvicorn

# View recent thumbnails
ls -lht /media/rusty_admin/project_data/reachy_emotion/videos/thumbs/ | head -10

# Count thumbnails
ls -1 /media/rusty_admin/project_data/reachy_emotion/videos/thumbs/*.jpg | wc -l

# Test specific video
curl http://10.0.4.130:8083/api/v1/media/{VIDEO_ID}/thumb | jq

# Run all tests
pytest tests/test_thumbnail_*.py -v && ./tests/manual_thumbnail_test.sh
```
