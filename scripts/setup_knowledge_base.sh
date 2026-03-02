#!/bin/bash
# Complete knowledge base setup script
# This script sets up PostgreSQL with pgvector, creates schema, and loads sample data

set -e  # Exit on error

echo "========================================="
echo "RivaAI Knowledge Base Setup"
echo "========================================="
echo ""

# Check if PostgreSQL is running
echo "1. Checking PostgreSQL..."
if ! pg_isready -h localhost -p 5432 > /dev/null 2>&1; then
    echo "   ✗ PostgreSQL is not running on localhost:5432"
    echo "   Please start PostgreSQL using: docker-compose up -d"
    exit 1
fi
echo "   ✓ PostgreSQL is running"
echo ""

# Check if database exists, create if not
echo "2. Checking database..."
if ! psql -h localhost -U postgres -lqt | cut -d \| -f 1 | grep -qw rivaai; then
    echo "   Creating database 'rivaai'..."
    psql -h localhost -U postgres -c "CREATE DATABASE rivaai;"
    echo "   ✓ Database created"
else
    echo "   ✓ Database 'rivaai' exists"
fi
echo ""

# Run schema initialization
echo "3. Initializing database schema..."
psql -h localhost -U postgres -d rivaai -f scripts/init_database.sql
echo "   ✓ Schema initialized"
echo ""

# Load sample data
echo "4. Loading sample data with embeddings..."
python scripts/load_knowledge_base.py
echo "   ✓ Sample data loaded"
echo ""

# Verify setup
echo "5. Verifying setup..."
CROP_COUNT=$(psql -h localhost -U postgres -d rivaai -t -c "SELECT COUNT(*) FROM crops;")
CHEMICAL_COUNT=$(psql -h localhost -U postgres -d rivaai -t -c "SELECT COUNT(*) FROM chemicals;")
SCHEME_COUNT=$(psql -h localhost -U postgres -d rivaai -t -c "SELECT COUNT(*) FROM schemes;")
KNOWLEDGE_COUNT=$(psql -h localhost -U postgres -d rivaai -t -c "SELECT COUNT(*) FROM knowledge_items;")

echo "   Crops: $CROP_COUNT"
echo "   Chemicals: $CHEMICAL_COUNT"
echo "   Schemes: $SCHEME_COUNT"
echo "   Knowledge Items: $KNOWLEDGE_COUNT"
echo ""

echo "========================================="
echo "✓ Knowledge Base Setup Complete!"
echo "========================================="
echo ""
echo "Next steps:"
echo "1. Ensure .env file has OPENAI_API_KEY set"
echo "2. Run the application: make run"
echo "3. Test retrieval: python examples/retrieval_example.py"
echo ""
