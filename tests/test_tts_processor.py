"""Unit tests for Text-to-Speech Processor."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from rivaai.speech.models import VoiceConfig
from rivaai.speech.tts_processor import TextToSpeechProcessor


@pytest.fixture
def mock_settings():
    """Mock settings for testing."""
    with patch("rivaai.speech.tts_processor.get_settings") as mock:
        settings = MagicMock()
        settings.elevenlabs_api_key = "test_api_key"
        settings.supported_languages = ["hi-IN", "mr-IN", "te-IN", "ta-IN", "bn-IN"]
        mock.return_value = settings
        yield settings


@pytest.fixture
def tts_processor(mock_settings):
    """Create TTS processor instance for testing."""
    with patch("rivaai.speech.tts_processor.AsyncElevenLabs"):
        processor = TextToSpeechProcessor(api_key="test_api_key")
        return processor


class TestTextToSpeechProcessor:
    """Test suite for TextToSpeechProcessor."""

    def test_initialization(self, mock_settings):
        """Test TTS processor initialization."""
        with patch("rivaai.speech.tts_processor.AsyncElevenLabs") as mock_client:
            processor = TextToSpeechProcessor(api_key="test_api_key")
            
            assert processor.api_key == "test_api_key"
            assert processor.supported_languages == mock_settings.supported_languages
            mock_client.assert_called_once_with(api_key="test_api_key")

    def test_initialization_without_api_key(self, mock_settings):
        """Test initialization fails without API key."""
        mock_settings.elevenlabs_api_key = ""
        
        with patch("rivaai.speech.tts_processor.AsyncElevenLabs"):
            with pytest.raises(ValueError, match="ElevenLabs API key is required"):
                TextToSpeechProcessor()

    def test_get_voice_id_default(self, tts_processor):
        """Test getting default voice ID for a language."""
        voice_id = tts_processor._get_voice_id("hi-IN")
        assert voice_id == tts_processor.VOICE_MAPPINGS["hi-IN"]

    def test_get_voice_id_custom(self, tts_processor):
        """Test getting custom voice ID from config."""
        voice_config = VoiceConfig(
            language_code="hi-IN",
            voice_name="custom_voice_id",
        )
        voice_id = tts_processor._get_voice_id("hi-IN", voice_config)
        assert voice_id == "custom_voice_id"

    def test_get_voice_id_unsupported_language(self, tts_processor):
        """Test error for unsupported language."""
        with pytest.raises(ValueError, match="Unsupported language"):
            tts_processor._get_voice_id("en-US")

    def test_transcode_linear16_to_mulaw(self, tts_processor):
        """Test audio transcoding from Linear16 to µ-law."""
        # Create sample Linear16 audio (16-bit PCM)
        linear_data = b"\x00\x00\x01\x00\x02\x00\x03\x00"
        
        mulaw_data = tts_processor._transcode_linear16_to_mulaw(linear_data)
        
        assert isinstance(mulaw_data, bytes)
        assert len(mulaw_data) == len(linear_data) // 2  # µ-law is 8-bit

    @pytest.mark.asyncio
    async def test_synthesize_speech_stream_empty_text(self, tts_processor):
        """Test synthesis with empty text."""
        chunks = []
        async for chunk in tts_processor.synthesize_speech_stream(
            text="",
            language_code="hi-IN",
        ):
            chunks.append(chunk)
        
        assert len(chunks) == 0

    @pytest.mark.asyncio
    async def test_synthesize_speech_stream_unsupported_language(self, tts_processor):
        """Test synthesis with unsupported language."""
        with pytest.raises(ValueError, match="Unsupported language"):
            async for _ in tts_processor.synthesize_speech_stream(
                text="Hello",
                language_code="en-US",
            ):
                pass

    @pytest.mark.asyncio
    async def test_synthesize_speech_stream_success(self, tts_processor):
        """Test successful streaming synthesis."""
        # Mock the ElevenLabs client
        mock_audio_chunks = [b"\x00\x01" * 160 for _ in range(5)]  # 5 chunks of audio
        
        async def mock_stream():
            for chunk in mock_audio_chunks:
                yield chunk
        
        tts_processor.client.text_to_speech.convert_as_stream = AsyncMock(
            return_value=mock_stream()
        )
        
        chunks = []
        async for chunk in tts_processor.synthesize_speech_stream(
            text="नमस्ते",  # Hindi: Hello
            language_code="hi-IN",
            output_mulaw=False,  # Skip µ-law conversion for simplicity
        ):
            chunks.append(chunk)
        
        assert len(chunks) > 0
        assert all(isinstance(chunk, bytes) for chunk in chunks)

    @pytest.mark.asyncio
    async def test_synthesize_speech_complete(self, tts_processor):
        """Test complete (non-streaming) synthesis."""
        # Mock the streaming method
        mock_chunks = [b"\x00\x01", b"\x02\x03", b"\x04\x05"]
        
        async def mock_stream(*args, **kwargs):
            for chunk in mock_chunks:
                yield chunk
        
        with patch.object(
            tts_processor,
            "synthesize_speech_stream",
            side_effect=mock_stream,
        ):
            audio = await tts_processor.synthesize_speech(
                text="Test",
                language_code="hi-IN",
            )
        
        assert audio == b"".join(mock_chunks)

    @pytest.mark.asyncio
    async def test_synthesize_with_safety_check_no_checker(self, tts_processor):
        """Test optimistic pipeline without safety checker."""
        mock_chunks = [b"\x00\x01", b"\x02\x03"]
        
        async def mock_stream(*args, **kwargs):
            for chunk in mock_chunks:
                yield chunk
        
        with patch.object(
            tts_processor,
            "synthesize_speech_stream",
            side_effect=mock_stream,
        ):
            chunks = []
            async for chunk in tts_processor.synthesize_with_safety_check(
                text="Test",
                language_code="hi-IN",
                safety_checker=None,
            ):
                chunks.append(chunk)
        
        assert chunks == mock_chunks

    @pytest.mark.asyncio
    async def test_synthesize_with_safety_check_passes(self, tts_processor):
        """Test optimistic pipeline with passing safety check."""
        mock_chunks = [b"\x00\x01", b"\x02\x03", b"\x04\x05"]
        
        async def mock_stream(*args, **kwargs):
            for chunk in mock_chunks:
                yield chunk
        
        async def safety_checker(text):
            await asyncio.sleep(0.01)  # Simulate check delay
            return True
        
        with patch.object(
            tts_processor,
            "synthesize_speech_stream",
            side_effect=mock_stream,
        ):
            chunks = []
            async for chunk in tts_processor.synthesize_with_safety_check(
                text="Safe content",
                language_code="hi-IN",
                safety_checker=safety_checker,
            ):
                chunks.append(chunk)
        
        assert len(chunks) == len(mock_chunks)

    @pytest.mark.asyncio
    async def test_synthesize_with_safety_check_fails(self, tts_processor):
        """Test optimistic pipeline with failing safety check."""
        mock_chunks = [b"\x00\x01", b"\x02\x03", b"\x04\x05"]
        
        async def mock_stream(*args, **kwargs):
            for chunk in mock_chunks:
                yield chunk
        
        async def safety_checker(text):
            await asyncio.sleep(0.01)  # Simulate check delay
            return False  # Fail the check
        
        with patch.object(
            tts_processor,
            "synthesize_speech_stream",
            side_effect=mock_stream,
        ):
            with pytest.raises(ValueError, match="Safety check failed"):
                async for _ in tts_processor.synthesize_with_safety_check(
                    text="Unsafe content",
                    language_code="hi-IN",
                    safety_checker=safety_checker,
                ):
                    pass

    @pytest.mark.asyncio
    async def test_synthesize_with_safety_check_error(self, tts_processor):
        """Test optimistic pipeline with safety check error."""
        mock_chunks = [b"\x00\x01", b"\x02\x03"]
        
        async def mock_stream(*args, **kwargs):
            for chunk in mock_chunks:
                yield chunk
        
        async def safety_checker(text):
            raise Exception("Safety check error")
        
        with patch.object(
            tts_processor,
            "synthesize_speech_stream",
            side_effect=mock_stream,
        ):
            with pytest.raises(ValueError, match="Safety check failed"):
                async for _ in tts_processor.synthesize_with_safety_check(
                    text="Test",
                    language_code="hi-IN",
                    safety_checker=safety_checker,
                ):
                    pass

    def test_all_languages_have_voice_mappings(self, tts_processor):
        """Test that all supported languages have voice mappings."""
        for lang in tts_processor.supported_languages:
            assert lang in tts_processor.VOICE_MAPPINGS, f"Missing voice mapping for {lang}"

    @pytest.mark.asyncio
    async def test_voice_config_applied(self, tts_processor):
        """Test that voice configuration is properly used."""
        voice_config = VoiceConfig(
            language_code="hi-IN",
            voice_name="custom_voice",
            speaking_rate=1.2,
            pitch=5.0,
        )
        
        mock_chunks = [b"\x00\x01"]
        
        async def mock_stream():
            for chunk in mock_chunks:
                yield chunk
        
        tts_processor.client.text_to_speech.convert_as_stream = AsyncMock(
            return_value=mock_stream()
        )
        
        chunks = []
        async for chunk in tts_processor.synthesize_speech_stream(
            text="Test",
            language_code="hi-IN",
            voice_config=voice_config,
            output_mulaw=False,
        ):
            chunks.append(chunk)
        
        # Verify the custom voice was used
        call_args = tts_processor.client.text_to_speech.convert_as_stream.call_args
        assert call_args.kwargs["voice_id"] == "custom_voice"
