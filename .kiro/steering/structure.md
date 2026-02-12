# Project Structure

## Root Layout

```
rivaai/                 # Main application package
├── config/            # Configuration and infrastructure
├── telephony/         # Call handling and WebSocket management
├── speech/            # STT/TTS processing and audio routing
├── llm/               # LLM orchestration and conversation management
├── knowledge/         # Knowledge base and retrieval layer
├── safety/            # Circuit breaker and semantic validation
├── session/           # Session management and privacy preservation
└── main.py            # FastAPI application entry point

tests/                 # Test suite
├── telephony/         # Telephony component tests
├── conftest.py        # Shared fixtures and Hypothesis configuration
└── test_*.py          # Test modules

examples/              # Usage examples
scripts/               # Database initialization and utilities
.kiro/                 # Kiro configuration
├── specs/             # Feature specifications
└── steering/          # Project steering documents
```

## Module Organization

### config/
Infrastructure and configuration management:
- `settings.py`: Pydantic settings with environment variable loading
- `database.py`: PostgreSQL connection pool management
- `redis_client.py`: Redis client with async support

### telephony/
PSTN and WebSocket handling:
- `gateway.py`: Twilio integration and call management
- `audio_router.py`: Audio stream routing between components
- `barge_in_handler.py`: Interrupt detection and handling
- `transcoding.py`: Audio format conversion (μ-law ↔ Linear16)
- `models.py`: Data models (CallSession, AudioChunk, etc.)

### speech/
Speech processing pipeline:
- `processor.py`: STT/TTS orchestration
- `models.py`: Speech-related data models
- Voice activity detection (VAD)
- Audio transcoding and streaming

### llm/
LLM integration and conversation management (in development)

### knowledge/
RAG and knowledge retrieval (in development)

### safety/
Safety mechanisms (in development):
- Circuit breaker patterns
- Semantic validation
- PII masking

### session/
Session state management (in development):
- Redis-backed session store
- 24-hour TTL enforcement
- Privacy preservation

## Code Conventions

### File Naming
- Module files: lowercase with underscores (`audio_router.py`)
- Test files: `test_` prefix (`test_audio_router.py`)
- Models: `models.py` in each module
- Init files: `__init__.py` for package exports

### Class Organization
- Use dataclasses for simple data containers
- Use Enums for fixed sets of values
- Pydantic models for validation and settings
- Type hints required on all functions and methods

### Import Structure
```python
# Standard library
import asyncio
from typing import Optional

# Third-party
from fastapi import FastAPI
from pydantic import BaseModel

# Local
from rivaai.config import get_settings
from rivaai.telephony.models import CallSession
```

### Async Patterns
- All I/O operations must be async
- Use `async def` for coroutines
- Use `AsyncGenerator` for streaming
- Proper cleanup with context managers

## Testing Structure

- Unit tests: `tests/test_<module>.py`
- Property tests: `tests/test_property_<feature>.py`
- Fixtures: `tests/conftest.py`
- Test markers: `@pytest.mark.property` for property-based tests
- Minimum 100 examples for property tests (configured in conftest.py)

## Configuration Files

- `.env.example`: Template for environment variables
- `pyproject.toml`: Poetry configuration and tool settings
- `requirements.txt`: Alternative pip-based dependency list
- `docker-compose.yml`: Local development services
- `Makefile`: Common development commands
