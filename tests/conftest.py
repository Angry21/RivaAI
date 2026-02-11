"""Pytest configuration and shared fixtures."""

import asyncio
from typing import AsyncGenerator, Generator

import pytest
from hypothesis import settings as hypothesis_settings

from rivaai.config import Settings

# Configure Hypothesis for property-based testing
# Minimum 100 iterations per property test as per design document
hypothesis_settings.register_profile(
    "rivaai",
    max_examples=100,
    deadline=None,  # Disable deadline for async tests
    print_blob=True,
)
hypothesis_settings.load_profile("rivaai")


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create event loop for async tests.

    Yields:
        Event loop instance
    """
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def test_settings() -> Settings:
    """Create test settings with safe defaults.

    Returns:
        Settings instance for testing
    """
    return Settings(
        environment="testing",
        debug=True,
        database_url="postgresql://postgres:postgres@localhost:5432/rivaai_test",
        redis_url="redis://localhost:6379/1",
        twilio_account_sid="test_account_sid",
        twilio_auth_token="test_auth_token",
        twilio_phone_number="+15555555555",
        deepgram_api_key="test_deepgram_key",
        elevenlabs_api_key="test_elevenlabs_key",
        openai_api_key="test_openai_key",
        anthropic_api_key="test_anthropic_key",
        groq_api_key="test_groq_key",
    )


@pytest.fixture
async def redis_client(test_settings: Settings) -> AsyncGenerator:
    """Create Redis client for testing.

    Args:
        test_settings: Test settings fixture

    Yields:
        Redis client instance
    """
    from rivaai.config.redis_client import RedisClient

    client = RedisClient(test_settings)
    await client.initialize()

    yield client

    # Cleanup
    await client.close()


@pytest.fixture
def db_pool(test_settings: Settings) -> Generator:
    """Create database pool for testing.

    Args:
        test_settings: Test settings fixture

    Yields:
        Database pool instance
    """
    from rivaai.config.database import DatabasePool

    pool = DatabasePool(test_settings)
    pool.initialize()

    yield pool

    # Cleanup
    pool.close()
