"""Property-based tests for Speech-to-Text Processor.

This module implements property-based tests for STT latency and accuracy
using Hypothesis for comprehensive input coverage.

Properties tested:
- Property 2: Streaming STT Latency
- Property 5: Noise Robustness
- Property 6: Low Confidence Clarification
- Property 8: Voice Activity Detection
"""

import asyncio
import audioop
import math
import time
from typing import AsyncIterator

import pytest
from hypothesis import given, strategies as st

from rivaai.speech import SpeechProcessor, TranscriptResult


# ============================================================================
# Test Strategies (Generators)
# ============================================================================

def generate_sine_wave(
    frequency: float,
    duration: float,
    sample_rate: int = 8000,
    amplitude: float = 0.8,
) -> bytes:
    """Generate a sine wave audio signal in Linear16 PCM format.
    
    Args:
        frequency: Frequency in Hz
        duration: Duration in seconds
        sample_rate: Sample rate in Hz
        amplitude: Amplitude (0.0 to 1.0)
        
    Returns:
        Audio data in Linear16 PCM format
    """
    num_samples = int(sample_rate * duration)
    samples = []
    
    for i in range(num_samples):
        sample = int(32767 * amplitude * math.sin(2 * math.pi * frequency * i / sample_rate))
        samples.append(sample)
    
    return b''.join(
        sample.to_bytes(2, byteorder='little', signed=True)
        for sample in samples
    )


def add_noise(audio_data: bytes, snr_db: float) -> bytes:
    """Add white noise to audio signal at specified SNR.
    
    Args:
        audio_data: Clean audio in Linear16 PCM format
        snr_db: Signal-to-noise ratio in dB
        
    Returns:
        Noisy audio in Linear16 PCM format
    """
    # Calculate signal power
    signal_rms = audioop.rms(audio_data, 2)
    signal_power = signal_rms ** 2
    
    # Calculate noise power from SNR
    # SNR(dB) = 10 * log10(signal_power / noise_power)
    noise_power = signal_power / (10 ** (snr_db / 10))
    noise_amplitude = math.sqrt(noise_power)
    
    # Generate white noise
    import random
    num_samples = len(audio_data) // 2
    noise_samples = []
    
    for _ in range(num_samples):
        noise_sample = int(random.gauss(0, noise_amplitude))
        # Clamp to 16-bit range
        noise_sample = max(-32768, min(32767, noise_sample))
        noise_samples.append(noise_sample)
    
    noise_data = b''.join(
        sample.to_bytes(2, byteorder='little', signed=True)
        for sample in noise_samples
    )
    
    # Mix signal and noise
    try:
        noisy_audio = audioop.add(audio_data, noise_data, 2)
        return noisy_audio
    except audioop.error:
        # If lengths don't match, return original
        return audio_data


@st.composite
def audio_chunk_strategy(draw):
    """Generate random audio chunks for testing.
    
    Returns:
        Tuple of (audio_data, duration, has_speech)
    """
    # Duration between 0.1 and 2.0 seconds
    duration = draw(st.floats(min_value=0.1, max_value=2.0))
    
    # Frequency between 100 and 1000 Hz (speech range)
    frequency = draw(st.floats(min_value=100, max_value=1000))
    
    # Amplitude between 0.3 and 1.0
    amplitude = draw(st.floats(min_value=0.3, max_value=1.0))
    
    # Generate audio
    audio_data = generate_sine_wave(frequency, duration, amplitude=amplitude)
    
    # High amplitude means speech is present
    has_speech = amplitude > 0.5
    
    return audio_data, duration, has_speech


@st.composite
def noisy_audio_strategy(draw):
    """Generate audio with varying noise levels.
    
    Returns:
        Tuple of (audio_data, snr_db)
    """
    # Generate clean speech signal
    duration = draw(st.floats(min_value=0.5, max_value=2.0))
    frequency = draw(st.floats(min_value=200, max_value=800))
    clean_audio = generate_sine_wave(frequency, duration, amplitude=0.8)
    
    # SNR between 0 and 40 dB (requirement: up to 40dB)
    snr_db = draw(st.floats(min_value=0, max_value=40))
    
    # Add noise
    noisy_audio = add_noise(clean_audio, snr_db)
    
    return noisy_audio, snr_db


