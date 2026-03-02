# Knowledge Base Setup Guide

This guide walks you through setting up the RivaAI knowledge base with PostgreSQL, pgvector, and sample data.

## Prerequisites

1. **PostgreSQL 14+** with pgvector extension
2. **Python 3.11+** with dependencies installed
3. **OpenAI API Key** for embedding generation

## Quick Setup

### Option 1: Using Docker Compose (Recommended)

```bash
# Start PostgreSQL and Redis
docker-compose up -d

# Run setup script
# On Linux/Mac:
bash scripts/setup_knowledge_base.sh

# On Windows:
powershell scripts/setup_knowledge_base.ps1
```

### Option 2: Manual Setup

#### Step 1: Start PostgreSQL

```bash
# Using Docker
docker run -d \
  --name rivaai-postgres \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=rivaai \
  -p 5432:5432 \
  pgvector/pgvector:pg16

# Or use existing PostgreSQL installation
```

#### Step 2: Initialize Database Schema

```bash
psql -h localhost -U postgres -d rivaai -f scripts/init_database.sql
```

#### Step 3: Configure Environment

```bash
# Copy example environment file
cp .env.example .env

# Edit .env and set your OpenAI API key
# OPENAI_API_KEY=sk-...
```

#### Step 4: Load Sample Data

```bash
python scripts/load_knowledge_base.py
```

## Database Schema

The knowledge base consists of several tables:

### Entity Tables

- **crops**: Agricultural crop information with embeddings
- **chemicals**: Pesticide/fertilizer information with safety limits
- **schemes**: Government welfare and education schemes

### Unified Retrieval Table

- **knowledge_items**: Aggregated searchable content from all entity tables
  - Optimized for vector similarity search
  - Includes metadata and domain classification
  - Used by the retrieval system

### Relationship Tables

- **crop_chemical_relationships**: Crop-chemical compatibility
- **crop_weather_requirements**: Weather requirements for crops

## Sample Data

The setup script loads sample data including:

- **3 Crops**: Wheat, Rice, Cotton (with Hindi, Marathi, Telugu, Tamil, Bengali names)
- **3 Chemicals**: Urea, DAP, Chlorpyrifos (with safety information)
- **2 Schemes**: PM-KISAN, Pradhan Mantri Fasal Bima Yojana

All data includes:
- Multi-language support
- Vector embeddings for semantic search
- Metadata for filtering and display

## Verification

After setup, verify the installation:

```bash
# Check table counts
psql -h localhost -U postgres -d rivaai -c "
  SELECT 
    (SELECT COUNT(*) FROM crops) as crops,
    (SELECT COUNT(*) FROM chemicals) as chemicals,
    (SELECT COUNT(*) FROM schemes) as schemes,
    (SELECT COUNT(*) FROM knowledge_items) as knowledge_items;
"

# Test retrieval
python examples/retrieval_example.py
```

Expected output:
```
crops | chemicals | schemes | knowledge_items
------+-----------+---------+----------------
    3 |         3 |       2 |               8
```

## Configuration

Key settings in `.env`:

```bash
# Database
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/rivaai

# Embeddings
OPENAI_API_KEY=sk-...
EMBEDDING_MODEL=text-embedding-3-large

# Retrieval
RETRIEVAL_RELEVANCE_THRESHOLD=0.7
RETRIEVAL_TOP_K=5
```

## Adding More Data

### Adding Crops

```python
from rivaai.knowledge import Crop, KnowledgeBaseLoader, get_embedding_generator
from rivaai.config import get_database_pool, get_settings

settings = get_settings()
db_pool = get_database_pool(settings)
embedding_gen = get_embedding_generator(settings)
loader = KnowledgeBaseLoader(db_pool, embedding_gen)

crop = Crop(
    id=None,
    name="Maize",
    local_names={"hi": "मक्का", "mr": "मका"},
    season="Kharif",
    region="All India",
    soil_requirements="Well-drained fertile soil",
    water_requirements="Moderate water requirement",
)

crop_id = loader.load_crop(crop)
print(f"Loaded crop with ID: {crop_id}")
```

### Updating knowledge_items

After adding new data to entity tables, update the unified table:

```sql
-- Run the INSERT queries from load_knowledge_base.py
-- Or use the populate_knowledge_items() function
```

## Troubleshooting

### pgvector Extension Not Found

```bash
# Install pgvector extension
# On Ubuntu/Debian:
sudo apt-get install postgresql-14-pgvector

# On Mac with Homebrew:
brew install pgvector

# Or use Docker image with pgvector pre-installed:
docker pull pgvector/pgvector:pg16
```

### Embedding Generation Fails

- Verify OpenAI API key is set correctly
- Check API key has sufficient credits
- Ensure network connectivity to OpenAI API

### Slow Vector Search

- Ensure ivfflat indexes are created (automatic after 1000+ rows)
- Adjust `lists` parameter in index creation for your data size
- Consider using HNSW index for larger datasets

## Performance Tuning

### Index Optimization

```sql
-- For datasets > 10,000 rows, adjust lists parameter
DROP INDEX IF EXISTS knowledge_items_embedding_idx;
CREATE INDEX knowledge_items_embedding_idx 
  ON knowledge_items 
  USING ivfflat (embedding vector_cosine_ops) 
  WITH (lists = 1000);
```

### Connection Pooling

Adjust in `.env`:
```bash
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=10
```

## Next Steps

1. **Test Retrieval**: Run `python examples/retrieval_example.py`
2. **Add More Data**: Use the data loader to add domain-specific content
3. **Integrate with LLM**: Connect retrieval to RAG pipeline
4. **Monitor Performance**: Check retrieval latency and accuracy

## Resources

- [pgvector Documentation](https://github.com/pgvector/pgvector)
- [OpenAI Embeddings Guide](https://platform.openai.com/docs/guides/embeddings)
- [PostgreSQL Performance Tuning](https://wiki.postgresql.org/wiki/Performance_Optimization)
