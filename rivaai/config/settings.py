"""Application settings and configuration management."""

from functools import lru_cache
from typing import List

from pydantic import Field, PostgresDsn, RedisDsn
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    app_name: str = "RivaAI"
    app_version: str = "0.1.0"
    debug: bool = False
    environment: str = Field(default="development", pattern="^(development|staging|production|testing)$")

    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    workers: int = 4

    # Telephony (Twilio)
    twilio_account_sid: str = Field(default="", description="Twilio Account SID")
    twilio_auth_token: str = Field(default="", description="Twilio Auth Token")
    twilio_phone_number: str = Field(default="", description="Twilio Phone Number")
    twilio_websocket_url: str = Field(
        default="", description="WebSocket URL for Twilio media streams"
    )

    # Speech Services
    deepgram_api_key: str = Field(default="", description="Deepgram API key for STT")
    elevenlabs_api_key: str = Field(default="", description="ElevenLabs API key for TTS")
    supported_languages: List[str] = Field(
        default=["hi-IN", "mr-IN", "te-IN", "ta-IN", "bn-IN"],
        description="Supported language codes",
    )

    # LLM Services
    openai_api_key: str = Field(default="", description="OpenAI API key")
    anthropic_api_key: str = Field(default="", description="Anthropic API key")
    groq_api_key: str = Field(default="", description="Groq API key for fast LLM")
    main_llm_model: str = Field(
        default="gpt-4-turbo-preview", description="Main LLM model for complex reasoning"
    )
    small_llm_model: str = Field(
        default="llama-3.1-8b-instant", description="Small LLM model for fast responses"
    )
    embedding_model: str = Field(
        default="text-embedding-3-large", description="Embedding model for vector search"
    )

    # Database (PostgreSQL with pgvector)
    database_url: PostgresDsn = Field(
        default="postgresql://postgres:postgres@localhost:5432/rivaai",
        description="PostgreSQL connection URL",
    )
    database_pool_size: int = Field(default=20, description="Database connection pool size")
    database_max_overflow: int = Field(
        default=10, description="Maximum overflow connections"
    )
    database_pool_timeout: int = Field(default=30, description="Connection pool timeout")
    database_pool_recycle: int = Field(
        default=3600, description="Connection recycle time in seconds"
    )

    # Redis (Session Store and Caching)
    redis_url: RedisDsn = Field(
        default="redis://localhost:6379/0", description="Redis connection URL"
    )
    redis_max_connections: int = Field(default=50, description="Redis connection pool size")
    session_ttl_hours: int = Field(default=24, description="Session TTL in hours")

    # Latency Budgets (milliseconds)
    call_establishment_latency_ms: int = Field(
        default=3000, description="Max latency for call establishment (3 rings)"
    )
    stt_partial_latency_ms: int = Field(
        default=500, description="Max latency for STT partial transcripts"
    )
    barge_in_latency_ms: int = Field(
        default=300, description="Max latency for barge-in interrupt"
    )
    tts_first_chunk_latency_ms: int = Field(
        default=800, description="Max latency for TTS first audio chunk"
    )
    simple_intent_latency_ms: int = Field(
        default=500, description="Max latency for simple intent responses"
    )
    clarification_latency_ms: int = Field(
        default=1200, description="Max latency for clarification responses"
    )
    complex_decision_latency_ms: int = Field(
        default=3000, description="Max latency for complex decision responses"
    )

    # Confidence Thresholds
    stt_confidence_threshold: float = Field(
        default=0.6, description="Minimum STT confidence for proceeding"
    )
    decision_confidence_threshold: float = Field(
        default=0.8, description="Minimum decision confidence for proceeding"
    )
    retrieval_relevance_threshold: float = Field(
        default=0.7, description="Minimum retrieval relevance score"
    )

    # Safety
    circuit_breaker_halt_latency_ms: int = Field(
        default=100, description="Max latency for circuit breaker halt"
    )
    safety_message_path: str = Field(
        default="assets/safety_messages", description="Path to pre-recorded safety messages"
    )

    # Retrieval
    retrieval_top_k: int = Field(default=5, description="Number of documents to retrieve")
    graph_traversal_depth: int = Field(default=2, description="Maximum graph traversal depth")
    hybrid_vector_weight: float = Field(
        default=0.6, description="Weight for vector score in hybrid search"
    )
    hybrid_graph_weight: float = Field(
        default=0.4, description="Weight for graph score in hybrid search"
    )

    # Response Generation
    max_response_tokens: int = Field(
        default=40, description="Maximum tokens in voice response"
    )
    max_sentence_words: int = Field(
        default=15, description="Maximum words per sentence"
    )

    # Monitoring
    log_level: str = Field(default="INFO", pattern="^(DEBUG|INFO|WARNING|ERROR|CRITICAL)$")
    enable_tracing: bool = Field(default=False, description="Enable distributed tracing")
    metrics_port: int = Field(default=9090, description="Prometheus metrics port")


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
