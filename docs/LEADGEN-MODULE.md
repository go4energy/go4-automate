# Leadgen Module

> B2B-Lead-Discovery-Pipeline für go4-automate.
> Findet Firmen über Google Places, reichert sie an (Impressum, Homepage-LLM-Analyse,
> Serper-Verify) und übergibt qualifizierte Leads an die Engagement-Pipeline.

---

## 1. Zweck

Das Leadgen-Modul findet B2B-Prospects automatisiert anhand eines Beuteschemas
(Branche + Region + Match-Kriterien), bewertet pro Place die Passung mit
einem LLM und übergibt Treffer mit strukturierten Anreicherungsdaten an
das Engagement-Modul. Anwendungsfälle:

- **Klassisch**: "Finde alle Elektrofachbetriebe in Region X mit 5–50 MA"
- **Homepage-Verkauf**: "Finde Arztpraxen in Schweinfurt mit fehlender oder
  schlechter Homepage" (siehe §6, Verify-Stage)
- Generell **jede branchen- und regionsabhängige B2B-Akquise**, bei der man
  mit einem Zielprofil + freier Output-Spec arbeitet.

---

## 2. Architektur — High-level

```
                 ┌──────────────────┐
                 │   LeadgenCampaign │   (Beuteschema, Queries,
                 │   (Beuteschema)   │    Region, Threshold)
                 └────────┬──────────┘
                          │  POST /runs
                          ▼
                 ┌──────────────────┐
                 │   LeadgenRun     │   ein Durchlauf der Pipeline
                 │ status, stage…   │
                 └────────┬──────────┘
                          │
   ┌──────────────────────┼──────────────────────────────────┐
   │                      │                                  │
   ▼ Stage 1              ▼ Stage 2 (optional)               ▼ Stage 3
┌───────────┐          ┌────────────┐         ┌──────────────────────────┐
│ places    │          │ impressum  │         │  verify (Serper) → llm   │
│ (Google   │  smart=  │ (regex     │ smart=  │  Haiku 4.5 Homepage-     │
│  Places)  │  skip→   │  scrape)   │ skip→   │  Analyse + Score          │
└───────────┘          └────────────┘         └──────────┬───────────────┘
                                                         │
                                                         ▼
                                               ┌─────────────────────┐
                                               │  Handoff →          │
                                               │  Engagement Pipeline │
                                               └─────────────────────┘
```

Pipeline-Modus pro Kampagne in `source_config.pipeline_mode`:

| Modus    | Reihenfolge                            | Wann |
|----------|----------------------------------------|------|
| `smart`  | places → llm (LLM extrahiert Impressum mit) | **Default**, 1 LLM-Call statt 2 Stages |
| `cheap`  | places → impressum                      | Nur regex, keine LLM-Kosten |
| `legacy` | places → impressum → llm                | Für Tests / Vergleich |

---

## 3. Stages im Detail

### 3.1 places — Google-Places-Discovery

Sucht über die Google Places API nach Firmen. Zwei Modi:

**Klassisch (`queries`-Liste):**
```python
queries = ["Elektriker Berlin", "Elektroinstallation Hamburg"]
```
Pro Query bis zu 3 Pages × 20 Ergebnisse = **60 Ergebnisse pro Query**.

**Hybrid (Tile-basiert):**
Aktiv wenn `source_config.search_modes.nearby` ODER `text` aktiv ist
und `nearby_types` / `text_synonyms` befüllt sind. Gebiet wird in Tiles
zerlegt (Bundesland / Kreis / Custom-Radius), pro Tile werden Nearby- und
Text-Suchen ausgeführt; bei Sättigung (60 Treffer in einem Tile) wird der
Tile in 4 Sub-Tiles geteilt (rekursiv bis `min_tile_km`).

**Output:** Zeile pro `LeadgenPlace` mit `status='discovered'`.
Dedup über `tenant_id + google_place_id`.

**Cost:** ~3 Cent pro Text-Search-Request (konfigurierbar).

