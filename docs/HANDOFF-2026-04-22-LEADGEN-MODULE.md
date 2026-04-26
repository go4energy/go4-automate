# Handoff 2026-04-22 — Leadgen-Modul

Stand: 2026-04-22, Session-Ende nach Schritt 1 (Fundament, committed) und
Schritt 2 (Stage 1 Places + Run-Infra + Frontend + Tests, unversioniert im
Working Tree).

## Scope

Neues nachladbares Plattform-Modul `leadgen` fuer B2B-Lead-Discovery:

1. Google Places API (New) Text-Search ueber konfigurierbare Queries
2. Impressum-Scraping (spaeter)
3. LLM-basierte Anreicherung (spaeter, Claude Haiku)
4. Fallback via Clay/Apollo (spaeter, optional)
5. Handoff an `engagement_pipelines` + `postmail`/`emailmarketing`

Der Ausloeser war ein externes Claude-Spec fuer ein Standalone-CLI-Tool
(`go4-leadgen`). Nach Review wurde bewusst plattform-integriert gebaut:
PostgreSQL statt SQLite, FastAPI statt Typer, Multi-Tenant, Worker statt CLI.
Outreach laeuft ueber bestehende Module, kein CSV-Export zu Odoo.

## Designentscheidungen

- **Neues Modul**, nicht Erweiterung von `research` (andere Domaene: B2B-Kontakte statt Content-Themen).
- **Bewusste Tabellentrennung** — Leadgen-Spezifika bleiben in eigenen Tabellen, beim Handoff wird in `contacts` geschrieben (mit `source='leadgen'`).
- **Auto-Pipeline-Option**: Beim Campaign-Create kann `create_new_pipeline=true` gesetzt werden — Service legt Engagement-Pipeline mit `channels=[postmail,email]`, `goal=erstkontakt`, Slug-Kollisionsschutz automatisch an.
- **Worker statt CLI** — analog zu `run_engagement_worker.py`, plattform-konform.
- **Tenant-spezifische Credentials** — `google_places_api_key` via `ModuleInterface.CREDENTIALS` mit `source=system_config`, wird ueber `TenantService.write_file_updates()` persistiert.
- **Ein Worker-Prozess** reicht fuer den Anfang (Entscheidung des Users).
- **Kein Cron-Auto-Setup** (CLAUDE.md Regel 5).

## Aktueller Git-Status

Branch: `feature/ad-management` (nicht `feature/leadgen` — alles lief auf dem bestehenden Branch weiter).

- **Commit `818deeb`**: `feat(leadgen): add module skeleton with DB schema`  
  Enthaelt nur Schritt 1 — 7 Dateien, 1035 Zeilen.
- **Working Tree uncommitted**: Schritt 2 (Places-Client, Worker, erweiterter Router+Service, Frontend, Tests) — User hat bewusst gesagt "keine commits mehr bis zum schluss".
- Davor im Tree: 26 modifizierte + 80 untracked Files aus anderen Sessions (letzter Commit davor war `7270976` vom 2026-03-20). **Nicht meine Baustelle** — separat aufraeumen.

## Was konkret existiert

### Backend

```
backend/app/leadgen/
├── __init__.py              # Paket-Marker
├── __manifest__.py          # Sidebar "SALES/Leadgen", Tab-Routen
├── config_schema.py         # ModuleInterface: 9 Params, 3 Actions, 1 Credential
├── models.py                # 5 SQLAlchemy-Modelle
├── schemas.py               # Pydantic (CampaignCreate, RunResponse, PlaceResponse, ...)
├── router.py                # 15 Endpoints unter /api/v1/leadgen/
├── service.py               # CampaignService, RunService, PlaceService
├── places_client.py         # Google Places API (New) Text-Search-Client
└── worker.py                # Stage-Executor fuer "places"

backend/run_leadgen_worker.py  # CLI-Entry: --run-id/--tenant/--interval

backend/alembic/versions/067_leadgen_module.py   # 5 Tabellen
backend/tests/test_leadgen.py                    # 16 Tests, alle gruen
```

### Frontend

```
frontend/src/api/leadgen.js
frontend/src/stores/leadgen.js           # Pinia mit Loading/Error-State
frontend/src/views/LeadgenView.vue       # 5 Tabs: Dashboard, Kampagnen, Places, Runs, Einstellungen
frontend/src/views/LeadgenCampaignEditView.vue
frontend/src/views/LeadgenCampaignDetailView.vue
frontend/src/views/LeadgenPlaceDetailView.vue
```

### DB-Schema (Alembic 067)

