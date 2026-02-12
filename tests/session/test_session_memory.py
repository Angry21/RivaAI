"""Unit tests for Session Memory."""

import hashlib
import json
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from rivaai.config.redis_client import RedisClient
from rivaai.config.settings import Settings
from rivaai.session.memory import SessionMemory
from rivaai.session.models import Entity, SessionContext, Speaker, Turn


@pytest.fixture
def mock_redis_client():
    """Create a mock Redis client."""
    client = AsyncMock(spec=RedisClient)
    client.settings = MagicMock()
    return client


@pytest.fixture
def settings():
    """Create test settings."""
    return Settings(session_ttl_hours=24)


@pytest.fixture
def session_memory(mock_redis_client, settings):
    """Create SessionMemory instance with mock Redis client."""
    return SessionMemory(mock_redis_client, settings)


class TestSessionMemory:
    """Test suite for SessionMemory class."""

    def test_hash_ani(self, session_memory):
        """Test ANI hashing using SHA-256."""
        ani = "+919876543210"
        expected_hash = hashlib.sha256(ani.encode()).hexdigest()

        result = session_memory._hash_ani(ani)

        assert result == expected_hash
        assert len(result) == 64  # SHA-256 produces 64 hex characters

    def test_hash_ani_consistency(self, session_memory):
        """Test that hashing the same ANI produces the same hash."""
        ani = "+919876543210"

        hash1 = session_memory._hash_ani(ani)
        hash2 = session_memory._hash_ani(ani)

        assert hash1 == hash2

    def test_hash_ani_different_inputs(self, session_memory):
        """Test that different ANIs produce different hashes."""
        ani1 = "+919876543210"
        ani2 = "+919876543211"

        hash1 = session_memory._hash_ani(ani1)
        hash2 = session_memory._hash_ani(ani2)

        assert hash1 != hash2

    def test_generate_session_id(self, session_memory):
        """Test session ID generation."""
        session_id = session_memory._generate_session_id()

        assert isinstance(session_id, str)
        assert len(session_id) > 0
        # UUID format check (basic)
        assert "-" in session_id

    def test_generate_unique_session_ids(self, session_memory):
        """Test that generated session IDs are unique."""
        id1 = session_memory._generate_session_id()
        id2 = session_memory._generate_session_id()

        assert id1 != id2

    def test_get_session_key(self, session_memory):
        """Test session key generation."""
        session_id = "test-session-123"
        expected_key = "session:test-session-123"

        result = session_memory._get_session_key(session_id)

        assert result == expected_key

    def test_get_ani_session_key(self, session_memory):
        """Test ANI session key generation."""
        ani_hash = "abc123"
        expected_key = "ani_session:abc123"

        result = session_memory._get_ani_session_key(ani_hash)

        assert result == expected_key

    @pytest.mark.asyncio
    async def test_create_session(self, session_memory, mock_redis_client):
        """Test creating a new session."""
        caller_ani = "+919876543210"
        domain = "farming"
        language_code = "hi-IN"

        mock_redis_client.set = AsyncMock(return_value=True)

        session_context = await session_memory.create_session(
            caller_ani, domain, language_code
        )

        # Verify session context
        assert session_context.session_id is not None
        assert session_context.caller_ani_hash == hashlib.sha256(
            caller_ani.encode()
        ).hexdigest()
        assert session_context.domain == domain
        assert session_context.language_code == language_code
        assert len(session_context.conversation_history) == 0
        assert len(session_context.extracted_entities) == 0
        assert isinstance(session_context.created_at, datetime)
        assert isinstance(session_context.last_updated, datetime)

        # Verify Redis calls
        assert mock_redis_client.set.call_count == 2  # Session data + ANI mapping

    @pytest.mark.asyncio
    async def test_create_session_with_ttl(self, session_memory, mock_redis_client):
        """Test that created sessions have 24-hour TTL."""
        caller_ani = "+919876543210"
        mock_redis_client.set = AsyncMock(return_value=True)

        await session_memory.create_session(caller_ani)

        # Verify TTL is set correctly (24 hours = 86400 seconds)
        expected_ttl = 24 * 3600
        calls = mock_redis_client.set.call_args_list

        for call in calls:
            assert call.kwargs.get("ttl_seconds") == expected_ttl

    @pytest.mark.asyncio
    async def test_get_session_exists(self, session_memory, mock_redis_client):
        """Test retrieving an existing session."""
        session_id = "test-session-123"
        session_data = {
            "session_id": session_id,
            "caller_ani_hash": "abc123",
            "conversation_history": [],
            "extracted_entities": [],
            "domain": "farming",
            "language_code": "hi-IN",
            "created_at": datetime.utcnow().isoformat(),
            "last_updated": datetime.utcnow().isoformat(),
            "metadata": {},
        }

        mock_redis_client.get = AsyncMock(return_value=json.dumps(session_data))

        result = await session_memory.get_session(session_id)

        assert result is not None
        assert result.session_id == session_id
        assert result.caller_ani_hash == "abc123"
        assert result.domain == "farming"

    @pytest.mark.asyncio
    async def test_get_session_not_exists(self, session_memory, mock_redis_client):
        """Test retrieving a non-existent session."""
        session_id = "non-existent-session"
        mock_redis_client.get = AsyncMock(return_value=None)

        result = await session_memory.get_session(session_id)

        assert result is None

    @pytest.mark.asyncio
    async def test_resume_session_exists(self, session_memory, mock_redis_client):
        """Test resuming an existing session."""
        caller_ani = "+919876543210"
        caller_ani_hash = hashlib.sha256(caller_ani.encode()).hexdigest()
        session_id = "test-session-123"

        session_data = {
            "session_id": session_id,
            "caller_ani_hash": caller_ani_hash,
            "conversation_history": [],
            "extracted_entities": [],
            "domain": "farming",
            "language_code": "hi-IN",
            "created_at": datetime.utcnow().isoformat(),
            "last_updated": datetime.utcnow().isoformat(),
            "metadata": {},
        }

        # Mock Redis to return session ID from ANI mapping, then session data
        mock_redis_client.get = AsyncMock(
            side_effect=[session_id, json.dumps(session_data)]
        )

        result = await session_memory.resume_session(caller_ani)

        assert result is not None
        assert result.session_id == session_id
        assert result.caller_ani_hash == caller_ani_hash

    @pytest.mark.asyncio
    async def test_resume_session_not_exists(self, session_memory, mock_redis_client):
        """Test resuming when no session exists."""
        caller_ani = "+919876543210"
        mock_redis_client.get = AsyncMock(return_value=None)

        result = await session_memory.resume_session(caller_ani)

        assert result is None

    @pytest.mark.asyncio
    async def test_update_session(self, session_memory, mock_redis_client):
        """Test updating a session."""
        session_context = SessionContext(
            session_id="test-session-123",
            caller_ani_hash="abc123",
            conversation_history=[],
            extracted_entities=[],
            domain="farming",
            language_code="hi-IN",
            created_at=datetime.utcnow(),
            last_updated=datetime.utcnow(),
        )

        mock_redis_client.set = AsyncMock(return_value=True)
        original_updated = session_context.last_updated

        await session_memory.update_session(session_context)

        # Verify last_updated was changed (or at least not earlier)
        assert session_context.last_updated >= original_updated
        # Verify Redis set was called
        mock_redis_client.set.assert_called_once()

    @pytest.mark.asyncio
    async def test_add_turn(self, session_memory, mock_redis_client):
        """Test adding a conversation turn."""
        session_id = "test-session-123"
        session_data = {
            "session_id": session_id,
            "caller_ani_hash": "abc123",
            "conversation_history": [],
            "extracted_entities": [],
            "domain": "farming",
            "language_code": "hi-IN",
            "created_at": datetime.utcnow().isoformat(),
            "last_updated": datetime.utcnow().isoformat(),
            "metadata": {},
        }

        mock_redis_client.get = AsyncMock(return_value=json.dumps(session_data))
        mock_redis_client.set = AsyncMock(return_value=True)

        entities = [
            Entity(
                entity_type="crop",
                value="wheat",
                confidence=0.9,
                requires_semantic_validation=True,
            )
        ]

        await session_memory.add_turn(
            session_id, Speaker.USER, "I want to grow wheat", entities
        )

        # Verify Redis set was called to update session
        mock_redis_client.set.assert_called_once()

    @pytest.mark.asyncio
    async def test_add_turn_with_entities(self, session_memory, mock_redis_client):
        """Test that entities are added to session-level extracted entities."""
        session_id = "test-session-123"
        session_context = SessionContext(
            session_id=session_id,
            caller_ani_hash="abc123",
            conversation_history=[],
            extracted_entities=[],
            domain="farming",
            language_code="hi-IN",
            created_at=datetime.utcnow(),
            last_updated=datetime.utcnow(),
        )

        mock_redis_client.get = AsyncMock(
            return_value=json.dumps(session_context.to_dict())
        )
        mock_redis_client.set = AsyncMock(return_value=True)

        entities = [
            Entity(
                entity_type="crop",
                value="wheat",
                confidence=0.9,
                requires_semantic_validation=True,
            )
        ]

        await session_memory.add_turn(
            session_id, Speaker.USER, "I want to grow wheat", entities
        )

        # Get the updated session from the set call
        call_args = mock_redis_client.set.call_args
        stored_data = json.loads(call_args[0][1])

        assert len(stored_data["conversation_history"]) == 1
        assert len(stored_data["extracted_entities"]) == 1
        assert stored_data["extracted_entities"][0]["value"] == "wheat"

    @pytest.mark.asyncio
    async def test_delete_session(self, session_memory, mock_redis_client):
        """Test deleting a session."""
        session_id = "test-session-123"
        caller_ani_hash = "abc123"

        session_data = {
            "session_id": session_id,
            "caller_ani_hash": caller_ani_hash,
            "conversation_history": [],
            "extracted_entities": [],
            "domain": "farming",
            "language_code": "hi-IN",
            "created_at": datetime.utcnow().isoformat(),
            "last_updated": datetime.utcnow().isoformat(),
            "metadata": {},
        }

        mock_redis_client.get = AsyncMock(return_value=json.dumps(session_data))
        mock_redis_client.delete = AsyncMock(return_value=1)

        await session_memory.delete_session(session_id)

        # Verify both session and ANI mapping were deleted
        assert mock_redis_client.delete.call_count == 2

    @pytest.mark.asyncio
    async def test_session_exists_true(self, session_memory, mock_redis_client):
        """Test checking if a session exists (true case)."""
        session_id = "test-session-123"
        mock_redis_client.exists = AsyncMock(return_value=True)

        result = await session_memory.session_exists(session_id)

        assert result is True

    @pytest.mark.asyncio
    async def test_session_exists_false(self, session_memory, mock_redis_client):
        """Test checking if a session exists (false case)."""
        session_id = "non-existent-session"
        mock_redis_client.exists = AsyncMock(return_value=False)

        result = await session_memory.session_exists(session_id)

        assert result is False

    @pytest.mark.asyncio
    async def test_extend_session_ttl(self, session_memory, mock_redis_client):
        """Test extending session TTL."""
        session_id = "test-session-123"
        caller_ani_hash = "abc123"

        session_data = {
            "session_id": session_id,
            "caller_ani_hash": caller_ani_hash,
            "conversation_history": [],
            "extracted_entities": [],
            "domain": "farming",
            "language_code": "hi-IN",
            "created_at": datetime.utcnow().isoformat(),
            "last_updated": datetime.utcnow().isoformat(),
            "metadata": {},
        }

        mock_redis_client.get = AsyncMock(return_value=json.dumps(session_data))
        mock_redis_client.expire = AsyncMock(return_value=True)

        result = await session_memory.extend_session_ttl(session_id)

        assert result is True
        # Verify expire was called for both session and ANI mapping
        assert mock_redis_client.expire.call_count == 2


