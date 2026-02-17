# Setup-Anleitung

## Voraussetzungen

### Server
- Hetzner Cloud VPS: CX31 oder besser (4 vCPU, 8 GB RAM, 80 GB SSD)
- Ubuntu 24.04 LTS
- Eigene Domain (z.B. automate.go4.energy)
- DNS A-Record zeigt auf Server-IP

### Lokale Entwicklung
- Docker Desktop + Docker Compose
- Git
- Node.js 20+ (für Frontend-Entwicklung)
- Python 3.12+ (für Backend-Entwicklung)

### Accounts & API-Keys
Bevor du startest, brauchst du folgende Accounts (Details in [CREDENTIALS.md](CREDENTIALS.md)):

| Account | Wofür | Dauer |
|---|---|---|
| Meta Business Manager | Facebook/Instagram Posting + Ads | ~30 Min |
| Meta Developer Account | Graph API Zugang | ~15 Min |
| Anthropic Account | Claude API für Content-Generierung | ~5 Min |
| OpenWeather Account | Wetterdaten für Ad-Boost | ~5 Min |
| Hetzner Cloud Account | Server-Hosting | ~10 Min |

## Installation (Server)

### 1. Server vorbereiten

```bash
# Als root einloggen
ssh root@DEINE_SERVER_IP

# System updaten
apt update && apt upgrade -y

# Benutzer anlegen
adduser go4
usermod -aG sudo go4
usermod -aG docker go4

# Docker installieren
curl -fsSL https://get.docker.com | sh

# Docker Compose (V2 ist bei Docker dabei)
docker compose version  # sollte 2.x zeigen

# Firewall konfigurieren
ufw allow OpenSSH
ufw allow 80
ufw allow 443
ufw enable

# SSH-Key Only (Passwort-Login deaktivieren)
nano /etc/ssh/sshd_config
# → PasswordAuthentication no
systemctl restart sshd

# Fail2ban für Brute-Force-Schutz
apt install -y fail2ban
systemctl enable fail2ban
```

### 2. Projekt klonen und konfigurieren

```bash
# Als go4-Benutzer
su - go4

# Repo klonen
git clone https://github.com/go4energy/go4-automate.git /opt/go4.automate
cd /opt/go4.automate

# Hauptkonfiguration anlegen
cp .env.example config/.env
nano config/.env
```

### 3. Hauptkonfiguration (.env)

```bash
# ============================================================
# go4.automate – Hauptkonfiguration
# ============================================================

# ---- Allgemein ----
APP_ENV=production
APP_DOMAIN=automate.go4.energy
APP_SECRET_KEY=<zufälligen-string-generieren>

# ---- PostgreSQL ----
POSTGRES_USER=go4
POSTGRES_PASSWORD=<sicheres-passwort>
POSTGRES_DB=go4automate
DATABASE_URL=postgresql+asyncpg://go4:<passwort>@postgres:5432/go4automate

# ---- Redis ----
REDIS_URL=redis://redis:6379/0

# ---- n8n ----
N8N_BASIC_AUTH_USER=admin
N8N_BASIC_AUTH_PASSWORD=<sicheres-passwort>
N8N_HOST=automate.go4.energy
N8N_PROTOCOL=https
N8N_ENCRYPTION_KEY=<zufälligen-string-generieren>
DB_TYPE=postgresdb
DB_POSTGRESDB_HOST=postgres
DB_POSTGRESDB_DATABASE=go4automate_n8n
DB_POSTGRESDB_USER=go4
DB_POSTGRESDB_PASSWORD=<passwort>

# ---- Meta / Facebook / Instagram ----
META_APP_ID=<deine-app-id>
META_APP_SECRET=<dein-app-secret>
META_SYSTEM_USER_TOKEN=<system-user-token>
META_PAGE_ID=429505256907828
META_INSTAGRAM_BUSINESS_ID=17841470139313765
META_PIXEL_ID=<deine-pixel-id>
META_AD_ACCOUNT_ID=act_XXXXXXXXX
META_API_VERSION=v21.0

# ---- Anthropic (Claude) ----
ANTHROPIC_API_KEY=sk-ant-...

# ---- OpenAI (optional, für Scoring/Klassifikation) ----
OPENAI_API_KEY=sk-...

# ---- OpenWeather ----
OPENWEATHER_API_KEY=<dein-api-key>

# ---- E-Mail (Brevo/Sendinblue) ----
SMTP_HOST=smtp-relay.brevo.com
SMTP_PORT=587
SMTP_USER=<dein-brevo-login>
SMTP_PASSWORD=<dein-smtp-password>
EMAIL_FROM=noreply@go4.energy
EMAIL_FROM_NAME="Go4 Energy"

# ---- Active Tenant (default) ----
ACTIVE_TENANT=go4energy
```