### 3.2 impressum — Regex-basiertes Scraping

Holt Impressum-Seiten der gefundenen Websites und parsed sie regex-basiert
auf §5-TMG-Felder: Geschäftsführer, E-Mail, Telefon, Anschrift,
Handelsregister, USt-ID.

Aktiv nur in `cheap`- und `legacy`-Pipeline-Modus. In `smart` übersprungen,
weil das LLM (Stage 3) die Impressum-Felder ohnehin sauberer extrahiert.

### 3.3 verify — Serper-Verifikation (NEU)

**Zweck:** Google Places liefert für viele kleine Firmen kein
`websiteUri`, obwohl die Firma sehr wohl eine Homepage hat. Diese Places
wurden früher als "keine Homepage" markiert — falsche Top-Leads für
Homepage-Sales-Kampagnen.

**Ablauf** (für jeden Place mit `website IS NULL`):
1. Eine Serper-Query `"<name> <city>"`
2. Top-3-Treffer durchgehen
3. Erste URL deren Domain **nicht** auf der Portal-Blacklist steht UND
   deren Second-Level-Domain einen Tokenmatch mit dem Praxis-/Firmennamen
   hat → **das ist ihre Homepage**
4. `place.website` setzen, `enrichment_flags["homepage_not_in_google"]=True`,
   Place läuft in den normalen LLM-Pfad
5. Wenn nichts gefunden → `enrichment_flags["serper_checked_at"]` setzen,
   synthetic Score 10 (`model_used="skip:no_website"`)

**Portal-Blacklist** (in `app/leadgen/website_verify.py:DEFAULT_PORTAL_BLACKLIST`):
- Deutsche Arzt-Portale: jameda, arzt-auskunft, sanego, doctolib, samedi,
  arzt-direkt, arzttermine, topmedic, weisse-liste, klinikbewertungen,
  medfuehrer
- Branchenbücher: gelbeseiten, 11880, dasoertliche, branchenbuch, yelp,
  firmenwissen, stadtbranchenbuch
- AT/CH: herold.at, firmenabc.at, wko.at, local.ch, search.ch
- Social: facebook, instagram, linkedin, xing, twitter, tiktok, youtube
- Google: google.com, maps.google, business.site, sites.google
- Wikipedia, Wikidata

Pro Kampagne kann via `serper_blacklist_extra: list[str]` ergänzt werden.

**Aktivierung:** Per Kampagne über `source_config.llm.verify_no_website_via_serper`
(default `True`). Schaltet sich automatisch ab, wenn `SERPER_API_KEY` leer.

**Cost:** ~$0.0003 pro Serper-Query (~3 Cent pro 100 Places).

### 3.4 llm — Haiku 4.5 Homepage-Analyse

Pro Place mit Website:
1. Bis zu 5 Unterseiten fetchen (`/`, `/impressum`, `/ueber-uns`, `/about`,
   `/leistungen`, `/services`, `/kontakt` etc. — konfigurierbar)
2. HTML strippen, auf Token-Budget kürzen (default 15.000 Zeichen)
3. Haiku-Call mit `target_profile` + `output_description` aus der Kampagne
4. Output (JSON, vom LLM): `target_match_score 0–10`, `services`, `brands`,
   `customer_segments`, `company_size_indicator`, `personalization_hook`,
   `red_flags`, `primary_contact`, `impressum`

Für Places ohne Website (nicht via Verify-Stage gerettet): synthetic Top-Score
10, kein LLM-Call.

**Cost-Tracking:** Pro Call werden Input/Output-Tokens und cents persistiert.
Modell-Pricing in `app/leadgen/homepage_analyzer.py:_PRICING_CENTS_PER_M`.

---

## 4. Datenmodell

```
LeadgenCampaign 1───┐
                    │
                    ├── LeadgenRun (n)            ─── stage_state JSONB (s.u.)
                    │
                    └── LeadgenPlace (n)
                          ├── LeadgenImpressum  (1:1, optional)
                          └── LeadgenLLMInsights(1:1, optional)
```

