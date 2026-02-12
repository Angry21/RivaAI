"""Property-based tests for Text-to-Speech Processor latency.

This module implements property-based tests for TTS streaming latency
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
    """Generate random text for TTS synthesis.
    
    Returns:
        Text string of varying length
    """
    # Generate text between 10 and 200 characters
    # Typical response length for voice interface
    min_length = draw(st.integers(min_value=10, max_value=50))
    max_length = draw(st.integers(min_value=min_length, max_value=200))
    
    # Use printable characters and common punctuation
    text = draw(st.text(
        alphabet=st.characters(whitelist_categories=('L', 'N', 'P', 'Z')),
        min_size=min_length,
        max_size=max_length
    ))
    
    # Ensure text is not empty after stripping
    text = text.strip()
    if not text:
        text = "Test message"
    
    return text


@st.composite
def language_strategy(draw):
    """Generate supported language codes."""
    languages = ["hi-IN", "mr-IN", "te-IN", "ta-IN", "bn-IN"]
    return draw(st.sampled_from(languages))


@st.composite
def voice_config_strategy(draw):
    """Generate optional voice configuration."""
    # 50% chance of None
    if draw(st.booleans()):
        return None
    
    # Generate voice config
    return VoiceConfig(
        language_code=draw(language_strategy()),
        voice_name=None,  # Use default voice
        speaking_rate=draw(st.floats(min_value=0.8, max_value=1.2)),
        pitch=draw(st.floats(min_value=-20.0, max_value=20.0)),
    )


# ============================================================================
# Property 4: Streaming TTS Latency
# ============================================================================

@pytest.mark.property
@pytest.mark.asyncio
@given(
    text=text_strategy(),
    language=language_strategy(),
    voice_config=voice_config_strategy(),
)
async def test_property_streaming_tts_latency(text, language, voice_config):
    """
    Feature: sochq, Property 4: Streaming TTS Latency
    
    For any text response, the TTS processor should begin streaming audio
    output within 800ms of receiving the text.
    
    **Validates: Requirements 1.5**
    
    This test verifies that the first audio chunk is yielded within the
    800ms latency requirement. The test uses mocked ElevenLabs API to
    simulate realistic streaming behavior.
    """
    # Mock the ElevenLabs client to simulate streaming
    with patch("rivaai.speech.tts_processor.AsyncElevenLabs") as mock_client_class:
        # Create processor
        processor = TextToSpeechProcessor(api_key="test_api_key")
        
        # Mock audio chunks (simulate realistic chunk sizes)
        # ElevenLabs typically streams in small chunks
        mock_chunks = [
            b'\x00\x01' * 160,  # ~20ms of audio at 8kHz
            b'\x02\x03' * 160,
            b'\x04\x05' * 160,
        ]
        
        # Create async generator for streaming
        async def mock_stream():
            # Simulate small delay for first chunk (network + processing)
            await asyncio.sleep(0.1)  # 100ms simulated latency
            for chunk in mock_chunks:
                yield chunk
                await asyncio.sleep(0.02)  # 20ms between chunks
        
        # Configure mock
        processor.client.text_to_speech.convert_as_stream = AsyncMock(
            return_value=mock_stream()
        )
        
        # Measure time to first audio chunk
        start_time = time.perf_counter()
        first_chunk_time = None
        chunk_count = 0
        
        async for chunk in processor.synthesize_speech_stream(
            text=text,
            language_code=language,
            voice_config=voice_config,
            output_mulaw=True,
        ):
            if first_chunk_time is None:
                first_chunk_time = time.perf_counter()
            chunk_count += 1
        
        # Calculate latency
        if first_chunk_time:
            latency_ms = (first_chunk_time - start_time) * 1000
            
            # Property: First audio chunk within 800ms
            assert latency_ms <= 800, (
                f"TTS latency {latency_ms:.1f}ms exceeds 800ms requirement "
                f"(text length: {len(text)}, language: {language})"
            )
            
            # Verify we got audio chunks
            assert chunk_count > 0, "Should receive at least one audio chunk"
        else:
            pytest.fail("No audio chunks received from TTS processor")


@pytest.mark.property
@pytest.mark.asyncio
@given(
    text=text_strategy(),
    language=language_strategy(),
)
async def test_property_tts_latency_with_varying_delays(text, language):
    """
    Property: TTS latency should be consistent across varying network delays.
    
    Tests that the processor handles different simulated network conditions
    while maintaining the 800ms first-chunk latency requirement.
    """
    with patch("rivaai.speech.tts_processor.AsyncElevenLabs"):
        processor = TextToSpeechProcessor(api_key="test_api_key")
        
        # Simulate varying network delays (50ms to 500ms)
        network_delay = 0.05 + (hash(text) % 450) / 1000.0  # Deterministic but varied
        
        mock_chunks = [b'\x00\x01' * 160, b'\x02\x03' * 160]
        
        async def mock_stream():
            await asyncio.sleep(network_delay)
            for chunk in mock_chunks:
                yield chunk
        
        processor.client.text_to_speech.convert_as_stream = AsyncMock(
            return_value=mock_stream()
        )
        
        start_time = time.perf_counter()
        first_chunk_time = None
        
        async for chunk in processor.synthesize_speech_stream(
            text=text,
            language_code=language,
        ):
            if first_chunk_time is None:
                first_chunk_time = time.perf_counter()
                break
        
        if first_chunk_time:
            latency_ms = (first_chunk_time - start_time) * 1000
            
            # Property: Should handle network delays within budget
            assert latency_ms <= 800, (
                f"TTS latency {latency_ms:.1f}ms exceeds 800ms with "
                f"network delay {network_delay*1000:.1f}ms"
            )


@pytest.mark.property
@pytest.mark.asyncio
@given(
    language=language_strategy(),
)
async def test_property_tts_empty_text_handling(language):
    """
    Property: Empty text should not cause latency violations.
    
    For any empty or whitespace-only text, the processor should handle
    it gracefully without blocking or exceeding latency requirements.
    """
    with patch("rivaai.speech.tts_processor.AsyncElevenLabs"):
        processor = TextToSpeechProcessor(api_key="test_api_key")
        
        # Test with empty text
        start_time = time.perf_counter()
        chunk_count = 0
        
        async for chunk in processor.synthesize_speech_stream(
            text="",
            language_code=language,
        ):
            chunk_count += 1
        
        elapsed_ms = (time.perf_counter() - start_time) * 1000
        
        # Property: Empty text should return quickly (no chunks)
        assert chunk_count == 0, "Empty text should not produce audio chunks"
        assert elapsed_ms < 100, (
            f"Empty text handling took {elapsed_ms:.1f}ms, should be near-instant"
        )


@pytest.mark.property
@pytest.mark.asyncio
@given(
    text=text_strategy(),
    language=language_strategy(),
)
async def test_property_tts_streaming_continuity(text, language):
    """
    Property: TTS streaming should provide continuous audio chunks.
    
    For any text input, the processor should stream multiple chunks
    without large gaps, maintaining smooth audio output.
    """
    with patch("rivaai.speech.tts_processor.AsyncElevenLabs"):
        processor = TextToSpeechProcessor(api_key="test_api_key")
        
        # Generate multiple chunks
        num_chunks = max(3, len(text) // 20)  # More chunks for longer text
        mock_chunks = [b'\x00\x01' * 160 for _ in range(num_chunks)]
        
        async def mock_stream():
            await asyncio.sleep(0.1)
            for chunk in mock_chunks:
                yield chunk
                await asyncio.sleep(0.02)  # 20ms between chunks
        
        processor.client.text_to_speech.convert_as_stream = AsyncMock(
            return_value=mock_stream()
        )
        
        chunk_times = []
        async for chunk in processor.synthesize_speech_stream(
            text=text,
            language_code=language,
        ):
            chunk_times.append(time.perf_counter())
        
        # Property: Should receive multiple chunks
        assert len(chunk_times) >= 2, "Should receive multiple audio chunks"
        
        # Property: First chunk within latency requirement
        # (chunk_times are absolute, need to compare with test start)
        # This is implicitly tested by the main latency test
        
        # Property: Chunks should arrive with reasonable spacing
        if len(chunk_times) > 1:
            gaps = [
                (chunk_times[i+1] - chunk_times[i]) * 1000
                for i in range(len(chunk_times) - 1)
            ]
            max_gap = max(gaps)
            
            # Gaps should be reasonable (< 200ms between chunks)
            assert max_gap < 200, (
                f"Gap between chunks {max_gap:.1f}ms too large, "
                f"may cause audio stuttering"
            )


@pytest.mark.property
@pytest.mark.asyncio
@given(
    text=text_strategy(),
    language=language_strategy(),
)
async def test_property_tts_audio_format(text, language):
    """
    Property: TTS output should be in correct audio format.
    
    For any text input, the processor should output audio in µ-law PCM
    format suitable for telephony (8kHz).
    """
    with patch("rivaai.speech.tts_processor.AsyncElevenLabs"):
        processor = TextToSpeechProcessor(api_key="test_api_key")
        
        # Mock audio chunks
        mock_chunks = [b'\x00\x01' * 160, b'\x02\x03' * 160]
        
        async def mock_stream():
            await asyncio.sleep(0.05)
            for chunk in mock_chunks:
                yield chunk
        
        processor.client.text_to_speech.convert_as_stream = AsyncMock(
            return_value=mock_stream()
        )
        
        chunks = []
        async for chunk in processor.synthesize_speech_stream(
            text=text,
            language_code=language,
            output_mulaw=True,
        ):
            chunks.append(chunk)
        
        # Property: Should receive audio chunks
        assert len(chunks) > 0, "Should receive audio chunks"
        
        # Property: Chunks should be bytes
        for chunk in chunks:
            assert isinstance(chunk, bytes), "Audio chunks must be bytes"
            assert len(chunk) > 0, "Audio chunks must not be empty"


@pytest.mark.property
@pytest.mark.asyncio
@given(
    language=language_strategy(),
)
async def test_property_tts_language_support(language):
    """
    Property: All supported languages should work with TTS.
    
    For any supported language, the processor should accept it and
    begin synthesis without errors.
    """
    with patch("rivaai.speech.tts_processor.AsyncElevenLabs"):
        processor = TextToSpeechProcessor(api_key="test_api_key")
        
        # Mock minimal stream
        async def mock_stream():
            await asyncio.sleep(0.05)
            yield b'\x00\x01' * 160
        
        processor.client.text_to_speech.convert_as_stream = AsyncMock(
            return_value=mock_stream()
        )
        
        # Property: Should not raise error for supported language
        chunk_received = False
        async for chunk in processor.synthesize_speech_stream(
            text="Test message",
            language_code=language,
        ):
            chunk_received = True
            break
        
        assert chunk_received, f"Should receive audio for language {language}"


@pytest.mark.property
@pytest.mark.asyncio
async def test_property_tts_unsupported_language():
    """
    Property: Unsupported languages should raise ValueError.
    
    For any unsupported language code, the processor should raise
    a clear error rather than proceeding with incorrect synthesis.
    """
    with patch("rivaai.speech.tts_processor.AsyncElevenLabs"):
        processor = TextToSpeechProcessor(api_key="test_api_key")
        
        # Property: Should raise ValueError for unsupported language
        with pytest.raises(ValueError, match="Unsupported language"):
            async for _ in processor.synthesize_speech_stream(
                text="Test",
                language_code="en-US",  # Not in supported list
            ):
                pass
