# go4-automate auf DGX Spark (GB10)

Setup-Dokumentation für die Installation auf NVIDIA DGX Spark mit Grace Blackwell (GB10).

## System-Info

| Komponente | Wert |
|------------|------|
| **Hardware** | NVIDIA DGX Spark (GB10) |
| **CPU** | ARM64 (Grace) |
| **GPU** | NVIDIA Blackwell |
| **OS** | Ubuntu 24.04.3 LTS |
| **CUDA** | 13.0 |
| **Python** | 3.12 |
| **Lokale IP** | 192.168.1.227 |

## Services Übersicht

| Service | Port | Typ | URL |
|---------|------|-----|-----|
| Frontend | 8081 | Native (Vite Dev) | https://automate.go4.energy |
| Backend | 8002 | Native (uvicorn) | intern |
| PostgreSQL | 5432 | Docker | intern |
| Redis | 6380 | Docker | intern |
| n8n | 5678 | Docker | https://n8n.go4.energy |
| XTTS | 8020 | Native (GPU) | intern |
| nginx | 80/443 | Native | Reverse Proxy |

## Voraussetzungen

```bash
# System-Pakete
sudo apt update
sudo apt install -y \
    python3.12-venv \
    portaudio19-dev \
    certbot \
    python3-certbot-nginx \
    nginx

# Rust (für XTTS Dependencies)
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
source ~/.cargo/env

# Docker (falls nicht vorhanden)
# https://docs.docker.com/engine/install/ubuntu/
```

## 1. Repository klonen

```bash
cd /opt
git clone <repo-url> go4-automate
cd go4-automate
```

## 2. Docker Services starten

```bash
# docker-compose.yml ist unter docker/
cd /opt/go4-automate/docker

# Services starten (Postgres, Redis, n8n)
docker compose up -d postgres redis n8n

# Status prüfen
docker compose ps
```

**Wichtig:** XTTS läuft nativ (nicht als Container) für bessere GPU-Performance.

## 3. Datenbank importieren

```bash
# Backup importieren
docker exec -i go4-postgres psql -U postgres -d go4automate < /tmp/go4automate.sql

# n8n Workflows importieren (falls vorhanden)
docker cp /tmp/n8n-workflows.json go4-n8n:/tmp/workflows.json
docker exec go4-n8n n8n import:workflow --input=/tmp/workflows.json
```

## 4. Backend Setup

```bash
cd /opt/go4-automate/backend

# Virtual Environment erstellen
python3 -m venv .venv
source .venv/bin/activate

# Dependencies installieren
pip install -r requirements.txt

# .env konfigurieren (siehe .env.example)
# Wichtig:
#   DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/go4automate
#   REDIS_URL=redis://localhost:6380/0
#   TTS_ENGINE=xtts
#   XTTS_URL=http://localhost:8020
```

### Backend starten

```bash
cd /opt/go4-automate/backend
source .venv/bin/activate
nohup uvicorn app.main:app --host 0.0.0.0 --port 8002 > /opt/go4-automate/logs/backend.log 2>&1 &
```

## 5. Frontend Setup

```bash
cd /opt/go4-automate/frontend

# Dependencies installieren
npm install

# vite.config.js prüfen:
#   server.port: 8081
#   proxy '/api' -> http://localhost:8002
```

### Frontend starten

```bash
cd /opt/go4-automate/frontend
nohup npm run dev > /opt/go4-automate/logs/frontend.log 2>&1 &
```

## 6. XTTS Setup (Native GPU)

```bash
# XTTS Virtual Environment
mkdir -p ~/xtts-server
python3 -m venv ~/xtts-server/.venv
source ~/xtts-server/.venv/bin/activate

# requirements.txt erstellen
cat > ~/xtts-server/requirements.txt << 'EOF'
torch==2.5.1
torchaudio==2.5.1
xtts-api-server>=0.8.0
EOF

# Installieren (dauert, PyTorch ist groß)
pip install -r ~/xtts-server/requirements.txt
```

**Wichtig:** PyTorch 2.5.1 verwenden! Neuere Versionen (2.6+) haben Kompatibilitätsprobleme mit XTTS.

### XTTS starten

```bash
source ~/xtts-server/.venv/bin/activate
nohup python -m xtts_api_server --host 0.0.0.0 --port 8020 > ~/xtts-server/xtts.log 2>&1 &

# Beim ersten Start werden Modelle heruntergeladen (~2 GB)
# Status prüfen:
curl http://localhost:8020/languages
```

## 7. nginx Reverse Proxy

### Configs erstellen

**/opt/go4-automate/config/nginx-go4automate.conf:**
```nginx
server {
    listen 80;
    server_name automate.go4.energy;

    location /.well-known/acme-challenge/ {
        root /var/www/html;
    }

    location / {
        proxy_pass http://127.0.0.1:8081;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_read_timeout 300s;
        client_max_body_size 100M;
    }
}
```

