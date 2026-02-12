"""Text-to-Speech Processor with streaming support using ElevenLabs Turbo."""

import asyncio
import audioop
import logging
from typing import AsyncIterator, Dict, Optional

import httpx
from elevenlabs import VoiceSettings
from elevenlabs.client import AsyncElevenLabs

from rivaai.config import get_settings
from rivaai.speech.models import VoiceConfig

logger = logging.getLogger(__name__)


class TextToSpeechProcessor:
    """Text-to-Speech processor integrating ElevenLabs Turbo.
    
    Provides streaming synthesis with <500ms first chunk latency,
    natural voices for all 5 supported languages, and outputs
    μ-law PCM at 8kHz for telephony compatibility.
    
    Implements Optimistic TTS Pipeline with parallel safety check
    and audio buffering for low latency.
    
    Supports languages: hi-IN, mr-IN, te-IN, ta-IN, bn-IN
    """

    # Voice mappings for each language
    # These are example voice IDs - replace with actual ElevenLabs voice IDs
    VOICE_MAPPINGS: Dict[str, str] = {
        "hi-IN": "pNInz6obpgDQGcFmaJgB",  # Hindi voice
        "mr-IN": "TX3LPaxmHKxFdv7VOQHJ",  # Marathi voice
        "te-IN": "EXAVITQu4vr4xnSDxMaL",  # Telugu voice
        "ta-IN": "ErXwobaYiN019PkySvjV",  # Tamil voice
        "bn-IN": "MF3mGyEYCl7XYWbV9V6O",  # Bengali voice
    }

    def __init__(self, api_key: Optional[str] = None):
        """Initialize the TTS Processor.
        
        Args:
            api_key: ElevenLabs API key. If None, loads from settings.
        """
        self.settings = get_settings()
        self.api_key = api_key or self.settings.elevenlabs_api_key
        
        if not self.api_key:
            raise ValueError("ElevenLabs API key is required")
        
        # Initialize ElevenLabs client
        self.client = AsyncElevenLabs(api_key=self.api_key)
        
        # Supported languages
        self.supported_languages = self.settings.supported_languages
        
        logger.info(
            f"TextToSpeechProcessor initialized with languages: {self.supported_languages}"
        )

    def _get_voice_id(self, language_code: str, voice_config: Optional[VoiceConfig] = None) -> str:
        """Get voice ID for the specified language.
        
        Args:
            language_code: Language code (e.g., 'hi-IN')
            voice_config: Optional voice configuration with custom voice_name
            
        Returns:
            ElevenLabs voice ID
            
        Raises:
            ValueError: If language is not supported
        """
        if language_code not in self.supported_languages:
            raise ValueError(
                f"Unsupported language: {language_code}. "
                f"Supported: {self.supported_languages}"
            )
        
        # Use custom voice if provided, otherwise use default mapping
        if voice_config and voice_config.voice_name:
            return voice_config.voice_name
        
        return self.VOICE_MAPPINGS.get(language_code, self.VOICE_MAPPINGS["hi-IN"])

    def _transcode_linear16_to_mulaw(self, linear_data: bytes) -> bytes:
        """Transcode Linear16 PCM to G.711 µ-law.
        
        ElevenLabs outputs Linear16 PCM. Telephony systems require
        G.711 µ-law encoding at 8kHz.
        
        Args:
            linear_data: Audio data in Linear16 PCM format
            
        Returns:
            Audio data in G.711 µ-law format
        """
        try:
            # Convert linear PCM to µ-law
            mulaw_data = audioop.lin2ulaw(linear_data, 2)  # 2 bytes per sample (16-bit)
            return mulaw_data
        except Exception as e:
            logger.error(f"Error transcoding Linear16 to µ-law: {e}")
            raise

    async def synthesize_speech_stream(
        self,
        text: str,
        language_code: str,
        voice_config: Optional[VoiceConfig] = None,
        output_mulaw: bool = True,
    ) -> AsyncIterator[bytes]:
        """Stream audio synthesis with <500ms first chunk latency.
        
        Synthesizes text to speech using ElevenLabs Turbo with streaming
        output. First audio chunk arrives within 500ms. Outputs μ-law PCM
        at 8kHz for telephony compatibility.
        
        Args:
            text: Text to synthesize
            language_code: Language code (e.g., 'hi-IN')
            voice_config: Optional voice configuration
            output_mulaw: Whether to output µ-law format (default: True)
            
        Yields:
            Audio chunks in μ-law PCM format (or Linear16 if output_mulaw=False)
            
        Raises:
            ValueError: If language_code is not supported
        """
        if not text or not text.strip():
            logger.warning("Empty text provided for synthesis")
            return
        
        if language_code not in self.supported_languages:
            raise ValueError(
                f"Unsupported language: {language_code}. "
                f"Supported: {self.supported_languages}"
            )
        
        logger.info(f"Starting TTS synthesis for language: {language_code}, text: '{text[:50]}...'")
        
        try:
            # Get voice ID
            voice_id = self._get_voice_id(language_code, voice_config)
            
            # Configure voice settings
            voice_settings = VoiceSettings(
                stability=0.5,
                similarity_boost=0.75,
                style=0.0,
                use_speaker_boost=True,
            )
            
            # Apply custom voice settings if provided
            if voice_config:
                # ElevenLabs doesn't directly support speaking_rate and pitch
                # These would need to be handled via post-processing or model selection
                pass
            
            # Stream audio from ElevenLabs
            # Using turbo model for low latency
            audio_stream = await self.client.text_to_speech.convert_as_stream(
                voice_id=voice_id,
                text=text,
                model_id="eleven_turbo_v2_5",  # Turbo model for low latency
                voice_settings=voice_settings,
                output_format="pcm_16000",  # 16kHz Linear16 PCM
            )
            
            first_chunk = True
            chunk_count = 0
            
            # Stream audio chunks
            async for chunk in audio_stream:
                if first_chunk:
                    logger.info("First TTS audio chunk received")
                    first_chunk = False
                
                chunk_count += 1
                
                # Downsample from 16kHz to 8kHz for telephony
                # ElevenLabs outputs 16kHz, but telephony uses 8kHz
                downsampled = audioop.ratecv(
                    chunk,
                    2,  # 2 bytes per sample (16-bit)
                    1,  # mono
                    16000,  # input rate
                    8000,  # output rate
                    None,  # state (None for first call)
                )[0]
                
                # Transcode to µ-law if requested
                if output_mulaw:
                    downsampled = self._transcode_linear16_to_mulaw(downsampled)
                
                yield downsampled
            
            logger.info(f"TTS synthesis completed. Total chunks: {chunk_count}")
            
        except Exception as e:
            logger.error(f"Error in TTS synthesis: {e}")
            raise

    async def synthesize_speech(
        self,
        text: str,
        language_code: str,
        voice_config: Optional[VoiceConfig] = None,
        output_mulaw: bool = True,
    ) -> bytes:
        """Synthesize complete audio (non-streaming).
        
        Useful for pre-generating safety messages or testing.
        
        Args:
            text: Text to synthesize
            language_code: Language code (e.g., 'hi-IN')
            voice_config: Optional voice configuration
            output_mulaw: Whether to output µ-law format (default: True)
            
        Returns:
            Complete audio data in μ-law PCM format (or Linear16 if output_mulaw=False)
        """
        audio_chunks = []
        
        async for chunk in self.synthesize_speech_stream(
            text=text,
            language_code=language_code,
            voice_config=voice_config,
            output_mulaw=output_mulaw,
        ):
            audio_chunks.append(chunk)
        
        return b"".join(audio_chunks)

    async def synthesize_with_safety_check(
        self,
        text: str,
        language_code: str,
        safety_checker: Optional[callable] = None,
        voice_config: Optional[VoiceConfig] = None,
        output_mulaw: bool = True,
    ) -> AsyncIterator[bytes]:
        """Optimistic TTS Pipeline: parallel safety check + audio buffering.
        
        Starts TTS synthesis immediately while running safety check in parallel.
        Buffers audio chunks and only yields them after safety check passes.
        If safety check fails, discards buffered audio and raises exception.
        
        This approach minimizes latency for safe content while still preventing
        unsafe audio from reaching the user.
        
        Args:
            text: Text to synthesize
            language_code: Language code (e.g., 'hi-IN')
            safety_checker: Async function that checks text safety (returns bool)
            voice_config: Optional voice configuration
            output_mulaw: Whether to output µ-law format (default: True)
            
        Yields:
            Audio chunks after safety check passes
            
        Raises:
            ValueError: If safety check fails
        """
        if not safety_checker:
            # No safety checker provided, proceed with normal synthesis
            async for chunk in self.synthesize_speech_stream(
                text=text,
                language_code=language_code,
                voice_config=voice_config,
                output_mulaw=output_mulaw,
            ):
                yield chunk
            return
        
        logger.info("Starting optimistic TTS pipeline with safety check")
        
        # Buffer for audio chunks
        audio_buffer = []
        safety_check_complete = False
        safety_check_passed = False
        
        # Start safety check in parallel
        async def run_safety_check():
            nonlocal safety_check_complete, safety_check_passed
            try:
                safety_check_passed = await safety_checker(text)
                safety_check_complete = True
                logger.info(f"Safety check completed: {'PASSED' if safety_check_passed else 'FAILED'}")
            except Exception as e:
                logger.error(f"Safety check error: {e}")
                safety_check_complete = True
                safety_check_passed = False
        
        # Start safety check task
        safety_task = asyncio.create_task(run_safety_check())
        
        try:
            # Start TTS synthesis
            async for chunk in self.synthesize_speech_stream(
                text=text,
                language_code=language_code,
                voice_config=voice_config,
                output_mulaw=output_mulaw,
            ):
                # Buffer the chunk
                audio_buffer.append(chunk)
                
                # If safety check is complete, decide what to do
                if safety_check_complete:
                    if not safety_check_passed:
                        # Safety check failed - discard buffer and stop
                        logger.warning("Safety check failed - discarding buffered audio")
                        raise ValueError("Safety check failed - content blocked")
                    
                    # Safety check passed - yield buffered chunks and continue streaming
                    if audio_buffer:
                        logger.info(f"Safety check passed - yielding {len(audio_buffer)} buffered chunks")
                        for buffered_chunk in audio_buffer:
                            yield buffered_chunk
                        audio_buffer.clear()
                    
                    # Yield current chunk
                    yield chunk
                else:
                    # Safety check still running - continue buffering
                    # Limit buffer size to prevent memory issues
                    if len(audio_buffer) > 50:  # ~1 second of audio at 20ms chunks
                        logger.warning("Audio buffer size limit reached, waiting for safety check")
                        await safety_task  # Wait for safety check to complete
            
            # Synthesis complete - wait for safety check if not done
            if not safety_check_complete:
                await safety_task
            
            # Yield any remaining buffered chunks if safety passed
            if safety_check_passed and audio_buffer:
                logger.info(f"Yielding final {len(audio_buffer)} buffered chunks")
                for buffered_chunk in audio_buffer:
                    yield buffered_chunk
            elif not safety_check_passed:
                raise ValueError("Safety check failed - content blocked")
                
        finally:
            # Ensure safety task is cleaned up
            if not safety_task.done():
                safety_task.cancel()
                try:
                    await safety_task
                except asyncio.CancelledError:
                    pass
