#!/bin/bash
# go4-automate – Project Setup Script
set -euo pipefail

echo "=== go4-automate Setup ==="
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

check() {
    if command -v "$1" &> /dev/null; then
        echo -e "${GREEN}[OK]${NC} $1 gefunden: $($1 --version 2>&1 | head -1)"
    else
        echo -e "${RED}[FEHLT]${NC} $1 nicht gefunden. Bitte installieren."
        return 1
    fi
}

echo "1. Prüfe Voraussetzungen..."
check python3
check node
check docker
check git
echo ""

echo "2. Backend Setup..."
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install --quiet -r requirements.txt
echo -e "${GREEN}[OK]${NC} Backend Dependencies installiert"
cd ..
echo ""

echo "3. Frontend Setup..."
cd frontend
npm ci --silent
echo -e "${GREEN}[OK]${NC} Frontend Dependencies installiert"
cd ..
echo ""

echo "4. Environment..."
if [ ! -f config/.env ]; then
    cp .env.example config/.env
    echo -e "${YELLOW}[INFO]${NC} config/.env erstellt aus .env.example"
    echo -e "${YELLOW}[INFO]${NC} Bitte config/.env mit echten Werten befüllen!"
else
    echo -e "${GREEN}[OK]${NC} config/.env existiert bereits"
fi

# Tenant-Konfiguration
mkdir -p config/tenants config/templates/follow-up
if [ ! -f config/tenants/default.env ]; then
    echo -e "${YELLOW}[INFO]${NC} Tenant-Config default.env bereits vorhanden"
fi
echo ""

echo "5. Docker Services starten..."
docker compose -f docker/docker-compose.yml up -d
echo ""

echo "6. Warte auf Datenbank..."
sleep 10

echo "7. Alembic Migration..."
cd backend
source .venv/bin/activate
alembic upgrade head 2>/dev/null && echo -e "${GREEN}[OK]${NC} Migrationen ausgeführt" || echo -e "${YELLOW}[INFO]${NC} Migrationen übersprungen (DB nicht erreichbar)"
cd ..
echo ""

echo "8. Healthcheck..."
if curl -sf http://localhost:8000/health > /dev/null; then
    echo -e "${GREEN}[OK]${NC} Backend ist healthy"
else
    echo -e "${RED}[FEHLER]${NC} Backend antwortet nicht"
fi
echo ""

echo "=== Setup abgeschlossen ==="
echo "Backend:  http://localhost:8000"
echo "API Docs: http://localhost:8000/docs"
echo "Frontend: http://localhost:5173 (dev) / http://localhost:80 (docker)"
echo "n8n:      http://localhost:5678"
