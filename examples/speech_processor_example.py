"""Example usage of SpeechProcessor for streaming STT.

This example demonstrates how to use the SpeechProcessor class
to transcribe audio streams in real-time.

Note: Requires a valid Deepgram API key in .env file.
"""

import asyncio
import audioop
import math
from typing import AsyncIterator

from rivaai.speech import SpeechProcessor


async def generate_test_audio_stream(duration_seconds: float = 2.0) -> AsyncIterator[bytes]:
    """Generate a test audio stream with sine wave.
    
    Args:
        duration_seconds: Duration of audio to generate
        
    Yields:
        Audio chunks in Linear16 PCM format (8kHz, 16-bit)
    """
    sample_rate = 8000
    chunk_duration = 0.02  # 20ms chunks (typical for telephony)
    chunk_samples = int(sample_rate * chunk_duration)
    total_chunks = int(duration_seconds / chunk_duration)
    
    frequency = 440  # A4 note
    
    for chunk_idx in range(total_chunks):
        samples = []
        for i in range(chunk_samples):
            sample_idx = chunk_idx * chunk_samples + i
            # Generate sine wave
            sample = int(20000 * math.sin(2 * math.pi * frequency * sample_idx / sample_rate))
            samples.append(sample)
        
        # Convert to bytes
        audio_chunk = b''.join(
            sample.to_bytes(2, byteorder='little', signed=True)
            for sample in samples
        )
        
        yield audio_chunk
        
        # Simulate real-time streaming
        await asyncio.sleep(chunk_duration)


async def main():
    """Main example function."""
    print("Speech Processor Example")
    print("=" * 50)
    
    # Initialize processor
    # API key will be loaded from .env file
    try:
        processor = SpeechProcessor()
        print(f"✓ Initialized SpeechProcessor")
        print(f"✓ Supported languages: {processor.get_supported_languages()}")
    except ValueError as e:
        print(f"✗ Error: {e}")
        print("  Please set DEEPGRAM_API_KEY in your .env file")
        return
    
    print("\n" + "=" * 50)
    print("Example 1: Voice Activity Detection")
    print("=" * 50)
    
    # Test VAD with speech-like audio
    sample_rate = 8000
    duration = 0.1
    num_samples = int(sample_rate * duration)
    
    # High energy audio (speech-like)
    samples = []
    for i in range(num_samples):
        sample = int(20000 * math.sin(2 * math.pi * 440 * i / sample_rate))
        samples.append(sample)
    
    speech_audio = b''.join(
        sample.to_bytes(2, byteorder='little', signed=True)
        for sample in samples
    )
    
    has_speech = processor.detect_voice_activity(speech_audio)
    print(f"High-energy audio contains speech: {has_speech}")
    
    # Silent audio
    silent_audio = b'\x00\x00' * num_samples
    has_speech = processor.detect_voice_activity(silent_audio)
    print(f"Silent audio contains speech: {has_speech}")
    
    print("\n" + "=" * 50)
    print("Example 2: Audio Transcoding (µ-law to Linear16)")
    print("=" * 50)
    
    # Convert Linear16 to µ-law
    mulaw_audio = audioop.lin2ulaw(speech_audio, 2)
    print(f"Original Linear16 size: {len(speech_audio)} bytes")
    print(f"µ-law encoded size: {len(mulaw_audio)} bytes")
    
    # Transcode back
    transcoded = processor._transcode_mulaw_to_linear16(mulaw_audio)
    print(f"Transcoded Linear16 size: {len(transcoded)} bytes")
    
    print("\n" + "=" * 50)
    print("Example 3: Streaming Transcription")
    print("=" * 50)
    print("Note: This requires a valid Deepgram API key")
    print("Generating test audio stream (2 seconds)...")
    
    # Uncomment to test with real API (requires valid API key)
    # try:
    #     audio_stream = generate_test_audio_stream(duration_seconds=2.0)
    #     
    #     print("\nTranscribing audio stream (Hindi)...")
    #     async for transcript in processor.process_audio_stream(
    #         audio_stream,
    #         language_code="hi-IN",
    #         is_mulaw=False,  # Our test audio is already Linear16
    #     ):
    #         status = "FINAL" if transcript.is_final else "partial"
    #         print(f"[{status}] {transcript.text} (confidence: {transcript.confidence:.2f})")
    # 
    # except Exception as e:
    #     print(f"Error during transcription: {e}")
    
    print("\n✓ Example completed successfully!")


if __name__ == "__main__":
    asyncio.run(main())
