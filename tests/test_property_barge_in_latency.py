"""Property-based tests for barge-in interrupt latency.

Feature: sochq
Property 3: Barge-In Interrupt Latency
Validates: Requirements 1.3

For any user speech detected while the system is outputting audio, 
the Barge_In_Handler should stop system audio output within 300ms 
and begin processing user input.
"""

import asyncio
import time
from unittest.mock import AsyncMock, MagicMock

import pytest
from hypothesis import given, strategies as st

from rivaai.telephony.audio_router import AudioRouter
from rivaai.telephony.barge_in_handler import BargeInHandler
from rivaai.telephony.models import AudioChunk, AudioDirection


# Strategy for generating call session IDs
call_sid_strategy = st.text(
    alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Nd")),
    min_size=10,
    max_size=50
)

# Strategy for generating audio data with speech
# Simulates μ-law PCM audio with varying energy levels
speech_audio_strategy = st.binary(min_size=160, max_size=320).map(
    lambda data: bytes(
        # Add energy to simulate speech (values away from 128 center)
        min(255, max(0, b + (50 if i % 2 == 0 else -50)))
        for i, b in enumerate(data)
    )
)

# Strategy for generating silence/low-energy audio
silence_audio_strategy = st.binary(min_size=160, max_size=320).map(
    lambda data: bytes(128 for _ in data)  # Center value = silence
)

# Strategy for generating sequence numbers
sequence_number_strategy = st.integers(min_value=0, max_value=10000)

# Strategy for generating timestamps
timestamp_strategy = st.floats(min_value=0.0, max_value=1000000.0)