| Tabelle | Zweck |
|---------|-------|
| `leadgen_campaigns` | Such-Konfiguration: Queries (JSONB), language, region, pv_relevance_threshold, target_engagement_pipeline_id (FK engagement_pipelines, nullable), status |
| `leadgen_runs` | Run-Tracking: current_stage, status (queued/running/paused/completed/failed), stage_state (JSONB fuer Resume), processed_count/success_count/error_count, cost_cents, last_error |
| `leadgen_places` | Ein Row pro Google-Place: alle Kontaktfelder + raw_payload, status (discovered/impressum_done/impressum_failed/llm_done/llm_failed/rejected/enrolled), contact_id (FK contacts nullable) |
| `leadgen_impressum` | 1:1 zu places — §5 TMG-Felder |
| `leadgen_llm_insights` | 1:1 zu places — pv_relevance_score, services, brands, personalization_hook, cost_cents |

Unique-Constraint: `(tenant_id, google_place_id)` verhindert Doppelung ueber Queries/Kampagnen hinweg.

## API-Endpoints (Live)

Alle unter `/api/v1/leadgen/`, brauchen `Authorization: Bearer` + `X-Tenant-ID`:

- `GET /health` — ohne Auth pruefbar
- `GET/POST /campaigns`, `GET/PUT/DELETE /campaigns/{id}`, `GET /campaigns/{id}/stats`
- `GET/POST /campaigns/{id}/runs`
- `GET /runs/{id}`, `POST /runs/{id}/pause`, `POST /runs/{id}/resume`
- `GET /campaigns/{id}/places` (Filter: `status`, Pagination: `page`, `size`)
- `GET /places/{id}`, `POST /places/{id}/reject` (Body: `{"reason":"..."}`)

## Tests

```bash
cd backend && source .venv/bin/activate
pytest tests/test_leadgen.py -v
# 16 passed
```

Abdeckung:
- `_parse_place` gegen 3 Fixture-Payloads
- Campaign-CRUD (Duplicate-Slug, Auto-Pipeline-Flow, Update, Delete)
- Run-Lifecycle (ohne Pipeline 400, ohne Queries 400, Success+Duplicate-Protection, Pause+Resume)
- Worker mit `_FakePlacesClient`: Stage-Durchlauf (4 Places aus 2 Queries mit Pagination), Dedup
- Place-Reject

## Live-HTTP-Verifikation

Eben getestet gegen PID 3603869 auf `localhost:8002`:
- Login → Token ✓
- Create Campaign mit `create_new_pipeline=true` → 201, Pipeline auto-angelegt ✓
- Start Run → 201, status=queued ✓
- Duplicate Run-Start → 400 "Es laeuft bereits ein Run" ✓
- Pause → 200 ✓ (nach Bugfix)
- Resume → 200 ✓ (nach Bugfix)
- Delete → 204 ✓

## Gefundene und gefixte Bugs

### MissingGreenlet bei pause/resume

**Symptom:** `POST /runs/{id}/pause` und `resume` gaben `500 Internal Server Error` (plain text), keine Exception im Log.

**Ursache:** `RunResponse.model_validate(run)` iteriert Pydantic-Felder, inkl. `updated_at`. Nach `await self.db.flush()` markiert SQLAlchemy `updated_at` als expired (wegen `onupdate=func.now()`). Pydantic's `from_attributes`-getattr triggert einen implicit Lazy-Load — in async-Session ohne greenlet-Kontext -> MissingGreenlet -> FastAPI serialization crashed -> Starlette ServerErrorMiddleware sendet "Internal Server Error" text.

**Fix:** Nach jeder schreibenden Service-Methode explizit `await self.db.refresh(obj)`. Betroffen: `RunService.pause/resume/mark_running/mark_failed/mark_completed`, `PlaceService.reject`. `CampaignService.create/update` und `RunService.start` hatten refresh schon.

**Merksatz:** Fuer alle neuen Service-Methoden auf der Plattform: wenn der Router das ORM-Objekt direkt per `ResponseModel.model_validate` zurueckgibt, immer `refresh` nach `flush`/`commit` wenn Columns mit `onupdate`/server_default geaendert wurden.

### SIM114 im Places-Parser

Ruff meinte `if locality / elif postal_town and not city` koenne man mit `or` kombinieren — false positive. Mit Fallback-Variable `address_city_fallback` umgeschrieben, Semantik erhalten.

## Naechste Schritte

### Unmittelbar vor Live-Test

