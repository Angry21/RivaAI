"""Tests for database connection pooling."""

import pytest

from rivaai.config import Settings
from rivaai.config.database import DatabasePool


@pytest.mark.skip(reason="Requires PostgreSQL database to be running")
def test_database_pool_initialization(test_settings: Settings) -> None:
    """Test database pool initialization."""
    pool = DatabasePool(test_settings)
    pool.initialize()

    assert pool._pool is not None

    # Check pool status
    status = pool.get_pool_status()
    assert status["status"] == "active"
    assert status["min_connections"] == 1
    assert status["max_connections"] == test_settings.database_pool_size + test_settings.database_max_overflow

    pool.close()


@pytest.mark.skip(reason="Requires PostgreSQL database to be running")
def test_database_connection_lifecycle(test_settings: Settings) -> None:
    """Test getting and releasing database connections."""
    pool = DatabasePool(test_settings)
    pool.initialize()

    # Get connection
    conn = pool.get_connection()
    assert conn is not None

    # Test connection with simple query
    with conn.cursor() as cursor:
        cursor.execute("SELECT 1")
        result = cursor.fetchone()
        assert result == (1,)

    # Release connection
    pool.release_connection(conn)

    pool.close()


@pytest.mark.skip(reason="Requires PostgreSQL database to be running")
def test_pgvector_extension_enabled(test_settings: Settings) -> None:
    """Test that pgvector extension is enabled."""
    pool = DatabasePool(test_settings)
    pool.initialize()

    conn = pool.get_connection()
    try:
        with conn.cursor() as cursor:
            # Check if pgvector extension exists
            cursor.execute(
                "SELECT EXISTS(SELECT 1 FROM pg_extension WHERE extname = 'vector')"
            )
            result = cursor.fetchone()
            assert result[0] is True
    finally:
        pool.release_connection(conn)
        pool.close()


@pytest.mark.skip(reason="Requires PostgreSQL database to be running")
def test_multiple_connections(test_settings: Settings) -> None:
    """Test getting multiple connections from pool."""
    pool = DatabasePool(test_settings)
    pool.initialize()

    connections = []
    try:
        # Get multiple connections
        for _ in range(5):
            conn = pool.get_connection()
            connections.append(conn)

        assert len(connections) == 5

    finally:
        # Release all connections
        for conn in connections:
            pool.release_connection(conn)
        pool.close()


def test_pool_not_initialized_error() -> None:
    """Test that accessing pool before initialization raises error."""
    pool = DatabasePool(Settings())

    with pytest.raises(RuntimeError, match="Database pool not initialized"):
        pool.get_connection()
