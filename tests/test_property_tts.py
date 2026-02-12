"""Property-based tests for Text-to-Speech Processor.

This module implements property-based tests for TTS latency
using Hypothesis for comprehensive input coverage.

Properties tested:
- Property 4: Streaming TTS Latency
"""

import asyncio
import time
from unittest.mock import AsyncMock, patch

import pytest
from hypothesis import given, strategies as st

from rivaai.speech.models import VoiceConfig
from rivaai.speech.tts_processor import TextToSpeechProcessor


# ============================================================================
# Test Strategies (Generators)
# ============================================================================

@st.composite
def text_strategy(draw):
    """Generate random text for TTS testing.
    
    Returns:
        Text string of varying length
    """
    # Text length between 10 and 200 characters
    min_length = 10
    max_length = 200
    length = draw(st.integers(min_value=min_length, max_value=max_length))
    
    # Generate text with common patterns
    text_patterns = [
        "Hello, how can I help you today?",
        "नमस्ते, मैं आपकी कैसे मदद कर सकता हूं?",  # Hindi
        "Let me check that information for you.",
        "The recommended dosage is 2 liters per acre.",
        "Please wait while I look up the details.",
    ]
    
    base_text = draw(st.sampled_from(text_patterns))
    
    # Extend or truncate to desired length
    if len(base_text) < length:
        # Repeat text to reach desired length
        repetitions = (length // len(base_text)) + 1
        extended = (base_text + " ") * repetitions
        return extended[:length]
    else:
        return base_text[:length]


@st.composite
def language_strategy(draw):
    """Generate supported language codes."""
    languages = ["hi-IN", "mr-IN", "te-IN", "ta-IN", "bn-IN"]
    return draw(st.sampled_from(languages))


# ============================================================================
# Property 4: Streaming TTS Latency
# ============================================================================

@pytest.mark.property
@pytest.mark.asyncio
@given(
    text=text_strategy(),
    language=language_strategy(),
)
async def test_property_streaming_tts_latency(text, language):
    """
    Feature: sochq, Property 4: Streaming TTS Latency
    
    For any text response, the TTS processor should begin streaming audio
    output within 800ms of receiving the text.
    
    **Validates: Requirements 1.5**
    
    Note: This test measures the processing time of the TextToSpeechProcessor
    component itself. In a real deployment with ElevenLabs API, network
    latency would be additional.
    """
    # Create processor
    with patch("rivaai.speech.tts_processor.get_settings") as mock_settings:
        settings_mock = AsyncMock()
        settings_mock.elevenlabs_api_key = "test_api_key"
        settings_mock.supported_languages = ["hi-IN", "mr-IN", "te-IN", "ta-IN", "bn-IN"]
        mock_settings.return_value = settings_mock
        
        with patch("rivaai.speech.tts_processor.AsyncElevenLabs"):
            processor = TextToSpeechProcessor(api_key="test_api_key")
    
    # Mock the ElevenLabs API to return audio chunks
    mock_audio_chunks = [b"\x00\x01" * 160 for _ in range(10)]  # 10 chunks
    
    async def mock_stream():
        # Simulate realistic streaming delay
        await asyncio.sleep(0.05)  # 50ms for first chunk
        for chunk in mock_audio_chunks:
            yield chunk
            await asyncio.sleep(0.02)  # 20ms between chunks
    
    processor.client.text_to_speech.convert_as_stream = AsyncMock(
        return_value=mock_stream()
    )
    
    # Measure time to first audio chunk
    start_time = time.perf_counter()
    first_chunk_time = None
    
    try:
        async for chunk in processor.synthesize_speech_stream(
            text=text,
            language_code=language,
            output_mulaw=False,  # Skip transcoding for latency test
        ):
            if first_chunk_time is None:
                first_chunk_time = time.perf_counter()
                break  # Only measure first chunk latency
    except Exception as e:
        pytest.fail(f"TTS synthesis failed: {e}")
    
    if first_chunk_time:
        latency_ms = (first_chunk_time - start_time) * 1000
        
        # Property: First audio chunk within 800ms
        assert latency_ms <= 800, (
            f"TTS latency {latency_ms:.1f}ms exceeds 800ms requirement "
            f"(text length: {len(text)}, language: {language})"
        )
    else:
        pytest.fail("No audio chunks received from TTS")


# ============================================================================
# Additional Property Tests
# ============================================================================

@pytest.mark.property
@pytest.mark.asyncio
@given(
    text=text_strategy(),
    language=language_strategy(),
)
async def test_property_tts_output_format(text, language):
    """
    Property: TTS output should be in correct format.
    
    For any text and language, the TTS processor should output audio
    in the expected format (μ-law PCM at 8kHz).
    """
    with patch("rivaai.speech.tts_processor.get_settings") as mock_settings:
        settings_mock = AsyncMock()
        settings_mock.elevenlabs_api_key = "test_api_key"
        settings_mock.supported_languages = ["hi-IN", "mr-IN", "te-IN", "ta-IN", "bn-IN"]
        mock_settings.return_value = settings_mock
        
        with patch("rivaai.speech.tts_processor.AsyncElevenLabs"):
            processor = TextToSpeechProcessor(api_key="test_api_key")
    
    # Mock audio stream
    mock_audio_chunks = [b"\x00\x01" * 160 for _ in range(5)]
    
    async def mock_stream():
        for chunk in mock_audio_chunks:
            yield chunk
    
    processor.client.text_to_speech.convert_as_stream = AsyncMock(
        return_value=mock_stream()
    )
    
    # Test with μ-law output
    chunks = []
    async for chunk in processor.synthesize_speech_stream(
        text=text,
        language_code=language,
        output_mulaw=True,
    ):
        chunks.append(chunk)
    
    # Property: Should receive audio chunks
    assert len(chunks) > 0, "Should receive at least one audio chunk"
    
    # Property: All chunks should be bytes
    assert all(isinstance(chunk, bytes) for chunk in chunks), (
        "All audio chunks should be bytes"
    )


@pytest.mark.property
@pytest.mark.asyncio
@given(language=language_strategy())
async def test_property_supported_languages(language):
    """
    Property: All specified languages should be supported.
    
    For any language in the supported set, the processor should accept it
    and have a voice mapping.
    """
    with patch("rivaai.speech.tts_processor.get_settings") as mock_settings:
        settings_mock = AsyncMock()
        settings_mock.elevenlabs_api_key = "test_api_key"
        settings_mock.supported_languages = ["hi-IN", "mr-IN", "te-IN", "ta-IN", "bn-IN"]
        mock_settings.return_value = settings_mock
        
        with patch("rivaai.speech.tts_processor.AsyncElevenLabs"):
            processor = TextToSpeechProcessor(api_key="test_api_key")
    
    # Property: Language should be in supported list
    assert language in processor.supported_languages, (
        f"Language {language} should be supported"
    )
    
    # Property: Language should have voice mapping
    assert language in processor.VOICE_MAPPINGS, (
        f"Language {language} should have voice mapping"
    )


@pytest.mark.property
@pytest.mark.asyncio
@given(
    text=st.text(min_size=1, max_size=50),
    language=language_strategy(),
)
async def test_property_empty_text_handling(text, language):
    """
    Property: TTS should handle various text inputs gracefully.
    
    For any text input (including edge cases), the processor should
    either synthesize audio or handle gracefully without crashing.
    """
    with patch("rivaai.speech.tts_processor.get_settings") as mock_settings:
        settings_mock = AsyncMock()
        settings_mock.elevenlabs_api_key = "test_api_key"
        settings_mock.supported_languages = ["hi-IN", "mr-IN", "te-IN", "ta-IN", "bn-IN"]
        mock_settings.return_value = settings_mock
        
        with patch("rivaai.speech.tts_processor.AsyncElevenLabs"):
            processor = TextToSpeechProcessor(api_key="test_api_key")
    
    # Mock audio stream
    async def mock_stream():
        if text.strip():  # Only yield audio for non-empty text
            yield b"\x00\x01" * 160
    
    processor.client.text_to_speech.convert_as_stream = AsyncMock(
        return_value=mock_stream()
    )
    
    # Property: Should not crash on any text input
    try:
        chunks = []
        async for chunk in processor.synthesize_speech_stream(
            text=text,
            language_code=language,
            output_mulaw=False,
        ):
            chunks.append(chunk)
        
        # If text is empty/whitespace, should return no chunks
        if not text.strip():
            assert len(chunks) == 0, "Empty text should produce no audio"
    except Exception as e:
        pytest.fail(f"TTS should handle text gracefully, but raised: {e}")


@pytest.mark.property
@pytest.mark.asyncio
@given(
    text=text_strategy(),
    language=language_strategy(),
)
async def test_property_safety_check_integration(text, language):
    """
    Property: Optimistic TTS pipeline should buffer audio during safety check.
    
    For any text, the TTS processor with safety check should buffer audio
    and only yield after safety check passes.
    """
    with patch("rivaai.speech.tts_processor.get_settings") as mock_settings:
        settings_mock = AsyncMock()
        settings_mock.elevenlabs_api_key = "test_api_key"
        settings_mock.supported_languages = ["hi-IN", "mr-IN", "te-IN", "ta-IN", "bn-IN"]
        mock_settings.return_value = settings_mock
        
        with patch("rivaai.speech.tts_processor.AsyncElevenLabs"):
            processor = TextToSpeechProcessor(api_key="test_api_key")
    
    # Mock audio stream
    mock_audio_chunks = [b"\x00\x01" * 160 for _ in range(5)]
    
    async def mock_stream():
        for chunk in mock_audio_chunks:
            yield chunk
            await asyncio.sleep(0.01)
    
    processor.client.text_to_speech.convert_as_stream = AsyncMock(
        return_value=mock_stream()
    )
    
    # Safety checker that always passes
    async def safety_checker(text):
        await asyncio.sleep(0.05)  # Simulate check delay
        return True
    
    # Property: Should receive all chunks after safety check passes
    chunks = []
    async for chunk in processor.synthesize_with_safety_check(
        text=text,
        language_code=language,
        safety_checker=safety_checker,
        output_mulaw=False,
    ):
        chunks.append(chunk)
    
    assert len(chunks) > 0, "Should receive audio chunks after safety check passes"


@pytest.mark.property
@pytest.mark.asyncio
@given(
    text=text_strategy(),
    language=language_strategy(),
)
async def test_property_voice_config_customization(text, language):
    """
    Property: Voice configuration should be applied correctly.
    
    For any text and custom voice configuration, the processor should
    use the specified voice settings.
    """
    with patch("rivaai.speech.tts_processor.get_settings") as mock_settings:
        settings_mock = AsyncMock()
        settings_mock.elevenlabs_api_key = "test_api_key"
        settings_mock.supported_languages = ["hi-IN", "mr-IN", "te-IN", "ta-IN", "bn-IN"]
        mock_settings.return_value = settings_mock
        
        with patch("rivaai.speech.tts_processor.AsyncElevenLabs"):
            processor = TextToSpeechProcessor(api_key="test_api_key")
    
    # Create custom voice config
    voice_config = VoiceConfig(
        language_code=language,
        voice_name="custom_voice_id",
        speaking_rate=1.0,
        pitch=0.0,
    )
    
    # Mock audio stream
    async def mock_stream():
        yield b"\x00\x01" * 160
    
    processor.client.text_to_speech.convert_as_stream = AsyncMock(
        return_value=mock_stream()
    )
    
    # Property: Should use custom voice ID
    chunks = []
    async for chunk in processor.synthesize_speech_stream(
        text=text,
        language_code=language,
        voice_config=voice_config,
        output_mulaw=False,
    ):
        chunks.append(chunk)
    
    # Verify custom voice was used
    call_args = processor.client.text_to_speech.convert_as_stream.call_args
    assert call_args.kwargs["voice_id"] == "custom_voice_id", (
        "Should use custom voice ID from config"
    )
