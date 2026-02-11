"""Unit tests for AudioRouter."""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from rivaai.config.redis_client import RedisClient
from rivaai.config.settings import Settings
from rivaai.telephony.audio_router import AudioRouter
from rivaai.telephony.models import AudioDirection


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


@pytest.mark.asyncio
class TestAudioRouter:
    """Test suite for AudioRouter."""

    async def test_route_incoming_audio(self, audio_router, mock_redis_client):
        """Test routing incoming audio from user."""
        # Arrange
        call_sid = "test_call_123"
        audio_data = b"\x00\x01\x02\x03"
        
        # Mock Redis client methods
        mock_redis_client._client.xadd = AsyncMock()
        
        # Act
        await audio_router.route_incoming_audio(audio_data, call_sid)
        
        # Assert
        mock_redis_client._client.xadd.assert_called_once()
        call_args = mock_redis_client._client.xadd.call_args
        
        # Verify stream key
        assert call_args[0][0] == f"audio:incoming:{call_sid}"
        
        # Verify data structure
        data = call_args[0][1]
        assert data["call_sid"] == call_sid
        assert data["audio_data"] == audio_data.hex()
        assert data["direction"] == AudioDirection.INCOMING.value
        assert "timestamp" in data
        assert "sequence_number" in data

    async def test_route_outgoing_audio(self, audio_router, mock_redis_client):
        """Test routing outgoing audio to user."""
        # Arrange
        call_sid = "test_call_456"
        audio_data = b"\x04\x05\x06\x07"
        
        # Mock Redis client methods
        mock_redis_client._client.xadd = AsyncMock()
        
        # Act
        await audio_router.route_outgoing_audio(audio_data, call_sid)
        
        # Assert
        mock_redis_client._client.xadd.assert_called_once()
        call_args = mock_redis_client._client.xadd.call_args
        
        # Verify stream key
        assert call_args[0][0] == f"audio:outgoing:{call_sid}"
        
        # Verify data structure
        data = call_args[0][1]
        assert data["call_sid"] == call_sid
        assert data["audio_data"] == audio_data.hex()
        assert data["direction"] == AudioDirection.OUTGOING.value
        
        # Verify system speaking flag is set
        assert await audio_router.is_system_speaking(call_sid) is True

    async def test_trigger_barge_in(self, audio_router, mock_redis_client):
        """Test barge-in triggering stops outgoing audio."""
        # Arrange
        call_sid = "test_call_789"
        
        # Set system as speaking
        audio_router._is_system_speaking[call_sid] = True
        
        # Mock Redis client methods
        mock_redis_client._client.delete = AsyncMock()
        mock_redis_client._client.set = AsyncMock()
        
        # Act
        await audio_router.trigger_barge_in(call_sid)
        
        # Assert
        # Verify system speaking flag is cleared
        assert await audio_router.is_system_speaking(call_sid) is False
        
        # Verify outgoing stream is flushed
        mock_redis_client._client.delete.assert_called()
        
        # Verify barge-in flag is set
        mock_redis_client._client.set.assert_called_once()
        call_args = mock_redis_client._client.set.call_args
        assert call_args[0][0] == f"barge_in:{call_sid}"
        assert call_args[0][1] == "1"

    async def test_sequence_numbers_increment(self, audio_router, mock_redis_client):
        """Test that sequence numbers increment correctly."""
        # Arrange
        call_sid = "test_call_seq"
        audio_data = b"\x00\x01"
        
        # Mock Redis client
        mock_redis_client._client.xadd = AsyncMock()
        
        # Act - Route multiple chunks
        await audio_router.route_incoming_audio(audio_data, call_sid)
        await audio_router.route_incoming_audio(audio_data, call_sid)
        await audio_router.route_incoming_audio(audio_data, call_sid)
        
        # Assert - Verify sequence numbers increment
        calls = mock_redis_client._client.xadd.call_args_list
        assert len(calls) == 3
        
        seq_nums = [int(call[0][1]["sequence_number"]) for call in calls]
        assert seq_nums == [1, 2, 3]

    async def test_separate_buffers_for_directions(self, audio_router, mock_redis_client):
        """Test that incoming and outgoing audio use separate buffers."""
        # Arrange
        call_sid = "test_call_buffers"
        audio_data = b"\x00\x01"
        
        # Mock Redis client
        mock_redis_client._client.xadd = AsyncMock()
        
        # Act - Route both incoming and outgoing
        await audio_router.route_incoming_audio(audio_data, call_sid)
        await audio_router.route_outgoing_audio(audio_data, call_sid)
        
        # Assert - Verify different stream keys
        calls = mock_redis_client._client.xadd.call_args_list
        assert len(calls) == 2
        
        incoming_key = calls[0][0][0]
        outgoing_key = calls[1][0][0]
        
        assert incoming_key == f"audio:incoming:{call_sid}"
        assert outgoing_key == f"audio:outgoing:{call_sid}"
        assert incoming_key != outgoing_key

    async def test_cleanup_call_streams(self, audio_router, mock_redis_client):
        """Test cleanup of call streams."""
        # Arrange
        call_sid = "test_call_cleanup"
        
        # Set up some state
        audio_router._sequence_counters[f"{call_sid}:incoming"] = 10
        audio_router._is_system_speaking[call_sid] = True
        
        # Mock Redis client
        mock_redis_client._client.delete = AsyncMock()
        
        # Act
        await audio_router.cleanup_call_streams(call_sid)
        
        # Assert
        # Verify Redis streams are deleted
        mock_redis_client._client.delete.assert_called_once()
        call_args = mock_redis_client._client.delete.call_args[0]
        
        assert f"audio:incoming:{call_sid}" in call_args
        assert f"audio:outgoing:{call_sid}" in call_args
        assert f"barge_in:{call_sid}" in call_args
        
        # Verify internal state is cleaned
        assert f"{call_sid}:incoming" not in audio_router._sequence_counters
        assert call_sid not in audio_router._is_system_speaking

    async def test_read_incoming_stream(self, audio_router, mock_redis_client):
        """Test reading from incoming audio stream."""
        # Arrange
        call_sid = "test_call_read"
        
        # Mock Redis stream data
        mock_messages = [
            (
                "1234567890-0",
                {
                    "call_sid": call_sid,
                    "audio_data": b"\x00\x01\x02".hex(),
                    "timestamp": "1234567890.0",
                    "sequence_number": "1",
                    "direction": AudioDirection.INCOMING.value,
                },
            )
        ]
        
        # Mock xread to return data once, then empty
        mock_redis_client._client.xread = AsyncMock(
            side_effect=[
                [(f"audio:incoming:{call_sid}", mock_messages)],
                [],  # Empty result to allow test to complete
            ]
        )
        
        # Act
        chunks = []
        async for chunk in audio_router.read_incoming_stream(call_sid, block_ms=10):
            chunks.append(chunk)
            if len(chunks) >= 1:
                break  # Exit after first chunk
        
        # Assert
        assert len(chunks) == 1
        chunk = chunks[0]
        assert chunk.call_sid == call_sid
        assert chunk.audio_data == b"\x00\x01\x02"
        assert chunk.sequence_number == 1
        assert chunk.direction == AudioDirection.INCOMING

    async def test_read_outgoing_stream_stops_on_barge_in(
        self, audio_router, mock_redis_client
    ):
        """Test that outgoing stream stops when barge-in is detected."""
        # Arrange
        call_sid = "test_call_barge"
        
        # Mock Redis methods
        mock_redis_client._client.exists = AsyncMock(return_value=True)  # Barge-in flag exists
        mock_redis_client._client.xread = AsyncMock(return_value=[])
        
        # Act
        chunks = []
        async for chunk in audio_router.read_outgoing_stream(call_sid, block_ms=10):
            chunks.append(chunk)
        
        # Assert - Stream should stop immediately due to barge-in
        assert len(chunks) == 0
        mock_redis_client._client.exists.assert_called()

    async def test_is_system_speaking_default_false(self, audio_router):
        """Test that is_system_speaking returns False by default."""
        # Arrange
        call_sid = "test_call_new"
        
        # Act
        result = await audio_router.is_system_speaking(call_sid)
        
        # Assert
        assert result is False

    async def test_stream_maxlen_limit(self, audio_router, mock_redis_client):
        """Test that streams have maxlen limit to prevent unbounded growth."""
        # Arrange
        call_sid = "test_call_maxlen"
        audio_data = b"\x00\x01"
        
        # Mock Redis client
        mock_redis_client._client.xadd = AsyncMock()
        
        # Act
        await audio_router.route_incoming_audio(audio_data, call_sid)
        
        # Assert - Verify maxlen parameter is set
        call_args = mock_redis_client._client.xadd.call_args
        assert call_args[1]["maxlen"] == 1000
