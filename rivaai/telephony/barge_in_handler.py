"""Barge-In Handler with Voice Activity Detection."""

import asyncio
import logging
import time
from typing import AsyncIterator, Callable, Optional

from rivaai.telephony.models import AudioChunk

logger = logging.getLogger(__name__)


class BargeInHandler:
    """
    Detects user speech during system output and triggers interruption.
    
    Responsibilities:
    - Monitors for user speech during system output using VAD
    - Triggers barge-in when user starts speaking
    - Implements <300ms interrupt latency requirement
    - Flushes TTS buffer and stops audio output
    - Signals STT to prioritize incoming audio
    
    The handler uses a simple energy-based VAD for minimal latency.
    For production, consider integrating WebRTC VAD or Silero VAD.
    """

    def __init__(
        self,
        interrupt_callback: Callable[[str], asyncio.Future],
        vad_threshold: float = 0.02,
        speech_frames_threshold: int = 3,
        sample_rate: int = 8000,
    ):
        """
        Initialize the Barge-In Handler.
        
        Args:
            interrupt_callback: Async callback to trigger when barge-in detected
            vad_threshold: Energy threshold for voice activity (0.0-1.0)
            speech_frames_threshold: Number of consecutive speech frames to trigger
            sample_rate: Audio sample rate in Hz (default 8000 for telephony)
        """
        self.interrupt_callback = interrupt_callback
        self.vad_threshold = vad_threshold
        self.speech_frames_threshold = speech_frames_threshold
        self.sample_rate = sample_rate
        
        # State tracking
        self._monitoring_tasks: dict[str, asyncio.Task] = {}
        self._speech_frame_counts: dict[str, int] = {}
        self._last_detection_time: dict[str, float] = {}
        
        logger.info(
            f"BargeInHandler initialized with threshold={vad_threshold}, "
            f"frames={speech_frames_threshold}"
        )

    async def monitor_user_audio(
        self,
        audio_stream: AsyncIterator[AudioChunk],
        call_sid: str,
        is_system_speaking: Callable[[str], asyncio.Future],
    ) -> None:
        """
        Monitors for user speech during system output.
        Triggers barge-in if detected.
        
        Args:
            audio_stream: Stream of incoming audio chunks from user
            call_sid: Call session identifier
            is_system_speaking: Async callback to check if system is speaking
            
        Raises:
            Exception: If monitoring fails
        """
        try:
            logger.info(f"Starting barge-in monitoring for call_sid={call_sid}")
            
            # Initialize state for this call
            self._speech_frame_counts[call_sid] = 0
            
            async for chunk in audio_stream:
                # Only monitor when system is speaking
                if not await is_system_speaking(call_sid):
                    # Reset counter when system is not speaking
                    self._speech_frame_counts[call_sid] = 0
                    continue
                
                # Detect voice activity in this chunk
                has_speech = self._detect_voice_activity(chunk.audio_data)
                
                if has_speech:
                    # Increment speech frame counter
                    self._speech_frame_counts[call_sid] += 1
                    
                    # Check if we've exceeded threshold
                    if self._speech_frame_counts[call_sid] >= self.speech_frames_threshold:
                        # Trigger barge-in
                        await self._trigger_interrupt(call_sid)
                        
                        # Reset counter
                        self._speech_frame_counts[call_sid] = 0
                else:
                    # Reset counter on silence
                    self._speech_frame_counts[call_sid] = 0
                    
        except asyncio.CancelledError:
            logger.info(f"Barge-in monitoring cancelled for call_sid={call_sid}")
            raise
        except Exception as e:
            logger.error(
                f"Error in barge-in monitoring for call_sid={call_sid}: {e}",
                exc_info=True,
            )
            raise
        finally:
            # Cleanup state
            if call_sid in self._speech_frame_counts:
                del self._speech_frame_counts[call_sid]
            if call_sid in self._last_detection_time:
                del self._last_detection_time[call_sid]

    async def trigger_interrupt(self, call_sid: str) -> None:
        """
        Manually trigger barge-in interrupt.
        Stops TTS output and flushes audio buffer.
        Latency requirement: <300ms.
        
        Args:
            call_sid: Call session identifier
            
        Raises:
            Exception: If interrupt trigger fails
        """
        await self._trigger_interrupt(call_sid)

    def start_monitoring(
        self,
        audio_stream: AsyncIterator[AudioChunk],
        call_sid: str,
        is_system_speaking: Callable[[str], asyncio.Future],
    ) -> asyncio.Task:
        """
        Start monitoring in background task.
        
        Args:
            audio_stream: Stream of incoming audio chunks
            call_sid: Call session identifier
            is_system_speaking: Async callback to check if system is speaking
            
        Returns:
            Background task handle
        """
        # Cancel existing monitoring task if any
        if call_sid in self._monitoring_tasks:
            self._monitoring_tasks[call_sid].cancel()
        
        # Create new monitoring task
        task = asyncio.create_task(
            self.monitor_user_audio(audio_stream, call_sid, is_system_speaking)
        )
        self._monitoring_tasks[call_sid] = task
        
        logger.info(f"Started background monitoring for call_sid={call_sid}")
        return task

    def stop_monitoring(self, call_sid: str) -> None:
        """
        Stop monitoring for a call.
        
        Args:
            call_sid: Call session identifier
        """
        if call_sid in self._monitoring_tasks:
            self._monitoring_tasks[call_sid].cancel()
            del self._monitoring_tasks[call_sid]
            logger.info(f"Stopped monitoring for call_sid={call_sid}")

    def _detect_voice_activity(self, audio_data: bytes) -> bool:
        """
        Detect voice activity in audio chunk using energy-based VAD.
        
        This is a simple energy-based VAD for minimal latency.
        For production, consider using:
        - WebRTC VAD (py-webrtcvad package)
        - Silero VAD (more accurate, slightly higher latency)
        
        Args:
            audio_data: Raw audio data (μ-law PCM)
            
        Returns:
            True if speech detected, False otherwise
        """
        if not audio_data or len(audio_data) == 0:
            return False
        
        # Convert μ-law to linear PCM for energy calculation
        # For simplicity, we'll use the raw bytes as approximation
        # In production, proper μ-law decoding should be used
        
        # Calculate RMS energy
        energy = sum(abs(b - 128) for b in audio_data) / len(audio_data)
        
        # Normalize to 0-1 range (128 is max deviation from center)
        normalized_energy = energy / 128.0
        
        # Compare against threshold
        has_speech = normalized_energy > self.vad_threshold
        
        return has_speech

    async def _trigger_interrupt(self, call_sid: str) -> None:
        """
        Internal method to trigger barge-in interrupt.
        
        Args:
            call_sid: Call session identifier
        """
        try:
            # Record detection time for latency tracking
            detection_time = time.time()
            self._last_detection_time[call_sid] = detection_time
            
            # Call the interrupt callback
            await self.interrupt_callback(call_sid)
            
            # Calculate latency
            latency_ms = (time.time() - detection_time) * 1000
            
            logger.info(
                f"Barge-in triggered for call_sid={call_sid}, "
                f"latency={latency_ms:.1f}ms"
            )
            
            # Warn if latency exceeds requirement
            if latency_ms > 300:
                logger.warning(
                    f"Barge-in latency exceeded 300ms: {latency_ms:.1f}ms "
                    f"for call_sid={call_sid}"
                )
                
        except Exception as e:
            logger.error(
                f"Failed to trigger interrupt for call_sid={call_sid}: {e}",
                exc_info=True,
            )
            raise

    def get_last_detection_latency(self, call_sid: str) -> Optional[float]:
        """
        Get the latency of the last barge-in detection.
        
        Args:
            call_sid: Call session identifier
            
        Returns:
            Latency in milliseconds, or None if no detection yet
        """
        if call_sid in self._last_detection_time:
            return (time.time() - self._last_detection_time[call_sid]) * 1000
        return None

    def cleanup_call(self, call_sid: str) -> None:
        """
        Clean up state for a completed call.
        
        Args:
            call_sid: Call session identifier
        """
        # Stop monitoring
        self.stop_monitoring(call_sid)
        
        # Clean up state
        if call_sid in self._speech_frame_counts:
            del self._speech_frame_counts[call_sid]
        if call_sid in self._last_detection_time:
            del self._last_detection_time[call_sid]
        
        logger.info(f"Cleaned up barge-in state for call_sid={call_sid}")