### 4.1 LeadgenCampaign
| Feld | Typ | Beschreibung |
|------|-----|--------------|
| `id` | int | PK |
| `tenant_id` | str(50) | FK tenants, alle Daten tenant-scoped |
| `name`, `slug` | str | Slug uniq pro Tenant |
| `queries` | JSONB list | Klassische Discovery-Queries |
| `language`, `region` | str | "de", "DE" |
| `source` | str(30) | Aktuell nur `google_places` |
| `source_config` | JSONB | Volle Pipeline-Konfig (s. §5) |
| `target_match_threshold` | int | 0–10, Mindest-Score für Handoff |
| `target_engagement_pipeline_id` | FK | Wohin qualifizierte Leads gehen |
| `status` | str | `draft \| active \| paused \| completed` |

### 4.2 LeadgenRun
| Feld | Typ | Beschreibung |
|------|-----|--------------|
| `current_stage` | str | `places \| impressum \| llm \| completed` |
| `status` | str | `queued \| running \| paused \| completed \| failed` |
| `processed_count`, `success_count`, `error_count` | int | Run-Total |
| `cost_cents` | int | Cents aller API-Calls (Places + LLM + Serper) |
| `stage_state` | JSONB | Pro-Stage-Workspace + Timeline-History (s. §4.5) |
| `started_at`, `completed_at`, `last_error` | | Audit |

### 4.3 LeadgenPlace
| Feld | Typ | Beschreibung |
|------|-----|--------------|
| `google_place_id` | str(255) | Uniq pro Tenant |
| `name`, address fields, `lat/lng`, `website`, `phone` | | Aus Places-API |
| `google_categories` | JSONB list | z.B. `["electrician","point_of_interest"]` |
| `rating`, `user_ratings_total` | | |
| `raw_payload` | JSONB | Volle Places-Response für Debug |
| `status` | str(30) | `discovered \| impressum_done \| impressum_failed \| llm_done \| llm_failed \| rejected \| enrolled` |
| `enrichment_flags` | JSONB | **NEU**: Sales-Signale (s. §4.4) |
| `contact_id` | FK contacts | Nach Handoff gesetzt |

### 4.4 enrichment_flags (Sales-Signale)
JSONB-Eimer für Signale, die nicht aus dem LLM kommen:
```json
{
  "homepage_not_in_google": true,    // Serper hat Homepage gefunden, Google nicht
  "no_calendar_in_google":  true,    // Kein Online-Termin-Link via Google
  "serper_checked_at":      "2026-04-26T12:34:56"  // Idempotenz-Marker
}
```

### 4.5 stage_state (Run-Workspace + Timeline)
Doppelte Funktion:
1. **Per-Stage-Workspace** für den Worker (top-level Keys, wechseln pro Stage)
2. **Timeline-History** unter `stages.{places, impressum, verify, llm}` (NEU,
   bleibt erhalten beim Stage-Wechsel)

Beispiel im laufenden Betrieb:
```json
{
  "stages": {
    "places":    {"status":"completed","started_at":"…","completed_at":"…","processed":572,"api_calls":32,"cost_cents":798},
    "impressum": {"status":"skipped","reason":"pipeline_mode=smart"},
    "verify":    {"status":"completed","checked":209,"homepages_found":21,"no_homepage":188,"started_at":"…","completed_at":"…"},
    "llm":       {"status":"running","total":209,"processed":175,"succeeded":168,"failed":7,"cost_cents":1090,"started_at":"…"}
  },
  "places_total": 209,    // legacy keys, werden vom Worker weiter verwendet
  "places_processed": 175,
  "places_succeeded": 168,
  "places_failed": 7,
  "llm_cost_cents": 1090
}
```

### 4.6 LeadgenImpressum
§5 TMG Felder. `email`, `phone`, `managing_directors[]`, `postal_address`,
`handelsregister`, `ust_id`, plus `source_url` und `extraction_error`.
Wird in `smart`-Modus von der LLM-Stage geschrieben (nicht regex).

