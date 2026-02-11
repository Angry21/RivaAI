"""Database connection management with connection pooling for PostgreSQL."""

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import psycopg2
from psycopg2 import pool
from psycopg2.extensions import connection as Connection

from rivaai.config.settings import Settings

logger = logging.getLogger(__name__)


class DatabasePool:
    """PostgreSQL connection pool manager with pgvector support."""

    def __init__(self, settings: Settings) -> None:
        """Initialize database connection pool.

        Args:
            settings: Application settings containing database configuration
        """
        self.settings = settings
        self._pool: pool.ThreadedConnectionPool | None = None

    def initialize(self) -> None:
        """Initialize the connection pool."""
        if self._pool is not None:
            logger.warning("Database pool already initialized")
            return

        try:
            # Extract connection parameters from URL
            db_url = str(self.settings.database_url)

            # Create connection pool
            self._pool = pool.ThreadedConnectionPool(
                minconn=1,
                maxconn=self.settings.database_pool_size + self.settings.database_max_overflow,
                dsn=db_url,
            )

            logger.info(
                f"Database pool initialized with size {self.settings.database_pool_size}"
            )

            # Enable pgvector extension on first connection
            self._enable_pgvector()

        except Exception as e:
            logger.error(f"Failed to initialize database pool: {e}")
            raise

    def _enable_pgvector(self) -> None:
        """Enable pgvector extension in the database."""
        try:
            conn = self.get_connection()
            try:
                with conn.cursor() as cursor:
                    cursor.execute("CREATE EXTENSION IF NOT EXISTS vector;")
                    conn.commit()
                    logger.info("pgvector extension enabled")
            finally:
                self.release_connection(conn)
        except Exception as e:
            logger.error(f"Failed to enable pgvector extension: {e}")
            raise

    def get_connection(self) -> Connection:
        """Get a connection from the pool.

        Returns:
            Database connection

        Raises:
            RuntimeError: If pool is not initialized
            psycopg2.Error: If connection cannot be obtained
        """
        if self._pool is None:
            raise RuntimeError("Database pool not initialized")

        try:
            conn = self._pool.getconn()
            return conn
        except Exception as e:
            logger.error(f"Failed to get connection from pool: {e}")
            raise

    def release_connection(self, conn: Connection) -> None:
        """Release a connection back to the pool.

        Args:
            conn: Database connection to release
        """
        if self._pool is None:
            logger.warning("Attempting to release connection but pool not initialized")
            return

        try:
            self._pool.putconn(conn)
        except Exception as e:
            logger.error(f"Failed to release connection to pool: {e}")

    @asynccontextmanager
    async def connection(self) -> AsyncGenerator[Connection, None]:
        """Context manager for database connections.

        Yields:
            Database connection

        Example:
            async with db_pool.connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("SELECT * FROM table")
        """
        conn = self.get_connection()
        try:
            yield conn
        finally:
            self.release_connection(conn)

    def close(self) -> None:
        """Close all connections in the pool."""
        if self._pool is not None:
            self._pool.closeall()
            self._pool = None
            logger.info("Database pool closed")

    def get_pool_status(self) -> dict[str, int]:
        """Get current pool status.

        Returns:
            Dictionary with pool statistics
        """
        if self._pool is None:
            return {"status": "not_initialized"}

        # Note: ThreadedConnectionPool doesn't expose detailed stats
        # This is a simplified status
        return {
            "min_connections": self._pool.minconn,
            "max_connections": self._pool.maxconn,
            "status": "active",
        }


# Global database pool instance
_db_pool: DatabasePool | None = None


def get_database_pool(settings: Settings | None = None) -> DatabasePool:
    """Get or create the global database pool instance.

    Args:
        settings: Application settings (required on first call)

    Returns:
        DatabasePool instance

    Raises:
        RuntimeError: If settings not provided on first call
    """
    global _db_pool

    if _db_pool is None:
        if settings is None:
            raise RuntimeError("Settings required to initialize database pool")
        _db_pool = DatabasePool(settings)
        _db_pool.initialize()

    return _db_pool


def close_database_pool() -> None:
    """Close the global database pool."""
    global _db_pool

    if _db_pool is not None:
        _db_pool.close()
        _db_pool = None
