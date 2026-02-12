"""Speech processing components for STT and TTS."""

from rivaai.speech.models import AudioChunk, AudioDirection, TranscriptResult, VoiceConfig
from rivaai.speech.processor import SpeechProcessor
from rivaai.speech.tts_processor import TextToSpeechProcessor

__all__ = [
    "AudioChunk",
    "AudioDirection",
    "TranscriptResult",
    "VoiceConfig",
    "SpeechProcessor",
    "TextToSpeechProcessor",
]
