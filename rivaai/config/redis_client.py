"""Redis client configuration for session storage and caching."""

import logging
from typing import Any

import redis.asyncio as redis
from redis.asyncio import ConnectionPool

from rivaai.config.settings import Settings

logger = logging.getLogger(__name__)


class RedisClient:
    """Redis client manager for session storage and caching."""

    def __init__(self, settings: Settings) -> None:
        """Initialize Redis client.

        Args:
            settings: Application settings containing Redis configuration
        """
        self.settings = settings
        self._pool: ConnectionPool | None = None
        self._client: redis.Redis | None = None

    async def initialize(self) -> None:
        """Initialize Redis connection pool and client."""
        if self._client is not None:
            logger.warning("Redis client already initialized")
            return

        try:
            # Create connection pool
            self._pool = ConnectionPool.from_url(
                str(self.settings.redis_url),
                max_connections=self.settings.redis_max_connections,
                decode_responses=True,
            )

            # Create Redis client
            self._client = redis.Redis(connection_pool=self._pool)

            # Test connection
            await self._client.ping()
            logger.info("Redis client initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize Redis client: {e}")
            raise

    async def get_client(self) -> redis.Redis:
        """Get Redis client instance.

        Returns:
            Redis client

        Raises:
            RuntimeError: If client is not initialized
        """
        if self._client is None:
            raise RuntimeError("Redis client not initialized")
        return self._client

    async def set(
        self, key: str, value: str, ttl_seconds: int | None = None
    ) -> bool:
        """Set a key-value pair in Redis.

        Args:
            key: Redis key
            value: Value to store
            ttl_seconds: Optional TTL in seconds

        Returns:
            True if successful
        """
        client = await self.get_client()
        if ttl_seconds:
            return await client.setex(key, ttl_seconds, value)
        return await client.set(key, value)

    async def get(self, key: str) -> str | None:
        """Get a value from Redis.

        Args:
            key: Redis key

        Returns:
            Value if exists, None otherwise
        """
        client = await self.get_client()
        return await client.get(key)

    async def delete(self, key: str) -> int:
        """Delete a key from Redis.

        Args:
            key: Redis key

        Returns:
            Number of keys deleted
        """
        client = await self.get_client()
        return await client.delete(key)

    async def exists(self, key: str) -> bool:
        """Check if a key exists in Redis.

        Args:
            key: Redis key

        Returns:
            True if key exists
        """
        client = await self.get_client()
        return await client.exists(key) > 0

    async def expire(self, key: str, ttl_seconds: int) -> bool:
        """Set TTL on an existing key.

        Args:
            key: Redis key
            ttl_seconds: TTL in seconds

        Returns:
            True if successful
        """
        client = await self.get_client()
        return await client.expire(key, ttl_seconds)

    async def hset(self, name: str, mapping: dict[str, Any]) -> int:
        """Set hash fields.

        Args:
            name: Hash name
            mapping: Dictionary of field-value pairs

        Returns:
            Number of fields added
        """
        client = await self.get_client()
        return await client.hset(name, mapping=mapping)

    async def hgetall(self, name: str) -> dict[str, str]:
        """Get all hash fields.

        Args:
            name: Hash name

        Returns:
            Dictionary of field-value pairs
        """
        client = await self.get_client()
        return await client.hgetall(name)

    async def close(self) -> None:
        """Close Redis connection."""
        if self._client is not None:
            await self._client.close()
            self._client = None
            logger.info("Redis client closed")

        if self._pool is not None:
            await self._pool.disconnect()
            self._pool = None


# Global Redis client instance
_redis_client: RedisClient | None = None


async def get_redis_client(settings: Settings | None = None) -> RedisClient:
    """Get or create the global Redis client instance.

    Args:
        settings: Application settings (required on first call)

    Returns:
        RedisClient instance

    Raises:
        RuntimeError: If settings not provided on first call
    """
    global _redis_client

    if _redis_client is None:
        if settings is None:
            raise RuntimeError("Settings required to initialize Redis client")
        _redis_client = RedisClient(settings)
        await _redis_client.initialize()

    return _redis_client


async def close_redis_client() -> None:
    """Close the global Redis client."""
    global _redis_client

    if _redis_client is not None:
        await _redis_client.close()
        _redis_client = None
