# Task 7.1: PostgreSQL with pgvector Setup - Quick Start Guide

This guide provides a quick reference for setting up and using the PostgreSQL knowledge base with pgvector extension.

## What Was Implemented

✅ PostgreSQL database configuration with pgvector extension  
✅ Database schema for farming, education, and welfare domains  
✅ Vector columns (1536 dimensions) for semantic search  
✅ Embedding generation using OpenAI text-embedding-3-large  
✅ Data loading utilities for crops, chemicals, and schemes  
✅ AWS RDS Proxy configuration guidance  
✅ ivfflat indexes for fast vector search  
✅ Sample data including welfare schemes from myScheme.gov.in  

## Quick Start

### 1. Start Local Database

```bash
# Start PostgreSQL and Redis
docker-compose up -d

# Verify services are running
docker-compose ps
```

### 2. Initialize Database Schema

```bash
# Run initialization script
docker exec -i rivaai-postgres psql -U postgres -d rivaai < scripts/init_database.sql

# Verify pgvector extension
docker exec -it rivaai-postgres psql -U postgres -d rivaai -c "\dx vector"
```

### 3. Configure Environment

```bash
# Copy example environment file
cp .env.example .env

# Edit .env and set your OpenAI API key
# DATABASE_URL=postgresql://postgres:postgres@localhost:5432/rivaai
# OPENAI_API_KEY=your_key_here
```

### 4. Load Sample Data

```bash
# Activate virtual environment
source .venv/bin/activate  # Linux/Mac
.venv\Scripts\activate.ps1  # Windows

# Load sample data (Wheat crop + welfare schemes)
python scripts/load_sample_data.py
```

### 5. Verify Setup

```bash
# Run tests
pytest tests/test_knowledge_base.py -v

# Check database contents
docker exec -it rivaai-postgres psql -U postgres -d rivaai -c "SELECT name FROM crops;"
docker exec -it rivaai-postgres psql -U postgres -d rivaai -c "SELECT name, domain FROM schemes;"
```

## Database Schema Overview

### Core Tables

**crops** - Agricultural crop information
- Columns: id, name, local_names (JSONB), season, region, soil_requirements, water_requirements, embedding (vector)
- Index: ivfflat on embedding for fast similarity search

**chemicals** - Pesticides and fertilizers with safety limits
- Columns: id, name, type, safe_dosage_min, safe_dosage_max, unit, safety_warnings (JSONB), embedding (vector)
- Index: ivfflat on embedding

**schemes** - Government welfare and education schemes
- Columns: id, name, domain, local_names (JSONB), eligibility_criteria (JSONB), required_documents (JSONB), application_process, contact_info (JSONB), last_updated, embedding (vector)
- Index: ivfflat on embedding

### Relationship Tables

**crop_chemical_relationships** - Graph relationships between crops and chemicals
- Foreign keys to crops and chemicals tables
- Relationship types: 'SAFE_FOR', 'REQUIRES', 'AVOID'

**crop_weather_requirements** - Weather requirements for crops
- Foreign key to crops table

## Using the Knowledge Base

### Generate Embeddings

```python
from rivaai.knowledge.embeddings import get_embedding_generator
from rivaai.config.settings import get_settings

settings = get_settings()
embedding_gen = get_embedding_generator(settings)

# Generate single embedding
embedding = embedding_gen.generate_embedding("Wheat crop information")

# Generate batch embeddings
embeddings = embedding_gen.generate_embeddings_batch([
    "Wheat", "Rice", "Cotton"
])
```

### Load Data Programmatically

```python
from rivaai.config.database import get_database_pool
from rivaai.knowledge.data_loader import KnowledgeBaseLoader
from rivaai.knowledge.embeddings import get_embedding_generator
from rivaai.knowledge.models import Crop

# Initialize
settings = get_settings()
db_pool = get_database_pool(settings)
embedding_gen = get_embedding_generator(settings)
loader = KnowledgeBaseLoader(db_pool, embedding_gen)

# Load a crop
wheat = Crop(
    id=None,
    name="Wheat",
    local_names={"hi": "गेहूं", "mr": "गहू"},
    season="Rabi",
    region="North India",
    soil_requirements="Well-drained loamy soil with pH 6.0-7.5",
    water_requirements="4-5 irrigations during growing season"
)

crop_id = loader.load_crop(wheat)
print(f"Loaded crop with ID: {crop_id}")
```

### Vector Search Query

```sql
-- Find crops similar to a query embedding
SELECT 
    id, 
    name,
    season,
    region,
    1 - (embedding <=> '[0.1, 0.2, ...]'::vector) AS similarity
FROM crops
ORDER BY embedding <=> '[0.1, 0.2, ...]'::vector
LIMIT 5;
```

## Sample Data Included

### Farming Domain
- **Wheat** crop with local names in 5 languages
- **Urea** fertilizer with safety limits
- **Chlorpyrifos** pesticide with warnings

