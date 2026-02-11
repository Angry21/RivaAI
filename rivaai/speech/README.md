# Speech Processing Module

This module provides Speech-to-Text (STT) processing capabilities using Deepgram Nova-2 API with streaming support.

## Components

### SpeechProcessor

The main class for speech-to-text processing with the following features:

- **Streaming Recognition**: Real-time transcription with partial results (<300ms latency)
- **Multi-language Support**: Supports 5 Indian languages (hi-IN, mr-IN, te-IN, ta-IN, bn-IN)
- **Audio Transcoding**: Automatic conversion from G.711 µ-law to Linear16 PCM
- **Confidence Scoring**: Detects low-confidence transcripts and requests clarification
- **Voice Activity Detection**: Simple energy-based VAD for speech detection

## Usage

### Basic Initialization

```python
from rivaai.speech import SpeechProcessor

# Initialize with API key from environment
processor = SpeechProcessor()

# Or provide API key explicitly
processor = SpeechProcessor(api_key="your_deepgram_api_key")
```

### Streaming Transcription

```python
import asyncio
from typing import AsyncIterator

async def audio_stream() -> AsyncIterator[bytes]:
    """Your audio stream generator."""
    # Yield audio chunks (G.711 µ-law or Linear16)
    yield audio_chunk

async def transcribe():
    processor = SpeechProcessor()
    
    async for transcript in processor.process_audio_stream(
        audio_stream(),
        language_code="hi-IN",
        is_mulaw=True,  # Set to False if audio is already Linear16
    ):
        if transcript.is_final:
            print(f"Final: {transcript.text} (confidence: {transcript.confidence})")
        else:
            print(f"Partial: {transcript.text}")

asyncio.run(transcribe())
```

### Single Audio Chunk Transcription

```python
async def transcribe_chunk():
    processor = SpeechProcessor()
    
    # Transcribe a single audio chunk
    result = await processor.transcribe_audio_chunk(
        audio_data=audio_bytes,
        language_code="hi-IN",
        is_mulaw=True,
    )
    
    if result:
        print(f"Transcript: {result.text}")
        print(f"Confidence: {result.confidence}")

asyncio.run(transcribe_chunk())
```

### Voice Activity Detection

```python
processor = SpeechProcessor()

# Check if audio contains speech
has_speech = processor.detect_voice_activity(audio_chunk)

if has_speech:
    print("Speech detected!")
else:
    print("No speech detected")
```

### Audio Transcoding

```python
processor = SpeechProcessor()

# Convert G.711 µ-law to Linear16 PCM
linear16_audio = processor._transcode_mulaw_to_linear16(mulaw_audio)
```

## Data Models

### TranscriptResult

Represents a transcription result:

```python
@dataclass
class TranscriptResult:
    text: str              # Transcribed text
    confidence: float      # Confidence score (0.0 to 1.0)
    is_final: bool        # Whether this is final or partial
    language_code: str    # Language code (e.g., 'hi-IN')
    timestamp: float      # Unix timestamp
```

### AudioChunk

Represents an audio data chunk:

```python
@dataclass
class AudioChunk:
    call_sid: str              # Call session identifier
    audio_data: bytes          # Raw audio bytes
    timestamp: float           # Unix timestamp
    sequence_number: int       # Sequence number
    direction: AudioDirection  # INCOMING or OUTGOING
```

## Configuration

The following settings can be configured via environment variables:

```bash
# Deepgram API key (required)
DEEPGRAM_API_KEY=your_api_key_here

# Confidence threshold for low-confidence detection (default: 0.6)
STT_CONFIDENCE_THRESHOLD=0.6

# Supported languages (default: hi-IN, mr-IN, te-IN, ta-IN, bn-IN)
SUPPORTED_LANGUAGES=["hi-IN", "mr-IN", "te-IN", "ta-IN", "bn-IN"]
```

## Supported Languages

The processor supports the following Indian language codes:

- `hi-IN` - Hindi (India)
- `mr-IN` - Marathi (India)
- `te-IN` - Telugu (India)
- `ta-IN` - Tamil (India)
- `bn-IN` - Bengali (India)

## Audio Format Requirements

### Input Audio

The processor accepts two audio formats:

1. **G.711 µ-law** (telephony standard):
   - Sample rate: 8kHz
   - Encoding: µ-law PCM
   - Automatically transcoded to Linear16

2. **Linear16 PCM**:
   - Sample rate: 8kHz
   - Encoding: 16-bit signed PCM
   - Channels: 1 (mono)

### Output Audio

Deepgram processes audio in Linear16 PCM format. The processor handles transcoding automatically when `is_mulaw=True`.

## Performance Characteristics

- **Streaming Latency**: <300ms for partial transcripts
- **Confidence Threshold**: 0.6 (configurable)
- **VAD Threshold**: 500 RMS energy (simple heuristic)

## Error Handling

The processor handles various error conditions:

```python
try:
    async for transcript in processor.process_audio_stream(...):
        print(transcript.text)
except ValueError as e:
    # Unsupported language or invalid configuration
    print(f"Configuration error: {e}")
except RuntimeError as e:
    # Deepgram connection failure
    print(f"Connection error: {e}")
except Exception as e:
    # Other errors
    print(f"Unexpected error: {e}")
```

## Low Confidence Handling

When transcription confidence falls below the threshold (default: 0.6), the processor logs a warning:

```python
# Automatic logging of low confidence
# WARNING: Low confidence transcript: 0.45 - 'unclear speech'
```

Your application should handle low-confidence transcripts by:
1. Requesting the user to repeat
2. Asking for clarification
3. Using alternative input methods (DTMF)

## Testing

Run the test suite:

```bash
# Activate virtual environment
.venv\Scripts\activate  # Windows
source .venv/bin/activate  # Linux/Mac

# Run tests
pytest tests/test_speech_processor.py -v
```

## Examples

See `examples/speech_processor_example.py` for a complete working example demonstrating:
- Voice activity detection
- Audio transcoding
- Streaming transcription setup

## Requirements

- Python 3.11+
- Deepgram SDK 3.2.7+
- Valid Deepgram API key

## Implementation Notes

### Audio Transcoding

The processor uses Python's `audioop` module for µ-law to Linear16 conversion. Note that `audioop` is deprecated in Python 3.13 and will need to be replaced with an alternative library in future versions.

### Voice Activity Detection

The current VAD implementation uses a simple RMS energy threshold. For production use, consider:
- WebRTC VAD for better accuracy
- Silero VAD for deep learning-based detection
- Deepgram's built-in VAD features

### Streaming Architecture

The processor uses asyncio for concurrent audio streaming and transcript reception:
1. Audio chunks are sent to Deepgram in real-time
2. Transcripts are received via callbacks
3. Results are queued and yielded to the caller

## Future Enhancements

Potential improvements for future versions:

1. **Enhanced VAD**: Integrate WebRTC VAD or Silero VAD
2. **Audio Preprocessing**: Add noise reduction and normalization
3. **Multi-channel Support**: Handle stereo audio streams
4. **Batch Processing**: Support for batch transcription of recorded audio
5. **Custom Models**: Support for Deepgram custom models
6. **Metrics Collection**: Add latency and accuracy metrics
