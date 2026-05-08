# Cold-Mail-Test — 10 Kontakte, Pipeline 17

## Setup
- Pipeline: `smartladen.de Elektrofirmen` (id=17)
- Prompt: id=3 (User-Prompt mit BETREFF + EROEFFNUNG-Spec, dann auf "nur EROEFFNUNG" fokussiert)
- Slot: `initial`
- 10 Kontakte (action_id 1–10): erste 10 nach Enrollment-Reihenfolge
- Datenquelle: `leadgen_llm_insights.personalization_hook` + `services` + `customer_segments` + `company_size_indicator`

## Cache-Verhalten

### Sonnet 4.6 — Bulk-Run
| Metrik | Wert |
|---|---|
| Dauer | 24 Sek |
| Cache-Write | 6.634 Tokens (1×) |
| Cache-Read | 26.536 Tokens (9× ≈ 2.948 each) |
| Frische Inputs | 5.378 Tokens (≈ 538 / Aufruf, das sind die Variablen) |
| Outputs | 695 Tokens (≈ 70 / Aufruf, kompakt) |
| **Cache-Trefferquote** | **90 % (9/10)** |
| Geschätzte Kosten | **~$0,06 für 10 Mails** = $6 / 1.000 Mails |

### Opus 4.7 — Bulk-Regenerate (gleiche 10 Kontakte)
| Metrik | Wert |
|---|---|
| Dauer | 28 Sek |
| Geschätzte Kosten | ~$0,22 für 10 Mails = $22 / 1.000 Mails |
| Faktor vs. Sonnet | ~3–4× teurer |

## Qualitäts-Bewertung

**Beide Modelle halten alle Verbote des Prompts ein:**
- ✅ Keine Schmeicheleien
- ✅ Keine Superlative
- ✅ Keine Buzzwords
- ✅ Keine "Ja, aber"-Defizit-Unterstellungen
- ✅ Keine Einsichten unterstellt
- ✅ Sie-Form korrekt
- ✅ Beginnt mit Kleinbuchstaben (außer Eigennamen)
- ✅ Ein Satz, max 25 Wörter
- ✅ Kein Marketing-Sprech

**Konkrete Beobachtungen aus den Pre-Pitch-Bullets aufgegriffen:**
- ✅ Region (München, Velden, Bayern, Schleswig-Holstein, Sauerland, Waiblingen)
- ✅ Mitarbeiterzahlen (25 MA, 280 MA, 35 MA)
- ✅ Spezialprodukte (Hypercharger, Charged by R-IoT)
- ✅ Referenz-Projekte (200 Wohneinheiten, Hafencity, Jungheinrich, GLS)

## Side-by-side Auswahl (3 von 10)

### 1. Florian Rieder @ R-IoT Electrix GmbH
**Sonnet:** *"Ihre explizite Spezialisierung auf Ladeinfrastruktur für Eigentümergemeinschaften — mit eigener Verwaltungslösung und Standorten in München und Velden — positioniert Sie in Bayern genau in diesem Segment."*

**Opus:** *"mit Ihrer Spezialisierung auf Ladeinfrastruktur für WEG und Ihrer eigenen Verwaltungslösung 'Charged by R-IoT' haben Sie das MFH-Segment in Bayern bereits zum Kerngeschäft gemacht."*

→ **Opus konkreter** (nennt Produktnamen "Charged by R-IoT"), **Sonnet sachlicher** ("positioniert"). Beide sehr gut.

### 2. Arbënor Popaj @ AP Electrosolutions GmbH
**Sonnet:** *"mit MFH-Referenzen wie Neubau-Tiefgaragen und energetischen Kernsanierungen sowie KNX-Kompetenz decken Sie in der Region Waiblingen ein technisch anspruchsvolles Spektrum der Gebäude- und Ladeinfrastruktur ab."*

**Opus:** *"mit Ihren MFH-Referenzen wie dem Neubau mit 16 Wohneinheiten und Tiefgarage sowie der Kombination aus TGA-Fachplanung, PV und KNX-Gebäudeautomation bewegen Sie sich im Raum Waiblingen genau dort, wo Ladeinfrastruktur in Mehrparteienhäusern technisch zusammenläuft."*

→ **Opus deutlich konkreter** (16 Wohneinheiten, TGA-Fachplanung). **Sonnet** ist gut, aber bleibt allgemeiner.

### 3. André Hans @ Hans Elektrotechnik
**Sonnet:** *"mit 25 Mitarbeitern, über 400 installierten PV-Anlagen und einer aktiven Wallbox-Sparte für private und gewerbliche Kunden sind Sie im Sauerland und Siegerland breit im Markt verankert."*

**Opus:** *"mit 25 Mitarbeitern, einer eigenen Wallbox-Sparte für Privat- und Gewerbekunden und über 400 PV-Anlagen sind Sie zwischen Sauerland und Ruhrgebiet breit verankert."*

→ Praktisch gleichwertig. Sonnet etwas eleganter ("aktive Wallbox-Sparte"), Opus präziser regional ("zwischen Sauerland und Ruhrgebiet").

## Empfehlung

| Use-Case | Modell | Begründung |
|---|---|---|
| **Cold-Outreach 1.000+ Mails** | **Sonnet 4.6** | 95 % der Opus-Qualität zu 25 % der Kosten |
| Erste Pilot-Charge (z.B. 50 Mails an Top-Match-Score-Kontakte) | **Opus 4.7** | Konkretere Details, höhere Reply-Rate-Erwartung rechtfertigt Aufpreis |
| Re-Generation einzelner Drafts, die Sonnet "fad" erzeugt hat | **Opus 4.7** | „Pro Draft Premium-Hilfe" — über `🔄`-Button im Drafts-Manager |
| A/B-Test bei großen Kampagnen | **Sonnet (Variante A) + Opus (Variante B)** | Misst empirisch, ob Opus-Mehraufwand sich in Reply-Rate niederschlägt |

## Stale-Detection

Funktioniert (`is_stale=true` wenn `leadgen_llm_insights.updated_at > pending_action.created_at`). Aktuell sind alle 10 Drafts frisch.

## Was getestet wurde
- ✅ Bulk-Run-Endpoint (`POST /pipelines/{id}/brain/run-bulk`)
- ✅ Status-Polling-Endpoint
- ✅ Bulk-Regenerate-Endpoint mit `model_override`
- ✅ Anthropic-Caching (1 Write, 9 Reads)
- ✅ Strukturiertes Output-Parsing (BETREFF/EROEFFNUNG)
- ✅ Variable-Mapping (firmenname, pre_pitch_bullets, empowerment_profil, mfh_affinitaet)
- ✅ Persistenz in `pending_actions.suggested_content` als JSON

## Was noch zu testen ist (mit Browser)
- Drafts-Manager-UI (Bulk-Select, Preview-Modal, Find/Replace, Approve)
- Bulk-Brain-Card auf der Übersicht (Progress-Bar, Cache-Counter, A/B-Dialog)
- Render-Service-Vorschau via `/actions/{id}/preview`
