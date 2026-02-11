"""Integration tests for BargeInHandler with AudioRouter."""

import asyncio
import pytest
from unittest.mock import AsyncMock

from rivaai.config.redis_client import RedisClient
from rivaai.config.settings import Settings
from rivaai.telephony.audio_router import AudioRouter
from rivaai.telephony.barge_in_handler import BargeInHandler
from rivaai.telephony.models import AudioChunk, AudioDirection


@pytest.fixture
def settings():
    """Create test settings."""
    return Settings(
        redis_url="redis://localhost:6379/0",
        redis_max_connections=10,
    )


@pytest.fixture
async def mock_redis_client(settings):
    """Create mock Redis client."""
    client = RedisClient(settings)
    client._client = AsyncMock()
    return client


@pytest.fixture
def audio_router(mock_redis_client, settings):
    """Create AudioRouter instance."""
    return AudioRouter(mock_redis_client, settings)


@pytest.fixture
def barge_in_handler(audio_router):
    """Create BargeInHandler instance integrated with AudioRouter."""
    return BargeInHandler(
        interrupt_callback=audio_router.trigger_barge_in,
        vad_threshold=0.02,
        speech_frames_threshold=3,
        sample_rate=8000,
    )


@pytest.mark.asyncio
class TestBargeInIntegration:
    """Integration tests for BargeInHandler with AudioRouter."""

    async def test_barge_in_triggers_audio_router(
        self, barge_in_handler, audio_router, mock_redis_client
    ):
        """Test that barge-in handler triggers audio router interrupt."""
        call_sid = "test_call_integration"
        
        # Mock Redis operations
        mock_redis_client._client.delete = AsyncMock()
        mock_redis_client._client.set = AsyncMock()
        
        # Trigger barge-in
        await barge_in_handler.trigger_interrupt(call_sid)
        
        # Verify audio router was called
        mock_redis_client._client.set.assert_called_once()
        call_args = mock_redis_client._client.set.call_args
        assert call_args[0][0] == f"barge_in:{call_sid}"

    async def test_barge_in_stops_system_speaking(
        self, barge_in_handler, audio_router, mock_redis_client
    ):
        """Test that barge-in stops system speaking flag."""
        call_sid = "test_call_speaking"
        
        # Set system as speaking
        audio_router._is_system_speaking[call_sid] = True
        assert await audio_router.is_system_speaking(call_sid) is True
        
        # Mock Redis operations
        mock_redis_client._client.delete = AsyncMock()
        mock_redis_client._client.set = AsyncMock()
        
        # Trigger barge-in
        await barge_in_handler.trigger_interrupt(call_sid)
        
        # System should no longer be speaking
        assert await audio_router.is_system_speaking(call_sid) is False

    async def test_monitoring_with_audio_router_stream(
        self, barge_in_handler, audio_router, mock_redis_client
    ):
        """Test monitoring with audio router's stream."""
        call_sid = "test_call_stream"
        
        # Mock Redis operations
        mock_redis_client._client.xadd = AsyncMock()
        mock_redis_client._client.delete = AsyncMock()
        mock_redis_client._client.set = AsyncMock()
        
        # Route some incoming audio
        for i in range(5):
            # High energy audio (speech)
            audio_data = bytes([200, 50, 220, 30] * 40)
            await audio_router.route_incoming_audio(audio_data, call_sid)
        
        # Set system as speaking
        audio_router._is_system_speaking[call_sid] = True
        
        # Create audio stream generator
        async def audio_stream():
            for i in range(5):
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
                audio_stream(),
                call_sid,
                audio_router.is_system_speaking,
            )
        )
        
        # Wait for processing
        await asyncio.sleep(0.1)
        
        # Cancel task
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        
        # Barge-in should have been triggered
        mock_redis_client._client.set.assert_called()

    async def test_latency_requirement_met(
        self, barge_in_handler, audio_router, mock_redis_client
    ):
        """Test that barge-in latency is under 300ms."""
        call_sid = "test_call_latency"
        
        # Mock Redis operations (make them fast)
        mock_redis_client._client.delete = AsyncMock()
        mock_redis_client._client.set = AsyncMock()
        
        # Measure latency
        import time
        start_time = time.time()
        
        await barge_in_handler.trigger_interrupt(call_sid)
        
        end_time = time.time()
        latency_ms = (end_time - start_time) * 1000
        
        # Verify latency is under 300ms
        assert latency_ms < 300, f"Latency {latency_ms}ms exceeds 300ms requirement"

    async def test_cleanup_integration(
        self, barge_in_handler, audio_router, mock_redis_client
    ):
        """Test cleanup of both components."""
        call_sid = "test_call_cleanup_integration"
        
        # Set up state in both components
        audio_router._is_system_speaking[call_sid] = True
        barge_in_handler._speech_frame_counts[call_sid] = 5
        
        # Mock Redis operations
        mock_redis_client._client.delete = AsyncMock()
        
        # Cleanup both
        barge_in_handler.cleanup_call(call_sid)
        await audio_router.cleanup_call_streams(call_sid)
        
        # Verify cleanup
        assert call_sid not in barge_in_handler._speech_frame_counts
        assert call_sid not in audio_router._is_system_speaking

    async def test_multiple_concurrent_calls(
        self, barge_in_handler, audio_router, mock_redis_client
    ):
        """Test handling multiple concurrent calls."""
        call_sids = ["call_1", "call_2", "call_3"]
        
        # Mock Redis operations
        mock_redis_client._client.delete = AsyncMock()
        mock_redis_client._client.set = AsyncMock()
        
        # Set up multiple calls
        for call_sid in call_sids:
            audio_router._is_system_speaking[call_sid] = True
            barge_in_handler._speech_frame_counts[call_sid] = 2
        
        # Trigger barge-in for one call
        await barge_in_handler.trigger_interrupt(call_sids[1])
        
        # Only that call should be affected
        assert await audio_router.is_system_speaking(call_sids[0]) is True
        assert await audio_router.is_system_speaking(call_sids[1]) is False
        assert await audio_router.is_system_speaking(call_sids[2]) is True

    async def test_barge_in_during_outgoing_audio(
        self, barge_in_handler, audio_router, mock_redis_client
    ):
        """Test barge-in while system is outputting audio."""
        call_sid = "test_call_outgoing"
        
        # Mock Redis operations
        mock_redis_client._client.xadd = AsyncMock()
        mock_redis_client._client.delete = AsyncMock()
        mock_redis_client._client.set = AsyncMock()
        
        # Route outgoing audio (system speaking)
        audio_data = bytes([100, 110, 120, 130] * 40)
        await audio_router.route_outgoing_audio(audio_data, call_sid)
        
        # Verify system is speaking
        assert await audio_router.is_system_speaking(call_sid) is True
        
        # Trigger barge-in
        await barge_in_handler.trigger_interrupt(call_sid)
        
        # System should stop speaking
        assert await audio_router.is_system_speaking(call_sid) is False
        
        # Barge-in flag should be set
        mock_redis_client._client.set.assert_called()
        call_args = mock_redis_client._client.set.call_args
        assert call_args[0][0] == f"barge_in:{call_sid}"
