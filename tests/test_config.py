"""Tests for configuration management."""

import pytest
from hypothesis import given
from hypothesis import strategies as st

from rivaai.config import Settings, get_settings


def test_settings_defaults() -> None:
    """Test that settings have sensible defaults."""
    settings = Settings()

    assert settings.app_name == "RivaAI"
    assert settings.app_version == "0.1.0"
    assert settings.environment in ["development", "staging", "production"]
    assert settings.host == "0.0.0.0"
    assert settings.port == 8000


def test_settings_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that settings can be loaded from environment variables."""
    monkeypatch.setenv("APP_NAME", "TestApp")
    monkeypatch.setenv("PORT", "9000")
    monkeypatch.setenv("DEBUG", "true")

    settings = Settings()

    assert settings.app_name == "TestApp"
    assert settings.port == 9000
    assert settings.debug is True


def test_get_settings_cached() -> None:
    """Test that get_settings returns cached instance."""
    settings1 = get_settings()
    settings2 = get_settings()

    assert settings1 is settings2


def test_latency_budgets(test_settings: Settings) -> None:
    """Test that latency budgets are properly configured."""
    assert test_settings.call_establishment_latency_ms == 3000
    assert test_settings.stt_partial_latency_ms == 500
    assert test_settings.barge_in_latency_ms == 300
    assert test_settings.tts_first_chunk_latency_ms == 800
    assert test_settings.simple_intent_latency_ms == 500
    assert test_settings.clarification_latency_ms == 1200
    assert test_settings.complex_decision_latency_ms == 3000


def test_confidence_thresholds(test_settings: Settings) -> None:
    """Test that confidence thresholds are properly configured."""
    assert test_settings.stt_confidence_threshold == 0.6
    assert test_settings.decision_confidence_threshold == 0.8
    assert test_settings.retrieval_relevance_threshold == 0.7


def test_supported_languages(test_settings: Settings) -> None:
    """Test that all required languages are supported."""
    expected_languages = ["hi-IN", "mr-IN", "te-IN", "ta-IN", "bn-IN"]
    assert test_settings.supported_languages == expected_languages


@given(
    port=st.integers(min_value=1024, max_value=65535),
    workers=st.integers(min_value=1, max_value=16),
)
def test_settings_validation(port: int, workers: int) -> None:
    """
    Feature: sochq, Property: Settings Validation
    Test that settings accept valid port and worker configurations.
    """
    settings = Settings(port=port, workers=workers)

    assert settings.port == port
    assert settings.workers == workers


@given(
    confidence=st.floats(min_value=0.0, max_value=1.0),
)
def test_confidence_threshold_range(confidence: float) -> None:
    """
    Feature: sochq, Property: Confidence Threshold Range
    Test that confidence thresholds accept valid float values between 0 and 1.
    """
    settings = Settings(
        stt_confidence_threshold=confidence,
        decision_confidence_threshold=confidence,
        retrieval_relevance_threshold=confidence,
    )

    assert 0.0 <= settings.stt_confidence_threshold <= 1.0
    assert 0.0 <= settings.decision_confidence_threshold <= 1.0
    assert 0.0 <= settings.retrieval_relevance_threshold <= 1.0


def test_database_pool_configuration(test_settings: Settings) -> None:
    """Test database pool configuration."""
    assert test_settings.database_pool_size == 20
    assert test_settings.database_max_overflow == 10
    assert test_settings.database_pool_timeout == 30
    assert test_settings.database_pool_recycle == 3600


def test_redis_configuration(test_settings: Settings) -> None:
    """Test Redis configuration."""
    assert test_settings.redis_max_connections == 50
    assert test_settings.session_ttl_hours == 24


def test_retrieval_configuration(test_settings: Settings) -> None:
    """Test retrieval configuration."""
    assert test_settings.retrieval_top_k == 5
    assert test_settings.graph_traversal_depth == 2
    assert test_settings.hybrid_vector_weight == 0.6
    assert test_settings.hybrid_graph_weight == 0.4
    # Weights should sum to 1.0
    assert (
        test_settings.hybrid_vector_weight + test_settings.hybrid_graph_weight == 1.0
    )


def test_response_generation_configuration(test_settings: Settings) -> None:
    """Test response generation configuration."""
    assert test_settings.max_response_tokens == 40
    assert test_settings.max_sentence_words == 15
