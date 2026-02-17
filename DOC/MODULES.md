# Module

## Modul 1: Content-Pipeline

### Zweck
Automatische Erstellung, Freigabe und Veröffentlichung von Social-Media-Posts auf Facebook, Instagram und LinkedIn.

### Warum?
- Ein KMU schafft es selten, regelmäßig 3-5x pro Woche hochwertigen Content zu produzieren
- KI-generierter Content mit Branchenkontext ist qualitativ vergleichbar mit Agentur-Content
- Automatisches Posting spart 5-10 Stunden pro Woche

### Funktionsweise

**Generierung (automatisch, Mo-Fr):**
1. n8n Cron-Job startet um 8:00 Uhr
2. Backend wählt nächstes Thema aus der Rotation (konfigurierbar pro Tenant)
3. Prompt wird mit Tenant-Kontext angereichert: Firmenname, Region, Tonalität, Zielgruppe, USP
4. Claude generiert JSON mit: Titel, Post-Text, Hashtags, Bild-Prompt
5. Post wird als "Draft" in der Datenbank gespeichert
6. Admin erhält Benachrichtigung

**Freigabe (manuell, im Dashboard):**
1. Admin öffnet Content-Dashboard
2. Sieht alle Drafts als Karten mit Vorschau
3. Kann Text bearbeiten, Hashtags ändern
4. Gibt frei und wählt Zeitpunkt (oder "sofort")
5. Status wechselt zu "Scheduled"

**Veröffentlichung (automatisch):**
1. n8n prüft alle 15 Minuten ob scheduled Posts fällig sind
2. Backend ruft Meta Graph API auf (Facebook Page Post)
3. Bei Instagram: Zweistufig (Container erstellen → publishen)
4. Status wechselt zu "Published", Meta Post-ID wird gespeichert

**Engagement-Tracking (automatisch, täglich):**
1. n8n holt Engagement-Daten für Posts der letzten 7 Tage
2. Likes, Kommentare, Shares werden in der DB gespeichert
3. Daten fließen in Reporting und zukünftig in die Content-Optimierung

### Themen-Rotation (Beispiel PV-Branche)
```
1. Referenzprojekte Unterfranken
2. Strompreis-Updates
3. KfW Förderung aktuell
4. Speicher ja oder nein?
5. Wallbox-Kombi
→ Nach Thema 5 wieder bei 1
```

### API-Endpoints
| Methode | Endpoint | Beschreibung |
|---|---|---|
| POST | /api/content/generate | LLM generiert neuen Post |
| GET | /api/content/ | Liste mit Filtern |
| GET | /api/content/{id} | Einzelner Post |
| PATCH | /api/content/{id}/approve | Freigeben + Scheduling |
| PATCH | /api/content/{id}/edit | Text bearbeiten |
| POST | /api/content/{id}/publish | Sofort veröffentlichen |
| DELETE | /api/content/{id} | Draft löschen |
| GET | /api/content/themes/rotation | Nächstes Thema anzeigen |

### Dateien
```
backend/app/content/
├── models.py          # ContentPiece (SQLAlchemy)
├── schemas.py         # Pydantic: Create, Generate, Approve, Response
├── service.py         # Business-Logik, Themen-Rotation, LLM-Aufruf
├── router.py          # FastAPI Endpoints
└── meta_client.py     # Facebook/Instagram Posting

frontend/src/
├── views/ContentDashboardView.vue
├── views/ContentEditView.vue
├── components/ContentCard.vue
├── stores/content.js
└── api/content.js

n8n/workflows/
└── 01-content-pipeline.json
```

---

## Modul 2: Ad-Management

### Zweck
Verwaltung und automatische Optimierung von Meta (Facebook/Instagram) Werbekampagnen mit Server-Side Tracking, Budget-Auto-Scaling und Wetter-basiertem Boost.

### Warum?
- Meta Ads sind der effektivste Kanal für lokale B2C-Lead-Generierung
- Manuelles Budget-Management ist zeitaufwändig und fehleranfällig
- Server-Side Tracking (Conversion API) liefert 20-30% mehr Daten als Browser-Pixel allein
- Wetter-Boost ist einzigartig: sonnige Tage = mehr PV-Interesse = höhere Conversion

### Funktionsweise