### 4.7 LeadgenLLMInsights
| Feld | Typ |
|------|-----|
| `target_match_score` | 0–10, Match zur Kampagne |
| `services`, `brands`, `customer_segments` | JSONB list |
| `company_size_indicator` | str(200) |
| `personalization_hook` | text — Kontaktblock + Pre-Pitch-Bullets |
| `red_flags` | JSONB list — z.B. "kein Impressum", "nicht mobil" |
| `primary_contact` | JSONB — `{salutation, first_name, last_name, gender, role, source}` |
| `pages_analyzed` | JSONB list — URLs die im Call landeten |
| `input_tokens`, `output_tokens`, `cost_cents`, `model_used` | Provenance |

`model_used="skip:no_website"` bedeutet: kein LLM-Call, synthetic Top-Score
für Place ohne Homepage.

---

## 5. Konfiguration

### 5.1 Per-Kampagne (source_config)

`backend/app/leadgen/source_config.py:GooglePlacesSourceConfig`:

```python
{
  "search_modes": {"nearby": false, "text": false},
  "nearby_types": [],
  "text_synonyms": [],
  "geographic": {
    "mode": "germany",                # germany | bundesland | radius
    "bundesland": null,
    "center_lat": null, "center_lng": null,
    "radius_km": null
  },
  "min_tile_km": 10.0,
  "max_api_calls": 2000,
  "language_code": "de",
  "region_code": "DE",
  "pipeline_mode": "smart",           # smart | cheap | legacy
  "flag_no_calendar": false,          # NEU: Online-Termin-Marker
  "impressum": {
    "max_concurrency": 5,
    "max_places_per_run": 2000,
    "respect_robots_txt": false,
    "user_agent": "...",
    "paths_to_try": ["/impressum", ...]
  },
  "llm": {
    "model": "claude-haiku-4-5",
    "provider": "anthropic",
    "max_concurrency": 5,
    "http_timeout_s": 15.0,
    "max_places_per_run": 2000,        # Kosten-Drossel pro Run
    "max_html_chars": 15000,           # Token-Budget pro Place-Call
    "verify_no_website_via_serper": true,  # NEU
    "serper_blacklist_extra": [],          # NEU: Hosts on top of default
    "target_profile": "...",               # Beuteschema (Freitext, max 4000 chars)
    "output_description": "...",           # Output-Spec (Freitext, max 4000 chars)
    "prompt_template": "",                 # leer = built-in default
    "user_agent": "...",
    "paths_to_fetch": ["/", "/impressum", ...]
  }
}
```

### 5.2 Globale Konfiguration (env)

`backend/.env`:
```
GOOGLE_PLACES_API_KEY=...           # Pflicht für places-Stage
ANTHROPIC_API_KEY=...               # Pflicht für llm-Stage (smart/legacy)
SERPER_API_KEY=...                  # Pflicht für verify-Stage
```

Settings-Schema in `app/config.py:Settings`. Werte werden via Pydantic
beim Backend-Start geladen.

### 5.3 Modul-Interface

`app/leadgen/config_schema.py:LeadgenInterface` deklariert für die
Settings-UI:

- **PARAMS**: tenant-globale Drosseln (Places-QPS, max. Pages pro Query,
  Impressum-Delay, robots.txt-Respekt, LLM-Modell, Token-Budget,
  Excluded-Hosts)
- **ACTIONS**: `start_run`, `pause_run`, `resume_run` — alle KI-aufrufbar
- **CREDENTIALS**: `google_places_api_key` (system_config)

---

## 6. API-Surface (`/api/v1/leadgen`)

### Health & Intake
- `GET  /health` — Modul-Health
- `POST /intake` — Wizard: Freitext-Beschreibung des Beuteschemas → Vorschlag
  `IntakeSuggestion` (queries, target_profile etc.)

