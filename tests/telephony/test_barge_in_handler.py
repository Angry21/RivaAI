"""Unit tests for BargeInHandler."""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock

from rivaai.telephony.barge_in_handler import BargeInHandler
from rivaai.telephony.models import AudioChunk, AudioDirection


@pytest.fixture
def interrupt_callback():
    """Create mock interrupt callback."""
    return AsyncMock()


@pytest.fixture
def is_system_speaking():
    """Create mock is_system_speaking callback."""
    mock = AsyncMock()
    mock.return_value = True  # Default to system speaking
    return mock


@pytest.fixture
def barge_in_handler(interrupt_callback):
    """Create BargeInHandler instance."""
    return BargeInHandler(
        interrupt_callback=interrupt_callback,
        vad_threshold=0.02,
        speech_frames_threshold=3,
        sample_rate=8000,
    )


@pytest.mark.asyncio
class TestBargeInHandler:
    """Test suite for BargeInHandler."""

    async def test_initialization(self, barge_in_handler, interrupt_callback):
        """Test BargeInHandler initialization."""
        assert barge_in_handler.interrupt_callback == interrupt_callback
        assert barge_in_handler.vad_threshold == 0.02
        assert barge_in_handler.speech_frames_threshold == 3
        assert barge_in_handler.sample_rate == 8000

    async def test_detect_voice_activity_silence(self, barge_in_handler):
        """Test VAD with silence (low energy)."""
        # Create silent audio (all zeros)
        silent_audio = bytes([128] * 160)  # 128 is center for μ-law
        
        has_speech = barge_in_handler._detect_voice_activity(silent_audio)
        
        assert has_speech is False

    async def test_detect_voice_activity_speech(self, barge_in_handler):
        """Test VAD with speech (high energy)."""
        # Create audio with high energy (simulating speech)
        speech_audio = bytes([200, 50, 220, 30, 210, 40] * 30)
        
        has_speech = barge_in_handler._detect_voice_activity(speech_audio)
        
        assert has_speech is True

    async def test_detect_voice_activity_empty_audio(self, barge_in_handler):
        """Test VAD with empty audio."""
        empty_audio = b""
        
        has_speech = barge_in_handler._detect_voice_activity(empty_audio)
        
        assert has_speech is False

    async def test_trigger_interrupt_directly(
        self, barge_in_handler, interrupt_callback
    ):
        """Test manually triggering interrupt."""
        call_sid = "test_call_123"
        
        await barge_in_handler.trigger_interrupt(call_sid)
        
        interrupt_callback.assert_called_once_with(call_sid)

    async def test_monitor_triggers_on_speech_threshold(
        self, barge_in_handler, interrupt_callback, is_system_speaking
    ):
        """Test that monitoring triggers interrupt after speech threshold."""
        call_sid = "test_call_456"
        
        # Create audio stream with speech
        async def audio_stream():
            for i in range(5):
                # High energy audio (speech)
                audio_data = bytes([200, 50, 220, 30] * 40)
                chunk = AudioChunk(
                    call_sid=call_sid,
                    audio_data=audio_data,
                    timestamp=float(i),
                    sequence_number=i,
                    direction=AudioDirection.INCOMING,
                )
                yield chunk
                await asyncio.sleep(0.01)
        
        # Start monitoring
        task = asyncio.create_task(
            barge_in_handler.monitor_user_audio(
                audio_stream(), call_sid, is_system_speaking
            )
        )
        
        # Wait a bit for processing
        await asyncio.sleep(0.1)
        
        # Cancel task
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        
        # Should have triggered interrupt (threshold is 3 frames)
        assert interrupt_callback.call_count >= 1

    async def test_monitor_no_trigger_when_system_not_speaking(
        self, barge_in_handler, interrupt_callback, is_system_speaking
    ):
        """Test that monitoring doesn't trigger when system is not speaking."""
        call_sid = "test_call_789"
        
        # System is NOT speaking
        is_system_speaking.return_value = False
        
        # Create audio stream with speech
        async def audio_stream():
            for i in range(5):
                # High energy audio (speech)
                audio_data = bytes([200, 50, 220, 30] * 40)
                chunk = AudioChunk(
                    call_sid=call_sid,
                    audio_data=audio_data,
                    timestamp=float(i),
                    sequence_number=i,
                    direction=AudioDirection.INCOMING,
                )
                yield chunk
                await asyncio.sleep(0.01)
        
        # Start monitoring
        task = asyncio.create_task(
            barge_in_handler.monitor_user_audio(
                audio_stream(), call_sid, is_system_speaking
            )
        )
        
        # Wait a bit for processing
        await asyncio.sleep(0.1)
        
        # Cancel task
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        
        # Should NOT have triggered interrupt
        interrupt_callback.assert_not_called()

    async def test_monitor_resets_counter_on_silence(
        self, barge_in_handler, interrupt_callback, is_system_speaking
    ):
        """Test that speech counter resets on silence."""
        call_sid = "test_call_reset"
        
        # Create audio stream with speech then silence
        async def audio_stream():
            # 2 frames of speech (below threshold of 3)
            for i in range(2):
                audio_data = bytes([200, 50, 220, 30] * 40)
                chunk = AudioChunk(
                    call_sid=call_sid,
                    audio_data=audio_data,
                    timestamp=float(i),
                    sequence_number=i,
                    direction=AudioDirection.INCOMING,
                )
                yield chunk
                await asyncio.sleep(0.01)
            
            # 1 frame of silence (should reset counter)
            audio_data = bytes([128] * 160)
            chunk = AudioChunk(
                call_sid=call_sid,
                audio_data=audio_data,
                timestamp=2.0,
                sequence_number=2,
                direction=AudioDirection.INCOMING,
            )
            yield chunk
            await asyncio.sleep(0.01)
            
            # 2 more frames of speech (still below threshold)
            for i in range(3, 5):
                audio_data = bytes([200, 50, 220, 30] * 40)
                chunk = AudioChunk(
                    call_sid=call_sid,
                    audio_data=audio_data,
                    timestamp=float(i),
                    sequence_number=i,
                    direction=AudioDirection.INCOMING,
                )
                yield chunk
                await asyncio.sleep(0.01)
        
        # Start monitoring
        task = asyncio.create_task(
            barge_in_handler.monitor_user_audio(
                audio_stream(), call_sid, is_system_speaking
            )
        )
        
        # Wait for processing
        await asyncio.sleep(0.15)
        
        # Cancel task
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        
        # Should NOT have triggered (counter reset by silence)
        interrupt_callback.assert_not_called()

    async def test_start_monitoring_creates_background_task(
        self, barge_in_handler, is_system_speaking
    ):
        """Test that start_monitoring creates a background task."""
        call_sid = "test_call_bg"
        
        async def audio_stream():
            for i in range(3):
                chunk = AudioChunk(
                    call_sid=call_sid,
                    audio_data=bytes([128] * 160),
                    timestamp=float(i),
                    sequence_number=i,
                    direction=AudioDirection.INCOMING,
                )
                yield chunk
                await asyncio.sleep(0.01)
        
        task = barge_in_handler.start_monitoring(
            audio_stream(), call_sid, is_system_speaking
        )
        
        assert task is not None
        assert not task.done()
        assert call_sid in barge_in_handler._monitoring_tasks
        
        # Cleanup
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

    async def test_stop_monitoring_cancels_task(
        self, barge_in_handler, is_system_speaking
    ):
        """Test that stop_monitoring cancels the background task."""
        call_sid = "test_call_stop"
        
        async def audio_stream():
            while True:
                chunk = AudioChunk(
                    call_sid=call_sid,
                    audio_data=bytes([128] * 160),
                    timestamp=0.0,
                    sequence_number=0,
                    direction=AudioDirection.INCOMING,
                )
                yield chunk
                await asyncio.sleep(0.01)
        
        task = barge_in_handler.start_monitoring(
            audio_stream(), call_sid, is_system_speaking
        )
        
        # Stop monitoring
        barge_in_handler.stop_monitoring(call_sid)
        
        # Give task a moment to process cancellation
        await asyncio.sleep(0.01)
        
        # Task should be cancelled
        assert task.cancelled() or task.done()
        assert call_sid not in barge_in_handler._monitoring_tasks

    async def test_cleanup_call_removes_state(
        self, barge_in_handler, is_system_speaking
    ):
        """Test that cleanup_call removes all state for a call."""
        call_sid = "test_call_cleanup"
        
        # Set up some state
        barge_in_handler._speech_frame_counts[call_sid] = 5
        barge_in_handler._last_detection_time[call_sid] = 123.456
        
        async def audio_stream():
            chunk = AudioChunk(
                call_sid=call_sid,
                audio_data=bytes([128] * 160),
                timestamp=0.0,
                sequence_number=0,
                direction=AudioDirection.INCOMING,
            )
            yield chunk
        
        task = barge_in_handler.start_monitoring(
            audio_stream(), call_sid, is_system_speaking
        )
        
        # Cleanup
        barge_in_handler.cleanup_call(call_sid)
        
        # All state should be removed
        assert call_sid not in barge_in_handler._speech_frame_counts
        assert call_sid not in barge_in_handler._last_detection_time
        assert call_sid not in barge_in_handler._monitoring_tasks

    async def test_get_last_detection_latency(self, barge_in_handler):
        """Test getting last detection latency."""
        call_sid = "test_call_latency"
        
        # No detection yet
        latency = barge_in_handler.get_last_detection_latency(call_sid)
        assert latency is None
        
        # Trigger interrupt
        await barge_in_handler.trigger_interrupt(call_sid)
        
        # Should have latency now
        latency = barge_in_handler.get_last_detection_latency(call_sid)
        assert latency is not None
        assert latency >= 0

    async def test_latency_warning_logged(
        self, barge_in_handler, interrupt_callback, caplog
    ):
        """Test that warning is logged if latency exceeds 300ms."""
        call_sid = "test_call_slow"
        
        # Make callback slow
        async def slow_callback(call_sid):
            await asyncio.sleep(0.35)  # 350ms
        
        barge_in_handler.interrupt_callback = slow_callback
        
        # Trigger interrupt
        await barge_in_handler.trigger_interrupt(call_sid)
        
        # Check for warning in logs
        assert any("exceeded 300ms" in record.message for record in caplog.records)

    async def test_multiple_calls_independent_state(
        self, barge_in_handler, interrupt_callback, is_system_speaking
    ):
        """Test that multiple calls maintain independent state."""
        call_sid_1 = "test_call_1"
        call_sid_2 = "test_call_2"
        
        # Set up state for both calls
        barge_in_handler._speech_frame_counts[call_sid_1] = 2
        barge_in_handler._speech_frame_counts[call_sid_2] = 1
        
        # Verify independent state
        assert barge_in_handler._speech_frame_counts[call_sid_1] == 2
        assert barge_in_handler._speech_frame_counts[call_sid_2] == 1
        
        # Cleanup one call
        barge_in_handler.cleanup_call(call_sid_1)
        
        # Only call_sid_1 should be removed
        assert call_sid_1 not in barge_in_handler._speech_frame_counts
        assert call_sid_2 in barge_in_handler._speech_frame_counts

    async def test_vad_threshold_configurable(self, interrupt_callback):
        """Test that VAD threshold is configurable."""
        # Create handler with high threshold
        handler = BargeInHandler(
            interrupt_callback=interrupt_callback,
            vad_threshold=0.5,  # High threshold
            speech_frames_threshold=3,
        )
        
        # Medium energy audio
        audio_data = bytes([150, 100, 160, 90] * 40)
        
        # Should not detect speech with high threshold
        has_speech = handler._detect_voice_activity(audio_data)
        assert has_speech is False
        
        # Create handler with low threshold
        handler_low = BargeInHandler(
            interrupt_callback=interrupt_callback,
            vad_threshold=0.01,  # Low threshold
            speech_frames_threshold=3,
        )
        
        # Should detect speech with low threshold
        has_speech = handler_low._detect_voice_activity(audio_data)
        assert has_speech is True

    async def test_speech_frames_threshold_configurable(self, interrupt_callback):
        """Test that speech frames threshold is configurable."""
        # Create handler with threshold of 1
        handler = BargeInHandler(
            interrupt_callback=interrupt_callback,
            vad_threshold=0.02,
            speech_frames_threshold=1,  # Trigger immediately
        )
        
        assert handler.speech_frames_threshold == 1
        
        # Create handler with threshold of 5
        handler_high = BargeInHandler(
            interrupt_callback=interrupt_callback,
            vad_threshold=0.02,
            speech_frames_threshold=5,  # Require 5 frames
        )
        
        assert handler_high.speech_frames_threshold == 5