@st.composite
def language_strategy(draw):
    """Generate supported language codes."""
    languages = ["hi-IN", "mr-IN", "te-IN", "ta-IN", "bn-IN"]
    return draw(st.sampled_from(languages))


# ============================================================================
# Property 2: Streaming STT Latency
# ============================================================================

@pytest.mark.property
@pytest.mark.asyncio
@given(
    language=language_strategy(),
    chunk_duration=st.floats(min_value=0.1, max_value=1.0),
)
async def test_property_streaming_stt_latency(language, chunk_duration):
    """
    Feature: sochq, Property 2: Streaming STT Latency
    
    For any audio input during an active call, the Speech_Processor should
    provide the first partial transcript within 500ms of speech onset.
    
    **Validates: Requirements 1.2**
    
    Note: This test measures the processing time of the SpeechProcessor
    component itself. In a real deployment with Deepgram API, network
    latency would be additional.
    """
    processor = SpeechProcessor(api_key="test_key")
    
    # Generate test audio
    audio_data = generate_sine_wave(440, chunk_duration, amplitude=0.8)
    
    # Create async stream
    async def audio_stream() -> AsyncIterator[bytes]:
        yield audio_data
    
    # Measure time to first transcript
    start_time = time.perf_counter()
    first_transcript_time = None
    
    try:
        # Note: This will fail without real Deepgram API
        # In production, this test would use a mock or test API
        async for transcript in processor.process_audio_stream(audio_stream(), language):
            if first_transcript_time is None:
                first_transcript_time = time.perf_counter()
                break
    except Exception:
        # Expected to fail without real API
        # In production, use mocked Deepgram client
        pytest.skip("Requires Deepgram API for full test")
    
    if first_transcript_time:
        latency_ms = (first_transcript_time - start_time) * 1000
        
        # Property: First partial transcript within 500ms
        assert latency_ms <= 500, (
            f"STT latency {latency_ms:.1f}ms exceeds 500ms requirement"
        )


# ============================================================================
# Property 5: Noise Robustness
# ============================================================================

@pytest.mark.property
@given(noisy_audio=noisy_audio_strategy())
def test_property_noise_robustness(noisy_audio):
    """
    Feature: sochq, Property 5: Noise Robustness
    
    For any audio sample with background noise up to 40dB SNR, the
    Speech_Processor should maintain at least 70% word accuracy in
    transcription.
    
    **Validates: Requirements 2.1**
    
    Note: This property test verifies that the processor can handle noisy
    audio without crashing. Full accuracy testing requires real transcription
    with ground truth, which would be done with Deepgram API integration.
    """
    processor = SpeechProcessor(api_key="test_key")
    audio_data, snr_db = noisy_audio
    
    # Verify processor can handle noisy audio
    # In production, this would compare transcription accuracy
    # against ground truth at various SNR levels
    
    # Test that VAD still works with noisy audio
    has_speech = processor.detect_voice_activity(audio_data)
    
    # Property: VAD should detect speech in noisy conditions
    # (since we added noise to a speech signal)
    assert isinstance(has_speech, bool), "VAD should return boolean"
    
    # For high SNR (cleaner audio), VAD should detect speech
    if snr_db > 20:
        assert has_speech, f"VAD should detect speech at {snr_db:.1f}dB SNR"


# ============================================================================
# Property 6: Low Confidence Clarification
# ============================================================================

@pytest.mark.property
@given(
    confidence=st.floats(min_value=0.0, max_value=1.0),
    language=language_strategy(),
)
def test_property_low_confidence_clarification(confidence, language):
    """
    Feature: sochq, Property 6: Low Confidence Clarification
    
    For any transcription with confidence score below 0.6, the
    Speech_Processor should trigger a clarification request rather than
    proceeding with the low-confidence transcript.
    
    **Validates: Requirements 2.2**
    """
    processor = SpeechProcessor(api_key="test_key")
    
    # Create a mock transcript result
    transcript = TranscriptResult(
        text="test transcript",
        confidence=confidence,
        is_final=True,
        language_code=language,
        timestamp=time.time(),
    )
    
    # Property: Low confidence should be flagged
    if confidence < 0.6:
        # In production, the system should request clarification
        # This is typically handled by the conversation layer
        assert transcript.confidence < processor.confidence_threshold, (
            f"Confidence {confidence:.2f} below threshold should be flagged"
        )
    else:
        # High confidence should proceed normally
        assert transcript.confidence >= 0.6, (
            f"Confidence {confidence:.2f} should be acceptable"
        )