### Campaigns CRUD
- `GET    /campaigns`               — Liste pro Tenant
- `POST   /campaigns`               — Anlegen (`create_new_pipeline`-Flag erzeugt
   eine Engagement-Pipeline mit gleichem Namen)
- `GET    /campaigns/{id}`          — Detail
- `PUT    /campaigns/{id}`          — Update
- `DELETE /campaigns/{id}`          — Löschen
- `GET    /campaigns/{id}/stats`    — Aggregierte Stats

### Runs
- `POST /campaigns/{id}/runs`       — Neuen Run starten (Stage `places`)
- `POST /campaigns/{id}/runs/enrich` — Enrich-only Run starten (sofort
   Stage `llm` mit `max_override` und `sampling: top_rated|random`)
- `GET  /campaigns/{id}/runs`       — Runs einer Kampagne
- `GET  /runs/{run_id}`             — Run-Detail (mit `stage_state`)
- `POST /runs/{run_id}/pause`       — Pausieren
- `POST /runs/{run_id}/resume`      — Wieder aufnehmen, optional `additional_budget`
- `POST /runs/{run_id}/advance-stage` — Manueller Stage-Übergang
   (z.B. `impressum_pending → impressum`)

### Places
- `GET  /campaigns/{id}/places`     — Liste mit `status`, `match`, Sortierung
- `GET  /places/{id}`               — Detail (Place + Impressum + LLM-Insights)
- `POST /places/{id}/reject`        — Place verwerfen, Reason persistieren

### Handoff & Export
- `POST /campaigns/{id}/handoff/preview`   — Welche Places würden gehandet?
- `POST /campaigns/{id}/handoff`           — Übergabe an Engagement-Pipeline
- `POST /campaigns/{id}/handoff/export-preview` — CSV-Vorschau
- `GET  /campaigns/{id}/export/accounts.csv` — CSV-Download Companies
- `GET  /campaigns/{id}/export/leads.csv`    — CSV-Download Contacts

---

## 7. Worker-Mechanik

`backend/app/leadgen/worker.py` + `run_leadgen_worker.py` (Daemon-Wrapper).

### 7.1 Polling
Default-Intervall **30 Sekunden**. Pro Tick:
1. Hole genau 1 Run mit `status IN ('queued','running')`, sortiert nach
   `created_at ASC`
2. Lade Tenant-Config + Places-Client + LLM-Service
3. Routing nach `current_stage` an `_process_*_stage()`
4. Wenn Stage-Func `True` zurückgibt → `_transition_stage(run, mode)`:
   - `_next_stage_for_mode(current, mode)` ermittelt Folge-Stage
   - Stage-State wird teilweise zurückgesetzt, **`stages`-History bleibt**
   - Nicht durchlaufene Stages werden bei Run-Abschluss als `skipped`
     markiert (Reason: `pipeline_mode=<mode>`)

### 7.2 Limits pro Invocation
- `MAX_QUERIES_PER_INVOCATION`: 5 Queries (Klassik-Modus)
- `MAX_CALLS_PER_INVOCATION`: 20 Places-API-Calls (Hybrid-Modus)
- `MAX_IMPRESSUM_PLACES_PER_INVOCATION`: 50
- `MAX_LLM_PLACES_PER_INVOCATION`: 25 (LLM-Calls dauern 2–5 s)

Diese Bounds verhindern, dass eine einzelne Run-Invocation den Worker
monopolisiert.

### 7.3 Re-Queue-Pattern (Backfill)
Um eine bereits abgeschlossene Stage neu zu durchlaufen:
```sql
UPDATE leadgen_runs
SET status='queued', current_stage='llm',
    stage_state=jsonb_build_object('stages', stage_state->'stages'),
    completed_at=NULL, last_error=NULL
WHERE id = <run_id>;
```
Worker greift im nächsten Pollcycle. Places mit existierenden LLM-Insights
werden via `LEFT JOIN ... WHERE LLMInsights.id IS NULL` ausgefiltert.

---

## 8. Frontend

