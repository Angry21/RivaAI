# Knowledge Base Setup Guide

This guide explains how to set up and populate the RivaAI knowledge base with pgvector for semantic search.

## Overview

The RivaAI knowledge base uses PostgreSQL with the pgvector extension to store domain-specific information with vector embeddings for semantic search. The system supports:

- **Farming domain**: Crop information, chemicals, safety limits
- **Education domain**: Scholarships, institutions, eligibility criteria
- **Welfare domain**: Government schemes from myScheme.gov.in

## Architecture

```
PostgreSQL + pgvector
├── Vector Search (semantic similarity)
├── Graph Relationships (foreign keys)
└── Hybrid Retrieval (0.6 * vector + 0.4 * graph)
```

## Prerequisites

- PostgreSQL 11.9+ (for pgvector support)
- Python 3.11+
- OpenAI API key (for embeddings)
- Docker (for local development)

## Local Development Setup

### 1. Start PostgreSQL with Docker

```bash
# Start services
docker-compose up -d

# Verify PostgreSQL is running
docker-compose ps
```

### 2. Initialize Database Schema

```bash
# Run initialization script
docker exec -i rivaai-postgres psql -U postgres -d rivaai < scripts/init_database.sql

# Or using psql directly
psql -h localhost -U postgres -d rivaai -f scripts/init_database.sql
```

### 3. Verify pgvector Extension

```bash
# Connect to database
psql -h localhost -U postgres -d rivaai

# Check extension
\dx vector

# Should show:
#  Name   | Version | Schema |      Description
# --------+---------+--------+------------------------
#  vector | 0.5.1   | public | vector data type and ivfflat access method
```

### 4. Load Sample Data

```bash
# Set OpenAI API key in .env
echo "OPENAI_API_KEY=your_key_here" >> .env

# Run data loader
python scripts/load_sample_data.py
```

## Database Schema

### Core Tables

#### crops
Stores agricultural crop information with embeddings.