1. **Google Places API Key** in Tenant-Config eintragen. Moeglichkeiten:
   - Ueber AI-Modul-Setup (wenn UI fertig): `PUT /api/v1/ai/modules/leadgen/config` mit `google_places_api_key`
   - Direkt: `config/tenants/go4energy.env` um `google_places_api_key=AIza...` erweitern
2. **Frontend im Browser pruefen**: Sidebar unter SALES sollte "Leadgen" zeigen (ggf. Frontend-Reload noetig, da Module-Liste beim Login geladen wird).
3. **Worker starten**: `cd backend && source .venv/bin/activate && python run_leadgen_worker.py --interval 15` (vorne im Terminal, ctrl+c stoppt).
4. **Test-Kampagne** mit 1-2 Queries anlegen, Run starten, Worker-Output beobachten, Places in UI pruefen.
5. **Vorbehalt**: Der Places-Client ist nur gegen Fixtures getestet. Beim ersten echten API-Call koennten kleine Anpassungen noetig sein (Field-Mask-Namen, Error-Format, Rate-Limit-Header).

### Schritt 3 — Stage 2 (Impressum-Scraping)

Plan:
- `app/leadgen/impressum.py`:
  - URL-Detection fuer Impressum-Seite (Pfade `/impressum`, `/imprint`, `/legal` + Link-Text-Heuristik)
  - BeautifulSoup4 + Regex-Extraktion fuer §5 TMG: Geschaeftsfuehrer, Email, Telefon, Postadresse, HRB, USt-ID
  - robots.txt-Respekt
  - Per-Host Rate-Limit (Default 5s zwischen Requests), parallelisiert ueber verschiedene Hosts
  - User-Agent `go4energy-leadbot/1.0 (kontakt@go4.energy)` — schon in config_schema als Default
  - Exclude-Liste (Facebook, Instagram, business.site, gelbeseiten, 11880, yelp)
- Worker erweitern um Stage `impressum` (nach `places`, sequenziell)
- Fixtures mit echten Impressum-HTMLs (anonymisiert) fuer Tests
- UI: Impressum-Daten im `LeadgenPlaceDetailView` anzeigen

### Schritt 4 — Stage 3 (LLM-Anreicherung)

- `app/leadgen/llm_enrichment.py` mit Claude Haiku via `services/llm.py`
- Pydantic-Schema fuer strukturierte Extraktion: pv_relevance_score (0-10), services, brands, customer_segments, company_size_indicator, personalization_hook, red_flags
- Pro Firma max. 3-4 Seiten laden (Homepage + Leistungen/Ueber uns/Referenzen) — in config_schema als `llm_max_pages_per_company` (Default 4)
- Token-Budget pro Firma: `llm_max_input_tokens_per_company` (Default 10000)
- Cache ueber `leadgen_llm_insights.place_id` unique constraint
- Kosten in cents pro Call loggen
- **Offen**: Pruefen ob `services/llm.py` Claude Haiku schon unterstuetzt — sonst kleine Erweiterung noetig.

### Schritt 5 — Handoff

- `app/leadgen/handoff.py`: nach Stage 3 kvalifizierte Places (pv_relevance_score >= threshold, status='llm_done', kein red_flag) in `contacts` schreiben
- `leadgen_places.contact_id` zurueckverlinken
- `pipeline_enrollments` per `engagement.service.EnrollmentService` anlegen
- Brain bekommt via Enrollment-Event die Ansprache-Aufgabe, erzeugt `pending_actions` fuer `postmail`/`email`
- `personalization_hook` als Template-Variable mitgeben
- UI: Bulk-Action "Enrollen" im Places-Tab mit Filtern (min_score, PLZ)

### Schritt 6 — Stage 4 Fallback (optional, niedrige Prioritaet)

Clay/Apollo-Anbindung fuer Firmen ohne Website oder mit gescheiterter Extraktion. Kann spaeter, nicht MVP-kritisch.

## Wichtige Gotchas fuer die Fortsetzung

