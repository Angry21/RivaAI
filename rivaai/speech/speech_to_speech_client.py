"""Speech-to-speech client for direct audio-to-audio processing with RAG integration."""

import asyncio
import logging
from typing import AsyncIterator, Dict, List, Optional

import httpx

from rivaai.config.settings import Settings

logger = logging.getLogger(__name__)


class SpeechToSpeechClient:
    """
    Speech-to-speech client that processes audio input and generates audio output directly.
    
    Supports multiple providers:
    - OpenAI Realtime API (GPT-4o Audio)
    - Custom models via API
    - Future: AWS Bedrock when speech models available
    """

    def __init__(self, settings: Settings):
        """Initialize speech-to-speech client.

        Args:
            settings: Application settings
        """
        self.settings = settings
        self.provider = settings.speech_model_provider
        self.http_client = httpx.AsyncClient(timeout=30.0)

    async def process_audio_stream(
        self,
        audio_stream: AsyncIterator[bytes],
        language_code: str = "hi-IN",
        rag_context: Optional[str] = None,
        system_prompt: Optional[str] = None,
    ) -> AsyncIterator[bytes]:
        """Process audio input and generate audio output directly.

        Args:
            audio_stream: Input audio stream (Linear16 PCM, 16kHz)
            language_code: Language code for processing
            rag_context: Optional RAG context to inject
            system_prompt: Optional system prompt for behavior control

        Yields:
            Audio output chunks (Linear16 PCM, 16kHz)

        Note:
            This eliminates the STT → LLM → TTS pipeline for lowest latency
        """
        if self.provider == "openai":
            async for chunk in self._process_openai_realtime(
                audio_stream, language_code, rag_context, system_prompt
            ):
                yield chunk
        elif self.provider == "custom":
            async for chunk in self._process_custom_api(
                audio_stream, language_code, rag_context, system_prompt
            ):
                yield chunk
        else:
            raise ValueError(f"Unsupported speech-to-speech provider: {self.provider}")

    async def _process_openai_realtime(
        self,
        audio_stream: AsyncIterator[bytes],
        language_code: str,
        rag_context: Optional[str],
        system_prompt: Optional[str],
    ) -> AsyncIterator[bytes]:
        """Process using OpenAI Realtime API (GPT-4o Audio).

        Args:
            audio_stream: Input audio stream
            language_code: Language code
            rag_context: RAG context
            system_prompt: System prompt

        Yields:
            Audio output chunks
        """
        # OpenAI Realtime API endpoint
        url = "https://api.openai.com/v1/realtime"
        
        headers = {
            "Authorization": f"Bearer {self.settings.openai_api_key}",
            "Content-Type": "application/json",
        }

        # Build session configuration
        session_config = {
            "model": "gpt-4o-realtime-preview",
            "modalities": ["audio", "text"],
            "voice": "alloy",  # Can be customized per language
            "input_audio_format": "pcm16",
            "output_audio_format": "pcm16",
            "turn_detection": {
                "type": "server_vad",
                "threshold": 0.5,
                "prefix_padding_ms": 300,
                "silence_duration_ms": 500,
            },
        }

        # Add system instructions with RAG context
        instructions = self._build_instructions(system_prompt, rag_context, language_code)
        if instructions:
            session_config["instructions"] = instructions

        try:
            # Establish WebSocket connection for streaming
            async with self.http_client.stream("POST", url, headers=headers, json=session_config) as response:
                # Stream audio input
                async for audio_chunk in audio_stream:
                    # Send audio to API
                    await response.awrite({
                        "type": "input_audio_buffer.append",
                        "audio": audio_chunk.hex(),  # Base64 or hex encoding
                    })

                    # Receive audio output
                    async for event in response.aiter_lines():
                        if event:
                            import json
                            data = json.loads(event)
                            
                            if data.get("type") == "response.audio.delta":
                                # Decode and yield audio chunk
                                audio_data = bytes.fromhex(data["delta"])
                                yield audio_data

        except Exception as e:
            logger.error(f"OpenAI Realtime API error: {e}")
            raise

    async def _process_custom_api(
        self,
        audio_stream: AsyncIterator[bytes],
        language_code: str,
        rag_context: Optional[str],
        system_prompt: Optional[str],
    ) -> AsyncIterator[bytes]:
        """Process using custom speech-to-speech API.

        Args:
            audio_stream: Input audio stream
            language_code: Language code
            rag_context: RAG context
            system_prompt: System prompt

        Yields:
            Audio output chunks

        Note:
            Implement this for custom speech models or future AWS Bedrock speech models
        """
        # Placeholder for custom API implementation
        # This would connect to your custom speech-to-speech model endpoint
        
        logger.warning("Custom speech-to-speech API not yet implemented")
        raise NotImplementedError("Custom speech-to-speech API not implemented")

    def _build_instructions(
        self,
        system_prompt: Optional[str],
        rag_context: Optional[str],
        language_code: str,
    ) -> str:
        """Build system instructions with RAG context.

        Args:
            system_prompt: Base system prompt
            rag_context: RAG context to inject
            language_code: Language code

        Returns:
            Combined instructions
        """
        instructions = []

        # Base system prompt
        if system_prompt:
            instructions.append(system_prompt)
        else:
            # Default prompt for RivaAI
            instructions.append(
                "You are RivaAI, a helpful voice assistant providing decision support "
                "to rural users in India. Speak clearly and simply in their language. "
                "Provide actionable advice based on verified information."
            )

        # Language instruction
        lang_map = {
            "hi-IN": "Respond in Hindi (हिंदी)",
            "mr-IN": "Respond in Marathi (मराठी)",
            "te-IN": "Respond in Telugu (తెలుగు)",
            "ta-IN": "Respond in Tamil (தமிழ்)",
            "bn-IN": "Respond in Bengali (বাংলা)",
        }
        if language_code in lang_map:
            instructions.append(lang_map[language_code])

        # RAG context injection
        if rag_context:
            instructions.append(
                f"\n\nRelevant information from knowledge base:\n{rag_context}\n\n"
                "Use this information to provide accurate, helpful responses."
            )

        return "\n\n".join(instructions)

    async def inject_rag_context(
        self,
        query_text: str,
        language_code: str,
    ) -> str:
        """Retrieve and format RAG context for speech-to-speech processing.

        Args:
            query_text: User query (from partial STT or intent detection)
            language_code: Language code

        Returns:
            Formatted RAG context string

        Note:
            This is called when we detect the user needs knowledge base information
            The context is injected into the speech-to-speech session
        """
        from rivaai.knowledge import get_retrieval_system
        from rivaai.config.database import get_database_pool
        from rivaai.llm import get_bedrock_embedding_client

        # Get retrieval system
        db_pool = get_database_pool(self.settings)
        embedding_client = get_bedrock_embedding_client(self.settings)
        retrieval_system = get_retrieval_system(db_pool, embedding_client, self.settings)

        # Perform retrieval
        results = await retrieval_system.search(
            query=query_text,
            top_k=self.settings.retrieval_top_k,
            threshold=self.settings.retrieval_relevance_threshold,
        )

        # Format context
        context = await retrieval_system.format_for_rag(
            results=results,
            max_tokens=2000,
        )

        return context

    async def close(self) -> None:
        """Close HTTP client."""
        await self.http_client.aclose()


