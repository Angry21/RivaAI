# Complete knowledge base setup script for Windows
# This script sets up PostgreSQL with pgvector, creates schema, and loads sample data

$ErrorActionPreference = "Stop"

Write-Host "=========================================" -ForegroundColor Cyan
Write-Host "RivaAI Knowledge Base Setup" -ForegroundColor Cyan
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host ""

# Check if PostgreSQL is running
Write-Host "1. Checking PostgreSQL..." -ForegroundColor Yellow
try {
    $null = & pg_isready -h localhost -p 5432 2>&1
    Write-Host "   [OK] PostgreSQL is running" -ForegroundColor Green
} catch {
    Write-Host "   [ERROR] PostgreSQL is not running on localhost:5432" -ForegroundColor Red
    Write-Host "   Please start PostgreSQL using: docker-compose up -d" -ForegroundColor Yellow
    exit 1
}
Write-Host ""

# Check if database exists, create if not
Write-Host "2. Checking database..." -ForegroundColor Yellow
$dbExists = & psql -h localhost -U postgres -lqt | Select-String -Pattern "rivaai"
if (-not $dbExists) {
    Write-Host "   Creating database 'rivaai'..." -ForegroundColor Yellow
    & psql -h localhost -U postgres -c "CREATE DATABASE rivaai;"
    Write-Host "   [OK] Database created" -ForegroundColor Green
} else {
    Write-Host "   [OK] Database 'rivaai' exists" -ForegroundColor Green
}
Write-Host ""

# Run schema initialization
Write-Host "3. Initializing database schema..." -ForegroundColor Yellow
& psql -h localhost -U postgres -d rivaai -f scripts/init_database.sql
Write-Host "   [OK] Schema initialized" -ForegroundColor Green
Write-Host ""

# Load sample data
Write-Host "4. Loading sample data with embeddings..." -ForegroundColor Yellow
& python scripts/load_knowledge_base.py
Write-Host "   [OK] Sample data loaded" -ForegroundColor Green
Write-Host ""

# Verify setup
Write-Host "5. Verifying setup..." -ForegroundColor Yellow
$cropCount = & psql -h localhost -U postgres -d rivaai -t -c 'SELECT COUNT(*) FROM crops;'
$chemicalCount = & psql -h localhost -U postgres -d rivaai -t -c 'SELECT COUNT(*) FROM chemicals;'
$schemeCount = & psql -h localhost -U postgres -d rivaai -t -c 'SELECT COUNT(*) FROM schemes;'
$knowledgeCount = & psql -h localhost -U postgres -d rivaai -t -c 'SELECT COUNT(*) FROM knowledge_items;'

Write-Host "   Crops: $($cropCount.Trim())" -ForegroundColor Cyan
Write-Host "   Chemicals: $($chemicalCount.Trim())" -ForegroundColor Cyan
Write-Host "   Schemes: $($schemeCount.Trim())" -ForegroundColor Cyan
Write-Host "   Knowledge Items: $($knowledgeCount.Trim())" -ForegroundColor Cyan
Write-Host ""

Write-Host "=========================================" -ForegroundColor Cyan
Write-Host "[SUCCESS] Knowledge Base Setup Complete!" -ForegroundColor Green
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "1. Ensure .env file has OPENAI_API_KEY set" -ForegroundColor White
Write-Host "2. Run the application: make run" -ForegroundColor White
Write-Host "3. Test retrieval: python examples/retrieval_example.py" -ForegroundColor White
Write-Host ""
