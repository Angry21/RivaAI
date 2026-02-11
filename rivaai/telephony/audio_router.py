"""Audio Router for managing bidirectional audio streams with Redis buffering."""

import asyncio
import logging
import time
from typing import AsyncIterator, Optional

from rivaai.config.redis_client import RedisClient
from rivaai.config.settings import Settings
from rivaai.telephony.models import AudioChunk, AudioDirection

logger = logging.getLogger(__name__)


class AudioRouter:
    """
    Manages bidirectional audio streams and coordinates barge-in detection.
    
    Responsibilities:
    - Routes incoming audio from user to STT processor
    - Routes outgoing audio from TTS to user
    - Implements audio chunk buffering with Redis Streams
    - Maintains separate buffers for user and system audio
    - Detects speech activity for barge-in handling
    """

    def __init__(self, redis_client: RedisClient, settings: Settings):
        """
        Initialize the Audio Router.
        
        Args:
            redis_client: Redis client for stream buffering
            settings: Application settings
        """
        self.redis_client = redis_client
        self.settings = settings
        self._sequence_counters: dict[str, int] = {}
        self._is_system_speaking: dict[str, bool] = {}
        logger.info("AudioRouter initialized")

    async def route_incoming_audio(
        self, audio_chunk: bytes, call_sid: str
    ) -> None:
        """
        Routes incoming audio from user to STT processor.
        Detects speech activity for barge-in handling.
        
        Args:
            audio_chunk: Raw audio data (μ-law PCM)
            call_sid: Call session identifier
            
        Raises:
            Exception: If routing fails
        """
        try:
            # Get sequence number for this call
            sequence_number = self._get_next_sequence(call_sid, AudioDirection.INCOMING)
            
            # Create audio chunk object
            chunk = AudioChunk(
                call_sid=call_sid,
                audio_data=audio_chunk,
                timestamp=time.time(),
                sequence_number=sequence_number,
                direction=AudioDirection.INCOMING,
            )
            
            # Add to Redis Stream for incoming audio
            stream_key = f"audio:incoming:{call_sid}"
            await self._add_to_stream(stream_key, chunk)
            
            logger.debug(
                f"Routed incoming audio: call_sid={call_sid}, "
                f"seq={sequence_number}, size={len(audio_chunk)} bytes"
            )
            
        except Exception as e:
            logger.error(
                f"Failed to route incoming audio for call_sid={call_sid}: {e}",
                exc_info=True,
            )
            raise

    async def route_outgoing_audio(
        self, audio_chunk: bytes, call_sid: str
    ) -> None:
        """
        Routes TTS audio to user.
        Can be interrupted by barge-in signal.
        
        Args:
            audio_chunk: Raw audio data (μ-law PCM)
            call_sid: Call session identifier
            
        Raises:
            Exception: If routing fails
        """
        try:
            # Get sequence number for this call
            sequence_number = self._get_next_sequence(call_sid, AudioDirection.OUTGOING)
            
            # Create audio chunk object
            chunk = AudioChunk(
                call_sid=call_sid,
                audio_data=audio_chunk,
                timestamp=time.time(),
                sequence_number=sequence_number,
                direction=AudioDirection.OUTGOING,
            )
            
            # Mark system as speaking
            self._is_system_speaking[call_sid] = True
            
            # Add to Redis Stream for outgoing audio
            stream_key = f"audio:outgoing:{call_sid}"
            await self._add_to_stream(stream_key, chunk)
            
            logger.debug(
                f"Routed outgoing audio: call_sid={call_sid}, "
                f"seq={sequence_number}, size={len(audio_chunk)} bytes"
            )
            
        except Exception as e:
            logger.error(
                f"Failed to route outgoing audio for call_sid={call_sid}: {e}",
                exc_info=True,
            )
            raise

    async def trigger_barge_in(self, call_sid: str) -> None:
        """
        Immediately stops outgoing audio and flushes TTS buffer.
        Signals STT to prioritize incoming audio.
        
        Args:
            call_sid: Call session identifier
            
        Raises:
            Exception: If barge-in trigger fails
        """
        try:
            # Mark system as not speaking
            self._is_system_speaking[call_sid] = False
            
            # Flush outgoing audio buffer
            stream_key = f"audio:outgoing:{call_sid}"
            await self._flush_stream(stream_key)
            
            # Set barge-in flag in Redis
            barge_in_key = f"barge_in:{call_sid}"
            client = await self.redis_client.get_client()
            await client.set(barge_in_key, "1", ex=5)  # 5 second TTL
            
            logger.info(f"Barge-in triggered for call_sid={call_sid}")
            
        except Exception as e:
            logger.error(
                f"Failed to trigger barge-in for call_sid={call_sid}: {e}",
                exc_info=True,
            )
            raise

    async def is_system_speaking(self, call_sid: str) -> bool:
        """
        Check if system is currently outputting audio.
        
        Args:
            call_sid: Call session identifier
            
        Returns:
            True if system is speaking
        """
        return self._is_system_speaking.get(call_sid, False)

    async def set_system_speaking(self, call_sid: str, speaking: bool) -> None:
        """
        Set the system speaking state for a call.
        
        Args:
            call_sid: Call session identifier
            speaking: True if system is speaking, False otherwise
        """
        self._is_system_speaking[call_sid] = speaking
        logger.debug(f"Set system speaking for call_sid={call_sid} to {speaking}")

    async def read_incoming_stream(
        self, call_sid: str, block_ms: int = 100
    ) -> AsyncIterator[AudioChunk]:
        """
        Read audio chunks from incoming stream.
        
        Args:
            call_sid: Call session identifier
            block_ms: Milliseconds to block waiting for new data
            
        Yields:
            AudioChunk objects from the stream
        """
        stream_key = f"audio:incoming:{call_sid}"
        client = await self.redis_client.get_client()
        
        # Start reading from the beginning or last ID
        last_id = "0"
        
        try:
            while True:
                # Read from stream with blocking
                result = await client.xread(
                    {stream_key: last_id}, block=block_ms, count=10
                )
                
                if not result:
                    # No new data, yield control
                    await asyncio.sleep(0.01)
                    continue
                
                # Process messages
                for stream_name, messages in result:
                    for message_id, data in messages:
                        # Reconstruct AudioChunk
                        chunk = AudioChunk(
                            call_sid=data["call_sid"],
                            audio_data=bytes.fromhex(data["audio_data"]),
                            timestamp=float(data["timestamp"]),
                            sequence_number=int(data["sequence_number"]),
                            direction=AudioDirection.INCOMING,
                        )
                        yield chunk
                        last_id = message_id
                        
        except asyncio.CancelledError:
            logger.info(f"Incoming stream reader cancelled for call_sid={call_sid}")
            raise
        except Exception as e:
            logger.error(
                f"Error reading incoming stream for call_sid={call_sid}: {e}",
                exc_info=True,
            )
            raise

    async def read_outgoing_stream(
        self, call_sid: str, block_ms: int = 100
    ) -> AsyncIterator[AudioChunk]:
        """
        Read audio chunks from outgoing stream.
        
        Args:
            call_sid: Call session identifier
            block_ms: Milliseconds to block waiting for new data
            
        Yields:
            AudioChunk objects from the stream
        """
        stream_key = f"audio:outgoing:{call_sid}"
        client = await self.redis_client.get_client()
        
        # Start reading from the beginning or last ID
        last_id = "0"
        
        try:
            while True:
                # Check for barge-in signal
                barge_in_key = f"barge_in:{call_sid}"
                if await client.exists(barge_in_key):
                    logger.info(f"Barge-in detected, stopping outgoing stream for call_sid={call_sid}")
                    break
                
                # Read from stream with blocking
                result = await client.xread(
                    {stream_key: last_id}, block=block_ms, count=10
                )
                
                if not result:
                    # No new data, yield control
                    await asyncio.sleep(0.01)
                    continue
                
                # Process messages
                for stream_name, messages in result:
                    for message_id, data in messages:
                        # Reconstruct AudioChunk
                        chunk = AudioChunk(
                            call_sid=data["call_sid"],
                            audio_data=bytes.fromhex(data["audio_data"]),
                            timestamp=float(data["timestamp"]),
                            sequence_number=int(data["sequence_number"]),
                            direction=AudioDirection.OUTGOING,
                        )
                        yield chunk
                        last_id = message_id
                        
        except asyncio.CancelledError:
            logger.info(f"Outgoing stream reader cancelled for call_sid={call_sid}")
            raise
        except Exception as e:
            logger.error(
                f"Error reading outgoing stream for call_sid={call_sid}: {e}",
                exc_info=True,
            )
            raise

    async def cleanup_call_streams(self, call_sid: str) -> None:
        """
        Clean up Redis streams for a completed call.
        
        Args:
            call_sid: Call session identifier
        """
        try:
            client = await self.redis_client.get_client()
            
            # Delete streams
            incoming_key = f"audio:incoming:{call_sid}"
            outgoing_key = f"audio:outgoing:{call_sid}"
            barge_in_key = f"barge_in:{call_sid}"
            
            await client.delete(incoming_key, outgoing_key, barge_in_key)
            
            # Clean up internal state - remove all sequence counters for this call
            keys_to_remove = [
                key for key in self._sequence_counters.keys() 
                if key.startswith(f"{call_sid}:")
            ]
            for key in keys_to_remove:
                del self._sequence_counters[key]
            
            if call_sid in self._is_system_speaking:
                del self._is_system_speaking[call_sid]
            
            logger.info(f"Cleaned up streams for call_sid={call_sid}")
            
        except Exception as e:
            logger.error(
                f"Failed to cleanup streams for call_sid={call_sid}: {e}",
                exc_info=True,
            )
            raise

    def _get_next_sequence(self, call_sid: str, direction: AudioDirection) -> int:
        """
        Get next sequence number for audio chunks.
        
        Args:
            call_sid: Call session identifier
            direction: Audio direction
            
        Returns:
            Next sequence number
        """
        key = f"{call_sid}:{direction.value}"
        if key not in self._sequence_counters:
            self._sequence_counters[key] = 0
        self._sequence_counters[key] += 1
        return self._sequence_counters[key]

    async def _add_to_stream(self, stream_key: str, chunk: AudioChunk) -> None:
        """
        Add audio chunk to Redis Stream.
        
        Args:
            stream_key: Redis stream key
            chunk: Audio chunk to add
        """
        client = await self.redis_client.get_client()
        
        # Prepare data for stream
        data = {
            "call_sid": chunk.call_sid,
            "audio_data": chunk.audio_data.hex(),  # Convert bytes to hex string
            "timestamp": str(chunk.timestamp),
            "sequence_number": str(chunk.sequence_number),
            "direction": chunk.direction.value,
        }
        
        # Add to stream with automatic ID generation
        await client.xadd(stream_key, data, maxlen=1000)  # Keep last 1000 chunks

    async def _flush_stream(self, stream_key: str) -> None:
        """
        Flush all entries from a Redis Stream.
        
        Args:
            stream_key: Redis stream key
        """
        client = await self.redis_client.get_client()
        
        # Delete and recreate stream (effectively flushing it)
        await client.delete(stream_key)