**Conversion-Tracking (Echtzeit):**
1. Besucher kommt auf Kunden-Website
2. Meta Pixel feuert im Browser (PageView, ViewContent, Lead etc.)
3. Gleichzeitig: JavaScript sendet Event an unsere Conversion API
4. Backend hasht persönliche Daten (SHA256) und sendet an Meta
5. Meta dedupliziert Browser- und Server-Events automatisch
6. Ergebnis: Bessere Attribution, weniger Datenverlust durch Ad-Blocker

**Performance-Sync (alle 4 Stunden):**
1. n8n ruft Backend auf
2. Backend holt Campaign Insights von Meta Marketing API
3. Berechnet: CPL, CPC, CTR, Frequency, Reach
4. Speichert in ad_performance Tabelle
5. Bei CPL > Max: Sofort-Alert

**Tägliche Optimierung (20:00 Uhr):**
1. n8n triggert Optimierungsrunde
2. Backend lädt alle aktiven Campaign-Configs
3. Für jede Kampagne:
   - Heutige Performance analysieren
   - Aktuelles Wetter prüfen
   - Regeln anwenden (in Reihenfolge):

```
Regel 1 - STOPP:    CPL > max_cpl UND keine Leads UND Budget verbrannt
                     → Kampagne pausieren

Regel 2 - REDUZIER: CPL > 1.5x target_cpl
                     → Budget -20% (nicht unter Minimum)

Regel 3 - WETTER:   Sonnig (Wolken < 40%, Temp > 10°C)
                     → Budget × 1.5 (Wetter-Boost)

Regel 4 - SCALE:    CPL < 0.8x target_cpl UND mindestens 2 Leads
                     → Budget +20% (nicht über Maximum)

Regel 5 - STANDARD: Alles im Rahmen
                     → Keine Änderung
```

4. Budget-Änderungen werden über Meta API durchgeführt
5. Admin erhält Zusammenfassung per E-Mail

**Wöchentlicher KI-Report (Montag 9:00):**
1. Performance der letzten 7 Tage wird mit Vorwoche verglichen
2. LLM (Claude) analysiert die Daten
3. Erstellt Report mit 3 konkreten Handlungsempfehlungen
4. Report per E-Mail an Admin

### Wetter-Boost erklärt
In der PV-Branche korreliert sonniges Wetter stark mit Kaufinteresse. Wenn jemand bei Sonnenschein draußen steht und an sein Dach denkt, ist die Wahrscheinlichkeit einer Anfrage höher. Deshalb erhöhen wir an sonnigen Tagen automatisch das Werbebudget um 50% (konfigurierbar). Das Budget wird morgens geprüft und abends zurückgesetzt.

### API-Endpoints
| Methode | Endpoint | Beschreibung |
|---|---|---|
| POST | /api/ads/conversions | Conversion Event tracken |
| GET | /api/ads/dashboard | Dashboard-Statistiken |
| GET | /api/ads/performance | Performance-History |
| GET | /api/ads/campaigns | Aktive Kampagnen |
| POST | /api/ads/campaigns/config | Kampagnen-Config anlegen |
| PATCH | /api/ads/campaigns/{id}/config | Config ändern |
| POST | /api/ads/campaigns/{id}/pause | Kampagne pausieren |
| POST | /api/ads/campaigns/{id}/resume | Kampagne aktivieren |
| POST | /api/ads/optimize | Manuelle Optimierung |
| GET | /api/ads/weather | Aktuelles Wetter + Boost-Status |

### Dateien
```
backend/app/ads/
├── models.py              # AdPerformance, CampaignConfig, ConversionEvent
├── schemas.py             # Pydantic Models
├── service.py             # Business-Logik
├── router.py              # FastAPI Endpoints
├── meta_ads_client.py     # Meta Marketing + Conversion API
├── weather_service.py     # OpenWeather API
├── optimizer.py           # Budget-Optimierungsregeln
├── hashing.py             # SHA256 Hashing für Meta CAPI
└── templates/pixel_snippet.py  # Pixel JS-Generator

frontend/src/
├── views/AdDashboardView.vue
├── views/AdCampaignConfigView.vue
├── components/ads/KpiCard.vue
├── components/ads/PerformanceChart.vue
├── components/ads/WeatherWidget.vue
├── stores/ads.js
└── api/ads.js

n8n/workflows/
├── 04-ads-daily-optimization.json
├── 05-ads-performance-sync.json
└── 06-ads-weekly-report.json
```

---

## Modul 3: Lead-Nurturing (geplant)