### 4. Ersten Tenant konfigurieren

```bash
cp config/tenants/default.env config/tenants/go4energy.env
nano config/tenants/go4energy.env
```

Inhalt: siehe [TENANT-CONFIG.md](TENANT-CONFIG.md)

### 5. Container starten

```bash
cd /opt/go4.automate

# Alle Container bauen und starten
docker compose -f docker/docker-compose.yml up -d --build

# Logs prüfen
docker compose -f docker/docker-compose.yml logs -f

# Einzelne Services prüfen
docker compose -f docker/docker-compose.yml ps
```

### 6. Datenbank initialisieren

```bash
# Alembic-Migrationen ausführen
docker compose -f docker/docker-compose.yml exec backend alembic upgrade head

# Prüfen ob Tabellen erstellt wurden
docker compose -f docker/docker-compose.yml exec postgres \
  psql -U go4 -d go4automate -c "\dt"
```

### 7. n8n einrichten

1. Browser: `https://automate.go4.energy` (oder deine Domain)
2. Login mit den Credentials aus `.env`
3. Workflows importieren:
   - Einstellungen → Workflows → Import
   - Dateien aus `n8n/workflows/` nacheinander importieren
4. In jedem Workflow die Variablen prüfen:
   - Backend-URL: `http://backend:3001`
   - X-Tenant-ID Header: `go4energy`
5. Workflows aktivieren

### 8. Meta Pixel installieren

Das Pixel-Snippet muss auf der Kunden-Website eingebaut werden:

```bash
# Snippet generieren
curl https://automate.go4.energy/api/ads/pixel-snippet?tenant_id=go4energy
```

Das generierte JavaScript in den `<head>`-Bereich jeder Seite einbauen. Details in [META-API-SETUP.md](META-API-SETUP.md).

### 9. Prüfen ob alles läuft

```bash
# Backend-Health
curl https://automate.go4.energy/api/health

# n8n erreichbar
curl -I https://automate.go4.energy

# Manuell einen Post generieren
curl -X POST https://automate.go4.energy/api/content/generate \
  -H "Content-Type: application/json" \
  -H "X-Tenant-ID: go4energy" \
  -d '{"content_type": "post", "platform": "facebook"}'
```

## Installation (Lokale Entwicklung)

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Lokale DB (Docker)
docker run -d --name go4-postgres \
  -e POSTGRES_USER=go4 \
  -e POSTGRES_PASSWORD=dev123 \
  -e POSTGRES_DB=go4automate \
  -p 5432:5432 postgres:16

# .env für lokale Entwicklung
cp .env.dev.example .env

# Migrationen
alembic upgrade head

# Server starten
uvicorn app.main:app --reload --port 3001
```

### Frontend

```bash
cd frontend
npm install
npm run dev
# → http://localhost:5173
```

### n8n (lokal)

```bash
docker run -d --name go4-n8n \
  -p 5678:5678 \
  -e N8N_BASIC_AUTH_ACTIVE=true \
  -e N8N_BASIC_AUTH_USER=admin \
  -e N8N_BASIC_AUTH_PASSWORD=dev123 \
  n8nio/n8n
```

## Updates

```bash
cd /opt/go4.automate

# Code aktualisieren
git pull origin main

# Container neu bauen
docker compose -f docker/docker-compose.yml up -d --build

# Migrationen ausführen (falls neue)
docker compose -f docker/docker-compose.yml exec backend alembic upgrade head
```

## Backup

```bash
# Manuelles Backup
./scripts/backup.sh

# Automatisches tägliches Backup (Cronjob)
crontab -e
# 0 3 * * * /opt/go4.automate/scripts/backup.sh
```

Das Backup-Script sichert die PostgreSQL-Datenbank, n8n-Daten und Konfigurationsdateien nach `/opt/go4.automate/data/backups/`.

## Troubleshooting

| Problem | Lösung |
|---|---|
| Container startet nicht | `docker compose logs <service>` prüfen |
| DB-Verbindung fehlgeschlagen | Passwort in .env prüfen, PostgreSQL Container läuft? |
| n8n "Bad Gateway" | Container-Name prüfen, internes Netzwerk ok? |
| Meta API Fehler 190 | Token abgelaufen → neuen System User Token generieren |
| "Tenant not found" | Tenant-Datei unter `config/tenants/` prüfen |
| HTTPS funktioniert nicht | DNS A-Record prüfen, Port 80+443 offen? |
