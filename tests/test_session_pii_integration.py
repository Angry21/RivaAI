"""Integration tests for SessionMemory with PII masking."""

import pytest

from rivaai.config.redis_client import RedisClient
from rivaai.config.settings import Settings
from rivaai.session.memory import SessionMemory
from rivaai.session.models import Speaker


@pytest.mark.asyncio
class TestSessionMemoryPIIMasking:
    """Test suite for SessionMemory PII masking integration."""

    @pytest.fixture
    def session_memory(
        self, redis_client: RedisClient, test_settings: Settings
    ) -> SessionMemory:
        """Create a SessionMemory instance for testing."""
        return SessionMemory(redis_client, test_settings)

    async def test_add_turn_masks_phone_number(
        self, session_memory: SessionMemory
    ) -> None:
        """Test that phone numbers are masked when adding turns."""
        # Create session
        session = await session_memory.create_session(
            caller_ani="+919876543210",
            domain="farming",
            language_code="hi-IN",
        )

        # Add turn with phone number
        await session_memory.add_turn(
            session_id=session.session_id,
            speaker=Speaker.USER,
            text="My phone number is 9876543210",
        )

        # Retrieve session and verify masking
        retrieved = await session_memory.get_session(session.session_id)
        assert retrieved is not None
        assert len(retrieved.conversation_history) == 1
        
        turn_text = retrieved.conversation_history[0].text
        assert "[MASKED_PHONE]" in turn_text
        assert "9876543210" not in turn_text

        # Cleanup
        await session_memory.delete_session(session.session_id)

    async def test_add_turn_masks_email(self, session_memory: SessionMemory) -> None:
        """Test that email addresses are masked when adding turns."""
        # Create session
        session = await session_memory.create_session(
            caller_ani="+919876543210",
            domain="education",
            language_code="hi-IN",
        )

        # Add turn with email
        await session_memory.add_turn(
            session_id=session.session_id,
            speaker=Speaker.USER,
            text="Contact me at farmer@example.com",
        )

        # Retrieve session and verify masking
        retrieved = await session_memory.get_session(session.session_id)
        assert retrieved is not None
        
        turn_text = retrieved.conversation_history[0].text
        assert "[MASKED_EMAIL]" in turn_text
        assert "farmer@example.com" not in turn_text

        # Cleanup
        await session_memory.delete_session(session.session_id)

    async def test_add_turn_masks_name(self, session_memory: SessionMemory) -> None:
        """Test that names are masked when adding turns."""
        # Create session
        session = await session_memory.create_session(
            caller_ani="+919876543210",
            domain="welfare",
            language_code="hi-IN",
        )

        # Add turn with name
        await session_memory.add_turn(
            session_id=session.session_id,
            speaker=Speaker.USER,
            text="My name is Rajesh Kumar",
        )

        # Retrieve session and verify masking
        retrieved = await session_memory.get_session(session.session_id)
        assert retrieved is not None
        
        turn_text = retrieved.conversation_history[0].text
        assert "[MASKED_NAME]" in turn_text
        assert "Rajesh Kumar" not in turn_text

        # Cleanup
        await session_memory.delete_session(session.session_id)

    async def test_add_turn_masks_multiple_pii(
        self, session_memory: SessionMemory
    ) -> None:
        """Test that multiple PII types are masked in a single turn."""
        # Create session
        session = await session_memory.create_session(
            caller_ani="+919876543210",
            domain="farming",
            language_code="hi-IN",
        )

        # Add turn with multiple PII types
        await session_memory.add_turn(
            session_id=session.session_id,
            speaker=Speaker.USER,
            text="My name is Priya Sharma, phone 9876543210, email priya@example.com",
        )

        # Retrieve session and verify masking
        retrieved = await session_memory.get_session(session.session_id)
        assert retrieved is not None
        
        turn_text = retrieved.conversation_history[0].text
        assert "[MASKED_NAME]" in turn_text
        assert "[MASKED_PHONE]" in turn_text
        assert "[MASKED_EMAIL]" in turn_text
        assert "Priya Sharma" not in turn_text
        assert "9876543210" not in turn_text
        assert "priya@example.com" not in turn_text

        # Cleanup
        await session_memory.delete_session(session.session_id)

    async def test_add_turn_preserves_non_pii(
        self, session_memory: SessionMemory
    ) -> None:
        """Test that non-PII content is preserved when masking."""
        # Create session
        session = await session_memory.create_session(
            caller_ani="+919876543210",
            domain="farming",
            language_code="hi-IN",
        )

        # Add turn with PII and non-PII content
        await session_memory.add_turn(
            session_id=session.session_id,
            speaker=Speaker.USER,
            text="My name is Ramesh and I need help with wheat farming",
        )

        # Retrieve session and verify
        retrieved = await session_memory.get_session(session.session_id)
        assert retrieved is not None
        
        turn_text = retrieved.conversation_history[0].text
        # PII should be masked
        assert "[MASKED_NAME]" in turn_text
        assert "Ramesh" not in turn_text
        # Non-PII should be preserved
        assert "wheat farming" in turn_text
        assert "need help" in turn_text

        # Cleanup
        await session_memory.delete_session(session.session_id)

    async def test_add_turn_no_pii(self, session_memory: SessionMemory) -> None:
        """Test that turns without PII are stored unchanged."""
        # Create session
        session = await session_memory.create_session(
            caller_ani="+919876543210",
            domain="farming",
            language_code="hi-IN",
        )

        original_text = "I need help with wheat farming"
        
        # Add turn without PII
        await session_memory.add_turn(
            session_id=session.session_id,
            speaker=Speaker.USER,
            text=original_text,
        )

        # Retrieve session and verify no masking occurred
        retrieved = await session_memory.get_session(session.session_id)
        assert retrieved is not None
        
        turn_text = retrieved.conversation_history[0].text
        assert turn_text == original_text

        # Cleanup
        await session_memory.delete_session(session.session_id)

    async def test_mask_pii_method_directly(
        self, session_memory: SessionMemory
    ) -> None:
        """Test the mask_pii method directly."""
        text = "My phone is 9876543210 and email is test@example.com"
        masked = session_memory.mask_pii(text)
        
        assert "[MASKED_PHONE]" in masked
        assert "[MASKED_EMAIL]" in masked
        assert "9876543210" not in masked
        assert "test@example.com" not in masked

    async def test_conversation_history_all_masked(
        self, session_memory: SessionMemory
    ) -> None:
        """Test that all turns in conversation history are masked."""
        # Create session
        session = await session_memory.create_session(
            caller_ani="+919876543210",
            domain="farming",
            language_code="hi-IN",
        )

        # Add multiple turns with PII
        await session_memory.add_turn(
            session_id=session.session_id,
            speaker=Speaker.USER,
            text="My name is Rajesh, phone 9876543210",
        )
        
        await session_memory.add_turn(
            session_id=session.session_id,
            speaker=Speaker.SYSTEM,
            text="Hello Rajesh, how can I help?",
        )
        
        await session_memory.add_turn(
            session_id=session.session_id,
            speaker=Speaker.USER,
            text="Email me at rajesh@example.com",
        )

        # Retrieve session and verify all turns are masked
        retrieved = await session_memory.get_session(session.session_id)
        assert retrieved is not None
        assert len(retrieved.conversation_history) == 3
        
        # Check first turn
        assert "[MASKED_NAME]" in retrieved.conversation_history[0].text
        assert "[MASKED_PHONE]" in retrieved.conversation_history[0].text
        
        # Check second turn
        assert "[MASKED_NAME]" in retrieved.conversation_history[1].text
        
        # Check third turn
        assert "[MASKED_EMAIL]" in retrieved.conversation_history[2].text

        # Cleanup
        await session_memory.delete_session(session.session_id)

    async def test_aadhaar_masking_in_session(
        self, session_memory: SessionMemory
    ) -> None:
        """Test that Aadhaar numbers are masked in session."""
        # Create session
        session = await session_memory.create_session(
            caller_ani="+919876543210",
            domain="welfare",
            language_code="hi-IN",
        )

        # Add turn with Aadhaar
        await session_memory.add_turn(
            session_id=session.session_id,
            speaker=Speaker.USER,
            text="My Aadhaar number is 2345 6789 0123",
        )

        # Retrieve session and verify masking
        retrieved = await session_memory.get_session(session.session_id)
        assert retrieved is not None
        
        turn_text = retrieved.conversation_history[0].text
        assert "[MASKED_AADHAAR]" in turn_text
        assert "2345 6789 0123" not in turn_text

        # Cleanup
        await session_memory.delete_session(session.session_id)
