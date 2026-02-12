"""Session memory management with Redis backend."""

import hashlib
import json
import logging
import uuid
from datetime import datetime
from typing import List, Optional

from rivaai.config.redis_client import RedisClient
from rivaai.config.settings import Settings
from rivaai.session.models import Entity, SessionContext, Speaker, Turn
from rivaai.session.pii_masker import PIIMasker

logger = logging.getLogger(__name__)


class SessionMemory:
    """Manages conversation sessions with privacy-preserving persistence."""

    def __init__(self, redis_client: RedisClient, settings: Settings) -> None:
        """Initialize session memory.

        Args:
            redis_client: Redis client for session storage
            settings: Application settings
        """
        self.redis_client = redis_client
        self.settings = settings
        self.session_ttl_seconds = settings.session_ttl_hours * 3600
        self.pii_masker = PIIMasker()

    def _hash_ani(self, caller_ani: str) -> str:
        """Hash caller ANI using SHA-256 for privacy.

        Args:
            caller_ani: Caller's phone number (ANI)

        Returns:
            SHA-256 hash of the ANI
        """
        return hashlib.sha256(caller_ani.encode()).hexdigest()

    def _generate_session_id(self) -> str:
        """Generate a unique session ID.

        Returns:
            UUID-based session ID
        """
        return str(uuid.uuid4())

    def _get_session_key(self, session_id: str) -> str:
        """Get Redis key for session data.

        Args:
            session_id: Session ID

        Returns:
            Redis key
        """
        return f"session:{session_id}"

    def _get_ani_session_key(self, caller_ani_hash: str) -> str:
        """Get Redis key for ANI to session ID mapping.

        Args:
            caller_ani_hash: Hashed caller ANI

        Returns:
            Redis key
        """
        return f"ani_session:{caller_ani_hash}"

    async def create_session(
        self,
        caller_ani: str,
        domain: str = "",
        language_code: str = "hi-IN",
    ) -> SessionContext:
        """Create a new session with 24-hour TTL.

        Args:
            caller_ani: Caller's phone number (ANI)
            domain: Domain of conversation (farming, education, welfare)
            language_code: Language code for the conversation

        Returns:
            New SessionContext instance
        """
        caller_ani_hash = self._hash_ani(caller_ani)
        session_id = self._generate_session_id()
        now = datetime.utcnow()

        session_context = SessionContext(
            session_id=session_id,
            caller_ani_hash=caller_ani_hash,
            conversation_history=[],
            extracted_entities=[],
            domain=domain,
            language_code=language_code,
            created_at=now,
            last_updated=now,
        )

        # Store session data
        await self._store_session(session_context)

        # Map ANI hash to session ID for resumption
        ani_session_key = self._get_ani_session_key(caller_ani_hash)
        await self.redis_client.set(
            ani_session_key, session_id, ttl_seconds=self.session_ttl_seconds
        )

        logger.info(f"Created session {session_id} for ANI hash {caller_ani_hash[:8]}...")

        return session_context

    async def _store_session(self, session_context: SessionContext) -> None:
        """Store session context in Redis.

        Args:
            session_context: Session context to store
        """
        session_key = self._get_session_key(session_context.session_id)
        session_data = json.dumps(session_context.to_dict())

        await self.redis_client.set(session_key, session_data, ttl_seconds=self.session_ttl_seconds)

    async def update_session(self, session_context: SessionContext) -> None:
        """Update session with new conversation state.

        Args:
            session_context: Updated session context
        """
        session_context.last_updated = datetime.utcnow()
        await self._store_session(session_context)

        logger.debug(f"Updated session {session_context.session_id}")

    async def get_session(self, session_id: str) -> Optional[SessionContext]:
        """Retrieve session by session ID.

        Args:
            session_id: Session ID

        Returns:
            SessionContext if exists, None otherwise
        """
        session_key = self._get_session_key(session_id)
        session_data = await self.redis_client.get(session_key)

        if session_data is None:
            logger.debug(f"Session {session_id} not found")
            return None

        try:
            data = json.loads(session_data)
            return SessionContext.from_dict(data)
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.error(f"Failed to deserialize session {session_id}: {e}")
            return None

    async def resume_session(self, caller_ani: str) -> Optional[SessionContext]:
        """Retrieve session if exists and not expired.

        Args:
            caller_ani: Caller's phone number (ANI)

        Returns:
            SessionContext if exists and not expired, None otherwise
        """
        caller_ani_hash = self._hash_ani(caller_ani)
        ani_session_key = self._get_ani_session_key(caller_ani_hash)

        # Get session ID from ANI mapping
        session_id = await self.redis_client.get(ani_session_key)

        if session_id is None:
            logger.debug(f"No active session for ANI hash {caller_ani_hash[:8]}...")
            return None

        # Retrieve session context
        session_context = await self.get_session(session_id)

        if session_context is not None:
            logger.info(f"Resumed session {session_id} for ANI hash {caller_ani_hash[:8]}...")

        return session_context

    def mask_pii(self, text: str) -> str:
        """Mask PII in text using NER-based tokenization.

        Detects and masks names, phone numbers, addresses, and other PII
        before storing conversation data.

        Args:
            text: Input text potentially containing PII

        Returns:
            Text with PII masked using [MASKED_<TYPE>] tokens
        """
        return self.pii_masker.mask_pii(text)

    async def add_turn(
        self,
        session_id: str,
        speaker: Speaker,
        text: str,
        entities: Optional[List[Entity]] = None,
    ) -> None:
        """Add a conversation turn to the session.

        Automatically masks PII in the text before storing.

        Args:
            session_id: Session ID
            speaker: Speaker (USER or SYSTEM)
            text: Text of the turn (will be PII masked automatically)
            entities: Optional list of extracted entities
        """
        session_context = await self.get_session(session_id)

        if session_context is None:
            logger.warning(f"Cannot add turn to non-existent session {session_id}")
            return

        # Mask PII before storing
        masked_text = self.mask_pii(text)

        turn = Turn(
            speaker=speaker,
            text=masked_text,
            timestamp=datetime.utcnow(),
            entities=entities or [],
        )

        session_context.conversation_history.append(turn)

        # Add entities to session-level extracted entities
        if entities:
            session_context.extracted_entities.extend(entities)

        await self.update_session(session_context)

    async def delete_session(self, session_id: str) -> None:
        """Delete a session and its ANI mapping.

        Args:
            session_id: Session ID
        """
        # Get session to find ANI hash
        session_context = await self.get_session(session_id)

        if session_context is not None:
            # Delete ANI mapping
            ani_session_key = self._get_ani_session_key(session_context.caller_ani_hash)
            await self.redis_client.delete(ani_session_key)

        # Delete session data
        session_key = self._get_session_key(session_id)
        await self.redis_client.delete(session_key)

        logger.info(f"Deleted session {session_id}")

    async def session_exists(self, session_id: str) -> bool:
        """Check if a session exists.

        Args:
            session_id: Session ID

        Returns:
            True if session exists, False otherwise
        """
        session_key = self._get_session_key(session_id)
        return await self.redis_client.exists(session_key)

    async def extend_session_ttl(self, session_id: str) -> bool:
        """Extend the TTL of a session to the full 24 hours.

        Args:
            session_id: Session ID

        Returns:
            True if successful, False otherwise
        """
        session_key = self._get_session_key(session_id)
        success = await self.redis_client.expire(session_key, self.session_ttl_seconds)

        if success:
            # Also extend ANI mapping TTL
            session_context = await self.get_session(session_id)
            if session_context is not None:
                ani_session_key = self._get_ani_session_key(session_context.caller_ani_hash)
                await self.redis_client.expire(ani_session_key, self.session_ttl_seconds)

        return success
