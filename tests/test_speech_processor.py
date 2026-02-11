"""Unit tests for Speech-to-Text Processor."""

import asyncio
import audioop
from typing import AsyncIterator

import pytest

from rivaai.speech import SpeechProcessor, TranscriptResult


class TestSpeechProcessor:
    """Test suite for SpeechProcessor class."""

    def test_initialization(self):
        """Test SpeechProcessor initialization."""
        # Should raise error without API key
        with pytest.raises(ValueError, match="Deepgram API key is required"):
            SpeechProcessor(api_key="")

    def test_get_supported_languages(self):
        """Test getting supported languages."""
        processor = SpeechProcessor(api_key="test_key")
        languages = processor.get_supported_languages()
        
        assert isinstance(languages, list)
        assert len(languages) == 5
        assert "hi-IN" in languages
        assert "mr-IN" in languages
        assert "te-IN" in languages
        assert "ta-IN" in languages
        assert "bn-IN" in languages

    def test_mulaw_to_linear16_transcoding(self):
        """Test audio transcoding from µ-law to Linear16."""
        processor = SpeechProcessor(api_key="test_key")
        
        # Create sample Linear16 audio
        sample_rate = 8000
        duration = 0.1  # 100ms
        num_samples = int(sample_rate * duration)
        
        # Generate a simple sine wave
        import math
        frequency = 440  # A4 note
        linear_samples = []
        for i in range(num_samples):
            sample = int(32767 * math.sin(2 * math.pi * frequency * i / sample_rate))
            linear_samples.append(sample)
        
        # Convert to bytes (16-bit signed integers)
        linear_data = b''.join(
            sample.to_bytes(2, byteorder='little', signed=True)
            for sample in linear_samples
        )
        
        # Convert to µ-law
        mulaw_data = audioop.lin2ulaw(linear_data, 2)
        
        # Test transcoding back to Linear16
        transcoded = processor._transcode_mulaw_to_linear16(mulaw_data)
        
        assert isinstance(transcoded, bytes)
        assert len(transcoded) == len(linear_data)

    def test_voice_activity_detection_with_speech(self):
        """Test VAD with audio containing speech-like energy."""
        processor = SpeechProcessor(api_key="test_key")
        
        # Create high-energy audio (simulating speech)
        import math
        sample_rate = 8000
        duration = 0.1
        num_samples = int(sample_rate * duration)
        
        samples = []
        for i in range(num_samples):
            # High amplitude signal
            sample = int(20000 * math.sin(2 * math.pi * 440 * i / sample_rate))
            samples.append(sample)
        
        audio_data = b''.join(
            sample.to_bytes(2, byteorder='little', signed=True)
            for sample in samples
        )
        
        has_speech = processor.detect_voice_activity(audio_data)
        assert has_speech is True

    def test_voice_activity_detection_with_silence(self):
        """Test VAD with silent audio."""
        processor = SpeechProcessor(api_key="test_key")
        
        # Create silent audio (all zeros)
        sample_rate = 8000
        duration = 0.1
        num_samples = int(sample_rate * duration)
        
        audio_data = b'\x00\x00' * num_samples
        
        has_speech = processor.detect_voice_activity(audio_data)
        assert has_speech is False

    @pytest.mark.asyncio
    async def test_process_audio_stream_unsupported_language(self):
        """Test that unsupported language raises ValueError."""
        processor = SpeechProcessor(api_key="test_key")
        
        async def dummy_stream() -> AsyncIterator[bytes]:
            yield b'\x00\x00'
        
        with pytest.raises(ValueError, match="Unsupported language"):
            async for _ in processor.process_audio_stream(
                dummy_stream(), "en-US"
            ):
                pass

    @pytest.mark.asyncio
    async def test_transcribe_audio_chunk_unsupported_language(self):
        """Test that unsupported language raises ValueError for single chunk."""
        processor = SpeechProcessor(api_key="test_key")
        
        with pytest.raises(ValueError, match="Unsupported language"):
            await processor.transcribe_audio_chunk(
                b'\x00\x00', "en-US"
            )


class TestTranscriptResult:
    """Test suite for TranscriptResult dataclass."""

    def test_transcript_result_creation(self):
        """Test creating a TranscriptResult."""
        result = TranscriptResult(
            text="नमस्ते",
            confidence=0.95,
            is_final=True,
            language_code="hi-IN",
            timestamp=1234567890.0,
        )
        
        assert result.text == "नमस्ते"
        assert result.confidence == 0.95
        assert result.is_final is True
        assert result.language_code == "hi-IN"
        assert result.timestamp == 1234567890.0

    def test_transcript_result_low_confidence(self):
        """Test TranscriptResult with low confidence."""
        result = TranscriptResult(
            text="unclear speech",
            confidence=0.45,
            is_final=False,
            language_code="hi-IN",
            timestamp=1234567890.0,
        )
        
        assert result.confidence < 0.6
        assert result.is_final is False
