"""Tests for Redis client."""

import pytest

from rivaai.config import Settings
from rivaai.config.redis_client import RedisClient


@pytest.mark.skip(reason="Requires Redis server to be running")
@pytest.mark.asyncio
async def test_redis_client_initialization(test_settings: Settings) -> None:
    """Test Redis client initialization."""
    client = RedisClient(test_settings)
    await client.initialize()

    redis_instance = await client.get_client()
    assert redis_instance is not None

    # Test ping
    result = await redis_instance.ping()
    assert result is True

    await client.close()


@pytest.mark.skip(reason="Requires Redis server to be running")
@pytest.mark.asyncio
async def test_redis_set_get(test_settings: Settings) -> None:
    """Test Redis set and get operations."""
    client = RedisClient(test_settings)
    await client.initialize()

    # Set value
    await client.set("test_key", "test_value")

    # Get value
    value = await client.get("test_key")
    assert value == "test_value"

    # Cleanup
    await client.delete("test_key")
    await client.close()


@pytest.mark.skip(reason="Requires Redis server to be running")
@pytest.mark.asyncio
async def test_redis_set_with_ttl(test_settings: Settings) -> None:
    """Test Redis set with TTL."""
    client = RedisClient(test_settings)
    await client.initialize()

    # Set value with TTL
    await client.set("test_key_ttl", "test_value", ttl_seconds=10)

    # Check value exists
    exists = await client.exists("test_key_ttl")
    assert exists is True

    # Get value
    value = await client.get("test_key_ttl")
    assert value == "test_value"

    # Cleanup
    await client.delete("test_key_ttl")
    await client.close()


@pytest.mark.skip(reason="Requires Redis server to be running")
@pytest.mark.asyncio
async def test_redis_delete(test_settings: Settings) -> None:
    """Test Redis delete operation."""
    client = RedisClient(test_settings)
    await client.initialize()

    # Set value
    await client.set("test_key_delete", "test_value")

    # Delete value
    deleted = await client.delete("test_key_delete")
    assert deleted == 1

    # Check value doesn't exist
    exists = await client.exists("test_key_delete")
    assert exists is False

    await client.close()


@pytest.mark.skip(reason="Requires Redis server to be running")
@pytest.mark.asyncio
async def test_redis_hash_operations(test_settings: Settings) -> None:
    """Test Redis hash operations."""
    client = RedisClient(test_settings)
    await client.initialize()

    # Set hash
    await client.hset("test_hash", {"field1": "value1", "field2": "value2"})

    # Get hash
    hash_data = await client.hgetall("test_hash")
    assert hash_data == {"field1": "value1", "field2": "value2"}

    # Cleanup
    await client.delete("test_hash")
    await client.close()


@pytest.mark.asyncio
async def test_redis_not_initialized_error() -> None:
    """Test that accessing client before initialization raises error."""
    client = RedisClient(Settings())

    with pytest.raises(RuntimeError, match="Redis client not initialized"):
        await client.get_client()
