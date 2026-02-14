#!/usr/bin/env python3
"""Quick test script to verify Reachy modules load correctly."""

import sys
sys.path.insert(0, "d:\\projects\\reachy_emotion")

def test_gesture_definitions():
    """Test gesture definitions module."""
    from apps.reachy.gestures.gesture_definitions import (
        GestureType, GESTURE_LIBRARY, get_gesture, list_gestures
    )
    
    print(f"✓ Gesture types defined: {len(GestureType)}")
    print(f"✓ Gestures in library: {len(GESTURE_LIBRARY)}")
    print(f"✓ Gesture names: {list_gestures()[:5]}...")
    
    wave = get_gesture(GestureType.WAVE)
    print(f"✓ Wave gesture: {wave.name} ({wave.total_duration}s)")
    
    return True

def test_emotion_gesture_map():
    """Test emotion-to-gesture mapping."""
    from apps.reachy.gestures.emotion_gesture_map import (
        EmotionGestureMapper, GestureKeyword
    )
    
    mapper = EmotionGestureMapper()
    
    # Test keyword parsing
    response = "I hear you [LISTEN]. That sounds difficult [EMPATHY]."
    keywords = mapper.parse_keywords_from_response(response)
    print(f"✓ Parsed keywords: {[k.value for k in keywords]}")
    
    # Test gesture extraction
    gestures = mapper.extract_gestures_from_response(response)
    print(f"✓ Extracted gestures: {[g.name for g in gestures]}")
    
    # Test emotion mapping
    happy_gestures = mapper.get_gestures_for_emotion("happy")
    print(f"✓ Happy gestures: {[g.name for g in happy_gestures[:3]]}...")
    
    # Test clean response
    clean = mapper.strip_keywords_from_response(response)
    print(f"✓ Clean response: '{clean}'")
    
    return True

def test_llm_prompts():
    """Test LLM prompt building."""
    from apps.llm.prompts.emotion_prompts import EmotionPromptBuilder
    
    builder = EmotionPromptBuilder(include_gestures=True)
    
    happy_prompt = builder.build_system_prompt("happy", confidence=0.9)
    print(f"✓ Happy prompt length: {len(happy_prompt)} chars")
    
    sad_prompt = builder.build_system_prompt("sad", confidence=0.85)
    print(f"✓ Sad prompt length: {len(sad_prompt)} chars")
    
    return True

def test_mock_llm_client():
    """Test mock LLM client."""
    import asyncio
    from apps.llm.client import MockEmpatheticLLMClient
    
    async def run_test():
        client = MockEmpatheticLLMClient()
        
        response = await client.generate_response(
            user_message="I'm feeling down today.",
            emotion="sad",
            confidence=0.9
        )
        
        print(f"✓ LLM response: '{response.clean_content[:50]}...'")
        print(f"✓ Gesture keywords: {response.gesture_keywords}")
        print(f"✓ Latency: {response.latency_ms:.1f}ms")
        
        await client.close()
        return True
    
    return asyncio.run(run_test())

def test_gesture_controller():
    """Test gesture controller in simulation mode."""
    import asyncio
    from apps.reachy.config import ReachyConfig
    from apps.reachy.gestures.gesture_controller import GestureController
    from apps.reachy.gestures.gesture_definitions import GestureType
    
    async def run_test():
        config = ReachyConfig(simulation_mode=True)
        controller = GestureController(config)
        
        await controller.connect()
        print(f"✓ Controller connected (simulation mode)")
        
        result = await controller.execute_gesture_by_type(GestureType.NOD)
        print(f"✓ Executed NOD gesture: {result.success} ({result.duration_ms:.1f}ms)")
        
        await controller.disconnect()
        return True
    
    return asyncio.run(run_test())

def test_pipeline():
    """Test the full emotion-LLM-gesture pipeline."""
    import asyncio
    from datetime import datetime, timezone
    from apps.pipeline.emotion_llm_gesture import (
        EmotionLLMGesturePipeline, PipelineConfig, EmotionEvent
    )
    from apps.reachy.config import ReachyConfig
    
    async def run_test():
        config = PipelineConfig(
            use_mock_llm=True,
            reachy_config=ReachyConfig(simulation_mode=True),
            enable_gestures=True
        )
        
        pipeline = EmotionLLMGesturePipeline(config)
        await pipeline.start()
        print(f"✓ Pipeline started: {pipeline.state.value}")
        
        event = EmotionEvent(
            emotion="sad",
            confidence=0.88,
            device_id="test-device",
            timestamp=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        )
        
        result = await pipeline.process_emotion_with_message(
            event=event,
            user_message="I'm feeling a bit down today."
        )
        
        print(f"✓ Pipeline result: success={result.success}")
        if result.llm_response:
            print(f"✓ Response: '{result.llm_response.clean_content[:50]}...'")
            print(f"✓ Gestures triggered: {result.llm_response.gesture_keywords}")
        print(f"✓ Processing time: {result.processing_time_ms:.1f}ms")
        
        await pipeline.stop()
        return True
    
    return asyncio.run(run_test())


if __name__ == "__main__":
    print("=" * 60)
    print("Reachy Mini Integration Module Tests")
    print("=" * 60)
    
    tests = [
        ("Gesture Definitions", test_gesture_definitions),
        ("Emotion-Gesture Mapping", test_emotion_gesture_map),
        ("LLM Prompts", test_llm_prompts),
        ("Mock LLM Client", test_mock_llm_client),
        ("Gesture Controller", test_gesture_controller),
        ("Full Pipeline", test_pipeline),
    ]
    
    passed = 0
    failed = 0
    
    for name, test_func in tests:
        print(f"\n--- {name} ---")
        try:
            if test_func():
                passed += 1
                print(f"PASSED: {name}")
            else:
                failed += 1
                print(f"FAILED: {name}")
        except Exception as e:
            failed += 1
            print(f"ERROR: {name} - {e}")
    
    print("\n" + "=" * 60)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 60)
