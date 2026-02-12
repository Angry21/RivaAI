"""Integration tests for Session Memory with real Redis."""

import asyncio
from datetime import datetime

import pytest

from rivaai.config.redis_client import RedisClient, get_redis_client
from rivaai.config.settings import Settings
from rivaai.session.memory import SessionMemory
from rivaai.session.models import Entity, Speaker


@pytest.fixture
async def redis_client():
    """Create a real Redis client for integration testing."""
    settings = Settings()
    client = RedisClient(settings)
    await client.initialize()
    yield client
    await client.close()


@pytest.fixture
async def session_memory(redis_client):
    """Create SessionMemory with real Redis client."""
    settings = Settings()
    return SessionMemory(redis_client, settings)


@pytest.mark.asyncio
@pytest.mark.integration
async def test_create_and_retrieve_session(session_memory):
    """Test creating and retrieving a session with real Redis."""
    caller_ani = "+919876543210"
    domain = "farming"
    language_code = "hi-IN"

    # Create session
    session_context = await session_memory.create_session(
        caller_ani, domain, language_code
    )

    assert session_context.session_id is not None
    assert session_context.domain == domain
    assert session_context.language_code == language_code

    # Retrieve session
    retrieved = await session_memory.get_session(session_context.session_id)

    assert retrieved is not None
    assert retrieved.session_id == session_context.session_id
    assert retrieved.caller_ani_hash == session_context.caller_ani_hash
    assert retrieved.domain == domain

    # Cleanup
    await session_memory.delete_session(session_context.session_id)


@pytest.mark.asyncio
@pytest.mark.integration
async def test_resume_session_flow(session_memory):
    """Test the complete session resumption flow."""
    caller_ani = "+919876543210"

    # Create initial session
    session1 = await session_memory.create_session(caller_ani, "farming", "hi-IN")

    # Add some conversation history
    await session_memory.add_turn(
        session1.session_id, Speaker.USER, "I want to grow wheat"
    )
    await session_memory.add_turn(
        session1.session_id, Speaker.SYSTEM, "What is your soil type?"
    )

    # Resume session (simulating user calling back)
    resumed = await session_memory.resume_session(caller_ani)

    assert resumed is not None
    assert resumed.session_id == session1.session_id
    assert len(resumed.conversation_history) == 2
    assert resumed.conversation_history[0].text == "I want to grow wheat"
    assert resumed.conversation_history[1].text == "What is your soil type?"

    # Cleanup
    await session_memory.delete_session(session1.session_id)


@pytest.mark.asyncio
@pytest.mark.integration
async def test_session_with_entities(session_memory):
    """Test session with entity extraction and storage."""
    caller_ani = "+919876543210"

    # Create session
    session = await session_memory.create_session(caller_ani, "farming", "hi-IN")

    # Add turn with entities
    entities = [
        Entity(
            entity_type="crop",
            value="wheat",
            confidence=0.9,
            requires_semantic_validation=True,
        ),
        Entity(
            entity_type="amount", value="50kg", confidence=0.85, requires_semantic_validation=False
        ),
    ]

    await session_memory.add_turn(
        session.session_id, Speaker.USER, "I need 50kg of wheat seeds", entities
    )

    # Retrieve and verify
    retrieved = await session_memory.get_session(session.session_id)

    assert retrieved is not None
    assert len(retrieved.conversation_history) == 1
    assert len(retrieved.extracted_entities) == 2
    assert retrieved.extracted_entities[0].value == "wheat"
    assert retrieved.extracted_entities[1].value == "50kg"

    # Cleanup
    await session_memory.delete_session(session.session_id)


@pytest.mark.asyncio
@pytest.mark.integration
async def test_session_ttl_extension(session_memory):
    """Test extending session TTL."""
    caller_ani = "+919876543210"

    # Create session
    session = await session_memory.create_session(caller_ani, "farming", "hi-IN")

    # Verify session exists
    exists = await session_memory.session_exists(session.session_id)
    assert exists is True

    # Extend TTL
    success = await session_memory.extend_session_ttl(session.session_id)
    assert success is True

    # Verify still exists
    exists = await session_memory.session_exists(session.session_id)
    assert exists is True

    # Cleanup
    await session_memory.delete_session(session.session_id)


@pytest.mark.asyncio
@pytest.mark.integration
async def test_multiple_sessions_different_anis(session_memory):
    """Test handling multiple sessions from different callers."""
    ani1 = "+919876543210"
    ani2 = "+919876543211"

    # Create two sessions
    session1 = await session_memory.create_session(ani1, "farming", "hi-IN")
    session2 = await session_memory.create_session(ani2, "education", "mr-IN")

    # Verify they are different
    assert session1.session_id != session2.session_id
    assert session1.caller_ani_hash != session2.caller_ani_hash
    assert session1.domain != session2.domain

    # Resume each session
    resumed1 = await session_memory.resume_session(ani1)
    resumed2 = await session_memory.resume_session(ani2)

    assert resumed1.session_id == session1.session_id
    assert resumed2.session_id == session2.session_id

    # Cleanup
    await session_memory.delete_session(session1.session_id)
    await session_memory.delete_session(session2.session_id)


@pytest.mark.asyncio
@pytest.mark.integration
async def test_delete_session_removes_ani_mapping(session_memory):
    """Test that deleting a session also removes ANI mapping."""
    caller_ani = "+919876543210"

    # Create session
    session = await session_memory.create_session(caller_ani, "farming", "hi-IN")

    # Verify can resume
    resumed = await session_memory.resume_session(caller_ani)
    assert resumed is not None

    # Delete session
    await session_memory.delete_session(session.session_id)

    # Verify cannot resume
    resumed = await session_memory.resume_session(caller_ani)
    assert resumed is None

    # Verify session doesn't exist
    exists = await session_memory.session_exists(session.session_id)
    assert exists is False
