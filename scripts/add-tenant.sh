#!/bin/bash
# go4-automate – Add New Tenant Script
set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

if [ $# -lt 2 ]; then
    echo "Usage: $0 <tenant_id> <tenant_name>"
    echo "Example: $0 kunde2 'Neue Firma GmbH'"
    exit 1
fi

TENANT_ID="$1"
TENANT_NAME="$2"
CONFIG_DIR="config/tenants"
API_URL="${API_URL:-http://localhost:8000}"

echo "=== Neuer Tenant: $TENANT_ID ==="

# 1. Tenant-Config erstellen
if [ -f "${CONFIG_DIR}/${TENANT_ID}.env" ]; then
    echo -e "${YELLOW}[INFO]${NC} Config ${CONFIG_DIR}/${TENANT_ID}.env existiert bereits"
else
    cp "${CONFIG_DIR}/default.env" "${CONFIG_DIR}/${TENANT_ID}.env"
    sed -i "s/^TENANT_ID=.*/TENANT_ID=${TENANT_ID}/" "${CONFIG_DIR}/${TENANT_ID}.env"
    sed -i "s/^TENANT_NAME=.*/TENANT_NAME=${TENANT_NAME}/" "${CONFIG_DIR}/${TENANT_ID}.env"
    echo -e "${GREEN}[OK]${NC} Config erstellt: ${CONFIG_DIR}/${TENANT_ID}.env"
    echo -e "${YELLOW}[INFO]${NC} Bitte ${CONFIG_DIR}/${TENANT_ID}.env anpassen!"
fi

# 2. Via API registrieren
echo "Registriere Tenant via API..."
RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "${API_URL}/api/v1/tenants" \
    -H "Content-Type: application/json" \
    -d "{\"tenant_id\": \"${TENANT_ID}\", \"tenant_name\": \"${TENANT_NAME}\"}")

HTTP_CODE=$(echo "$RESPONSE" | tail -1)
BODY=$(echo "$RESPONSE" | sed '$d')

if [ "$HTTP_CODE" = "201" ]; then
    echo -e "${GREEN}[OK]${NC} Tenant registriert"
elif [ "$HTTP_CODE" = "409" ]; then
    echo -e "${YELLOW}[INFO]${NC} Tenant existiert bereits in DB"
else
    echo -e "${RED}[FEHLER]${NC} API-Fehler (HTTP $HTTP_CODE): $BODY"
fi

echo ""
echo "=== Tenant-Setup abgeschlossen ==="
echo "Config: ${CONFIG_DIR}/${TENANT_ID}.env"
echo "Test:   curl -H 'X-Tenant-ID: ${TENANT_ID}' ${API_URL}/api/v1/leads"