### Welfare Schemes (from myScheme.gov.in)
- **PM-KISAN** - Direct income support for farmers
- **Ayushman Bharat (PMJAY)** - Health insurance scheme
- **National Scholarship Portal** - Pre-matric scholarship

All schemes include:
- Multi-language names (Hindi, Marathi, Telugu, Tamil, Bengali)
- Eligibility criteria
- Required documents
- Application process
- Contact information

## AWS RDS Proxy Setup

For production deployment with 1000+ concurrent connections:

1. Create RDS PostgreSQL instance (version 15.4+)
2. Install pgvector extension
3. Set up AWS RDS Proxy for connection pooling
4. Configure security groups and IAM roles
5. Update DATABASE_URL to use proxy endpoint

See `docs/AWS_RDS_PROXY_SETUP.md` for detailed instructions.

## Performance Optimization

### Index Creation

```sql
-- Create ivfflat indexes (after loading data)
CREATE INDEX crops_embedding_idx ON crops 
    USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

CREATE INDEX chemicals_embedding_idx ON chemicals 
    USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

CREATE INDEX schemes_embedding_idx ON schemes 
    USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
```

### Analyze Tables

```sql
-- Update statistics for query optimization
ANALYZE crops;
ANALYZE chemicals;
ANALYZE schemes;
```

### Monitor Performance

```sql
-- Check index usage
SELECT 
    schemaname,
    tablename,
    indexname,
    idx_scan,
    idx_tup_read
FROM pg_stat_user_indexes
WHERE tablename IN ('crops', 'chemicals', 'schemes');

-- Check table sizes
SELECT 
    pg_size_pretty(pg_total_relation_size('crops')) AS crops_size,
    pg_size_pretty(pg_total_relation_size('chemicals')) AS chemicals_size,
    pg_size_pretty(pg_total_relation_size('schemes')) AS schemes_size;
```

## Configuration Settings

Key settings in `.env`:

```bash
# Database
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/rivaai
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=10

# Embeddings
OPENAI_API_KEY=your_key_here
EMBEDDING_MODEL=text-embedding-3-large

# Retrieval
RETRIEVAL_TOP_K=5
GRAPH_TRAVERSAL_DEPTH=2
HYBRID_VECTOR_WEIGHT=0.6
HYBRID_GRAPH_WEIGHT=0.4
```

## Files Created

### Core Implementation
- `rivaai/knowledge/embeddings.py` - Embedding generation
- `rivaai/knowledge/models.py` - Data models
- `rivaai/knowledge/data_loader.py` - Data loading utilities
- `rivaai/knowledge/__init__.py` - Module exports

### Scripts
- `scripts/init_database.sql` - Database schema (enhanced)
- `scripts/load_sample_data.py` - Sample data loader

### Documentation
- `docs/KNOWLEDGE_BASE_SETUP.md` - Comprehensive setup guide
- `docs/AWS_RDS_PROXY_SETUP.md` - Production deployment guide
- `docs/TASK_7.1_SETUP_GUIDE.md` - This quick start guide

### Tests
- `tests/test_knowledge_base.py` - Unit tests for knowledge base

## Next Steps

After completing Task 7.1, proceed to:

1. **Task 7.2**: Implement relational schema for graph relationships
2. **Task 7.3**: Implement Retrieval Layer with SQL-based hybrid search
3. **Task 7.4**: Write property test for graph-augmented retrieval
4. **Task 7.5**: Load verified knowledge for farming domain

## Troubleshooting

### pgvector Extension Not Found

```bash
# Install pgvector in Docker container
docker exec -it rivaai-postgres bash
apt-get update && apt-get install -y postgresql-15-pgvector
exit

# Restart container
docker-compose restart postgres
```

### OpenAI API Errors

- Verify API key is set: `echo $OPENAI_API_KEY`
- Check API quota and rate limits
- Ensure network connectivity

### Database Connection Issues

```bash
# Check if PostgreSQL is running
docker-compose ps

# View logs
docker-compose logs postgres

# Test connection
psql -h localhost -U postgres -d rivaai -c "SELECT 1;"
```

## Validation Checklist

- [x] PostgreSQL running with pgvector extension
- [x] Database schema created with vector columns
- [x] ivfflat indexes created for vector search
- [x] Embedding generation working with OpenAI API
- [x] Sample data loaded (crops, chemicals, schemes)
- [x] Welfare schemes from myScheme.gov.in included
- [x] Tests passing
- [x] AWS RDS Proxy documentation provided

## References

- [pgvector GitHub](https://github.com/pgvector/pgvector)
- [OpenAI Embeddings API](https://platform.openai.com/docs/guides/embeddings)
- [myScheme.gov.in](https://www.myscheme.gov.in/)
- Design Document: `.kiro/specs/sochq/design.md`
- Requirements: `.kiro/specs/sochq/requirements.md`
