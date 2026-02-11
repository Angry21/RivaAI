"""Speech processing components for STT and TTS."""

from rivaai.speech.models import AudioChunk, AudioDirection, TranscriptResult, VoiceConfig
from rivaai.speech.processor import SpeechProcessor

__all__ = [
    "AudioChunk",
    "AudioDirection",
    "TranscriptResult",
    "VoiceConfig",
    "SpeechProcessor",
]