### 8.1 Views
- `LeadgenView.vue` — Kampagnen-Liste
- `LeadgenCampaignEditView.vue` — Anlegen/Bearbeiten (Wizard + freies
  source_config-Editor)
- `LeadgenCampaignDetailView.vue` — Detail mit Tabs `details` / `places`
- `LeadgenPlaceDetailView.vue` — Place-Detail (Anschrift, Impressum, LLM,
  enrichment_flags, Handoff-Button)

### 8.2 Komponenten
- `components/leadgen/LeadgenRunStageTimeline.vue` — **NEU**: 4-Zeilen-Timeline
  pro Run (places → impressum → verify → llm). Liest aus `stage_state.stages.*`
  mit Fallback auf `current_stage` für alte Runs ohne Tracking.

### 8.3 Store
`stores/leadgen.js` (Pinia, Setup-Style):
- `campaigns`, `places`, `runs` State
- `loadAll(campaignId)`, `launchRun`, `pauseRunAction`, `resumeRunAction`,
  `advanceRunStageAction`
- Auto-Polling alle 5 s solange ein Run aktiv ist

### 8.4 Routing
Tab-Routen siehe Manifest (`__manifest__.py`):
- `/leadgen` — Kampagnen-Liste
- `/leadgen/campaigns/:id` (= `details`)
- `/leadgen/campaigns/:id/places`
- `/leadgen/campaigns/:id/edit`
- `/leadgen/campaigns/:id/places/:id`

---

## 9. Cost-Modell

| Komponente | Kosten | Notiz |
|------------|--------|-------|
| Google Places Text Search (Pro-SKU) | ~3 Cent/Request | Pro Page mit bis zu 20 Ergebnissen |
| Google Places Nearby Search | ~3 Cent/Request | Pro Tile |
| Serper (verify) | $0.30 / 1000 Queries (~3 Cent / 100 Places) | Nur für Places ohne Homepage |
| Anthropic Haiku 4.5 (default) | $1 / 1M input, $5 / 1M output | Pro Place ~3000 Input + ~1000 Output Tokens → ~0.8 Cent |
| Anthropic Sonnet 4.6 (alternativ) | $3 / 1M input, $15 / 1M output | 3× teurer |
| Anthropic Opus 4.7 (alternativ) | $15 / 1M input, $75 / 1M output | 15× teurer |

**Beispielrun** für eine Schweinfurt-Arzt-Kampagne (572 Places):
- Places-Discovery: 32 Calls × 3 ¢ = **0.96 €**
- Verify: 209 Serper-Calls × 0.03 ¢ = **0.06 €**
- LLM (363 + ~10 promoted = 373 Haiku-Calls): **~0.30 €**
- **Total ≈ 1.30 € pro 572 Places** = 0.23 ¢ pro Place

---

## 10. Setup / Voraussetzungen

### Pflicht-Credentials in `backend/.env`
```
GOOGLE_PLACES_API_KEY=…   # https://console.cloud.google.com → Places API (New)
ANTHROPIC_API_KEY=…       # https://console.anthropic.com
SERPER_API_KEY=…          # https://serper.dev → Dashboard → API Key
```

### Migration anwenden
```bash
cd backend && alembic upgrade head
```

### Worker starten
```bash
cd backend && source .venv/bin/activate
python run_leadgen_worker.py    # läuft mit 30s-Polling-Intervall
```

(Niemals automatisch via `setup.sh` starten — Cron/Worker manuell &
mit Freigabe, gemäß CLAUDE.md.)

### Frontend
Standard `npm run dev -- --host 0.0.0.0 --port 8081`. Modul ist über
Sidebar "SALES → Leadgen" erreichbar (siehe Manifest).

---

## 11. Operational Notes

### 11.1 Run hängt bei "queued" / wird nicht gepickt
- Worker-Process läuft? `ps aux | grep run_leadgen`
- DB-Connection ok? Worker-Logs via `tail -50 /tmp/leadgen_worker.log`
- Anderer Run blockiert? Worker pickt **streng FIFO** nach `created_at` —
  ein älterer queued/running Run hält neuere Runs zurück.

