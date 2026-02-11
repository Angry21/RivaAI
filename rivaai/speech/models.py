"""Data models for speech processing components."""

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class AudioDirection(Enum):
    """Direction of audio flow."""

    INCOMING = "incoming"  # User to system
    OUTGOING = "outgoing"  # System to user


@dataclass
class TranscriptResult:
    """Result from speech-to-text processing.
    
    Attributes:
        text: Transcribed text
        confidence: Confidence score from 0.0 to 1.0
        is_final: Whether this is a final transcript or partial
        language_code: Language code (e.g., 'hi-IN')
        timestamp: Unix timestamp when transcript was generated
    """

    text: str
    confidence: float
    is_final: bool
    language_code: str
    timestamp: float


@dataclass
class AudioChunk:
    """Audio data chunk for processing.
    
    Attributes:
        call_sid: Unique call session identifier
        audio_data: Raw audio bytes (μ-law PCM or Linear16)
        timestamp: Unix timestamp when chunk was received
        sequence_number: Sequence number for ordering
        direction: Direction of audio flow
    """

    call_sid: str
    audio_data: bytes
    timestamp: float
    sequence_number: int
    direction: AudioDirection


@dataclass
class VoiceConfig:
    """Configuration for text-to-speech voice.
    
    Attributes:
        language_code: Language code (e.g., 'hi-IN')
        voice_name: Name of the voice to use
        speaking_rate: Speaking rate from 0.8 to 1.2
        pitch: Pitch adjustment from -20.0 to 20.0
    """

    language_code: str
    voice_name: str
    speaking_rate: float = 1.0
    pitch: float = 0.0