class HybridSpeechProcessor:
    """
    Hybrid processor that can switch between:
    1. Speech-to-speech (lowest latency, no RAG)
    2. STT → LLM + RAG → TTS (higher latency, with knowledge)
    
    Intelligently routes based on query complexity and knowledge requirements.
    """

    def __init__(self, settings: Settings):
        """Initialize hybrid speech processor.

        Args:
            settings: Application settings
        """
        self.settings = settings
        self.speech_to_speech = SpeechToSpeechClient(settings)
        self.use_speech_to_speech = settings.use_speech_to_speech

    async def process_audio(
        self,
        audio_stream: AsyncIterator[bytes],
        language_code: str = "hi-IN",
        requires_rag: bool = False,
    ) -> AsyncIterator[bytes]:
        """Process audio with intelligent routing.

        Args:
            audio_stream: Input audio stream
            language_code: Language code
            requires_rag: Whether query requires knowledge base

        Yields:
            Audio output chunks

        Note:
            - Simple queries: Use speech-to-speech (fastest)
            - Complex queries needing RAG: Use STT → LLM+RAG → TTS
        """
        if self.use_speech_to_speech and not requires_rag:
            # Fast path: Direct speech-to-speech
            logger.info("Using speech-to-speech (fast path)")
            async for chunk in self.speech_to_speech.process_audio_stream(
                audio_stream, language_code
            ):
                yield chunk
        else:
            # Knowledge path: Traditional pipeline with RAG
            logger.info("Using STT → LLM+RAG → TTS (knowledge path)")
            # This would call the traditional pipeline
            # Implemented in speech/processor.py
            raise NotImplementedError("Traditional pipeline integration pending")

    async def close(self) -> None:
        """Close resources."""
        await self.speech_to_speech.close()


def get_speech_to_speech_client(settings: Settings) -> SpeechToSpeechClient:
    """Get speech-to-speech client instance.

    Args:
        settings: Application settings

    Returns:
        SpeechToSpeechClient instance
    """
    return SpeechToSpeechClient(settings)


def get_hybrid_speech_processor(settings: Settings) -> HybridSpeechProcessor:
    """Get hybrid speech processor instance.

    Args:
        settings: Application settings

    Returns:
        HybridSpeechProcessor instance
    """
    return HybridSpeechProcessor(settings)