### 11.2 Run failed mit ValidationError
- `output_description` zu lang? Cap ist **4000 Zeichen** (war früher 2000).
- `target_profile` zu lang? Cap ist **4000 Zeichen**.
- `prompt_template` zu lang? Cap ist **8000 Zeichen**.

### 11.3 Verify findet nichts trotz Serper-Key
- Key korrekt geladen? `python -c "from app.config import Settings; print(bool(Settings().serper_api_key))"`
- Backend nach Key-Änderung neu gestartet? Pydantic lädt `.env` nur beim
  Import.
- Kampagne hat `verify_no_website_via_serper=true`? Per default ja, kann
  aber pro Kampagne deaktiviert sein.

### 11.4 Backfill: existierende synthetic-Insights nachträglich verifizieren
```sql
-- Synthetic Insights wegwerfen, Places auf discovered zurück
DELETE FROM leadgen_llm_insights
WHERE model_used = 'skip:no_website'
  AND place_id IN (
    SELECT id FROM leadgen_places
    WHERE campaign_id = <id> AND (website IS NULL OR website = '')
  );
UPDATE leadgen_places SET status='discovered'
WHERE campaign_id=<id> AND (website IS NULL OR website='') AND status='llm_done';

-- Run neu queuen (Stage llm)
UPDATE leadgen_runs
SET status='queued', current_stage='llm',
    stage_state=jsonb_build_object('stages', stage_state->'stages'),
    completed_at=NULL, last_error=NULL
WHERE id = <run_id>;
```

Worker pickt im nächsten Cycle, neue Insights werden geschrieben (echtes
Haiku für gefundene Homepages, synthetic für tatsächlich keine).

---

## 12. Recent Changes (2026-04-26)

| Migration | Was |
|-----------|-----|
| `069`     | `target_match_score` (rename von `pv_relevance_score`), `primary_contact` JSONB |
| `070`     | `enrichment_flags` JSONB auf `leadgen_places` |

| Code-Change | Was |
|-------------|-----|
| `worker.py` | No-Site-Places: synthetic Score 10 statt rausfiltern |
| `worker.py` | Verify-Sub-Stage: Serper vor LLM für Places ohne Homepage |
| `worker.py` | Calendar-Heuristik bei Places-Parse (opt-in: `flag_no_calendar`) |
| `worker.py` | Per-Stage-Tracking via `stage_state.stages.*` |
| `website_verify.py` (neu) | Serper-Wrapper + Portal-Blacklist + Booking-Detect |
| `stage_state.py` (neu) | Helper: mark_running/completed/skipped, update_counters |
| `source_config.py` | `verify_no_website_via_serper`, `serper_blacklist_extra`, `flag_no_calendar` |
| `LeadgenRunStageTimeline.vue` (neu) | 4-Zeilen-Timeline pro Run |

---

## 13. Roadmap / TODO

Kurzfristig:
- [ ] Frontend: Anzeige der `enrichment_flags` als Badges in Place-Liste
  + Detail-View
- [ ] Frontend: Filter "nur Places mit `homepage_not_in_google`"
- [ ] Frontend: Filter "nur Places mit `no_calendar_in_google`"

Mittelfristig:
- [ ] Verify als echte Stage rausziehen (heute Sub-Step im LLM-Stage),
  damit Re-Queue der Verify-Stage allein möglich ist
- [ ] Adaptive Modell-Wahl: Haiku für 80 % der Places, Sonnet für die
  unentschlossenen (target_match_score 4–6)
- [ ] Multi-Source-Discovery: zusätzliche Lead-Quellen (Northdata,
  Handelsregister-API, OpenStreetMap)

Langfristig:
- [ ] Pipeline-Templates pro Branche (Arzt, Handwerk, Kanzlei …) —
  vorgefertigte `target_profile` + `queries` + Threshold

