# AI Module Control

Stand: 2026-03-14

## Ziel

Komplexe Module sollen spaeter nicht primär ueber grosse Formulare konfiguriert werden, sondern ueber einen Chatbot, der:

- das Modul kennt
- die kanonischen Parameter kennt
- fehlende Informationen gezielt abfragt
- Secrets und Zugaenge strukturiert behandelt
- Modul-Aktionen kontrolliert ausloesen kann

Der Enduser bekommt nur eine kleine Menge einfacher Schalter im Frontend.

## Grundprinzip

Die kanonische Modulbeschreibung liegt weiterhin im Modul selbst:

- `__manifest__.py`
- `config_schema.py`
- `ModuleInterface`

Der Chatbot arbeitet nicht direkt gegen beliebige Dateien, sondern gegen standardisierte Modul-Schnittstellen.

## Einheitliches Setup-Schema

Jedes Modul kann ueber `ModuleInterface.get_setup_schema()` ein gemeinsames Schema bereitstellen.

Struktur:

- `parameters`
  - kanonische Modul-Config
- `actions`
  - ausfuehrbare Modul-Aktionen
- `enduser_controls`
  - kleine, spaeter sichtbare User-Schalter
- `credentials`
  - Zugangsdaten-/Secret-Beschreibung

Aktueller Implementierungsstand:

- `credentials` werden im `ModuleInterface` getrennt von normalen Modulparametern verarbeitet
- Secret-Credentials werden beim Lesen nur redaktiert ausgegeben
- der Redaction-Platzhalter ist `***configured***`
- das `setup-schema` liefert fuer Credentials zusaetzlich:
  - `value`
  - `configured`

## Wichtige Metadaten pro Feld

Felder koennen fuer AI-/Admin-Steuerung annotiert werden:

- `editable_by_ai`
- `editable_by_enduser`
- `secret`
- `requires_confirmation`
- `risk_level`
- `source`

Damit kann ein Chatbot erkennen:

- was er ueberhaupt setzen darf
- was nur fuer Admins gedacht ist
- was als Secret behandelt werden muss
- was eine explizite Bestaetigung braucht

Fuer Credentials gilt aktuell zusaetzlich:

- `source = module_config`
  - Wert wird im Modul-Config-Block des Tenants gespeichert
- `source = system_config`
  - Wert wird ueber den Tenant-Config-Pfad geschrieben
  - technische Persistierung erfolgt ueber `TenantService.write_file_updates(...)`
  - Secret-Werte werden auch in diesem Pfad nur redaktiert zurueckgegeben

## Kanonische Endpunkte

Ueber `backend/app/ai/router.py` stehen modulbezogene Setup-Endpunkte zur Verfuegung:

- `GET /api/v1/ai/modules/{module}/setup-schema`
- `GET /api/v1/ai/modules/{module}/config`
- `PUT /api/v1/ai/modules/{module}/config`
- `POST /api/v1/ai/modules/{module}/actions/{action_key}`

Diese Endpunkte sind der bevorzugte Zugang fuer spaetere Chatbot-Workflows.

## Rollenmodell

### Chatbot / Admin

Soll koennen:

- Modul-Schema lesen
- Config lesen und schreiben
- Secrets strukturiert abfragen
- Testlaeufe starten
- Modul-Aktionen ausfuehren

### Enduser

Soll nur einfache Controls sehen, z. B.:

- E-Mail-Briefing an/aus
- Kalender-Briefing an/aus
- Uhrzeit

## Referenzfall Briefing

Im `briefing`-Modul ist dieses Muster jetzt erstmals konkret umgesetzt:

- AI-bearbeitbare Modul-Parameter
- deklarative Aktionen
  - `run_sources_now`
  - `generate_channel_episode`
  - `run_personal_briefing`
- kleine Enduser-Controls
  - `email_enabled`
  - `calendar_enabled`
  - `delivery_time`
- Credential-Schema fuer Google/Microsoft OAuth App-Zugaenge

Zusatz:

- `POST /api/v1/briefing/personal/run`
  - fuehrt einen manuellen persoenlichen Briefing-Fetch aus
- fuer `microsoft_client_secret` und vergleichbare Secrets gilt:
  - Lesen nur redaktiert
  - Schreiben ueber den AI-Modulpfad persistiert `system_config`-Werte ueber Tenant-Config

## Referenzfall Email Marketing

Im `emailmarketing`-Modul ist dasselbe Muster als zweiter Referenzfall hinterlegt:

- AI-bearbeitbare Modul-Parameter
- deklarative Aktionen
  - `verify_provider`
  - `send_single_test_email`
- Credential-Schema fuer Provider-Zugaenge

## Wichtige Architekturregel

Der Chatbot soll niemals „frei“ an beliebigen Dateien oder Tabellen operieren.

Stattdessen gilt:

1. Modul-Schema lesen
2. fehlende Werte abfragen
3. kanonische Config ueber Modul-Interface setzen
4. deklarierte Aktion ausfuehren
5. Ergebnis und Fehler strukturiert zurueckgeben

## Naechste Schritte

1. Riskante Aktionen mit expliziter Confirmation-Schicht versehen
2. Weitere Module an dasselbe Setup-Muster anbinden
3. `integrations` spaeter als eigenes steuerbares Modul einfuehren
4. langfristig das Credential-Handling ueber weitere Module konsistent angleichen
