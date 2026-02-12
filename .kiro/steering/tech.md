# Technology Stack

## Core Technologies

- **Language**: Python 3.11+
- **Framework**: FastAPI with uvicorn (uvloop on Linux/Mac)
- **Async**: asyncio with async/await patterns throughout
- **Type System**: Full type hints with mypy strict checking

## Key Dependencies

### Backend & API
- FastAPI for async HTTP/WebSocket handling
- uvicorn with uvloop for high-performance event loop (Linux/Mac only)
- Pydantic v2 for data validation and settings management

### Telephony & Speech
- Twilio for PSTN connectivity and WebSocket media streams
- Deepgram Nova-2 for Speech-to-Text (STT)
- ElevenLabs Turbo for Text-to-Speech (TTS)

### Data Storage
- PostgreSQL with pgvector extension for knowledge store
- Redis for session management with 24-hour TTL

### LLM & AI
- GPT-4/Claude for complex reasoning
- Groq API for fast responses
- Hypothesis for property-based testing

## Build System

Uses Poetry for dependency management. Alternative: pip with requirements.txt.

### Common Commands

```bash
# Installation
make install              # Install all dependencies
poetry install            # Alternative: direct poetry command

# Testing
make test                 # Run all tests
make test-unit            # Run unit tests only (excludes property tests)
make test-prop            # Run property-based tests only
pytest -v                 # Direct pytest with verbose output
pytest -m property        # Run only property-based tests

# Code Quality
make lint                 # Run ruff and mypy
make format               # Format with black and auto-fix with ruff
black rivaai tests        # Format code
ruff check rivaai tests   # Lint code
mypy rivaai               # Type checking

# Running
make run                  # Run application
make dev                  # Run with auto-reload
python -m rivaai.main     # Direct Python execution

# Cleanup
make clean                # Remove build artifacts and cache
```

## Development Infrastructure

```bash
# Start local services (PostgreSQL + Redis)
docker-compose up -d

# Stop services
docker-compose down

# View logs
docker-compose logs -f
```

## Code Style

- **Line Length**: 100 characters (black, ruff, mypy configured)
- **Formatter**: Black
- **Linter**: Ruff
- **Type Checker**: mypy with strict settings
- **Docstrings**: Google style with type annotations
- **Async**: Use async/await, avoid blocking operations

## Testing Configuration

- **Framework**: pytest with pytest-asyncio
- **Property Testing**: Hypothesis with minimum 100 examples per test
- **Async Mode**: Auto-detection enabled
- **Markers**: Use `@pytest.mark.property` for property-based tests

## Platform Notes

- **uvloop**: Only available on Linux/Mac, gracefully falls back on Windows
- **Audio Processing**: Uses audioop for μ-law/Linear16 transcoding
- **Event Loop**: asyncio with uvloop optimization where available
