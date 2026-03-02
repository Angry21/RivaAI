# Complete knowledge base setup script for Windows using Docker
# This script sets up PostgreSQL with pgvector, creates schema, and loads sample data

$ErrorActionPreference = "Stop"

Write-Host "=========================================" -ForegroundColor Cyan
Write-Host "RivaAI Knowledge Base Setup (Docker)" -ForegroundColor Cyan
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host ""

# Check if Docker containers are running
Write-Host "1. Checking Docker containers..." -ForegroundColor Yellow
$postgresRunning = docker ps --filter "name=rivaai-postgres" --filter "status=running" --format "{{.Names}}"
if (-not $postgresRunning) {
    Write-Host "   [ERROR] PostgreSQL container is not running" -ForegroundColor Red
    Write-Host "   Please start containers using: docker-compose up -d" -ForegroundColor Yellow
    exit 1
}
Write-Host "   [OK] PostgreSQL container is running" -ForegroundColor Green
Write-Host ""

# Wait for PostgreSQL to be ready
Write-Host "2. Waiting for PostgreSQL to be ready..." -ForegroundColor Yellow
$maxAttempts = 30
$attempt = 0
while ($attempt -lt $maxAttempts) {
    $ready = docker exec rivaai-postgres pg_isready -U postgres 2>&1
    if ($ready -match "accepting connections") {
        Write-Host "   [OK] PostgreSQL is ready" -ForegroundColor Green
        break
    }
    $attempt++
    Start-Sleep -Seconds 1
}
if ($attempt -eq $maxAttempts) {
    Write-Host "   [ERROR] PostgreSQL did not become ready in time" -ForegroundColor Red
    exit 1
}
Write-Host ""

# Check if database exists, create if not
Write-Host "3. Checking database..." -ForegroundColor Yellow
$dbExists = docker exec rivaai-postgres psql -U postgres -lqt 2>&1 | Select-String -Pattern "rivaai"
if (-not $dbExists) {
    Write-Host "   Creating database 'rivaai'..." -ForegroundColor Yellow
    docker exec rivaai-postgres psql -U postgres -c "CREATE DATABASE rivaai;" | Out-Null
    Write-Host "   [OK] Database created" -ForegroundColor Green
} else {
    Write-Host "   [OK] Database 'rivaai' exists" -ForegroundColor Green
}
Write-Host ""

# Run schema initialization
Write-Host "4. Initializing database schema..." -ForegroundColor Yellow
Get-Content scripts/init_database.sql | docker exec -i rivaai-postgres psql -U postgres -d rivaai | Out-Null
Write-Host "   [OK] Schema initialized" -ForegroundColor Green
Write-Host ""

# Load sample data
Write-Host "5. Loading sample data with embeddings..." -ForegroundColor Yellow
& python scripts/load_knowledge_base.py
if ($LASTEXITCODE -ne 0) {
    Write-Host "   [ERROR] Failed to load sample data" -ForegroundColor Red
    exit 1
}
Write-Host "   [OK] Sample data loaded" -ForegroundColor Green
Write-Host ""

# Verify setup
Write-Host "6. Verifying setup..." -ForegroundColor Yellow
$cropCount = docker exec rivaai-postgres psql -U postgres -d rivaai -t -c 'SELECT COUNT(*) FROM crops;' 2>&1 | Select-String -Pattern '\d+' | ForEach-Object { $_.Matches.Value }
$chemicalCount = docker exec rivaai-postgres psql -U postgres -d rivaai -t -c 'SELECT COUNT(*) FROM chemicals;' 2>&1 | Select-String -Pattern '\d+' | ForEach-Object { $_.Matches.Value }
$schemeCount = docker exec rivaai-postgres psql -U postgres -d rivaai -t -c 'SELECT COUNT(*) FROM schemes;' 2>&1 | Select-String -Pattern '\d+' | ForEach-Object { $_.Matches.Value }
$knowledgeCount = docker exec rivaai-postgres psql -U postgres -d rivaai -t -c 'SELECT COUNT(*) FROM knowledge_items;' 2>&1 | Select-String -Pattern '\d+' | ForEach-Object { $_.Matches.Value }

Write-Host "   Crops: $cropCount" -ForegroundColor Cyan
Write-Host "   Chemicals: $chemicalCount" -ForegroundColor Cyan
Write-Host "   Schemes: $schemeCount" -ForegroundColor Cyan
Write-Host "   Knowledge Items: $knowledgeCount" -ForegroundColor Cyan
Write-Host ""

Write-Host "=========================================" -ForegroundColor Cyan
Write-Host "[SUCCESS] Knowledge Base Setup Complete!" -ForegroundColor Green
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "1. Ensure .env file has OPENAI_API_KEY set" -ForegroundColor White
Write-Host "2. Run verification: python scripts/verify_knowledge_base.py" -ForegroundColor White
Write-Host "3. Test retrieval: python examples/retrieval_example.py" -ForegroundColor White
Write-Host ""
