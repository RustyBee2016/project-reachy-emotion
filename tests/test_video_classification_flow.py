#!/usr/bin/env python3
"""
Step-by-step diagnostic tests for video classification flow.
Tests each component individually to isolate the 404 error.
"""

import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Test configuration
TEST_VIDEO_FILENAME = "test_video_happy.mp4"
TEST_EMOTION = "happy"


def test_step_1_environment_variables():
    """Step 1: Check environment variables affecting API URLs."""
    print("\n" + "="*60)
    print("STEP 1: Environment Variables")
    print("="*60)
    
    env_vars = {
        "REACHY_API_BASE": os.getenv("REACHY_API_BASE"),
        "REACHY_GATEWAY_BASE": os.getenv("REACHY_GATEWAY_BASE"),
        "REACHY_API_TOKEN": os.getenv("REACHY_API_TOKEN"),
    }
    
    for key, value in env_vars.items():
        status = "✅ SET" if value else "⚠️  NOT SET (using default)"
        print(f"  {key}: {value or 'None'} {status}")
    
    # Check if environment is overriding defaults
    if env_vars["REACHY_API_BASE"]:
        print(f"\n⚠️  WARNING: REACHY_API_BASE is set to: {env_vars['REACHY_API_BASE']}")
        print("   This overrides the default localhost:8083")
        return False
    
    print("\n✅ No environment overrides detected")
    return True


def test_step_2_api_client_configuration():
    """Step 2: Verify api_client.py configuration."""
    print("\n" + "="*60)
    print("STEP 2: API Client Configuration")
    print("="*60)
    
    try:
        from apps.web import api_client
        
        base_url = api_client._base_url()
        gateway_base = api_client._gateway_base()
        
        print(f"  Media API Base: {base_url}")
        print(f"  Gateway Base: {gateway_base}")
        
        # Expected values
        expected_media = "http://localhost:8083/api/media"
        expected_gateway = "http://localhost:8000"
        
        media_correct = base_url == expected_media
        gateway_correct = gateway_base == expected_gateway
        
        if media_correct:
            print(f"  ✅ Media API Base is correct")
        else:
            print(f"  ❌ Media API Base is WRONG")
            print(f"     Expected: {expected_media}")
            print(f"     Got: {base_url}")
        
        if gateway_correct:
            print(f"  ✅ Gateway Base is correct")
        else:
            print(f"  ⚠️  Gateway Base mismatch")
            print(f"     Expected: {expected_gateway}")
            print(f"     Got: {gateway_base}")
        
        return media_correct
        
    except Exception as e:
        print(f"  ❌ Error importing api_client: {e}")
        return False


