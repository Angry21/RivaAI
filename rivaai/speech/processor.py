"""Speech-to-Text Processor with streaming support using Deepgram Nova-2."""

import asyncio
import audioop
import logging
from typing import AsyncIterator, List, Optional

import httpx
from deepgram import (
    DeepgramClient,
    DeepgramClientOptions,
    LiveOptions,
    LiveTranscriptionEvents,
)

from rivaai.config import get_settings
from rivaai.speech.models import TranscriptResult

logger = logging.getLogger(__name__)


class SpeechProcessor:
    """Speech-to-Text processor integrating Deepgram Nova-2.
    
    Provides streaming recognition with partial results, confidence scoring,
    and support for multiple Indian languages. Handles audio transcoding
    from G.711 µ-law to Linear16 PCM format required by Deepgram.
    
    Supports languages: hi-IN, mr-IN, te-IN, ta-IN, bn-IN
    """

    def __init__(self, api_key: Optional[str] = None):
        """Initialize the Speech Processor.
        
        Args:
            api_key: Deepgram API key. If None, loads from settings.
        """
        self.settings = get_settings()
        self.api_key = api_key or self.settings.deepgram_api_key
        
        if not self.api_key:
            raise ValueError("Deepgram API key is required")
        
        # Configure Deepgram client
        config = DeepgramClientOptions(
            options={"keepalive": "true"}
        )
        self.client = DeepgramClient(self.api_key, config)
        
        # Supported languages
        self.supported_languages = self.settings.supported_languages
        
        # Confidence threshold for low-confidence detection
        self.confidence_threshold = self.settings.stt_confidence_threshold
        
        logger.info(
            f"SpeechProcessor initialized with languages: {self.supported_languages}"
        )

    def get_supported_languages(self) -> List[str]:
        """Returns list of supported language codes.
        
        Returns:
            List of language codes (e.g., ['hi-IN', 'mr-IN', ...])
        """
        return self.supported_languages.copy()

    async def detect_language(
        self,
        audio_data: bytes,
        is_mulaw: bool = True,
    ) -> Optional[str]:
        """Detect language from audio sample.
        
        Uses Deepgram's language detection to identify the spoken language.
        Returns None if detection fails or confidence is too low.
        
        Args:
            audio_data: Audio data bytes
            is_mulaw: Whether audio is in G.711 µ-law format
            
        Returns:
            Detected language code (e.g., 'hi-IN') or None if detection fails
        """
        try:
            # Transcode if needed
            if is_mulaw:
                audio_data = self._transcode_mulaw_to_linear16(audio_data)
            
            # Use Deepgram's prerecorded API with language detection
            payload = {
                "buffer": audio_data,
            }
            
            options = {
                "model": "nova-2",
                "detect_language": True,  # Enable language detection
                "encoding": "linear16",
                "sample_rate": 8000,
                "channels": 1,
            }
            
            response = await self.client.listen.asyncrest.v("1").transcribe_file(
                payload, options
            )
            
            # Extract detected language
            if response.results and response.results.channels:
                detected_language = response.results.channels[0].detected_language
                
                if detected_language:
                    # Check if detected language is in our supported list
                    if detected_language in self.supported_languages:
                        logger.info(f"Language detected: {detected_language}")
                        return detected_language
                    else:
                        logger.warning(
                            f"Detected language {detected_language} not in supported list"
                        )
                        return None
            
            logger.warning("Language detection failed: no language detected")
            return None
            
        except Exception as e:
            logger.error(f"Error detecting language: {e}")
            return None

    def _transcode_mulaw_to_linear16(self, mulaw_data: bytes) -> bytes:
        """Transcode G.711 µ-law audio to Linear16 PCM.
        
        Deepgram requires Linear16 PCM format. Telephony systems typically
        use G.711 µ-law encoding at 8kHz.
        
        Args:
            mulaw_data: Audio data in G.711 µ-law format
            
        Returns:
            Audio data in Linear16 PCM format
        """
        try:
            # Convert µ-law to linear PCM (16-bit)
            # audioop.ulaw2lin converts µ-law to linear samples
            linear_data = audioop.ulaw2lin(mulaw_data, 2)  # 2 bytes per sample (16-bit)
            return linear_data
        except Exception as e:
            logger.error(f"Error transcoding µ-law to Linear16: {e}")
            raise

    def detect_voice_activity(self, audio_chunk: bytes) -> bool:
        """Detect if audio chunk contains speech using simple energy-based VAD.
        
        This is a basic implementation using RMS energy. For production,
        consider using WebRTC VAD or Silero VAD for better accuracy.
        
        Args:
            audio_chunk: Audio data in Linear16 PCM format
            
        Returns:
            True if audio contains speech, False otherwise
        """
        try:
            # Calculate RMS (Root Mean Square) energy
            rms = audioop.rms(audio_chunk, 2)  # 2 bytes per sample
            
            # Threshold for speech detection (tuned empirically)
            # This is a simple heuristic; production should use proper VAD
            speech_threshold = 500
            
            return rms > speech_threshold
        except Exception as e:
            logger.error(f"Error in voice activity detection: {e}")
            return False

    async def process_audio_stream(
        self,
        audio_stream: AsyncIterator[bytes],
        language_code: str,
        is_mulaw: bool = True,
    ) -> AsyncIterator[TranscriptResult]:
        """Stream audio to Deepgram and yield partial/final transcripts.
        
        Processes streaming audio with real-time transcription. Yields
        TranscriptResult objects with partial results (<300ms latency)
        and final transcripts.
        
        Args:
            audio_stream: Async iterator yielding audio chunks
            language_code: Language code (e.g., 'hi-IN')
            is_mulaw: Whether audio is in G.711 µ-law format (default: True)
            
        Yields:
            TranscriptResult objects with text, confidence, and metadata
            
        Raises:
            ValueError: If language_code is not supported
        """
        if language_code not in self.supported_languages:
            raise ValueError(
                f"Unsupported language: {language_code}. "
                f"Supported: {self.supported_languages}"
            )
        
        logger.info(f"Starting audio stream processing for language: {language_code}")
        
        try:
            # Create a queue to collect transcripts from Deepgram callbacks
            transcript_queue: asyncio.Queue[Optional[TranscriptResult]] = asyncio.Queue()
            
            # Configure Deepgram live transcription options
            options = LiveOptions(
                model="nova-2",
                language=language_code,
                encoding="linear16",
                sample_rate=8000,
                channels=1,
                interim_results=True,  # Enable partial results
                punctuate=True,
                smart_format=True,
                utterance_end_ms=1000,  # End utterance after 1s of silence
            )
            
            # Create live transcription connection
            dg_connection = self.client.listen.asynclive.v("1")
            
            # Set up event handlers
            async def on_message(self, result, **kwargs):
                """Handle transcript messages from Deepgram."""
                try:
                    sentence = result.channel.alternatives[0].transcript
                    
                    if len(sentence) == 0:
                        return
                    
                    confidence = result.channel.alternatives[0].confidence
                    is_final = result.is_final
                    
                    transcript = TranscriptResult(
                        text=sentence,
                        confidence=confidence,
                        is_final=is_final,
                        language_code=language_code,
                        timestamp=asyncio.get_event_loop().time(),
                    )
                    
                    await transcript_queue.put(transcript)
                    
                    # Log low confidence warnings
                    if confidence < self.confidence_threshold:
                        logger.warning(
                            f"Low confidence transcript: {confidence:.2f} - '{sentence}'"
                        )
                    
                except Exception as e:
                    logger.error(f"Error processing transcript: {e}")
            
            async def on_error(self, error, **kwargs):
                """Handle errors from Deepgram."""
                logger.error(f"Deepgram error: {error}")
                await transcript_queue.put(None)  # Signal error
            
            async def on_close(self, close_msg, **kwargs):
                """Handle connection close."""
                logger.info(f"Deepgram connection closed: {close_msg}")
                await transcript_queue.put(None)  # Signal completion
            
            # Register event handlers
            dg_connection.on(LiveTranscriptionEvents.Transcript, on_message)
            dg_connection.on(LiveTranscriptionEvents.Error, on_error)
            dg_connection.on(LiveTranscriptionEvents.Close, on_close)
            
            # Start the connection
            if not await dg_connection.start(options):
                raise RuntimeError("Failed to start Deepgram connection")
            
            # Create tasks for sending audio and receiving transcripts
            async def send_audio():
                """Send audio chunks to Deepgram."""
                try:
                    async for audio_chunk in audio_stream:
                        # Transcode if needed
                        if is_mulaw:
                            audio_chunk = self._transcode_mulaw_to_linear16(audio_chunk)
                        
                        # Send to Deepgram
                        await dg_connection.send(audio_chunk)
                    
                    # Signal end of audio stream
                    await dg_connection.finish()
                    
                except Exception as e:
                    logger.error(f"Error sending audio: {e}")
                    await transcript_queue.put(None)
            
            # Start sending audio in background
            send_task = asyncio.create_task(send_audio())
            
            # Yield transcripts as they arrive
            try:
                while True:
                    transcript = await transcript_queue.get()
                    
                    if transcript is None:
                        # End of stream or error
                        break
                    
                    yield transcript
                    
            finally:
                # Clean up
                send_task.cancel()
                try:
                    await send_task
                except asyncio.CancelledError:
                    pass
                
                # Close connection if still open
                try:
                    await dg_connection.finish()
                except Exception:
                    pass
        
        except Exception as e:
            logger.error(f"Error in audio stream processing: {e}")
            raise

    async def transcribe_audio_chunk(
        self,
        audio_data: bytes,
        language_code: str,
        is_mulaw: bool = True,
    ) -> Optional[TranscriptResult]:
        """Transcribe a single audio chunk (non-streaming).
        
        Useful for testing or processing pre-recorded audio.
        
        Args:
            audio_data: Audio data bytes
            language_code: Language code (e.g., 'hi-IN')
            is_mulaw: Whether audio is in G.711 µ-law format
            
        Returns:
            TranscriptResult or None if no speech detected
        """
        if language_code not in self.supported_languages:
            raise ValueError(
                f"Unsupported language: {language_code}. "
                f"Supported: {self.supported_languages}"
            )
        
        try:
            # Transcode if needed
            if is_mulaw:
                audio_data = self._transcode_mulaw_to_linear16(audio_data)
            
            # Use Deepgram's prerecorded API for single chunks
            payload = {
                "buffer": audio_data,
            }
            
            options = {
                "model": "nova-2",
                "language": language_code,
                "encoding": "linear16",
                "sample_rate": 8000,
                "channels": 1,
                "punctuate": True,
                "smart_format": True,
            }
            
            response = await self.client.listen.asyncrest.v("1").transcribe_file(
                payload, options
            )
            
            # Extract transcript
            if response.results and response.results.channels:
                alternative = response.results.channels[0].alternatives[0]
                
                if alternative.transcript:
                    return TranscriptResult(
                        text=alternative.transcript,
                        confidence=alternative.confidence,
                        is_final=True,
                        language_code=language_code,
                        timestamp=asyncio.get_event_loop().time(),
                    )
            
            return None
            
        except Exception as e:
            logger.error(f"Error transcribing audio chunk: {e}")
            raise
