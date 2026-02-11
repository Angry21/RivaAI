# RivaAI Setup Guide

This guide walks through setting up the RivaAI development environment.

## Prerequisites

- Python 3.11 or higher
- Poetry (Python package manager)
- Docker and Docker Compose (for local PostgreSQL and Redis)
- PostgreSQL 16 with pgvector extension
- Redis 7

## Quick Start

### 1. Install Dependencies

```bash
# Install Poetry if not already installed
curl -sSL https://install.python-poetry.org | python3 -

# Install project dependencies
make install
# or
poetry install
```

### 2. Start Infrastructure Services

```bash
# Start PostgreSQL and Redis using Docker Compose
docker-compose up -d

# Verify services are running
docker-compose ps
```

### 3. Configure Environment

```bash
# Copy example environment file
cp .env.example .env

# Edit .env and add your API keys:
# - TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN
# - DEEPGRAM_API_KEY
# - ELEVENLABS_API_KEY
# - OPENAI_API_KEY or ANTHROPIC_API_KEY
# - GROQ_API_KEY
```

### 4. Initialize Database

The database will be automatically initialized when you start the application for the first time. The `init_database.sql` script is mounted in the Docker container and runs on first startup.

To manually initialize:

```bash
# Connect to PostgreSQL
docker exec -it rivaai-postgres psql -U postgres -d rivaai

# Run initialization script
\i /docker-entrypoint-initdb.d/init.sql
```

### 5. Run the Application

```bash
# Development mode with auto-reload
make dev
# or
poetry run uvicorn rivaai.main:app --reload --host 0.0.0.0 --port 8000

# Production mode
make run
# or
poetry run python -m rivaai.main
```

### 6. Verify Installation

```bash
# Check health endpoint
curl http://localhost:8000/health

# Check readiness endpoint
curl http://localhost:8000/ready

# Check root endpoint
curl http://localhost:8000/
```

## Running Tests

```bash
# Run all tests
make test

# Run unit tests only
make test-unit

# Run property-based tests only
make test-prop

# Run with coverage
poetry run pytest --cov=rivaai --cov-report=html
```

## Development Workflow

### Code Formatting

```bash
# Format code with Black and Ruff
make format
```

### Linting

```bash
# Run linters
make lint
```

### Database Management

```bash
# Connect to PostgreSQL
docker exec -it rivaai-postgres psql -U postgres -d rivaai

# View tables
\dt

# Check pgvector extension
SELECT * FROM pg_extension WHERE extname = 'vector';

# Query crops
SELECT id, name, local_names FROM crops;
```

### Redis Management

```bash
# Connect to Redis
docker exec -it rivaai-redis redis-cli

# Check keys
KEYS *

# Get value
GET key_name

# Monitor commands
MONITOR
```

## Project Structure

```
rivaai/
├── rivaai/
│   ├── config/          # Configuration management
│   ├── telephony/       # Call handling and WebSocket management
│   ├── speech/          # STT/TTS processing and audio routing
│   ├── llm/             # LLM orchestration and conversation management
│   ├── knowledge/       # Knowledge base and retrieval layer
│   ├── safety/          # Circuit breaker and semantic validation
│   ├── session/         # Session management and privacy preservation
│   └── main.py          # FastAPI application entry point
├── tests/               # Unit and property-based tests
├── scripts/             # Database initialization and utilities
├── pyproject.toml       # Poetry configuration
├── docker-compose.yml   # Local development infrastructure
└── Makefile             # Development commands
```

## Configuration

All configuration is managed through environment variables. See `.env.example` for available options.

Key configuration areas:

- **Telephony**: Twilio credentials and phone number
- **Speech Services**: Deepgram (STT) and ElevenLabs (TTS) API keys
- **LLM Services**: OpenAI, Anthropic, and Groq API keys
- **Database**: PostgreSQL connection URL and pool settings
- **Redis**: Redis connection URL and session TTL
- **Latency Budgets**: Maximum latencies for various operations
- **Confidence Thresholds**: Minimum confidence scores for proceeding
- **Safety**: Circuit breaker configuration
- **Retrieval**: Hybrid search weights and top-k settings

## AWS RDS Proxy Setup (Production)

For production deployment with 1000+ concurrent calls:

1. Create RDS PostgreSQL instance with pgvector extension
2. Set up RDS Proxy for connection pooling
3. Configure security groups and VPC
4. Update `DATABASE_URL` to point to RDS Proxy endpoint
5. Adjust pool settings based on load testing

Example RDS Proxy configuration:
- Max connections: 1000
- Connection borrow timeout: 30s
- Init query: `SET application_name = 'rivaai'`

## Troubleshooting

### PostgreSQL Connection Issues

```bash
# Check if PostgreSQL is running
docker-compose ps postgres

# View PostgreSQL logs
docker-compose logs postgres

# Restart PostgreSQL
docker-compose restart postgres
```

### Redis Connection Issues

```bash
# Check if Redis is running
docker-compose ps redis

# View Redis logs
docker-compose logs redis

# Restart Redis
docker-compose restart redis
```

### pgvector Extension Not Found

```bash
# Connect to PostgreSQL
docker exec -it rivaai-postgres psql -U postgres -d rivaai

# Enable extension manually
CREATE EXTENSION IF NOT EXISTS vector;
```

### Import Errors

```bash
# Ensure you're in the Poetry shell
poetry shell

# Or prefix commands with poetry run
poetry run python -m rivaai.main
```

## Next Steps

After completing setup:

1. Review the [Requirements Document](.kiro/specs/sochq/requirements.md)
2. Review the [Design Document](.kiro/specs/sochq/design.md)
3. Review the [Implementation Plan](.kiro/specs/sochq/tasks.md)
4. Start implementing components following the task list
5. Write tests for each component (unit + property-based)
6. Run tests frequently to ensure correctness

## Support

For issues or questions, refer to:
- Requirements: `.kiro/specs/sochq/requirements.md`
- Design: `.kiro/specs/sochq/design.md`
- Tasks: `.kiro/specs/sochq/tasks.md`
