# Quick Test Guide - Database Integration

**Quick reference for testing the new database-integrated endpoints**

---

## Prerequisites

```bash
# Install test dependencies
pip install pytest pytest-asyncio httpx sqlalchemy[asyncio] aiosqlite

# Verify installation
pytest --version
```

---

## Run Automated Tests

### All Tests
```bash
cd /home/rusty_admin/projects/reachy_08.4.2
pytest tests/apps/api/ -v
```

### Specific Test Files
```bash
# Metadata tests
pytest tests/apps/api/test_video_metadata.py -v

# Listing tests
pytest tests/apps/api/test_video_listing.py -v
```

### With Coverage
```bash
pytest tests/apps/api/ --cov=apps/api/app --cov-report=html
# Open htmlcov/index.html in browser
```

### Single Test
```bash
pytest tests/apps/api/test_video_metadata.py::TestVideoMetadataByUUID::test_get_video_metadata_by_uuid_success -v
```

---

## Manual Testing with curl

### Setup
```bash
# Set base URL
BASE_URL="http://localhost:8081"

# Example UUID (replace with actual UUID from your database)
VIDEO_UUID="550e8400-e29b-41d4-a716-446655440000"
```

### Test 1: Get Video Metadata by UUID
```bash
curl -X GET "${BASE_URL}/api/videos/${VIDEO_UUID}" | jq
```

**Expected Response**:
```json
{
  "status": "ok",
  "video": {
    "schema_version": "v1",
    "video_id": "550e8400-e29b-41d4-a716-446655440000",
    "file_name": "video.mp4",
    "file_path": "temp/video.mp4",
    "split": "temp",
    "label": null,
    "size_bytes": 1048576,
    "duration_sec": 5.2,
    "fps": 30.0,
    "width": 1920,
    "height": 1080,
    "sha256": "abc123",
    "mtime": 1700000000.0,
    "created_at": "2025-11-25T12:00:00Z",
    "updated_at": "2025-11-25T12:00:00Z",
    "lookup_method": "uuid"
  }
}
```

### Test 2: Get Video Metadata by Filename (Backward Compatibility)
```bash
curl -X GET "${BASE_URL}/api/videos/luma_1.mp4" | jq
```

**Expected**: Should return UUID from database, not filename stem

### Test 3: List All Videos
```bash
curl -X GET "${BASE_URL}/api/videos/list" | jq
```

### Test 4: List Videos with Pagination
```bash
# First page
curl -X GET "${BASE_URL}/api/videos/list?limit=10&offset=0" | jq

# Second page
curl -X GET "${BASE_URL}/api/videos/list?limit=10&offset=10" | jq
```

### Test 5: Filter by Split
```bash
# Temp videos
curl -X GET "${BASE_URL}/api/videos/list?split=temp" | jq

# Dataset videos
curl -X GET "${BASE_URL}/api/videos/list?split=dataset_all" | jq
```

### Test 6: Filter by Label
```bash
curl -X GET "${BASE_URL}/api/videos/list?label=happy" | jq
```

### Test 7: Combined Filters
```bash
curl -X GET "${BASE_URL}/api/videos/list?split=dataset_all&label=happy&limit=20" | jq
```

### Test 8: Sorting
```bash
# Sort by size (largest first)
curl -X GET "${BASE_URL}/api/videos/list?order_by=size_bytes&order=desc" | jq

# Sort by creation date (newest first)
curl -X GET "${BASE_URL}/api/videos/list?order_by=created_at&order=desc" | jq
```

### Test 9: Get Video URL
```bash
curl -X GET "${BASE_URL}/api/videos/${VIDEO_UUID}/url" | jq
```

**Expected Response**:
```json
{
  "status": "ok",
  "video_id": "550e8400-e29b-41d4-a716-446655440000",
  "stream_url": "/videos/temp/video.mp4",
  "thumbnail_url": "/thumbs/video.jpg",
  "expires_at": null
}
```

### Test 10: Get Thumbnail
```bash
curl -X GET "${BASE_URL}/api/videos/${VIDEO_UUID}/thumb" --output test_thumb.jpg
file test_thumb.jpg  # Should show: JPEG image data
```

### Test 11: Error Cases

#### Video Not Found
```bash
curl -X GET "${BASE_URL}/api/videos/nonexistent-uuid" | jq
# Expected: 404 with error message
```

#### Invalid Split
```bash
curl -X GET "${BASE_URL}/api/videos/list?split=invalid" | jq
# Expected: 400 with error message
```

#### Invalid Pagination
```bash
curl -X GET "${BASE_URL}/api/videos/list?limit=-10" | jq
# Expected: 400 with error message
```

---

## Python Testing Script

