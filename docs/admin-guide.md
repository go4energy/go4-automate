# go4-automate – Admin Guide

Dieses Dokument beschreibt die Einrichtung und Konfiguration der go4-automate Plattform.

## Inhaltsverzeichnis

- [Voraussetzungen](#voraussetzungen)
- [Installation](#installation)
- [Externe Dienste konfigurieren](#externe-dienste-konfigurieren)
  - [Datenbank (PostgreSQL)](#datenbank-postgresql)
  - [Redis](#redis)
  - [n8n Workflows](#n8n-workflows)
  - [Anthropic (Claude)](#anthropic-claude)
  - [OpenAI](#openai)
  - [Meta (Facebook/Instagram)](#meta-facebookinstagram)
  - [Microsoft 365 OAuth (Kalender/E-Mail)](#microsoft-365-oauth-kalendere-mail)
  - [Google OAuth (Kalender/E-Mail)](#google-oauth-kalendere-mail)
  - [SMTP (E-Mail-Versand)](#smtp-e-mail-versand)
  - [Serper (Websuche)](#serper-websuche)
  - [OpenWeather](#openweather)
  - [Text-to-Speech (TTS)](#text-to-speech-tts)
  - [Ollama (Lokales LLM)](#ollama-lokales-llm)
- [Sicherheit](#sicherheit)
- [Environment Variables Referenz](#environment-variables-referenz)

---

## Voraussetzungen

- Python 3.12+
- Node.js 20+
- PostgreSQL 16
- Redis 7
- Docker + Docker Compose (empfohlen)

## Installation

```bash
# Repository klonen
git clone <repo-url> /opt/go4-automate
cd /opt/go4-automate

# Environment konfigurieren
cp .env.example backend/.env
# .env anpassen (siehe Abschnitte unten)

# Docker-Dienste starten (PostgreSQL, Redis, n8n)
docker compose -f docker/docker-compose.yml up -d

# Backend
cd backend
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload --host 0.0.0.0 --port 8001

# Frontend
cd ../frontend
npm install
npm run dev
```

---

## Externe Dienste konfigurieren

Alle Konfiguration erfolgt ueber Environment Variables in `backend/.env`. Jeder Abschnitt beschreibt einen externen Dienst, welche Variablen benoetigt werden, und wie man die Credentials beschafft.

> **Hinweis:** Nur die Dienste konfigurieren, die tatsaechlich genutzt werden. Die Plattform startet auch mit leeren API Keys — die entsprechenden Features sind dann einfach deaktiviert.

---

### Datenbank (PostgreSQL)

PostgreSQL 16 als primaere Datenbank.

```env
DATABASE_URL=postgresql+asyncpg://postgres:DEIN_PASSWORT@localhost:5432/go4automate
```

Bei Docker-Setup (empfohlen) wird die DB automatisch ueber `docker-compose.yml` gestartet.

---

### Redis

Redis 7 fuer Caching und Queue.

```env
REDIS_URL=redis://localhost:6379/0
```

Bei Docker-Setup automatisch verfuegbar.

---

### n8n Workflows

[n8n](https://n8n.io) wird fuer automatisierte Workflows genutzt (Content Pipeline, Ads Pipeline).

```env
N8N_URL=http://localhost:5678
N8N_API_KEY=dein-n8n-api-key
N8N_BASIC_AUTH_USER=admin
N8N_BASIC_AUTH_PASSWORD=dein-passwort
```

**Einrichtung:**
1. n8n laeuft als Docker-Container (siehe `docker/docker-compose.yml`)
2. n8n Admin-UI oeffnen: `http://localhost:5678`
3. Settings → API → API Key erstellen
4. Key in `.env` als `N8N_API_KEY` eintragen

---

### Anthropic (Claude)

Claude wird fuer Content-Generierung, Chat und Briefing-Zusammenfassungen genutzt.

```env
ANTHROPIC_API_KEY=sk-ant-...
LLM_MODEL_CONTENT=claude-sonnet-4-5-20250929
```

**Einrichtung:**
1. Konto erstellen: [console.anthropic.com](https://console.anthropic.com)
2. Settings → API Keys → Create Key
3. Key in `.env` als `ANTHROPIC_API_KEY` eintragen

---

### OpenAI

OpenAI wird fuer Analyse, Klassifikation und Scoring genutzt (guenstigere Modelle).

```env
OPENAI_API_KEY=sk-...
LLM_MODEL_ANALYSIS=gpt-4o-mini
LLM_MODEL_CLASSIFICATION=gpt-4o-mini
LLM_MODEL_SCORING=gpt-4o-mini
```

**Einrichtung:**
1. Konto erstellen: [platform.openai.com](https://platform.openai.com)
2. API Keys → Create new secret key
3. Key in `.env` als `OPENAI_API_KEY` eintragen

---

### Meta (Facebook/Instagram)

Fuer automatisches Posten auf Facebook/Instagram und Ads Management.

```env
META_SYSTEM_USER_TOKEN=dein-system-user-token
META_PAGE_ID=123456789
META_INSTAGRAM_BUSINESS_ID=123456789
META_AD_ACCOUNT_ID=act_123456789
META_PIXEL_ID=123456789
META_API_VERSION=v21.0
```

**Einrichtung:**
1. [Meta Business Suite](https://business.facebook.com) oeffnen
2. Einstellungen → Business-Einstellungen
3. **System User erstellen:**
   - Nutzer → Systemnutzer → Hinzufuegen
   - Rolle: Admin
   - Token generieren mit Berechtigungen: `pages_manage_posts`, `pages_read_engagement`, `instagram_basic`, `instagram_content_publish`, `ads_management`, `ads_read`
4. **Page ID:** Facebook-Seite → Info → Seiten-ID
5. **Instagram Business ID:** Business Suite → Instagram-Konto → ID aus der URL
6. **Ad Account ID:** Werbeanzeigenmanager → Konto-ID (mit `act_` Prefix)
7. **Pixel ID:** Events Manager → Datenquellen → Pixel-ID

---

### Microsoft 365 OAuth (Kalender/E-Mail)

Fuer das Briefing-Modul: Kalender-Termine und E-Mails als Quellen abrufen.

```env
APP_URL=https://automate.go4.energy
MICROSOFT_CLIENT_ID=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
MICROSOFT_CLIENT_SECRET=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
MICROSOFT_TENANT_ID=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
```

**Einrichtung:**

#### 1. App Registration erstellen
1. [Azure Portal](https://portal.azure.com) oeffnen
2. **Microsoft Entra ID** (ehemals Azure AD) → **App registrations** → **New registration**
3. Ausfuellen:
   - **Name:** `go4-automate Briefing`
   - **Supported account types:** `Accounts in this organizational directory only` (Single Tenant)
   - **Redirect URI:** Platform = **Web**, URL:
     ```
     https://automate.go4.energy/api/v1/briefing/oauth/callback
     ```
4. **Register** klicken

#### 2. Werte notieren
Auf der Uebersichtsseite der neuen App:
- **Application (client) ID** → `MICROSOFT_CLIENT_ID`
- **Directory (tenant) ID** → `MICROSOFT_TENANT_ID`

#### 3. Client Secret erstellen
1. Links: **Certificates & secrets** → **New client secret**
2. Description: `go4-automate`, Expiry: `24 months`
3. **Add** klicken → den **Value** sofort kopieren (wird nur einmal angezeigt)
4. Value → `MICROSOFT_CLIENT_SECRET`

#### 4. API Permissions setzen
1. Links: **API permissions** → **Add a permission** → **Microsoft Graph** → **Delegated permissions**
2. Folgende Permissions hinzufuegen:
   - `Calendars.Read` — Kalender-Termine lesen
   - `Mail.Read` — E-Mails lesen
   - `User.Read` — Benutzer-Profil (ist meist schon vorhanden)
   - `offline_access` — Refresh Token (ist meist schon vorhanden)
3. Empfohlen: **Grant admin consent for [Organisation]** klicken — dann muessen Nutzer nicht einzeln zustimmen

#### 5. `.env` aktualisieren
```env
APP_URL=https://automate.go4.energy
MICROSOFT_CLIENT_ID=<Application (client) ID>
MICROSOFT_CLIENT_SECRET=<Client Secret Value>
MICROSOFT_TENANT_ID=<Directory (tenant) ID>
```

#### 6. Nutzung
1. Im Briefing-Modul eine Quelle vom Typ **Kalender** oder **E-Mail** erstellen
2. Quelle speichern
3. Button **Microsoft 365** klicken → Popup oeffnet sich
4. Mit Microsoft-Konto anmelden und Berechtigungen erteilen
5. Popup schliesst sich automatisch, Quelle zeigt "Verbunden"

> **Wichtig:** Die Redirect URI in der App Registration muss exakt mit `{APP_URL}/api/v1/briefing/oauth/callback` uebereinstimmen. Bei Aenderung der Domain muss sie in Azure angepasst werden.

---

### Google OAuth (Kalender/E-Mail)

Fuer das Briefing-Modul: Google Kalender und Gmail als Quellen.

```env
APP_URL=https://automate.go4.energy
GOOGLE_CLIENT_ID=xxxxxxxxxxxx.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=GOCSPX-xxxxxxxxxxxxxxxxx
```

**Einrichtung:**

#### 1. Google Cloud Projekt erstellen
1. [Google Cloud Console](https://console.cloud.google.com) oeffnen
2. Projekt erstellen oder bestehendes auswaehlen

#### 2. APIs aktivieren
1. **APIs & Services** → **Library**
2. Folgende APIs suchen und aktivieren:
   - **Google Calendar API**
   - **Gmail API**

#### 3. OAuth Consent Screen konfigurieren
1. **APIs & Services** → **OAuth consent screen**
2. User Type: **Internal** (nur fuer eigene Organisation) oder **External**
3. App-Name, Support-Email, etc. ausfuellen
4. Scopes hinzufuegen:
   - `https://www.googleapis.com/auth/calendar.readonly`
   - `https://www.googleapis.com/auth/gmail.readonly`
   - `openid`
   - `email`
5. Falls External: Test-User hinzufuegen (bis zur Veroeffentlichung)

#### 4. OAuth Credentials erstellen
1. **APIs & Services** → **Credentials** → **Create Credentials** → **OAuth client ID**
2. Application type: **Web application**
3. Name: `go4-automate Briefing`
4. **Authorized redirect URIs** hinzufuegen:
   ```
   https://automate.go4.energy/api/v1/briefing/oauth/callback
   ```
5. **Create** klicken
6. **Client ID** und **Client Secret** notieren

#### 5. `.env` aktualisieren
```env
APP_URL=https://automate.go4.energy
GOOGLE_CLIENT_ID=<Client ID>
GOOGLE_CLIENT_SECRET=<Client Secret>
```

#### 6. Nutzung
Identisch zu Microsoft 365 — im Briefing-Modul eine Quelle erstellen, speichern, dann **Google** Button klicken.

> **Hinweis:** Bei External User Type muss die App erst von Google verifiziert werden, damit beliebige Nutzer sich verbinden koennen. Bis dahin funktioniert es nur fuer hinzugefuegte Test-User.

---

### SMTP (E-Mail-Versand)

Fuer Benachrichtigungen und System-Mails.

```env
SMTP_HOST=smtp.example.com
SMTP_PORT=587
SMTP_USER=user@example.com
SMTP_PASSWORD=dein-passwort
SMTP_FROM=noreply@go4.energy
```

**Gaengige Provider:**
| Provider | Host | Port |
|----------|------|------|
| Gmail | smtp.gmail.com | 587 |
| Microsoft 365 | smtp.office365.com | 587 |
| Mailgun | smtp.mailgun.org | 587 |

> Bei Gmail muss ein **App-Passwort** verwendet werden (nicht das normale Passwort). Google-Konto → Sicherheit → 2FA aktivieren → App-Passwoerter.

---

### Serper (Websuche)

[Serper.dev](https://serper.dev) wird fuer Briefing-Quellen vom Typ **Websuche** genutzt.

```env
SERPER_API_KEY=dein-serper-key
```

**Einrichtung:**
1. Konto erstellen: [serper.dev](https://serper.dev)
2. Dashboard → API Key kopieren
3. In `.env` als `SERPER_API_KEY` eintragen

---

### OpenWeather

Fuer Wetter-Daten in Briefings oder Content.

```env
OPENWEATHER_API_KEY=dein-key
```

**Einrichtung:**
1. Konto erstellen: [openweathermap.org](https://openweathermap.org/api)
2. API Keys → Key kopieren
3. In `.env` als `OPENWEATHER_API_KEY` eintragen

---

### Text-to-Speech (TTS)

Fuer Audio-Briefings. Zwei Engines werden unterstuetzt:

#### Piper (Standard)
Schnelle, lokale TTS Engine.
```env
TTS_ENGINE=piper
TTS_URL=http://localhost:10200
```

#### XTTS (High Quality)
Hochwertiges TTS mit Voice Cloning.
```env
TTS_ENGINE=xtts
XTTS_URL=http://localhost:8020
SPEAKER_UPLOAD_DIR=uploads/speakers
```

#### Deaktivieren
```env
TTS_ENGINE=disabled
```

---

### Ollama (Lokales LLM)

Alternative zu Anthropic fuer Briefing-Zusammenfassungen — laeuft lokal, keine API-Kosten.

```env
LLM_MODEL_BRIEFING=ollama
OLLAMA_URL=http://localhost:11434
OLLAMA_MODEL=mistral
```

**Einrichtung:**
1. Ollama installieren: [ollama.ai](https://ollama.ai)
2. Modell herunterladen: `ollama pull mistral`
3. In `.env` konfigurieren

Standardmaessig wird Anthropic genutzt (`LLM_MODEL_BRIEFING=anthropic`).

---

## Sicherheit

### Pflicht-Aenderungen vor Production

Diese Werte **muessen** vor dem produktiven Einsatz geaendert werden:

```env
SECRET_KEY=<zufaelliger String, mind. 32 Zeichen>
JWT_SECRET=<zufaelliger String, mind. 32 Zeichen>
INITIAL_ADMIN_PASSWORD=<sicheres Admin-Passwort>
```

Zufaellige Keys generieren:
```bash
python3 -c "import secrets; print(secrets.token_urlsafe(48))"
```

### Weitere Sicherheits-Einstellungen

```env
# Erlaubte Frontend-Origins (CORS) — Domain anpassen!
ALLOWED_ORIGINS=["https://automate.go4.energy"]

# Listener-Selbstregistrierung deaktivieren (Briefing PWA)
LISTENER_SELF_REGISTRATION=false

# JWT Token Ablauf (Stunden, Standard: 720 = 30 Tage)
JWT_EXPIRY_HOURS=720
```

---

## Environment Variables Referenz

Vollstaendige Liste aller konfigurierbaren Variablen:

| Variable | Beschreibung | Standard | Pflicht |
|----------|-------------|----------|---------|
| **App** | | | |
| `APP_NAME` | Anwendungsname | `go4-automate` | |
| `APP_URL` | Oeffentliche URL (fuer OAuth Callbacks) | `http://localhost:8001` | Ja (Production) |
| `DEBUG` | Debug-Modus | `false` | |
| `PLATFORM_NAME` | Plattformname | `go4-automate` | |
| `DOMAIN` | Domain | `localhost` | |
| `TIMEZONE` | Zeitzone | `Europe/Vienna` | |
| **Datenbank** | | | |
| `DATABASE_URL` | PostgreSQL Connection String | `postgresql+asyncpg://...` | Ja |
| **Redis** | | | |
| `REDIS_URL` | Redis Connection String | `redis://localhost:6379/0` | Ja |
| **Sicherheit** | | | |
| `SECRET_KEY` | Verschluesselungs-Key | `change-me-in-production` | Ja |
| `BACKEND_SECRET` | Backend-zu-Backend Auth | _(leer)_ | |
| `ALLOWED_ORIGINS` | CORS Origins (JSON Array) | `["http://localhost:5173"]` | Ja (Production) |
| `JWT_SECRET` | JWT Signing Key | `change-me-in-production` | Ja |
| `JWT_EXPIRY_HOURS` | JWT Token Ablauf in Stunden | `720` | |
| `INITIAL_ADMIN_PASSWORD` | Initiales Admin-Passwort | `changeme` | Ja |
| `LISTENER_SELF_REGISTRATION` | Listener-Selbstregistrierung | `true` | |
| **AI / LLM** | | | |
| `ANTHROPIC_API_KEY` | Anthropic API Key | _(leer)_ | Ja* |
| `OPENAI_API_KEY` | OpenAI API Key | _(leer)_ | Ja* |
| `LLM_MODEL_CONTENT` | Modell fuer Content | `claude-sonnet-4-5-20250929` | |
| `LLM_MODEL_ANALYSIS` | Modell fuer Analyse | `gpt-4o-mini` | |
| `LLM_MODEL_CLASSIFICATION` | Modell fuer Klassifikation | `gpt-4o-mini` | |
| `LLM_MODEL_SCORING` | Modell fuer Scoring | `gpt-4o-mini` | |
| `LLM_MODEL_BRIEFING` | Briefing Engine | `anthropic` | |
| `OLLAMA_URL` | Ollama Server URL | `http://localhost:11434` | |
| `OLLAMA_MODEL` | Ollama Modell | `mistral` | |
| **Meta** | | | |
| `META_SYSTEM_USER_TOKEN` | System User Token | _(leer)_ | Fuer Meta |
| `META_PAGE_ID` | Facebook Page ID | _(leer)_ | Fuer Meta |
| `META_INSTAGRAM_BUSINESS_ID` | Instagram Business ID | _(leer)_ | Fuer Meta |
| `META_AD_ACCOUNT_ID` | Ad Account ID | _(leer)_ | Fuer Meta |
| `META_PIXEL_ID` | Pixel ID | _(leer)_ | Fuer Meta |
| `META_API_VERSION` | API Version | `v21.0` | |
| **Microsoft 365 OAuth** | | | |
| `MICROSOFT_CLIENT_ID` | Azure App Client ID | _(leer)_ | Fuer MS365 |
| `MICROSOFT_CLIENT_SECRET` | Azure App Client Secret | _(leer)_ | Fuer MS365 |
| `MICROSOFT_TENANT_ID` | Azure Directory Tenant ID | _(leer)_ | Fuer MS365 |
| **Google OAuth** | | | |
| `GOOGLE_CLIENT_ID` | Google OAuth Client ID | _(leer)_ | Fuer Google |
| `GOOGLE_CLIENT_SECRET` | Google OAuth Client Secret | _(leer)_ | Fuer Google |
| **n8n** | | | |
| `N8N_URL` | n8n Server URL | `http://localhost:5678` | Fuer Workflows |
| `N8N_API_KEY` | n8n API Key | _(leer)_ | Fuer Workflows |
| `N8N_BASIC_AUTH_USER` | n8n Basic Auth User | _(leer)_ | |
| `N8N_BASIC_AUTH_PASSWORD` | n8n Basic Auth Passwort | _(leer)_ | |
| **SMTP** | | | |
| `SMTP_HOST` | SMTP Server | _(leer)_ | Fuer E-Mail |
| `SMTP_PORT` | SMTP Port | `587` | |
| `SMTP_USER` | SMTP Benutzername | _(leer)_ | Fuer E-Mail |
| `SMTP_PASSWORD` | SMTP Passwort | _(leer)_ | Fuer E-Mail |
| `SMTP_FROM` | Absender-Adresse | `noreply@go4.energy` | |
| **Suche** | | | |
| `SERPER_API_KEY` | Serper.dev API Key | _(leer)_ | Fuer Websuche |
| **Wetter** | | | |
| `OPENWEATHER_API_KEY` | OpenWeather API Key | _(leer)_ | Fuer Wetter |
| **TTS** | | | |
| `TTS_ENGINE` | TTS Engine (`piper`/`xtts`/`disabled`) | `piper` | |
| `TTS_URL` | Piper TTS Server URL | `http://localhost:10200` | Fuer Piper |
| `XTTS_URL` | XTTS Server URL | `http://localhost:8020` | Fuer XTTS |
| `SPEAKER_UPLOAD_DIR` | Speaker-Dateien Verzeichnis | `uploads/speakers` | |
| `BRIEFING_AUDIO_DIR` | Briefing-Audio Verzeichnis | `uploads/briefing` | |
| **Uploads** | | | |
| `UPLOAD_DIR` | Upload-Verzeichnis | `uploads` | |
| `MAX_UPLOAD_SIZE_MB` | Max Upload-Groesse in MB | `10` | |
| **Tenant** | | | |
| `DEFAULT_TENANT_ID` | Standard-Tenant ID | `default` | |
| `ACTIVE_TENANT` | Aktiver Tenant | `go4energy` | |
| `TENANT_CONFIG_DIR` | Tenant-Config Verzeichnis | `config/tenants` | |
| `TEMPLATE_DIR` | Template-Verzeichnis | `config/templates` | |

\* Mindestens einer der AI API Keys wird fuer die Kernfunktionen benoetigt.
