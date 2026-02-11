#!/usr/bin/env python3
"""Test script to verify web app database connectivity and video workflow.

This script tests:
1. Gateway API connectivity (Ubuntu 2, port 8000)
2. Media Mover API connectivity (Ubuntu 1, port 8083)
3. Database-backed video listing
4. Video staging to dataset_all with database persistence
"""

import requests
import sys
from datetime import datetime

# Configuration
GATEWAY_URL = "http://10.0.4.140:8000"
MEDIA_MOVER_URL = "http://10.0.4.130:8083"

def test_gateway_health():
    """Test Gateway health endpoint."""
    print("\n=== Testing Gateway Health ===")
    try:
        response = requests.get(f"{GATEWAY_URL}/health", timeout=5)
        if response.status_code == 200:
            print(f"✅ Gateway is healthy: {response.text}")
            return True
        else:
            print(f"❌ Gateway returned status {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Gateway connection failed: {e}")
        return False

def test_media_mover_health():
    """Test Media Mover health endpoint."""
    print("\n=== Testing Media Mover Health ===")
    try:
        response = requests.get(f"{MEDIA_MOVER_URL}/health", timeout=5)
        if response.status_code == 200:
            print(f"✅ Media Mover is healthy")
            return True
        else:
            print(f"❌ Media Mover returned status {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Media Mover connection failed: {e}")
        return False

def test_list_videos():
    """Test video listing from database."""
    print("\n=== Testing Video Listing (Database Query) ===")
    try:
        response = requests.get(
            f"{MEDIA_MOVER_URL}/api/v1/media/list",
            params={"split": "temp", "limit": 5, "offset": 0},
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            if data.get("status") == "success":
                items = data.get("data", {}).get("items", [])
                total = data.get("data", {}).get("pagination", {}).get("total", 0)
                print(f"✅ Successfully listed {len(items)} videos (total: {total})")
                
                if items:
                    print("\nSample video:")
                    video = items[0]
                    print(f"  - ID: {video.get('video_id')}")
                    print(f"  - Path: {video.get('file_path')}")
                    print(f"  - Size: {video.get('size_bytes')} bytes")
                    print(f"  - Split: {video.get('split')}")
                return True, items
            else:
                print(f"❌ Unexpected response format: {data}")
                return False, []
        else:
            print(f"❌ List videos failed with status {response.status_code}")
            print(f"Response: {response.text}")
            return False, []
    except Exception as e:
        print(f"❌ List videos failed: {e}")
        return False, []

def test_stage_video_dry_run(video_id):
    """Test video staging to dataset_all (dry run)."""
    print(f"\n=== Testing Video Staging (Dry Run) ===")
    print(f"Video ID: {video_id}")
    
    try:
        correlation_id = f"test-{datetime.now().timestamp()}"
        response = requests.post(
            f"{MEDIA_MOVER_URL}/api/v1/promote/stage",
            json={
                "video_ids": [video_id],
                "label": "happy",
                "dry_run": True
            },
            headers={
                "Content-Type": "application/json",
                "X-Correlation-ID": correlation_id
            },
            timeout=15
        )
        
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text[:500]}")
        
        if response.status_code in [200, 202]:
            print(f"✅ Dry run staging successful")
            return True
        elif response.status_code == 500:
            print(f"❌ Server error - likely database connectivity issue on Ubuntu 1")
            print(f"   Check that REACHY_DATABASE_URL is set correctly on Ubuntu 1")
            print(f"   Expected: postgresql+asyncpg://reachy_dev:PASSWORD@10.0.4.130:5432/reachy_emotion")
            return False
        else:
            print(f"❌ Staging failed with status {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Staging request failed: {e}")
        return False

def main():
    """Run all tests."""
    print("=" * 70)
    print("Web App Database Connectivity Test")
    print("=" * 70)
    
    results = []
    
    # Test 1: Gateway health
    results.append(("Gateway Health", test_gateway_health()))
    
    # Test 2: Media Mover health
    results.append(("Media Mover Health", test_media_mover_health()))
    
    # Test 3: List videos (database query)
    success, videos = test_list_videos()
    results.append(("List Videos (DB)", success))
    
    # Test 4: Stage video (dry run, database write)
    if videos:
        video_id = videos[0].get("video_id")
        results.append(("Stage Video (Dry Run)", test_stage_video_dry_run(video_id)))
    else:
        print("\n⚠️  Skipping stage test - no videos found")
        results.append(("Stage Video (Dry Run)", None))
    
    # Summary
    print("\n" + "=" * 70)
    print("Test Summary")
    print("=" * 70)
    
    for test_name, result in results:
        if result is True:
            status = "✅ PASS"
        elif result is False:
            status = "❌ FAIL"
        else:
            status = "⚠️  SKIP"
        print(f"{test_name:.<50} {status}")
    
    # Overall result
    passed = sum(1 for _, r in results if r is True)
    failed = sum(1 for _, r in results if r is False)
    skipped = sum(1 for _, r in results if r is None)
    
    print("\n" + "=" * 70)
    print(f"Results: {passed} passed, {failed} failed, {skipped} skipped")
    print("=" * 70)
    
    if failed > 0:
        sys.exit(1)
    else:
        sys.exit(0)

if __name__ == "__main__":
    main()