class TestSessionContext:
    """Test suite for SessionContext model."""

    def test_to_dict(self):
        """Test converting SessionContext to dictionary."""
        now = datetime.utcnow()
        entity = Entity(
            entity_type="crop",
            value="wheat",
            confidence=0.9,
            requires_semantic_validation=True,
        )
        turn = Turn(speaker=Speaker.USER, text="Hello", timestamp=now, entities=[entity])

        session_context = SessionContext(
            session_id="test-123",
            caller_ani_hash="abc123",
            conversation_history=[turn],
            extracted_entities=[entity],
            domain="farming",
            language_code="hi-IN",
            created_at=now,
            last_updated=now,
        )

        result = session_context.to_dict()

        assert result["session_id"] == "test-123"
        assert result["caller_ani_hash"] == "abc123"
        assert len(result["conversation_history"]) == 1
        assert len(result["extracted_entities"]) == 1
        assert result["domain"] == "farming"
        assert result["language_code"] == "hi-IN"

    def test_from_dict(self):
        """Test creating SessionContext from dictionary."""
        now = datetime.utcnow()
        data = {
            "session_id": "test-123",
            "caller_ani_hash": "abc123",
            "conversation_history": [
                {
                    "speaker": "user",
                    "text": "Hello",
                    "timestamp": now.isoformat(),
                    "entities": [
                        {
                            "entity_type": "crop",
                            "value": "wheat",
                            "confidence": 0.9,
                            "requires_semantic_validation": True,
                            "metadata": {},
                        }
                    ],
                    "metadata": {},
                }
            ],
            "extracted_entities": [
                {
                    "entity_type": "crop",
                    "value": "wheat",
                    "confidence": 0.9,
                    "requires_semantic_validation": True,
                    "metadata": {},
                }
            ],
            "domain": "farming",
            "language_code": "hi-IN",
            "created_at": now.isoformat(),
            "last_updated": now.isoformat(),
            "metadata": {},
        }

        result = SessionContext.from_dict(data)

        assert result.session_id == "test-123"
        assert result.caller_ani_hash == "abc123"
        assert len(result.conversation_history) == 1
        assert len(result.extracted_entities) == 1
        assert result.domain == "farming"
        assert result.language_code == "hi-IN"

    def test_round_trip_serialization(self):
        """Test that to_dict and from_dict are inverse operations."""
        now = datetime.utcnow()
        entity = Entity(
            entity_type="crop",
            value="wheat",
            confidence=0.9,
            requires_semantic_validation=True,
        )
        turn = Turn(speaker=Speaker.USER, text="Hello", timestamp=now, entities=[entity])

        original = SessionContext(
            session_id="test-123",
            caller_ani_hash="abc123",
            conversation_history=[turn],
            extracted_entities=[entity],
            domain="farming",
            language_code="hi-IN",
            created_at=now,
            last_updated=now,
        )

        # Convert to dict and back
        data = original.to_dict()
        restored = SessionContext.from_dict(data)

        assert restored.session_id == original.session_id
        assert restored.caller_ani_hash == original.caller_ani_hash
        assert len(restored.conversation_history) == len(original.conversation_history)
        assert len(restored.extracted_entities) == len(original.extracted_entities)
        assert restored.domain == original.domain
        assert restored.language_code == original.language_code