Save as `test_endpoints.py`:

```python
#!/usr/bin/env python3
"""Quick test script for database integration endpoints."""

import requests
import sys

BASE_URL = "http://localhost:8081"

def test_list_videos():
    """Test video listing endpoint."""
    print("Testing: GET /api/videos/list")
    response = requests.get(f"{BASE_URL}/api/videos/list?limit=5")
    assert response.status_code == 200
    data = response.json()
    assert "videos" in data
    assert "pagination" in data
    print(f"✓ Found {data['pagination']['total']} videos")
    return data["videos"]

def test_video_metadata(video_id):
    """Test video metadata endpoint."""
    print(f"Testing: GET /api/videos/{video_id}")
    response = requests.get(f"{BASE_URL}/api/videos/{video_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["video"]["video_id"] == video_id
    print(f"✓ Retrieved metadata for {video_id}")
    return data["video"]

def test_video_url(video_id):
    """Test video URL generation."""
    print(f"Testing: GET /api/videos/{video_id}/url")
    response = requests.get(f"{BASE_URL}/api/videos/{video_id}/url")
    assert response.status_code == 200
    data = response.json()
    assert "stream_url" in data
    assert "thumbnail_url" in data
    print(f"✓ Generated URLs for {video_id}")
    return data

def main():
    """Run all tests."""
    try:
        # Test 1: List videos
        videos = test_list_videos()
        
        if not videos:
            print("⚠ No videos in database, skipping video-specific tests")
            return
        
        # Test 2: Get metadata for first video
        video_id = videos[0]["video_id"]
        metadata = test_video_metadata(video_id)
        
        # Test 3: Get URL for video
        urls = test_video_url(video_id)
        
        print("\n✅ All tests passed!")
        
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        sys.exit(1)
    except requests.exceptions.ConnectionError:
        print(f"\n❌ Cannot connect to {BASE_URL}")
        print("   Make sure the API server is running")
        sys.exit(1)

if __name__ == "__main__":
    main()
```

Run with:
```bash
python test_endpoints.py
```

---

## Database Setup for Testing

If you need to add test data to the database:

```sql
-- Connect to database
psql -d reachy_emotion -U your_user

-- Insert test video
INSERT INTO video (
    video_id,
    file_path,
    split,
    label,
    size_bytes,
    sha256,
    duration_sec,
    fps,
    width,
    height
) VALUES (
    '550e8400-e29b-41d4-a716-446655440000',
    'temp/test_video.mp4',
    'temp',
    NULL,
    1048576,
    'abc123def456',
    5.2,
    30.0,
    1920,
    1080
);

-- Verify insertion
SELECT video_id, file_path, split FROM video LIMIT 5;
```

---

## Performance Testing

### Simple Load Test with curl
```bash
# Test 100 requests
for i in {1..100}; do
    curl -s -o /dev/null -w "%{time_total}\n" \
        "${BASE_URL}/api/videos/list?limit=10"
done | awk '{sum+=$1; count++} END {print "Average:", sum/count, "seconds"}'
```

### With Apache Bench
```bash
# 1000 requests, 10 concurrent
ab -n 1000 -c 10 "${BASE_URL}/api/videos/list?limit=10"
```

---

## Troubleshooting

### Tests Fail with "Module not found"
```bash
# Make sure you're in the project root
cd /home/rusty_admin/projects/reachy_08.4.2

# Install in development mode
pip install -e .
```

### Database Connection Errors
```bash
# Check database is running
psql -d reachy_emotion -c "SELECT 1"

# Check connection string in .env
cat apps/api/.env | grep DATABASE_URL
```

### Import Errors
```bash
# Verify Python path
export PYTHONPATH=/home/rusty_admin/projects/reachy_08.4.2:$PYTHONPATH

# Or use pytest with proper path
python -m pytest tests/apps/api/ -v
```

---

## Success Indicators

### ✅ Tests Pass
- All pytest tests complete successfully
- No errors or warnings
- Coverage > 85%

### ✅ Manual Tests Work
- All curl commands return expected responses
- UUIDs returned from database
- Pagination works correctly
- Filtering works as expected

### ✅ Performance Acceptable
- Metadata endpoint < 50ms
- List endpoint < 100ms
- No database connection errors

---

## Next Steps After Testing

1. **If tests pass**: Deploy to staging
2. **If tests fail**: Review errors, fix issues, retest
3. **After staging**: Monitor for 24 hours
4. **After validation**: Deploy to production

---

**Quick Commands Summary**:
```bash
# Run all tests
pytest tests/apps/api/ -v

# Test one endpoint
curl http://localhost:8081/api/videos/list | jq

# Check coverage
pytest tests/apps/api/ --cov --cov-report=html
```