### Zweck
Automatische Nachfass-Sequenz für eingehende Leads mit personalisierten E-Mails, SMS und Vertriebsübergabe.

### Warum?
- 80% der Leads werden nie nachgefasst oder zu spät kontaktiert
- Eine automatische Sequenz wandelt 15-25% mehr Leads in Termine um
- Personalisierte Inhalte (basierend auf Konfigurator-Daten) erhöhen die Relevanz

### Geplante 6-Stufen-Sequenz
```
Tag 0:  Lead kommt rein (Konfigurator, Facebook, Website)
        → Sofort: SMS/WhatsApp "Danke, wir melden uns!"
        → Sofort: Lead-Scoring (KI bewertet 0-100)

Tag 1:  Email 1: "Ihre PV-Anlage – so geht es weiter"
        → Persönliche Begrüßung, nächste Schritte erklärt
        → Basierend auf Konfigurator-Daten (kWp, Dachform, Budget)

Tag 3:  Email 2: "Familie Müller aus [Ort] hat es gemacht"
        → Referenzprojekt aus der gleichen Region
        → Vorher/Nachher Stromrechnung

Tag 5:  Email 3: "Die 5 häufigsten Fragen zur PV-Anlage"
        → FAQ / Einwandbehandlung
        → Abgestimmt auf Score: hoher Score = technisch, niedriger = emotional

Tag 7:  Email 4: "Aktuelle Förderung: bis zu €10.200 vom Staat"
        → KfW-Förderung aktuell
        → Rechenbeispiel mit ihren Daten

Tag 10: Vertrieb wird benachrichtigt
        → "Lead X hat alle Mails geöffnet, Score: 78 – bitte anrufen"
        → Oder: "Lead Y hat nichts geöffnet – in Kalt-Liste verschieben"
```

Bei Antwort oder Terminbuchung: Sequenz stoppt automatisch.

---

## Modul 4: Lead-Scoring (geplant)

### Zweck
KI-basierte Bewertung eingehender Leads auf einer Skala von 0-100, basierend auf Verhaltensdaten und Profil.

### Scoring-Faktoren
| Faktor | Punkte |
|---|---|
| Konfigurator vollständig ausgefüllt | +25 |
| Dach geeignet (Süd/Südwest, >30m²) | +15 |
| Budget angegeben >€15.000 | +10 |
| PLZ in Kerngebiet (50km Radius) | +10 |
| E-Mail geöffnet | +5 pro Mail |
| Website erneut besucht | +10 |
| Auf CTA geklickt | +15 |
| Mehrfach-Anfrage (Spam-Verdacht) | -20 |
| Anonyme/Fake E-Mail (tempmail) | -30 |

### Routing
- Score >70: "Hot Lead" → Sofort Vertrieb benachrichtigen
- Score 40-70: "Warm Lead" → Nurture-Sequenz starten
- Score <40: "Kalt" → In Newsletter-Liste, gelegentlicher Content

---

## Modul 5: Reporting (geplant)

### Zweck
Automatisierte wöchentliche und monatliche Reports mit KI-Analyse und Handlungsempfehlungen.

### Wöchentlicher Report (E-Mail an Admin)
- Content-Performance: Posts veröffentlicht, Engagement, Top-Post
- Ad-Performance: Spend, Leads, CPL, Trend
- Lead-Übersicht: Neue Leads, Score-Verteilung, Conversion-Rate
- KI-Analyse: 3 konkrete Empfehlungen
- Wetter-Boost-Bilanz: Tage mit Boost, Zusatz-Leads

### Monatlicher Report (PDF für Kunden)
- Executive Summary (1 Seite)
- Performance-Dashboard mit Charts
- Vergleich zum Vormonat
- ROI-Berechnung: Werbekosten vs. gewonnene Aufträge
- Ausblick und Empfehlungen

---

## Modul 6: WhatsApp Business (geplant)

### Zweck
Automatisierte Kundenkommunikation über WhatsApp Business API für Terminbestätigungen, Follow-ups und Lead-Qualifizierung.

### Geplante Funktionen
- Automatische Terminbestätigung nach Konfigurator
- Follow-up nach Vor-Ort-Termin
- Schnelle Rückfragen-Beantwortung (KI-gestützt)
- Erinnerungen vor Terminen

### Separate Meta App
WhatsApp Business API läuft über eine eigene Meta App (`go4-whatsapp`), getrennt von der Marketing-App, um die Genehmigungsprozesse zu vereinfachen.
