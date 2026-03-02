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

    # Telephony - India-compatible options
    telephony_provider: str = Field(
        default="amazon_connect",
        description="Telephony provider: amazon_connect, exotel, or twilio"
    )
    
    # Amazon Connect (Primary for India)
    amazon_connect_instance_id: str = Field(default="", description="Amazon Connect instance ID")
    amazon_connect_contact_flow_id: str = Field(default="", description="Contact flow ID")
    amazon_connect_phone_number: str = Field(default="", description="Amazon Connect phone number")
    
    # Exotel (Alternative for India)
    exotel_api_key: str = Field(default="", description="Exotel API key")
    exotel_api_token: str = Field(default="", description="Exotel API token")
    exotel_sid: str = Field(default="", description="Exotel SID")
    exotel_phone_number: str = Field(default="", description="Exotel phone number")
    
    # Twilio (Fallback - limited India support)
    twilio_account_sid: str = Field(default="", description="Twilio Account SID")
    twilio_auth_token: str = Field(default="", description="Twilio Auth Token")
    twilio_phone_number: str = Field(default="", description="Twilio Phone Number")

    # Speech Services - AWS Native (Primary for low latency)
    use_aws_speech: bool = Field(default=True, description="Use AWS Transcribe/Polly for speech")
    
    # AWS Transcribe (STT)
    transcribe_language_code: str = Field(default="hi-IN", description="Primary language for transcription")
    transcribe_enable_partial_results: bool = Field(default=True, description="Enable streaming partial results")
    
    # AWS Polly (TTS)
    polly_voice_id: str = Field(default="Aditi", description="Polly voice ID (Aditi for Hindi)")
    polly_engine: str = Field(default="neural", description="Polly engine: standard or neural")
    
    # Speech-to-Speech Model (Future - lowest latency)
    use_speech_to_speech: bool = Field(default=False, description="Use direct speech-to-speech model")
    speech_model_provider: str = Field(
        default="bedrock",
        description="Speech model provider: bedrock, openai, or custom"
    )
    
    # Fallback: External Speech Services
    deepgram_api_key: str = Field(default="", description="Deepgram API key (fallback STT)")
    elevenlabs_api_key: str = Field(default="", description="ElevenLabs API key (fallback TTS)")
    
    # Supported Languages
    supported_languages: List[str] = Field(
        default=["hi-IN", "mr-IN", "te-IN", "ta-IN", "bn-IN"],
        description="Supported language codes",
    )

    # AWS Configuration
    aws_region: str = Field(default="us-east-1", description="AWS region for services")
    aws_access_key_id: str = Field(default="", description="AWS access key ID (optional if using IAM roles)")
    aws_secret_access_key: str = Field(default="", description="AWS secret access key (optional if using IAM roles)")

    # AWS Bedrock - LLM Services
    use_bedrock: bool = Field(default=True, description="Use AWS Bedrock for LLM services")
    bedrock_main_model: str = Field(
        default="anthropic.claude-3-5-sonnet-20241022-v2:0",
        description="Main LLM model via Bedrock for complex reasoning"
    )
    bedrock_fast_model: str = Field(
        default="anthropic.claude-3-haiku-20240307-v1:0",
        description="Fast LLM model via Bedrock for simple responses"
    )
    bedrock_embedding_model: str = Field(
        default="amazon.titan-embed-text-v2:0",
        description="Embedding model via Bedrock for vector search"
    )
    embedding_dimensions: int = Field(
        default=1024,
        description="Embedding dimensions (1024 for Titan V2, 1536 for OpenAI)"
    )

    # Fallback: External LLM Services (if not using Bedrock)
    openai_api_key: str = Field(default="", description="OpenAI API key (fallback)")
    anthropic_api_key: str = Field(default="", description="Anthropic API key (fallback)")
    groq_api_key: str = Field(default="", description="Groq API key (fallback)")
    main_llm_model: str = Field(
        default="gpt-4-turbo-preview", description="Fallback main LLM model"
    )
    small_llm_model: str = Field(
        default="llama-3.1-8b-instant", description="Fallback small LLM model"
    )
    embedding_model: str = Field(
        default="text-embedding-3-large", description="Fallback embedding model"
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
