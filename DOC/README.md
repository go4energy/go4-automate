# GO4.AUTOMATE

**Multi-Tenant Marketing-Automatisierungsplattform für KMU**

> Automatisierte Content-Erstellung, Social-Media-Posting, Lead-Nurturing, Ad-Optimierung und Reporting – alles aus einer Plattform, konfigurierbar pro Kunde.

---

## Was ist go4.automate?

go4.automate ist eine Self-Hosted Marketing-Automatisierungsplattform, die speziell für kleine und mittlere Unternehmen im B2C-Bereich entwickelt wurde. Die Plattform kombiniert KI-gestützte Content-Erstellung mit automatisiertem Social-Media-Management, intelligentem Lead-Scoring und datengetriebener Werbebudget-Optimierung.

**Kernidee:** Ein System, das für beliebig viele Unternehmen konfiguriert werden kann – durch einfaches Anpassen einer Konfigurationsdatei pro Kunde (Tenant).

## Für wen ist das?

- **Marketingagenturen**, die mehrere Kunden effizient betreuen wollen
- **KMU mit begrenztem Marketing-Budget**, die Enterprise-Level-Automatisierung brauchen
- **Unternehmen in der Energiebranche** (PV, Wärmepumpen, E-Mobilität) mit regionalem Fokus

## Kernfunktionen

| Modul | Beschreibung | Status |
|---|---|---|
| **Content-Pipeline** | LLM generiert Posts → Freigabe → Auto-Posting auf Facebook/Instagram | 🔨 In Entwicklung |
| **Ad-Management** | Meta Pixel + Conversion API, Budget-Auto-Optimierung, Wetter-Boost | 🔨 In Entwicklung |
| **Lead-Nurturing** | 6-stufige Follow-up-Sequenz nach Konfigurator-Nutzung | 📋 Geplant |
| **Lead-Scoring** | KI-basierte Bewertung eingehender Leads (0-100) | 📋 Geplant |
| **Reporting** | Wöchentliche KI-Reports mit Handlungsempfehlungen | 📋 Geplant |
| **WhatsApp Business** | Automatisierte Kundenkommunikation | 📋 Geplant |

## Tech-Stack

| Bereich | Technologie |
|---|---|
| Backend API | Python 3.12 / FastAPI |
| Frontend | Vue 3 (Composition API) + Tailwind CSS |
| Datenbank | PostgreSQL 16 + Redis 7 |
| Workflow-Engine | n8n (Self-Hosted) |
| KI / LLM | Anthropic Claude + OpenAI GPT |
| Container | Docker + Docker Compose |
| Reverse Proxy | Caddy 2 (Auto-HTTPS) |
| Hosting | Hetzner Cloud VPS |

## Schnellstart

```bash
# 1. Repo klonen
git clone https://github.com/go4energy/go4-automate.git
cd go4-automate

# 2. Konfiguration anlegen
cp .env.example .env
nano .env  # Credentials eintragen

# 3. Ersten Tenant konfigurieren
cp config/tenants/default.env config/tenants/mein-kunde.env
nano config/tenants/mein-kunde.env

# 4. Starten
docker compose -f docker/docker-compose.yml up -d

# 5. n8n öffnen
open https://automate.meine-domain.de
```

## Dokumentation

| Dokument | Beschreibung |
|---|---|
| [docs/VISION.md](docs/VISION.md) | Vision, Strategie und Geschäftsmodell |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | Technische Architektur und Systemübersicht |
| [docs/SETUP.md](docs/SETUP.md) | Installations- und Einrichtungsanleitung |
| [docs/MODULES.md](docs/MODULES.md) | Detailbeschreibung aller Module |
| [docs/META-API-SETUP.md](docs/META-API-SETUP.md) | Meta Developer Account & API-Einrichtung |
| [docs/TENANT-CONFIG.md](docs/TENANT-CONFIG.md) | Multi-Tenant Konfigurationsanleitung |
| [docs/CREDENTIALS.md](docs/CREDENTIALS.md) | Übersicht aller benötigten API-Keys und Zugangsdaten |
| [docs/ROADMAP.md](docs/ROADMAP.md) | Entwicklungs-Roadmap und Meilensteine |

## Lizenz

Proprietary – © 2026 Go4 Energy GmbH. Alle Rechte vorbehalten.
