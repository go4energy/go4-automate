#!/bin/bash
# go4-automate – Database Backup Script
set -euo pipefail

BACKUP_DIR="./backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

mkdir -p "$BACKUP_DIR"

echo "=== go4-automate Backup ==="
echo "Zeitstempel: $TIMESTAMP"

# PostgreSQL App-Datenbank Backup
echo "Erstelle PostgreSQL Backup (go4automate)..."
BACKUP_FILE="${BACKUP_DIR}/go4automate_${TIMESTAMP}.sql.gz"
docker exec go4-postgres pg_dump -U postgres go4automate | gzip > "$BACKUP_FILE"
echo "Backup gespeichert: $BACKUP_FILE"
SIZE=$(du -sh "$BACKUP_FILE" | cut -f1)
echo "Größe: $SIZE"

# n8n Datenbank Backup
echo "Erstelle PostgreSQL Backup (n8n)..."
N8N_BACKUP="${BACKUP_DIR}/n8n_${TIMESTAMP}.sql.gz"
docker exec go4-postgres pg_dump -U postgres n8n | gzip > "$N8N_BACKUP"
echo "Backup gespeichert: $N8N_BACKUP"
N8N_SIZE=$(du -sh "$N8N_BACKUP" | cut -f1)
echo "Größe: $N8N_SIZE"

# Alte Backups aufräumen (älter als 30 Tage)
echo "Räume alte Backups auf (>30 Tage)..."
find "$BACKUP_DIR" -name "*.sql.gz" -mtime +30 -delete 2>/dev/null || true

BACKUP_COUNT=$(find "$BACKUP_DIR" -name "*.sql.gz" | wc -l)
echo "Aktuelle Backups: $BACKUP_COUNT"

echo "=== Backup abgeschlossen ==="