```sql
CREATE TABLE crops (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    local_names JSONB,                    -- Multi-language names
    season VARCHAR(50),                   -- Rabi, Kharif, etc.
    region VARCHAR(100),
    soil_requirements TEXT,
    water_requirements TEXT,
    embedding vector(1536),               -- pgvector type
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### chemicals
Stores pesticide/fertilizer information with safety limits.

```sql
CREATE TABLE chemicals (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    type VARCHAR(50),                     -- pesticide, fertilizer
    safe_dosage_min FLOAT,
    safe_dosage_max FLOAT,
    unit VARCHAR(20),
    safety_warnings JSONB,
    embedding vector(1536),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### schemes
Stores government welfare and education schemes.

```sql
CREATE TABLE schemes (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    domain VARCHAR(50) NOT NULL,          -- 'welfare', 'education'
    local_names JSONB,
    eligibility_criteria JSONB,
    required_documents JSONB,
    application_process TEXT,
    contact_info JSONB,
    last_updated TIMESTAMP,
    embedding vector(1536),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Relationship Tables

#### crop_chemical_relationships
Graph relationships between crops and chemicals.

```sql
CREATE TABLE crop_chemical_relationships (
    id SERIAL PRIMARY KEY,
    crop_id INTEGER REFERENCES crops(id) ON DELETE CASCADE,
    chemical_id INTEGER REFERENCES chemicals(id) ON DELETE CASCADE,
    relationship_type VARCHAR(50),        -- 'SAFE_FOR', 'REQUIRES', 'AVOID'
    dosage_recommendation VARCHAR(255),
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(crop_id, chemical_id, relationship_type)
);
```

### Vector Indexes

```sql
-- ivfflat indexes for fast approximate nearest neighbor search
CREATE INDEX crops_embedding_idx ON crops 
    USING ivfflat (embedding vector_cosine_ops);

CREATE INDEX chemicals_embedding_idx ON chemicals 
    USING ivfflat (embedding vector_cosine_ops);

CREATE INDEX schemes_embedding_idx ON schemes 
    USING ivfflat (embedding vector_cosine_ops);
```

## Embedding Generation

### Using OpenAI text-embedding-3-large

```python
from rivaai.knowledge.embeddings import get_embedding_generator
from rivaai.config.settings import get_settings

settings = get_settings()
embedding_gen = get_embedding_generator(settings)

# Generate single embedding
text = "Wheat crop requires well-drained loamy soil"
embedding = embedding_gen.generate_embedding(text)

# Generate batch embeddings
texts = ["Wheat", "Rice", "Cotton"]
embeddings = embedding_gen.generate_embeddings_batch(texts)
```

### Embedding Strategy

For each entity, we generate embeddings from comprehensive text:

**Crops**: `{name} ({local_names}). Season: {season}. Region: {region}. Soil: {soil_requirements}. Water: {water_requirements}`

**Chemicals**: `{name} - {type}. Safe dosage: {min}-{max} {unit}. Warnings: {warnings}`

**Schemes**: `{name} ({local_names}) - {domain} scheme. Eligibility: {criteria}. Required documents: {docs}. Process: {process}`

## Loading Data

### Programmatic Loading

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

# Load crop
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
```

### Bulk Loading from CSV

```python
import csv
from rivaai.knowledge.models import Scheme
from datetime import datetime

def load_schemes_from_csv(loader, csv_path):
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            scheme = Scheme(
                id=None,
                name=row['name'],
                domain=row['domain'],
                local_names=json.loads(row['local_names']),
                eligibility_criteria=json.loads(row['eligibility_criteria']),
                required_documents=json.loads(row['required_documents']),
                application_process=row['application_process'],
                contact_info=json.loads(row['contact_info']),
                last_updated=datetime.now()
            )
            loader.load_scheme(scheme)
```

## Welfare Schemes Data Source

### myScheme.gov.in Integration

The primary data source for welfare schemes is [myScheme.gov.in](https://www.myscheme.gov.in/), the Government of India's national platform for scheme discovery.

**Key Schemes to Include**:

1. **PM-KISAN** - Direct income support for farmers
2. **Ayushman Bharat (PMJAY)** - Health insurance
3. **National Scholarship Portal** - Education scholarships
4. **PM Awas Yojana** - Housing scheme
5. **MGNREGA** - Rural employment guarantee
6. **Pradhan Mantri Fasal Bima Yojana** - Crop insurance

**Data Collection Process**:

1. Access scheme details from myScheme.gov.in API or web scraping
2. Extract: name, eligibility, documents, process, contact info
3. Translate to supported languages (hi, mr, te, ta, bn)
4. Generate embeddings
5. Load into database

**Update Frequency**: Monthly (schemes change frequently)

## Vector Search Queries

### Semantic Search

```sql
-- Find crops similar to query
SELECT 
    id, 
    name, 
    1 - (embedding <=> '[0.1, 0.2, ...]'::vector) AS similarity
FROM crops
ORDER BY embedding <=> '[0.1, 0.2, ...]'::vector
LIMIT 5;
```

### Hybrid Search (Vector + Graph)

```sql
-- Find crops and related chemicals
WITH crop_matches AS (
    SELECT 
        id,
        name,
        1 - (embedding <=> $1::vector) AS vector_score
    FROM crops
    ORDER BY embedding <=> $1::vector
    LIMIT 5
)
SELECT 
    c.name AS crop_name,
    ch.name AS chemical_name,
    ccr.relationship_type,
    ccr.dosage_recommendation,
    (0.6 * cm.vector_score + 0.4 * 1.0) AS hybrid_score
FROM crop_matches cm
JOIN crop_chemical_relationships ccr ON cm.id = ccr.crop_id
JOIN chemicals ch ON ccr.chemical_id = ch.id
ORDER BY hybrid_score DESC;
```

## Performance Optimization

### Index Tuning

```sql
-- Analyze tables after bulk loading
ANALYZE crops;
ANALYZE chemicals;
ANALYZE schemes;

-- Check index usage
SELECT 
    schemaname,
    tablename,
    indexname,
    idx_scan,
    idx_tup_read,
    idx_tup_fetch
FROM pg_stat_user_indexes
WHERE tablename IN ('crops', 'chemicals', 'schemes');
```

### Query Optimization

```sql
-- Use EXPLAIN ANALYZE to check query plans
EXPLAIN ANALYZE
SELECT * FROM crops
ORDER BY embedding <=> '[...]'::vector
LIMIT 5;

-- Adjust ivfflat lists parameter based on data size
-- Rule of thumb: lists = rows / 1000
ALTER INDEX crops_embedding_idx SET (lists = 100);
```

## Monitoring

### Check Database Size

```sql
SELECT 
    pg_size_pretty(pg_database_size('rivaai')) AS db_size,
    pg_size_pretty(pg_total_relation_size('crops')) AS crops_size,
    pg_size_pretty(pg_total_relation_size('chemicals')) AS chemicals_size,
    pg_size_pretty(pg_total_relation_size('schemes')) AS schemes_size;
```

### Monitor Query Performance

```sql
-- Enable pg_stat_statements extension
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;

-- View slow queries
SELECT 
    query,
    calls,
    mean_exec_time,
    max_exec_time
FROM pg_stat_statements
WHERE query LIKE '%embedding%'
ORDER BY mean_exec_time DESC
LIMIT 10;
```

## Backup and Recovery

### Backup

```bash
# Full database backup
pg_dump -h localhost -U postgres rivaai > rivaai_backup.sql

# Backup with compression
pg_dump -h localhost -U postgres rivaai | gzip > rivaai_backup.sql.gz

# Backup specific tables
pg_dump -h localhost -U postgres -t crops -t chemicals -t schemes rivaai > knowledge_base_backup.sql
```

### Restore

```bash
# Restore from backup
psql -h localhost -U postgres rivaai < rivaai_backup.sql

# Restore from compressed backup
gunzip -c rivaai_backup.sql.gz | psql -h localhost -U postgres rivaai
```

## Troubleshooting

### pgvector Extension Not Found

```bash
# Install pgvector
git clone https://github.com/pgvector/pgvector.git
cd pgvector
make
sudo make install

# Enable in database
psql -h localhost -U postgres -d rivaai -c "CREATE EXTENSION vector;"
```

### Slow Vector Queries

1. Ensure indexes are created: `\d+ crops`
2. Analyze tables: `ANALYZE crops;`
3. Increase `lists` parameter for larger datasets
4. Consider using HNSW index (pgvector 0.5.0+) for better performance

### Embedding Generation Failures

1. Check OpenAI API key: `echo $OPENAI_API_KEY`
2. Verify API quota and rate limits
3. Check network connectivity
4. Review error logs: `tail -f logs/rivaai.log`

## Next Steps

After setting up the knowledge base:

1. Implement Retrieval Layer (Task 7.3)
2. Add graph traversal for related entities
3. Implement semantic caching with Redis
4. Load production data for all domains
5. Set up automated data updates

## References

- [pgvector Documentation](https://github.com/pgvector/pgvector)
- [OpenAI Embeddings API](https://platform.openai.com/docs/guides/embeddings)
- [myScheme.gov.in](https://www.myscheme.gov.in/)
- [PostgreSQL Performance Tuning](https://www.postgresql.org/docs/current/performance-tips.html)