1. **Nach `flush()` immer `refresh()`** wenn das Objekt zurueck an einen Pydantic-Response-Model geht (siehe Bug oben).
2. **Alembic-Nummer**: letzte ist jetzt `067`. Naechste waere `068`. Stil ist reiner String `"067"`, nicht `"067_description"`.
3. **Engagement-Pipeline-Cascade**: Beim Loeschen einer Campaign wird die Auto-Pipeline NICHT mitgeloescht (`ondelete=SET NULL` auf Campaign-Seite). Beabsichtigt — Pipeline soll weiterleben. Testartefakte sammeln sich also im `engagement`-Modul.
4. **`expire_on_commit=False`** ist in `async_session` aktiv, reicht aber nicht gegen `onupdate`-expire nach flush.
5. **tests/conftest.py nutzt synchrones SQLite** hinter `AsyncSessionShim`. FKs sind da nicht enforced, also kann `X-Tenant-ID: go4energy` ohne vorherige Tenant-Erzeugung im Test funktionieren. Live-Backend gegen PostgreSQL braucht den Tenant.
6. **Vite Dev-Server** wird vom `npm run dev`-Parent reanimiert, wenn man nur den vite-Child killt. Sauber stoppen: `pkill -f 'npm.*run dev'`. Das ist aber fast nie noetig — HMR findet meine neuen Views automatisch via `import.meta.glob('@/views/*.vue')`.
7. **Backend-Restart** unter `/opt/go4-automate/backend` (nicht `/projects/findfox/backend`, das ist ein anderer Service auf 8000). Standardpfad: `pkill -9 -f 'go4-automate.*uvicorn.*8002'; sleep 2; source .venv/bin/activate && nohup uvicorn app.main:app --host 0.0.0.0 --port 8002 > /tmp/go4-backend.log 2>&1 &`.
8. **Module-Discovery liefert 19 Module** beim Start — wenn `leadgen` nicht dabei ist, hat der Restart nicht gegriffen.
9. **bcrypt-Warning** `'crypt' is deprecated` und `error reading bcrypt version` beim Login sind bekannt und harmlos (aus MEMORY).

## Config-Parameter (ModuleInterface)

Aus `config_schema.py`:
- `places_qps` (default 10) — Google-API-Rate
- `max_places_pages_per_query` (default 3) — max 60 Ergebnisse pro Query
- `impressum_per_host_delay_s` (default 5) — Rate-Limit pro Host
- `respect_robots_txt` (default true, requires_confirmation, high risk)
- `crawler_user_agent` (default `go4energy-leadbot/1.0 (kontakt@go4.energy)`, requires_confirmation, high risk)
- `llm_model` (default `claude-haiku-4-5`)
- `llm_max_pages_per_company` (default 4)
- `llm_max_input_tokens_per_company` (default 10000)
- `excluded_website_hosts` (Komma-getrennt, default facebook.com,instagram.com,business.site,gelbeseiten.de,11880.com,yelp.*)

Actions: `start_run`, `pause_run`, `resume_run`.
Credentials: `google_places_api_key` (system_config, required_for: start_run).

## Commit-Strategie zum Session-Ende

User hat fuer diese Session gesagt "keine commits mehr bis zum schluss".
Empfohlen beim Wiedereinstieg:

```bash
git add backend/app/leadgen/ \
        backend/run_leadgen_worker.py \
        backend/tests/test_leadgen.py \
        frontend/src/api/leadgen.js \
        frontend/src/stores/leadgen.js \
        frontend/src/views/Leadgen*.vue
git commit -m "feat(leadgen): Stage 1 (Places) + Run-Infra + Frontend + Tests"
```

**Wichtig**: nur leadgen-Dateien stagen, die 104+ anderen Uncommitted-Changes NICHT anfassen.

## Kontextdokumente

- `docs/ENGAGEMENT-SYSTEM.md` — Pipelines, pending_actions, Brain
- `docs/INTEGRATIONS-ARCHITECTURE.md` — integration_connections, capability-Modell
- `docs/AI-MODULE-CONTROL.md` — ModuleInterface, Credential-Handling
- `backend/app/engagement/service.py` — Referenzmuster fuer Service/Router
- `backend/app/assistant/config_schema.py` — Referenzmuster fuer ModuleInterface mit credentials
- `backend/app/engagement/models.py` — Referenzmuster fuer SQLAlchemy 2.0-Style-Models mit JSONB

## Abnahmekriterien Schritt 2 (alle erfuellt)

- [x] Modul `leadgen` im Manifest-Discovery
- [x] Alle 5 Tabellen im Schema
- [x] 15 REST-Endpoints live und OpenAPI-dokumentiert
- [x] Campaign-CRUD mit Auto-Pipeline-Option
- [x] Run-Start mit Validierung (Queries vorhanden, Pipeline verknuepft, kein Duplicate)
- [x] Pause/Resume funktionsfaehig (nach Bugfix)
- [x] Worker-CLI `--help`, `--run-id`, `--interval`
- [x] 16 Unit-Tests alle gruen inkl. Worker gegen Mock-Client
- [x] Frontend mit Tabs, Campaign-Edit, Detail-View, Place-Detail
- [x] Ruff + ESLint + Prettier sauber
