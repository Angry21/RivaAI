# RivaAI - Cognitive Voice Interface for Decision Intelligence

RivaAI is a telephony-based cognitive voice interface that provides decision support to users through natural phone conversations. The system is designed for users with basic feature phones in rural environments, requiring no digital literacy.

## Features

- **Streaming Voice Interface**: Full-duplex audio with barge-in support
- **Multi-language Support**: Hindi, Marathi, Telugu, Tamil, Bengali
- **RAG-Based Decisions**: Verified information from domain-specific knowledge bases
- **Safety-First Design**: Circuit breaker mechanisms prevent harmful outputs
- **Privacy-Preserving**: Automatic PII masking and 24-hour data retention

## Architecture

The system uses:
- **Backend**: Python with FastAPI + uvloop for async WebSocket handling
- **Telephony**: Twilio for PSTN connectivity with WebSocket media streams
- **Speech**: Deepgram Nova-2 (STT), ElevenLabs Turbo (TTS)
- **LLM**: GPT-4/Claude for complex reasoning, Groq API for fast responses
- **Knowledge Store**: PostgreSQL with pgvector extension
- **Session Store**: Redis with 24-hour TTL
- **Infrastructure**: Kubernetes for auto-scaling, AWS RDS Proxy for connection pooling

## Project Structure

```
rivaai/
├── telephony/       # Call handling and WebSocket management
├── speech/          # STT/TTS processing and audio routing
├── llm/             # LLM orchestration and conversation management
├── knowledge/       # Knowledge base and retrieval layer
├── safety/          # Circuit breaker and semantic validation
├── session/         # Session management and privacy preservation
├── config/          # Configuration management
└── tests/           # Unit and property-based tests
```

## Setup

1. Install dependencies:
```bash
poetry install
```

2. Configure environment variables (see `.env.example`)

3. Set up PostgreSQL with pgvector extension

4. Run the application:
```bash
poetry run uvicorn rivaai.main:app --host 0.0.0.0 --port 8000
```

## Testing

Run all tests:
```bash
poetry run pytest
```

Run property-based tests:
```bash
poetry run pytest -m property
```

## Development

The implementation follows a phased approach:
1. Core Infrastructure (telephony, audio, session management)
2. Safety and Validation (circuit breaker, semantic validator)
3. Knowledge and RAG (graph-augmented vector store, hybrid retrieval)
4. Optimization (intent routing, SLM integration, latency optimization)
5. Scale and Polish (load testing, multi-domain expansion)

## License

Proprietary - All rights reserved
