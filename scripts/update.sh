#!/bin/bash
# go4-automate – Update/Deploy Script
set -euo pipefail

echo "=== go4-automate Update ==="
echo ""

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# 1. Backup
echo "1. Erstelle Backup..."
bash scripts/backup.sh
echo ""

# 2. Pull latest code
echo "2. Pull latest code..."
git pull origin main
echo ""

# 3. Rebuild und starten
echo "3. Rebuild und starten..."
docker compose -f docker/docker-compose.yml up -d --build
echo ""

# 4. Warte auf Healthchecks
echo "4. Warte auf Healthchecks..."
sleep 15

# 5. Alembic Migration
echo "5. Alembic Migration..."
docker exec go4-backend alembic upgrade head 2>/dev/null && \
    echo -e "${GREEN}[OK]${NC} Migrationen ausgeführt" || \
    echo -e "${YELLOW}[WARNUNG]${NC} Migrationen fehlgeschlagen"
echo ""

# 6. Smoke-Test
echo "6. Smoke-Test..."
if curl -sf http://localhost:8000/health > /dev/null; then
    echo -e "${GREEN}[OK]${NC} Backend healthy"
else
    echo -e "${RED}[FEHLER]${NC} Backend nicht erreichbar!"
    echo "Rollback: docker compose -f docker/docker-compose.yml down && git checkout HEAD~1"
    exit 1
fi

if curl -sf http://localhost:8081 > /dev/null; then
    echo -e "${GREEN}[OK]${NC} Frontend healthy"
else
    echo -e "${YELLOW}[WARNUNG]${NC} Frontend nicht erreichbar"
fi

if curl -sf http://localhost:5678/healthz > /dev/null; then
    echo -e "${GREEN}[OK]${NC} n8n healthy"
else
    echo -e "${YELLOW}[WARNUNG]${NC} n8n nicht erreichbar"
fi

echo ""
echo "=== Update abgeschlossen ==="
