# Docker Rules

## Grundregeln
- **Docker Compose** immer verwenden (nicht einzelne `docker run`)
- **Healthchecks** für JEDEN Service definieren
- **Multi-stage Builds** für kleinere Images
- **Non-root User** in allen Containern
- **Named Volumes** für persistente Daten (nie Bind-Mounts in Production)

## Python Dockerfile Pattern
```dockerfile
FROM python:3.12-slim AS base

WORKDIR /app

RUN groupadd -r appuser && useradd -r -g appuser -d /app -s /sbin/nologin appuser

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ ./app/
COPY alembic.ini .
COPY alembic/ ./alembic/

RUN chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

## Vue Dockerfile Pattern
```dockerfile
FROM node:20-alpine AS build

WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM caddy:2-alpine
COPY --from=build /app/dist /srv
COPY Caddyfile /etc/caddy/Caddyfile
EXPOSE 80
```

## Healthchecks
```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
  interval: 30s
  timeout: 10s
  retries: 3
  start_period: 10s
```

## Deployment-Reihenfolge
1. **Backup** – Datenbank + Volumes sichern
2. **Pull** – Neue Images holen / bauen
3. **Up** – `docker compose up -d --build`
4. **Healthcheck** – Warten bis alle Services healthy sind
5. **Smoke-Test** – Manuell oder Script: Health-Endpoints prüfen

```bash
#!/bin/bash
# Deployment
./scripts/backup.sh
docker compose -f docker/docker-compose.yml pull
docker compose -f docker/docker-compose.yml up -d --build
sleep 10
curl -f http://localhost:8000/health || echo "BACKEND HEALTH FAILED"
curl -f http://localhost:80 || echo "FRONTEND HEALTH FAILED"
```

## Volumes
- `postgres_data` – Datenbank-Daten
- `redis_data` – Redis Persistence
- NIEMALS Volumes löschen ohne Backup
