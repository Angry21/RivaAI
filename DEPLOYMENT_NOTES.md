# RivaAI Deployment Notes

## Platform-Specific Dependencies

### Windows Development Environment

The current development environment is running on Windows. Note the following:

**uvloop**: This package is NOT supported on Windows. The `requirements.txt` has been configured to exclude uvloop for Windows compatibility. 

- For **Windows development**: uvloop is commented out in requirements.txt
- For **Linux/Mac deployment**: Uncomment uvloop in requirements.txt or install separately:
  ```bash
  pip install uvloop==0.19.0
  ```

### Production Deployment (Linux)

For production deployment on Linux servers, you MUST install uvloop for optimal performance:

1. Uncomment the uvloop line in `requirements.txt`
2. Or install directly: `pip install uvloop==0.19.0`
3. FastAPI with uvloop provides significant performance improvements for async operations

## Installed Dependencies

All core dependencies have been successfully installed in `.venv`:

### Core Framework
- FastAPI 0.109.0
- Uvicorn 0.27.0 (with standard extras)
- WebSockets 12.0

### Database & Caching
- PostgreSQL: psycopg2-binary 2.9.9
- pgvector 0.2.4 (for vector embeddings)
- Redis 5.0.1

### Data Validation
- Pydantic 2.5.3
- Pydantic Settings 2.1.0

### Testing Framework
- pytest 7.4.4
- pytest-asyncio 0.23.3
- hypothesis 6.96.1 (property-based testing)
- pytest-cov 4.1.0

### Code Quality
- black 24.1.1
- ruff 0.1.14
- mypy 1.8.0

## Next Steps

1. Set up PostgreSQL database with pgvector extension
2. Set up Redis server for session management
3. Configure environment variables in `.env` file (use `.env.example` as template)
4. Initialize database schema
5. Run tests to verify setup

## AWS RDS Proxy Configuration

For production deployment with 1000+ concurrent calls:

1. Set up AWS RDS Proxy for PostgreSQL connection pooling
2. Configure connection pooling parameters in `.env`:
   - `DATABASE_POOL_SIZE=20`
   - `DATABASE_MAX_OVERFLOW=10`
   - `DATABASE_POOL_TIMEOUT=30`
   - `DATABASE_POOL_RECYCLE=3600`

3. Update `DATABASE_URL` to point to RDS Proxy endpoint

## Testing the Installation

Run the following command to verify the installation:

```bash
.venv\Scripts\python.exe -m pytest tests/ -v
```

Note: Database and Redis tests are currently skipped as they require running services.