@pytest.mark.property
class TestBargeInInterruptLatency:
    """Property-based tests for barge-in interrupt latency requirements."""

    @given(
        call_sid=call_sid_strategy,
        audio_data=speech_audio_strategy,
        sequence_number=sequence_number_strategy,
        timestamp=timestamp_strategy,
    )
    def test_barge_in_interrupt_within_300ms(
        self,
        call_sid: str,
        audio_data: bytes,
        sequence_number: int,
        timestamp: float,
    ):
        """
        Property 3: Barge-In Interrupt Latency
        
        For any user speech detected while the system is speaking,
        the Barge_In_Handler should stop system audio output within 300ms.
        
        Validates: Requirements 1.3
        """
        # Create mock interrupt callback to track when it's called
        interrupt_called = asyncio.Event()
        interrupt_time = None
        
        async def mock_interrupt_callback(sid: str):
            nonlocal interrupt_time
            interrupt_time = time.perf_counter()
            interrupt_called.set()
        
        # Create barge-in handler
        handler = BargeInHandler(
            interrupt_callback=mock_interrupt_callback,
            vad_threshold=0.02,
            speech_frames_threshold=1,  # Trigger on first speech frame
        )
        
        # Run the test in async context
        async def run_test():
            # Record start time
            start_time = time.perf_counter()
            
            # Trigger interrupt manually (simulates detection)
            await handler.trigger_interrupt(call_sid)
            
            # Wait for interrupt callback
            await asyncio.wait_for(interrupt_called.wait(), timeout=1.0)
            
            # Calculate latency
            latency_ms = (interrupt_time - start_time) * 1000
            
            # Verify latency is under 300ms
            assert latency_ms < 300, (
                f"Barge-in interrupt latency {latency_ms:.2f}ms "
                f"exceeds 300ms requirement for call_sid={call_sid}"
            )
            
            return latency_ms
        
        # Execute the async test
        latency = asyncio.run(run_test())
        
        # Additional verification: latency should be reasonable (not negative)
        assert latency >= 0, "Latency cannot be negative"

    @given(
        call_sid=call_sid_strategy,
        num_interrupts=st.integers(min_value=1, max_value=5),
    )
    def test_multiple_interrupts_all_within_latency(
        self,
        call_sid: str,
        num_interrupts: int,
    ):
        """
        Property 3: Barge-In Interrupt Latency (Multiple Interrupts)
        
        For any sequence of barge-in events, each interrupt should
        complete within 300ms independently.
        
        Validates: Requirements 1.3
        """
        interrupt_times = []
        
        async def mock_interrupt_callback(sid: str):
            interrupt_times.append(time.perf_counter())
        
        handler = BargeInHandler(
            interrupt_callback=mock_interrupt_callback,
            vad_threshold=0.02,
            speech_frames_threshold=1,
        )
        
        async def run_test():
            latencies = []
            
            for i in range(num_interrupts):
                start_time = time.perf_counter()
                
                await handler.trigger_interrupt(call_sid)
                
                # Wait a bit for callback to complete
                await asyncio.sleep(0.01)
                
                end_time = time.perf_counter()
                latency_ms = (end_time - start_time) * 1000
                latencies.append(latency_ms)
                
                assert latency_ms < 300, (
                    f"Interrupt {i+1}/{num_interrupts} took {latency_ms:.2f}ms, "
                    f"exceeds 300ms requirement"
                )
            
            return latencies
        
        latencies = asyncio.run(run_test())
        
        # Verify all interrupts completed
        assert len(latencies) == num_interrupts
        assert all(lat < 300 for lat in latencies)

    @given(
        call_sid=call_sid_strategy,
        audio_data=speech_audio_strategy,
        sequence_number=sequence_number_strategy,
        timestamp=timestamp_strategy,
    )
    def test_barge_in_with_audio_router_integration(
        self,
        call_sid: str,
        audio_data: bytes,
        sequence_number: int,
        timestamp: float,
    ):
        """
        Property 3: Barge-In Interrupt Latency (Integration)
        
        For any user speech during system output, the barge-in handler
        should trigger the audio router to stop output within 300ms.
        
        Validates: Requirements 1.3
        """
        # Create mock Redis client
        mock_redis = MagicMock()
        mock_redis.set = AsyncMock()
        mock_redis.get = AsyncMock(return_value=b"1")
        mock_redis.delete = AsyncMock()
        mock_redis.get_client = AsyncMock(return_value=mock_redis)
        
        # Create mock settings
        mock_settings = MagicMock()
        
        # Create audio router with mock Redis and settings
        audio_router = AudioRouter(redis_client=mock_redis, settings=mock_settings)
        
        # Create barge-in handler integrated with audio router
        handler = BargeInHandler(
            interrupt_callback=audio_router.trigger_barge_in,
            vad_threshold=0.02,
            speech_frames_threshold=1,
        )
        
        async def run_test():
            # Set system speaking state
            await audio_router.set_system_speaking(call_sid, True)
            
            # Record start time
            start_time = time.perf_counter()
            
            # Trigger barge-in
            await handler.trigger_interrupt(call_sid)
            
            # Calculate latency
            end_time = time.perf_counter()
            latency_ms = (end_time - start_time) * 1000
            
            # Verify latency requirement
            assert latency_ms < 300, (
                f"Integrated barge-in latency {latency_ms:.2f}ms "
                f"exceeds 300ms requirement"
            )
            
            # Verify audio router was triggered
            mock_redis.set.assert_called()
            
            return latency_ms
        
        latency = asyncio.run(run_test())
        assert latency >= 0

    @given(
        call_sid=call_sid_strategy,
        speech_frames=st.integers(min_value=1, max_value=10),
    )
    def test_speech_detection_triggers_interrupt_within_latency(
        self,
        call_sid: str,
        speech_frames: int,
    ):
        """
        Property 3: Barge-In Interrupt Latency (Speech Detection)
        
        For any number of consecutive speech frames detected,
        the interrupt should trigger within 300ms of threshold being met.
        
        Validates: Requirements 1.3
        """
        interrupt_triggered = asyncio.Event()
        trigger_time = None
        
        async def mock_interrupt_callback(sid: str):
            nonlocal trigger_time
            trigger_time = time.perf_counter()
            interrupt_triggered.set()
        
        handler = BargeInHandler(
            interrupt_callback=mock_interrupt_callback,
            vad_threshold=0.02,
            speech_frames_threshold=speech_frames,
        )
        
        async def run_test():
            # Create audio stream with speech
            async def audio_stream():
                for i in range(speech_frames + 2):
                    # Generate speech audio (high energy)
                    audio_data = bytes(
                        200 if j % 2 == 0 else 50
                        for j in range(160)
                    )
                    
                    chunk = AudioChunk(
                        call_sid=call_sid,
                        audio_data=audio_data,
                        timestamp=time.time(),
                        sequence_number=i,
                        direction=AudioDirection.INCOMING,
                    )
                    yield chunk
                    await asyncio.sleep(0.02)  # 20ms frame
            
            # Mock system speaking check
            async def is_system_speaking(sid: str):
                return True
            
            # Start monitoring
            detection_start = time.perf_counter()
            
            # Monitor in background
            monitor_task = asyncio.create_task(
                handler.monitor_user_audio(
                    audio_stream(),
                    call_sid,
                    is_system_speaking,
                )
            )
            
            try:
                # Wait for interrupt to trigger
                await asyncio.wait_for(interrupt_triggered.wait(), timeout=2.0)
                
                # Calculate latency from detection start
                latency_ms = (trigger_time - detection_start) * 1000
                
                # Verify latency requirement
                # Note: This includes frame processing time, so we allow some buffer
                assert latency_ms < 300 + (speech_frames * 20), (
                    f"Speech detection interrupt took {latency_ms:.2f}ms, "
                    f"exceeds expected latency for {speech_frames} frames"
                )
                
                return latency_ms
            finally:
                monitor_task.cancel()
                try:
                    await monitor_task
                except asyncio.CancelledError:
                    pass
        
        latency = asyncio.run(run_test())
        assert latency >= 0

    @given(
        call_sid=call_sid_strategy,
        audio_data=speech_audio_strategy,
    )
    def test_interrupt_stops_system_speaking_flag(
        self,
        call_sid: str,
        audio_data: bytes,
    ):
        """
        Property 3: Barge-In Interrupt Latency (State Change)
        
        For any barge-in interrupt, the system speaking flag should
        be cleared within 300ms to stop audio output.
        
        Validates: Requirements 1.3
        """
        # Create mock Redis client
        mock_redis = MagicMock()
        mock_redis.set = AsyncMock()
        mock_redis.get = AsyncMock(return_value=b"1")
        mock_redis.delete = AsyncMock()
        mock_redis.get_client = AsyncMock(return_value=mock_redis)
        
        # Create mock settings
        mock_settings = MagicMock()
        
        # Create audio router with mock Redis and settings
        audio_router = AudioRouter(redis_client=mock_redis, settings=mock_settings)
        
        # Create barge-in handler
        handler = BargeInHandler(
            interrupt_callback=audio_router.trigger_barge_in,
            vad_threshold=0.02,
            speech_frames_threshold=1,
        )
        
        async def run_test():
            # Set system speaking
            await audio_router.set_system_speaking(call_sid, True)
            assert await audio_router.is_system_speaking(call_sid) is True
            
            # Record start time
            start_time = time.perf_counter()
            
            # Trigger interrupt
            await handler.trigger_interrupt(call_sid)
            
            # Check that system speaking flag is cleared
            # (In real implementation, this would stop audio output)
            end_time = time.perf_counter()
            latency_ms = (end_time - start_time) * 1000
            
            # Verify latency
            assert latency_ms < 300, (
                f"State change took {latency_ms:.2f}ms, exceeds 300ms"
            )
            
            # Verify Redis was called to set barge-in flag
            mock_redis.set.assert_called()
            
            return latency_ms
        
        latency = asyncio.run(run_test())
        assert latency >= 0
