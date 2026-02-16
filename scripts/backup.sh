#!/bin/bash
# go4-automate – Database Backup Script
set -euo pipefail

BACKUP_DIR="./backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="${BACKUP_DIR}/go4automate_${TIMESTAMP}.sql.gz"

mkdir -p "$BACKUP_DIR"

echo "=== go4-automate Backup ==="
echo "Zeitstempel: $TIMESTAMP"

# PostgreSQL Backup
echo "Erstelle PostgreSQL Backup..."
docker exec go4-postgres pg_dump -U postgres go4automate | gzip > "$BACKUP_FILE"
echo "Backup gespeichert: $BACKUP_FILE"

# Größe anzeigen
SIZE=$(du -sh "$BACKUP_FILE" | cut -f1)
echo "Größe: $SIZE"

# Alte Backups aufräumen (älter als 30 Tage)
echo "Räume alte Backups auf (>30 Tage)..."
find "$BACKUP_DIR" -name "*.sql.gz" -mtime +30 -delete 2>/dev/null || true

BACKUP_COUNT=$(find "$BACKUP_DIR" -name "*.sql.gz" | wc -l)
echo "Aktuelle Backups: $BACKUP_COUNT"

echo "=== Backup abgeschlossen ==="