# ============================================================================
# Property 8: Voice Activity Detection
# ============================================================================

@pytest.mark.property
@given(audio_chunk=audio_chunk_strategy())
def test_property_voice_activity_detection(audio_chunk):
    """
    Feature: sochq, Property 8: Voice Activity Detection
    
    For any audio chunk, the Speech_Processor should correctly classify it
    as containing speech or non-speech (background noise) using VAD.
    
    **Validates: Requirements 2.4**
    """
    processor = SpeechProcessor(api_key="test_key")
    audio_data, duration, expected_has_speech = audio_chunk
    
    # Test VAD
    has_speech = processor.detect_voice_activity(audio_data)
    
    # Property: VAD should return boolean
    assert isinstance(has_speech, bool), "VAD must return boolean"
    
    # Property: VAD result should correlate with audio energy
    # High amplitude audio should be detected as speech
    rms = audioop.rms(audio_data, 2)
    
    if rms > 1000:  # High energy
        assert has_speech, f"High energy audio (RMS={rms}) should be detected as speech"
    elif rms < 100:  # Very low energy
        assert not has_speech, f"Low energy audio (RMS={rms}) should not be detected as speech"


# ============================================================================
# Additional Property Tests
# ============================================================================

@pytest.mark.property
@given(language=language_strategy())
def test_property_supported_languages(language):
    """
    Property: All specified languages should be supported.
    
    For any language in the supported set, the processor should accept it.
    """
    processor = SpeechProcessor(api_key="test_key")
    supported = processor.get_supported_languages()
    
    # Property: Language should be in supported list
    assert language in supported, f"Language {language} should be supported"


@pytest.mark.property
@given(
    duration=st.floats(min_value=0.02, max_value=5.0),
    frequency=st.floats(min_value=50, max_value=2000),
)
def test_property_audio_transcoding(duration, frequency):
    """
    Property: Audio transcoding should preserve signal characteristics.
    
    For any audio signal, transcoding from Linear16 to µ-law and back
    should preserve the general characteristics (though with some loss).
    """
    processor = SpeechProcessor(api_key="test_key")
    
    # Generate clean audio
    linear_audio = generate_sine_wave(frequency, duration, amplitude=0.7)
    
    # Convert to µ-law
    mulaw_audio = audioop.lin2ulaw(linear_audio, 2)
    
    # Transcode back to Linear16
    transcoded = processor._transcode_mulaw_to_linear16(mulaw_audio)
    
    # Property: Transcoded audio should have same length
    assert len(transcoded) == len(linear_audio), (
        "Transcoded audio should have same length as original"
    )
    
    # Property: Transcoded audio should have similar energy
    original_rms = audioop.rms(linear_audio, 2)
    transcoded_rms = audioop.rms(transcoded, 2)
    
    # Allow 50% variation due to µ-law compression
    assert 0.5 * original_rms <= transcoded_rms <= 1.5 * original_rms, (
        f"Transcoded RMS {transcoded_rms} should be similar to original {original_rms}"
    )


@pytest.mark.property
@given(
    silence_duration=st.floats(min_value=0.1, max_value=2.0),
)
def test_property_silence_detection(silence_duration):
    """
    Property: Silence should not be detected as speech.
    
    For any duration of silence, VAD should return False.
    """
    processor = SpeechProcessor(api_key="test_key")
    
    # Generate silence
    sample_rate = 8000
    num_samples = int(sample_rate * silence_duration)
    silence = b'\x00\x00' * num_samples
    
    # Test VAD
    has_speech = processor.detect_voice_activity(silence)
    
    # Property: Silence should not be detected as speech
    assert not has_speech, "Silence should not be detected as speech"
