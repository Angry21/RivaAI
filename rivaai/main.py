"""Main FastAPI application entry point."""

import logging
import sys
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from rivaai.config import get_settings
from rivaai.config.database import close_database_pool, get_database_pool
from rivaai.config.redis_client import close_redis_client, get_redis_client

# Try to import uvloop for Linux/Mac (not available on Windows)
try:
    import uvloop
    uvloop.install()
    logger = logging.getLogger(__name__)
    logger.info("uvloop installed successfully")
except ImportError:
    logger = logging.getLogger(__name__)
    logger.info("uvloop not available (Windows environment) - using default asyncio event loop")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager for startup and shutdown events.

    Args:
        app: FastAPI application instance

    Yields:
        None
    """
    # Startup
    settings = get_settings()
    logger.info(f"Starting {settings.app_name} v{settings.app_version}")
    logger.info(f"Environment: {settings.environment}")

    # Initialize database pool
    try:
        db_pool = get_database_pool(settings)
        logger.info("Database pool initialized")
    except Exception as e:
        logger.error(f"Failed to initialize database pool: {e}")
        raise

    # Initialize Redis client
    try:
        redis_client = await get_redis_client(settings)
        logger.info("Redis client initialized")
    except Exception as e:
        logger.error(f"Failed to initialize Redis client: {e}")
        raise

    logger.info("Application startup complete")

    yield

    # Shutdown
    logger.info("Shutting down application")

    # Close Redis client
    await close_redis_client()
    logger.info("Redis client closed")

    # Close database pool
    close_database_pool()
    logger.info("Database pool closed")

    logger.info("Application shutdown complete")


# Create FastAPI application
app = FastAPI(
    title="RivaAI",
    description="Cognitive Voice Interface for Decision Intelligence",
    version="0.1.0",
    lifespan=lifespan,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root() -> dict[str, str]:
    """Root endpoint for health check.

    Returns:
        Status message
    """
    settings = get_settings()
    return {
        "status": "ok",
        "service": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment,
    }


@app.get("/health")
async def health() -> dict[str, str]:
    """Health check endpoint.

    Returns:
        Health status
    """
    return {"status": "healthy"}


@app.get("/ready")
async def ready() -> dict[str, str]:
    """Readiness check endpoint.

    Returns:
        Readiness status
    """
    # TODO: Add checks for database and Redis connectivity
    return {"status": "ready"}


if __name__ == "__main__":
    import uvicorn

    settings = get_settings()
    uvicorn.run(
        "rivaai.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level=settings.log_level.lower(),
    )