def test_step_3_list_videos_endpoint():
    """Step 3: Test the list_videos endpoint directly."""
    print("\n" + "="*60)
    print("STEP 3: List Videos Endpoint")
    print("="*60)
    
    try:
        import requests
        from apps.web import api_client
        
        base_url = api_client._base_url()
        
        # Test the actual endpoint being called
        test_url = f"{base_url}/videos/list"
        print(f"  Testing URL: {test_url}")
        print(f"  Parameters: split=temp, limit=5, offset=0")
        
        response = requests.get(
            test_url,
            params={"split": "temp", "limit": 5, "offset": 0},
            headers=api_client._headers(),
            timeout=10
        )
        
        print(f"  HTTP Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"  ✅ Success! Response keys: {list(data.keys())}")
            
            # Check response structure
            if "items" in data or "videos" in data:
                videos_key = "items" if "items" in data else "videos"
                videos = data.get(videos_key, [])
                print(f"  Videos found: {len(videos)}")
                
                if videos:
                    print(f"  Sample video keys: {list(videos[0].keys())}")
                    if "video_id" in videos[0]:
                        print(f"  ✅ video_id field present")
                    else:
                        print(f"  ⚠️  video_id field MISSING")
                        print(f"     Available fields: {list(videos[0].keys())}")
            
            return True
        elif response.status_code == 404:
            print(f"  ❌ 404 Not Found - Endpoint doesn't exist")
            print(f"  Response: {response.text[:200]}")
            return False
        elif response.status_code == 500:
            print(f"  ❌ 500 Internal Server Error")
            print(f"  Response: {response.text[:200]}")
            return False
        else:
            print(f"  ⚠️  Unexpected status code: {response.status_code}")
            print(f"  Response: {response.text[:200]}")
            return False
            
    except requests.exceptions.ConnectionError as e:
        print(f"  ❌ Connection Error: Cannot reach {test_url}")
        print(f"  Is the FastAPI service running on port 8083?")
        return False
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return False


def test_step_4_api_client_list_videos():
    """Step 4: Test api_client.list_videos() function."""
    print("\n" + "="*60)
    print("STEP 4: api_client.list_videos() Function")
    print("="*60)
    
    try:
        from apps.web import api_client
        
        print(f"  Calling: api_client.list_videos(split='temp', limit=5)")
        
        result = api_client.list_videos(split="temp", limit=5, offset=0)
        
        print(f"  ✅ Success! Response type: {type(result)}")
        print(f"  Response keys: {list(result.keys())}")
        
        # Check for videos
        videos_key = None
        for key in ["items", "videos", "data"]:
            if key in result:
                videos_key = key
                break
        
        if videos_key:
            videos = result[videos_key]
            print(f"  Videos found: {len(videos)}")
            return True
        else:
            print(f"  ⚠️  No videos array found in response")
            print(f"  Available keys: {list(result.keys())}")
            return False
            
    except Exception as e:
        print(f"  ❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_step_5_refresh_video_metadata():
    """Step 5: Test _refresh_video_metadata() logic."""
    print("\n" + "="*60)
    print("STEP 5: _refresh_video_metadata() Logic")
    print("="*60)
    
    try:
        from apps.web import api_client
        
        # Simulate the current_video dict from session state
        test_current = {
            "path": f"/tmp/{TEST_VIDEO_FILENAME}",
            "name": TEST_VIDEO_FILENAME,
            "for_training": False,
            "correlation_id": "test-correlation-id",
        }
        
        print(f"  Test video filename: {TEST_VIDEO_FILENAME}")
        print(f"  Querying temp videos to find matching file...")
        
        # Get list of temp videos
        listing = api_client.list_videos(split="temp", limit=200, offset=0)
        
        videos_key = "items" if "items" in listing else "videos"
        videos = listing.get(videos_key, [])
        
        print(f"  Found {len(videos)} videos in temp/")
        
        # Try to find matching video
        found = False
        for item in videos:
            file_path = item.get("file_path")
            if file_path:
                item_filename = Path(file_path).name
                print(f"    - {item_filename}")
                
                if item_filename == TEST_VIDEO_FILENAME:
                    video_id = item.get("video_id")
                    print(f"  ✅ Found matching video!")
                    print(f"     video_id: {video_id}")
                    print(f"     file_path: {file_path}")
                    found = True
                    break
        
        if not found:
            print(f"  ⚠️  No matching video found for: {TEST_VIDEO_FILENAME}")
            print(f"  This is expected if you haven't generated a video yet")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_step_6_stage_to_dataset_all():
    """Step 6: Test stage_to_dataset_all() endpoint."""
    print("\n" + "="*60)
    print("STEP 6: stage_to_dataset_all() Endpoint")
    print("="*60)
    
    try:
        import requests
        from apps.web import api_client
        import uuid
        
        # Use a fake UUID for dry-run test
        test_video_id = str(uuid.uuid4())
        
        print(f"  Testing with fake video_id: {test_video_id}")
        print(f"  Emotion label: {TEST_EMOTION}")
        print(f"  Dry run: True")
        
        base_url = api_client._base_url()
        url = f"{base_url}/promote/stage"
        
        print(f"  URL: {url}")
        
        payload = {
            "video_ids": [test_video_id],
            "label": TEST_EMOTION,
            "dry_run": True,
        }
        
        response = requests.post(
            url,
            json=payload,
            headers={**api_client._headers(), "X-Correlation-ID": "test-correlation"},
            timeout=30
        )
        
        print(f"  HTTP Status: {response.status_code}")
        
        if response.status_code == 202:
            data = response.json()
            print(f"  ✅ Success! Endpoint is working")
            print(f"  Response: {data}")
            return True
        elif response.status_code == 404:
            print(f"  ❌ 404 - Video not found (expected for fake ID)")
            print(f"  Response: {response.json()}")
            return True  # This is actually OK for a fake ID
        elif response.status_code == 422:
            print(f"  ⚠️  422 - Validation error")
            print(f"  Response: {response.json()}")
            return False
        else:
            print(f"  ❌ Unexpected status: {response.status_code}")
            print(f"  Response: {response.text[:200]}")
            return False
            
    except Exception as e:
        print(f"  ❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all diagnostic tests in sequence."""
    print("\n" + "="*70)
    print("VIDEO CLASSIFICATION FLOW - DIAGNOSTIC TESTS")
    print("="*70)
    print("\nThis will test each step of the video classification process")
    print("to identify where the 404 error is occurring.\n")
    
    results = {}
    
    # Run tests in sequence
    results["Step 1: Environment Variables"] = test_step_1_environment_variables()
    results["Step 2: API Client Config"] = test_step_2_api_client_configuration()
    results["Step 3: List Videos Endpoint"] = test_step_3_list_videos_endpoint()
    results["Step 4: list_videos() Function"] = test_step_4_api_client_list_videos()
    results["Step 5: Refresh Metadata Logic"] = test_step_5_refresh_video_metadata()
    results["Step 6: stage_to_dataset_all()"] = test_step_6_stage_to_dataset_all()
    
    # Summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    
    all_passed = True
    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {status}  {test_name}")
        if not passed:
            all_passed = False
    
    print("\n" + "="*70)
    
    if all_passed:
        print("✅ All tests passed! The system should be working.")
    else:
        print("❌ Some tests failed. Review the output above for details.")
        print("\nCommon fixes:")
        print("  1. Check if REACHY_API_BASE environment variable is set incorrectly")
        print("  2. Verify FastAPI service is running on port 8083")
        print("  3. Check if the /api/media/videos/list endpoint exists")
    
    print("="*70 + "\n")
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
