# Tech Stack – Verbindliche Versionen

| Kategorie | Technologie | Version |
|-----------|------------|---------|
| Runtime | Python | ^3.12.0 |
| Runtime | Node.js | ^20.0.0 |
| Backend Framework | FastAPI | ^0.115.0 |
| ASGI Server | Uvicorn | ^0.32.0 |
| Frontend Framework | Vue | ^3.5.0 |
| Build Tool | Vite | ^6.0.0 |
| CSS | Tailwind CSS | ^3.4.0 |
| Charts | ApexCharts | ^4.1.0 |
| Charts (Vue) | vue3-apexcharts | ^1.7.0 |
| Datenbank | PostgreSQL | ^16.0 |
| ORM | SQLAlchemy | ^2.0.0 |
| Migrations | Alembic | ^1.14.0 |
| Validation | Pydantic | ^2.10.0 |
| Cache/Queue | Redis | ^7.0 |
| HTTP Client | httpx | ^0.28.0 |
| Logging | loguru | ^0.7.0 |
| State Management | Pinia | ^2.3.0 |
| HTTP Client (Vue) | axios | ^1.7.0 |
| Linting (Python) | ruff | ^0.8.0 |
| Testing | pytest | ^8.3.0 |
| Container | Docker + Compose | latest |
| Reverse Proxy | Caddy | ^2.9.0 |
| Workflows | n8n | ^1.70.0 |

## NIEMALS verwenden

- **Flask** – wir nutzen FastAPI
- **Django** – wir nutzen FastAPI
- **Express** – wir nutzen FastAPI
- **jQuery** – wir nutzen Vue 3
- **Moment.js** – nutze `date-fns` oder native `Intl`
- **requests** – wir nutzen `httpx`
- **print()** – wir nutzen `loguru`
- **logging (stdlib)** – wir nutzen `loguru`
- **SQLAlchemy 1.x Syntax** – nur 2.x Style mit `select()`, `Session.execute()`
- **TypeScript** – wir nutzen JavaScript mit JSDoc wo nötig
- **Options API (Vue)** – nur Composition API mit `<script setup>`
- **var** – nutze `const` / `let`

## Regel: Neue Packages

Vor dem Hinzufügen eines neuen Packages:
1. Prüfe ob FastAPI/Vue/Python-stdlib die Funktionalität bereits bieten
2. Prüfe ob ein bereits installiertes Package es kann
3. Nur wenn beides nicht zutrifft: Package vorschlagen mit Begründung
4. Package muss aktiv maintained sein (letztes Release < 6 Monate)
