"""AWS speech services client for Transcribe (STT) and Polly (TTS)."""

import asyncio
import logging
from typing import AsyncIterator, Optional

import boto3
from botocore.exceptions import ClientError

from rivaai.config.settings import Settings

logger = logging.getLogger(__name__)


class AWSTranscribeClient:
    """Client for AWS Transcribe streaming STT."""

    def __init__(self, settings: Settings):
        """Initialize AWS Transcribe client.

        Args:
            settings: Application settings with AWS configuration
        """
        self.settings = settings
        self.client = boto3.client(
            "transcribe",
            region_name=settings.aws_region,
            aws_access_key_id=settings.aws_access_key_id or None,
            aws_secret_access_key=settings.aws_secret_access_key or None,
        )
        self.language_code = settings.transcribe_language_code
        self.enable_partial_results = settings.transcribe_enable_partial_results

    async def transcribe_stream(
        self,
        audio_stream: AsyncIterator[bytes],
        language_code: Optional[str] = None,
    ) -> AsyncIterator[dict]:
        """Transcribe streaming audio using AWS Transcribe.

        Args:
            audio_stream: Async iterator of audio chunks (Linear16 PCM, 16kHz)
            language_code: Language code (defaults to settings)

        Yields:
            Transcription results with partial and final transcripts

        Note:
            AWS Transcribe requires Linear16 PCM at 16kHz
            Audio format conversion should be done before calling this
        """
        lang = language_code or self.language_code

        try:
            # Start streaming transcription session
            response = await asyncio.to_thread(
                self.client.start_stream_transcription,
                LanguageCode=lang,
                MediaSampleRateHertz=16000,
                MediaEncoding="pcm",
                EnablePartialResultsStabilization=self.enable_partial_results,
                PartialResultsStability="high",
            )

            # Process audio stream
            async for audio_chunk in audio_stream:
                # Send audio to Transcribe
                await asyncio.to_thread(
                    response["TranscriptResultStream"].send_audio_event,
                    AudioChunk=audio_chunk,
                )

                # Receive transcription results
                async for event in response["TranscriptResultStream"]:
                    if "TranscriptEvent" in event:
                        transcript_event = event["TranscriptEvent"]
                        results = transcript_event.get("Transcript", {}).get("Results", [])

                        for result in results:
                            if result.get("Alternatives"):
                                alternative = result["Alternatives"][0]
                                yield {
                                    "text": alternative.get("Transcript", ""),
                                    "is_final": not result.get("IsPartial", True),
                                    "confidence": alternative.get("Confidence", 0.0),
                                    "language_code": lang,
                                }

        except ClientError as e:
            logger.error(f"AWS Transcribe error: {e}")
            raise


class AWSPollyClient:
    """Client for AWS Polly streaming TTS."""

    def __init__(self, settings: Settings):
        """Initialize AWS Polly client.

        Args:
            settings: Application settings with AWS configuration
        """
        self.settings = settings
        self.client = boto3.client(
            "polly",
            region_name=settings.aws_region,
            aws_access_key_id=settings.aws_access_key_id or None,
            aws_secret_access_key=settings.aws_secret_access_key or None,
        )
        self.voice_id = settings.polly_voice_id
        self.engine = settings.polly_engine

    # Voice mapping for Indian languages
    VOICE_MAP = {
        "hi-IN": "Aditi",  # Hindi (female, neural)
        "mr-IN": "Aditi",  # Marathi (use Hindi voice)
        "te-IN": "Aditi",  # Telugu (use Hindi voice)
        "ta-IN": "Aditi",  # Tamil (use Hindi voice)
        "bn-IN": "Aditi",  # Bengali (use Hindi voice)
        "en-IN": "Kajal",  # English-India (female, neural)
    }

    async def synthesize_speech_stream(
        self,
        text: str,
        language_code: str = "hi-IN",
        voice_id: Optional[str] = None,
    ) -> AsyncIterator[bytes]:
        """Synthesize speech using AWS Polly with streaming.

        Args:
            text: Text to synthesize
            language_code: Language code
            voice_id: Optional voice ID override

        Yields:
            Audio chunks (PCM format)

        Note:
            Polly returns audio in PCM format which needs conversion to μ-law for telephony
        """
        voice = voice_id or self.VOICE_MAP.get(language_code, self.voice_id)

        try:
            response = await asyncio.to_thread(
                self.client.synthesize_speech,
                Text=text,
                OutputFormat="pcm",  # Linear16 PCM
                VoiceId=voice,
                Engine=self.engine,
                LanguageCode=language_code,
                SampleRate="16000",
            )

            # Stream audio chunks
            audio_stream = response.get("AudioStream")
            if audio_stream:
                chunk_size = 1024
                while True:
                    chunk = await asyncio.to_thread(audio_stream.read, chunk_size)
                    if not chunk:
                        break
                    yield chunk

        except ClientError as e:
            logger.error(f"AWS Polly error: {e}")
            raise

    async def get_available_voices(self, language_code: str = "hi-IN") -> list:
        """Get available Polly voices for a language.

        Args:
            language_code: Language code

        Returns:
            List of available voice IDs
        """
        try:
            response = await asyncio.to_thread(
                self.client.describe_voices,
                LanguageCode=language_code,
            )
            return [voice["Id"] for voice in response.get("Voices", [])]
        except ClientError as e:
            logger.error(f"Error fetching Polly voices: {e}")
            return []


def get_aws_transcribe_client(settings: Settings) -> AWSTranscribeClient:
    """Get AWS Transcribe client instance.

    Args:
        settings: Application settings

    Returns:
        AWSTranscribeClient instance
    """
    return AWSTranscribeClient(settings)


def get_aws_polly_client(settings: Settings) -> AWSPollyClient:
    """Get AWS Polly client instance.

    Args:
        settings: Application settings

    Returns:
        AWSPollyClient instance
    """
    return AWSPollyClient(settings)
