"""Integration tests for AudioRouter with Redis."""

import asyncio
import pytest

from rivaai.config.redis_client import RedisClient, get_redis_client
from rivaai.config.settings import get_settings
from rivaai.telephony.audio_router import AudioRouter
from rivaai.telephony.models import AudioDirection


@pytest.mark.integration
@pytest.mark.asyncio
class TestAudioRouterIntegration:
    """Integration tests for AudioRouter with real Redis."""

    @pytest.fixture(autouse=True)
    async def setup_teardown(self):
        """Set up and tear down for each test."""
        # Setup
        settings = get_settings()
        self.redis_client = await get_redis_client(settings)
        self.audio_router = AudioRouter(self.redis_client, settings)
        
        yield
        
        # Teardown - clean up any test data
        client = await self.redis_client.get_client()
        # Delete any test keys
        keys = await client.keys("audio:*:test_*")
        if keys:
            await client.delete(*keys)
        keys = await client.keys("barge_in:test_*")
        if keys:
            await client.delete(*keys)

    async def test_bidirectional_audio_streaming(self):
        """Test bidirectional audio streaming through Redis."""
        # Arrange
        call_sid = "test_call_bidirectional"
        incoming_audio = b"\x00\x01\x02\x03\x04"
        outgoing_audio = b"\x05\x06\x07\x08\x09"
        
        # Act - Route audio in both directions
        await self.audio_router.route_incoming_audio(incoming_audio, call_sid)
        await self.audio_router.route_outgoing_audio(outgoing_audio, call_sid)
        
        # Assert - Read back from streams
        incoming_chunks = []
        async for chunk in self.audio_router.read_incoming_stream(call_sid, block_ms=10):
            incoming_chunks.append(chunk)
            break  # Get first chunk
        
        outgoing_chunks = []
        async for chunk in self.audio_router.read_outgoing_stream(call_sid, block_ms=10):
            outgoing_chunks.append(chunk)
            break  # Get first chunk
        
        # Verify incoming audio
        assert len(incoming_chunks) == 1
        assert incoming_chunks[0].audio_data == incoming_audio
        assert incoming_chunks[0].direction == AudioDirection.INCOMING
        
        # Verify outgoing audio
        assert len(outgoing_chunks) == 1
        assert outgoing_chunks[0].audio_data == outgoing_audio
        assert outgoing_chunks[0].direction == AudioDirection.OUTGOING
        
        # Cleanup
        await self.audio_router.cleanup_call_streams(call_sid)

    async def test_multiple_audio_chunks_in_sequence(self):
        """Test streaming multiple audio chunks maintains sequence."""
        # Arrange
        call_sid = "test_call_sequence"
        chunks_to_send = [
            b"\x00\x01",
            b"\x02\x03",
            b"\x04\x05",
        ]
        
        # Act - Send multiple chunks
        for audio_data in chunks_to_send:
            await self.audio_router.route_incoming_audio(audio_data, call_sid)
        
        # Assert - Read back and verify sequence
        received_chunks = []
        async for chunk in self.audio_router.read_incoming_stream(call_sid, block_ms=10):
            received_chunks.append(chunk)
            if len(received_chunks) >= len(chunks_to_send):
                break
        
        assert len(received_chunks) == len(chunks_to_send)
        
        # Verify sequence numbers are in order
        for i, chunk in enumerate(received_chunks):
            assert chunk.sequence_number == i + 1
            assert chunk.audio_data == chunks_to_send[i]
        
        # Cleanup
        await self.audio_router.cleanup_call_streams(call_sid)

    async def test_barge_in_stops_outgoing_stream(self):
        """Test that barge-in immediately stops outgoing audio stream."""
        # Arrange
        call_sid = "test_call_barge_in"
        
        # Send some outgoing audio
        await self.audio_router.route_outgoing_audio(b"\x00\x01", call_sid)
        
        # Trigger barge-in
        await self.audio_router.trigger_barge_in(call_sid)
        
        # Act - Try to read from outgoing stream
        chunks = []
        async for chunk in self.audio_router.read_outgoing_stream(call_sid, block_ms=10):
            chunks.append(chunk)
        
        # Assert - Stream should stop immediately due to barge-in
        # (may get 0 or 1 chunk depending on timing)
        assert len(chunks) <= 1
        
        # Verify barge-in flag is set
        client = await self.redis_client.get_client()
        barge_in_key = f"barge_in:{call_sid}"
        assert await client.exists(barge_in_key)
        
        # Cleanup
        await self.audio_router.cleanup_call_streams(call_sid)

    async def test_separate_buffers_for_multiple_calls(self):
        """Test that multiple concurrent calls have separate buffers."""
        # Arrange
        call_sid_1 = "test_call_multi_1"
        call_sid_2 = "test_call_multi_2"
        
        audio_1 = b"\x00\x01\x02"
        audio_2 = b"\x03\x04\x05"
        
        # Act - Route audio for both calls
        await self.audio_router.route_incoming_audio(audio_1, call_sid_1)
        await self.audio_router.route_incoming_audio(audio_2, call_sid_2)
        
        # Assert - Read from each stream separately
        chunks_1 = []
        async for chunk in self.audio_router.read_incoming_stream(call_sid_1, block_ms=10):
            chunks_1.append(chunk)
            break
        
        chunks_2 = []
        async for chunk in self.audio_router.read_incoming_stream(call_sid_2, block_ms=10):
            chunks_2.append(chunk)
            break
        
        # Verify each call has its own audio
        assert len(chunks_1) == 1
        assert chunks_1[0].audio_data == audio_1
        assert chunks_1[0].call_sid == call_sid_1
        
        assert len(chunks_2) == 1
        assert chunks_2[0].audio_data == audio_2
        assert chunks_2[0].call_sid == call_sid_2
        
        # Cleanup
        await self.audio_router.cleanup_call_streams(call_sid_1)
        await self.audio_router.cleanup_call_streams(call_sid_2)

    async def test_stream_cleanup_removes_all_data(self):
        """Test that cleanup removes all stream data from Redis."""
        # Arrange
        call_sid = "test_call_cleanup_verify"
        
        # Add some data
        await self.audio_router.route_incoming_audio(b"\x00\x01", call_sid)
        await self.audio_router.route_outgoing_audio(b"\x02\x03", call_sid)
        await self.audio_router.trigger_barge_in(call_sid)
        
        # Verify data exists
        client = await self.redis_client.get_client()
        incoming_key = f"audio:incoming:{call_sid}"
        outgoing_key = f"audio:outgoing:{call_sid}"
        barge_in_key = f"barge_in:{call_sid}"
        
        assert await client.exists(incoming_key)
        assert await client.exists(outgoing_key)
        assert await client.exists(barge_in_key)
        
        # Act - Cleanup
        await self.audio_router.cleanup_call_streams(call_sid)
        
        # Assert - All data removed
        assert not await client.exists(incoming_key)
        assert not await client.exists(outgoing_key)
        assert not await client.exists(barge_in_key)

    async def test_concurrent_audio_routing(self):
        """Test concurrent audio routing operations."""
        # Arrange
        call_sid = "test_call_concurrent"
        num_chunks = 10
        
        # Act - Route multiple chunks concurrently
        tasks = []
        for i in range(num_chunks):
            audio_data = bytes([i, i + 1])
            task = self.audio_router.route_incoming_audio(audio_data, call_sid)
            tasks.append(task)
        
        await asyncio.gather(*tasks)
        
        # Assert - All chunks should be in the stream
        chunks = []
        async for chunk in self.audio_router.read_incoming_stream(call_sid, block_ms=10):
            chunks.append(chunk)
            if len(chunks) >= num_chunks:
                break
        
        assert len(chunks) == num_chunks
        
        # Verify sequence numbers are unique and in range
        seq_nums = [chunk.sequence_number for chunk in chunks]
        assert len(set(seq_nums)) == num_chunks  # All unique
        assert min(seq_nums) >= 1
        assert max(seq_nums) <= num_chunks
        
        # Cleanup
        await self.audio_router.cleanup_call_streams(call_sid)