**/opt/go4-automate/config/nginx-n8n.conf:**
```nginx
server {
    listen 80;
    server_name n8n.go4.energy;

    location /.well-known/acme-challenge/ {
        root /var/www/html;
    }

    location / {
        proxy_pass http://127.0.0.1:5678;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_read_timeout 300s;
        client_max_body_size 100M;
    }
}
```

### Aktivieren

```bash
sudo ln -s /opt/go4-automate/config/nginx-go4automate.conf /etc/nginx/sites-enabled/go4automate
sudo ln -s /opt/go4-automate/config/nginx-n8n.conf /etc/nginx/sites-enabled/n8n
sudo nginx -t
sudo systemctl reload nginx
```

## 8. SSL Zertifikate (Let's Encrypt)

```bash
# Verzeichnis für ACME Challenge
sudo mkdir -p /var/www/html/.well-known/acme-challenge

# Zertifikate holen
sudo certbot --nginx -d automate.go4.energy -d n8n.go4.energy

# Certbot passt die nginx Configs automatisch an
```

## 9. DNS Konfiguration

A-Records setzen:
```
automate.go4.energy  →  <öffentliche IP>
n8n.go4.energy       →  <öffentliche IP>
```

**Wichtig:** Keine AAAA-Records (IPv6) setzen, oder auf korrekte IPv6 zeigen lassen.

## 10. Router Port-Forwarding (UniFi)

| Extern | Intern | Protokoll |
|--------|--------|-----------|
| 80 | 80 | TCP |
| 443 | 443 | TCP |
| 5678 | 5678 | TCP (optional, für n8n direkt) |

Ziel-IP: 192.168.1.227

## Services Management

### Alle Services starten

```bash
# Docker Services
cd /opt/go4-automate/docker
docker compose up -d

# Backend
cd /opt/go4-automate/backend
source .venv/bin/activate
nohup uvicorn app.main:app --host 0.0.0.0 --port 8002 > /opt/go4-automate/logs/backend.log 2>&1 &

# Frontend
cd /opt/go4-automate/frontend
nohup npm run dev > /opt/go4-automate/logs/frontend.log 2>&1 &

# XTTS
source ~/xtts-server/.venv/bin/activate
nohup python -m xtts_api_server --host 0.0.0.0 --port 8020 > ~/xtts-server/xtts.log 2>&1 &
```

### Status prüfen

```bash
# Docker
docker compose -f /opt/go4-automate/docker/docker-compose.yml ps

# Prozesse
ps aux | grep -E "uvicorn|vite|xtts" | grep -v grep

# Ports
ss -tlnp | grep -E ":(80|443|5678|6380|8002|8020|8081) "

# Health Checks
curl -s http://localhost:8002/health          # Backend
curl -s http://localhost:8020/languages       # XTTS
curl -s http://localhost:8081                 # Frontend
```

### Logs

```bash
# Backend
tail -f /opt/go4-automate/logs/backend.log

# Frontend
tail -f /opt/go4-automate/logs/frontend.log

# XTTS
tail -f ~/xtts-server/xtts.log

# Docker
docker compose -f /opt/go4-automate/docker/docker-compose.yml logs -f
```

## Backup

### Datenbank exportieren

```bash
docker exec go4-postgres pg_dump -U postgres go4automate > /tmp/go4automate-backup-$(date +%Y%m%d).sql
```

### n8n Workflows exportieren

```bash
docker exec go4-n8n n8n export:workflow --all --output=/tmp/workflows.json
docker cp go4-n8n:/tmp/workflows.json /tmp/n8n-workflows-$(date +%Y%m%d).json
```

## Troubleshooting

### Port bereits belegt

```bash
sudo lsof -i :<port>
# oder
ss -tlnp | grep :<port>
```

### XTTS PyTorch Fehler

Falls `_pickle.UnpicklingError` oder `weights_only` Fehler:
```bash
# PyTorch auf 2.5.1 downgraden
source ~/xtts-server/.venv/bin/activate
pip install torch==2.5.1 torchaudio==2.5.1
```

### Let's Encrypt Challenge fehlgeschlagen

1. DNS prüfen: `dig +short <domain> A`
2. Port-Forwarding prüfen (80 → 80, nicht 80 → 8081)
3. nginx Config: `/.well-known/acme-challenge/` muss vor `/` kommen

### Redis Port-Konflikt

Standard-Redis läuft auf 6379. Falls belegt, nutze 6380:
```bash
# In docker-compose.yml:
ports:
  - '127.0.0.1:6380:6379'

# In backend/.env:
REDIS_URL=redis://localhost:6380/0
```

## Systemd Services (Optional)

Für Autostart bei Reboot können systemd Services erstellt werden. Beispiel für Backend:

```ini
# /etc/systemd/system/go4-backend.service
[Unit]
Description=go4-automate Backend
After=network.target

[Service]
Type=simple
User=go4energy
WorkingDirectory=/opt/go4-automate/backend
ExecStart=/opt/go4-automate/backend/.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8002
Restart=always

[Install]
WantedBy=multi-user.target
```

---

*Dokumentation erstellt: 2026-02-24*
