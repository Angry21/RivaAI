# Session Management Module

This module provides privacy-preserving session management for RivaAI conversations using Redis as the backend storage.

## Features

- **Privacy-First Design**: Caller ANI is hashed using SHA-256 before storage
- **24-Hour TTL**: Sessions automatically expire after 24 hours
- **Session Resumption**: Users can resume conversations if they call back within the TTL window
- **Conversation History**: Stores complete conversation turns with extracted entities
- **Entity Tracking**: Maintains session-level extracted entities for context

## Components

### SessionMemory

Main class for managing conversation sessions.

**Key Methods:**
- `create_session()`: Create a new session with 24-hour TTL
- `resume_session()`: Retrieve existing session by caller ANI
- `update_session()`: Update session with new conversation state
- `add_turn()`: Add a conversation turn to the session
- `delete_session()`: Delete session and ANI mapping
- `extend_session_ttl()`: Extend session TTL to full 24 hours

### Models

**SessionContext**: Complete session state including:
- Session ID and hashed caller ANI
- Conversation history (list of turns)
- Extracted entities
- Domain and language code
- Timestamps

**Turn**: Single conversation turn with:
- Speaker (USER or SYSTEM)
- Text (PII masked)
- Timestamp
- Extracted entities

**Entity**: Extracted entity with:
- Entity type (crop, chemical, scheme, amount)
- Value
- Confidence score
- Validation requirement flag

## Usage Example

```python
from rivaai.config.redis_client import get_redis_client
from rivaai.config.settings import get_settings
from rivaai.session import SessionMemory, Speaker, Entity

# Initialize
settings = get_settings()
redis_client = await get_redis_client(settings)
session_memory = SessionMemory(redis_client, settings)

# Create new session
session = await session_memory.create_session(
    caller_ani="+919876543210",
    domain="farming",
    language_code="hi-IN"
)

# Add conversation turn
entities = [
    Entity(
        entity_type="crop",
        value="wheat",
        confidence=0.9,
        requires_semantic_validation=True
    )
]

await session_memory.add_turn(
    session.session_id,
    Speaker.USER,
    "I want to grow wheat",
    entities
)

# Resume session (if user calls back)
resumed = await session_memory.resume_session("+919876543210")
if resumed:
    print(f"Resumed session with {len(resumed.conversation_history)} turns")
```

## Privacy Features

1. **ANI Hashing**: Phone numbers are hashed using SHA-256 before storage
2. **Automatic Expiration**: Sessions expire after 24 hours via Redis TTL
3. **PII Masking**: Text should be PII-masked before calling `add_turn()` (handled by safety module)
4. **No Audio Storage**: Only text transcripts are stored, never audio

## Testing

Run unit tests:
```bash
pytest tests/session/test_session_memory.py -v
```

Run integration tests (requires Redis):
```bash
pytest tests/session/test_session_integration.py -v -m integration
```

## Requirements Validation

This implementation validates:
- **Requirement 3.1**: Session creation with 24-hour TTL
- **Requirement 3.3**: Session resumption for returning callers
- **Requirement 3.4**: Anonymized pattern retention (via automatic expiration)

Note: PII masking (Requirement 3.2) will be implemented in task 5.2.
