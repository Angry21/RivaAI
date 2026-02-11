"""Audio transcoding utilities for converting between audio formats."""

import audioop
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class AudioTranscoder:
    """
    Handles audio transcoding between different formats.
    
    Primary use case: Converting G.711 μ-law PCM (telephony standard) to Linear16 PCM
    (required by most STT services like Deepgram).
    """

    # Audio format constants
    MULAW_SAMPLE_WIDTH = 1  # 8-bit μ-law
    LINEAR16_SAMPLE_WIDTH = 2  # 16-bit linear PCM
    TELEPHONY_SAMPLE_RATE = 8000  # 8kHz

    def __init__(self):
        """Initialize the audio transcoder."""
        logger.info("AudioTranscoder initialized")

    def mulaw_to_linear16(
        self,
        mulaw_data: bytes,
        sample_rate: int = TELEPHONY_SAMPLE_RATE
    ) -> bytes:
        """
        Convert G.711 μ-law PCM to Linear16 PCM.
        
        Args:
            mulaw_data: Audio data in μ-law format (8-bit)
            sample_rate: Sample rate in Hz (default: 8000)
            
        Returns:
            Audio data in Linear16 format (16-bit signed PCM)
            
        Raises:
            ValueError: If input data is invalid
        """
        try:
            if not mulaw_data:
                raise ValueError("Empty audio data provided")
            
            # Convert μ-law to linear PCM using audioop
            linear_data = audioop.ulaw2lin(mulaw_data, self.LINEAR16_SAMPLE_WIDTH)
            
            logger.debug(
                f"Transcoded μ-law to Linear16: "
                f"input_size={len(mulaw_data)} bytes, "
                f"output_size={len(linear_data)} bytes"
            )
            
            return linear_data
            
        except Exception as e:
            logger.error(f"Failed to transcode μ-law to Linear16: {e}", exc_info=True)
            raise

    def linear16_to_mulaw(
        self,
        linear_data: bytes,
        sample_rate: int = TELEPHONY_SAMPLE_RATE
    ) -> bytes:
        """
        Convert Linear16 PCM to G.711 μ-law PCM.
        
        Args:
            linear_data: Audio data in Linear16 format (16-bit signed PCM)
            sample_rate: Sample rate in Hz (default: 8000)
            
        Returns:
            Audio data in μ-law format (8-bit)
            
        Raises:
            ValueError: If input data is invalid
        """
        try:
            if not linear_data:
                raise ValueError("Empty audio data provided")
            
            # Convert linear PCM to μ-law using audioop
            mulaw_data = audioop.lin2ulaw(linear_data, self.LINEAR16_SAMPLE_WIDTH)
            
            logger.debug(
                f"Transcoded Linear16 to μ-law: "
                f"input_size={len(linear_data)} bytes, "
                f"output_size={len(mulaw_data)} bytes"
            )
            
            return mulaw_data
            
        except Exception as e:
            logger.error(f"Failed to transcode Linear16 to μ-law: {e}", exc_info=True)
            raise

    def resample_audio(
        self,
        audio_data: bytes,
        from_rate: int,
        to_rate: int,
        sample_width: int = LINEAR16_SAMPLE_WIDTH
    ) -> bytes:
        """
        Resample audio to a different sample rate.
        
        Args:
            audio_data: Input audio data
            from_rate: Source sample rate in Hz
            to_rate: Target sample rate in Hz
            sample_width: Sample width in bytes (default: 2 for Linear16)
            
        Returns:
            Resampled audio data
            
        Raises:
            ValueError: If input data is invalid
        """
        try:
            if not audio_data:
                raise ValueError("Empty audio data provided")
            
            if from_rate == to_rate:
                return audio_data
            
            # Resample using audioop
            resampled_data, _ = audioop.ratecv(
                audio_data,
                sample_width,
                1,  # mono channel
                from_rate,
                to_rate,
                None  # no state (for streaming, state would be maintained)
            )
            
            logger.debug(
                f"Resampled audio: {from_rate}Hz -> {to_rate}Hz, "
                f"input_size={len(audio_data)} bytes, "
                f"output_size={len(resampled_data)} bytes"
            )
            
            return resampled_data
            
        except Exception as e:
            logger.error(
                f"Failed to resample audio from {from_rate}Hz to {to_rate}Hz: {e}",
                exc_info=True
            )
            raise

    def validate_audio_format(
        self,
        audio_data: bytes,
        expected_format: str,
        sample_rate: int
    ) -> bool:
        """
        Validate audio data format and sample rate.
        
        Args:
            audio_data: Audio data to validate
            expected_format: Expected format ("mulaw" or "linear16")
            sample_rate: Expected sample rate in Hz
            
        Returns:
            True if valid, False otherwise
        """
        try:
            if not audio_data:
                logger.warning("Empty audio data provided for validation")
                return False
            
            # Basic validation: check if data size is reasonable
            if expected_format == "mulaw":
                # μ-law: 1 byte per sample
                expected_bytes_per_second = sample_rate * self.MULAW_SAMPLE_WIDTH
            elif expected_format == "linear16":
                # Linear16: 2 bytes per sample
                expected_bytes_per_second = sample_rate * self.LINEAR16_SAMPLE_WIDTH
            else:
                logger.error(f"Unknown audio format: {expected_format}")
                return False
            
            # Check if data size is a multiple of sample width
            if expected_format == "mulaw":
                is_valid = len(audio_data) % self.MULAW_SAMPLE_WIDTH == 0
            else:
                is_valid = len(audio_data) % self.LINEAR16_SAMPLE_WIDTH == 0
            
            if not is_valid:
                logger.warning(
                    f"Audio data size {len(audio_data)} is not a multiple of "
                    f"sample width for format {expected_format}"
                )
            
            return is_valid
            
        except Exception as e:
            logger.error(f"Failed to validate audio format: {e}", exc_info=True)
            return False
