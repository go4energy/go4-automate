# Integrations Architecture

Stand: 2026-03-14

## Ziel

Externe Provider wie Microsoft 365 / Microsoft Graph, Google Workspace und spaeter IMAP sollen nicht mehr pro Fachmodul separat eingebunden werden.

Stattdessen gibt es einen gemeinsamen Integration-Layer fuer:

- Mail lesen
- Kalender lesen
- Mail senden
- optionale Mail-Aktionen wie Reply, Move, Delete

## Fachliche Trennung

### 1. Personal Connections

Fuer persoenliche Nutzerfaelle:

- persoenliches Morgenbriefing
- persoenliche Inbox-Ansicht
- persoenliche Kalenderdaten

Merkmale:

- meist delegated OAuth
- an einen konkreten Plattform-User gebunden
- typischerweise nur lesende Capabilities fuer das `briefing`-Modul

### 2. Shared / Service Mailboxes

Fuer organisationale Faelle:

- `sales@`
- `support@`
- `marketing@`
- andere allgemeine Team-Postfaecher

Merkmale:

- delegated oder application auth
- nicht an einen einzelnen User gekoppelt
- fuer Versand, CRM, Inbox-Workflows und spaeter Automationen

## Modulgrenzen

### Briefing

Das `briefing`-Modul bleibt fachlich lesend:

- Mail lesen
- Kalender lesen
- Inhalte priorisieren
- Briefing generieren

Keine destruktiven Mail-Aktionen in Phase 1.

### Mail / Inbox / CRM

Aktive Mailbearbeitung gehoert in ein separates Modul bzw. einen separaten Capability-Bereich:

- antworten
- weiterleiten
- verschieben
- loeschen
- archivieren
- kategorisieren
- Zuweisung an Benutzer

### Email Marketing

Outbound-Versand fuer Kampagnen bleibt getrennt von persoenlichen Briefing-Verbindungen:

- dedizierte Shared Mailbox oder Service-Mailbox
- klares Senderprofil
- eigenes Logging, Limits und Compliance

## Technische Architektur

Neues Paket:

- `backend/app/integrations/`

Zentrale Bausteine:

- `types.py`
  - provider-agnostische Typen und Capabilities
- `interfaces.py`
  - gemeinsame Ports fuer Mail/Calendar Read und Mail Actions
- `service.py`
  - Capability-Pruefung und Routing-Helfer
- `microsoft_graph/`
  - Graph-spezifische Auth-, Scope- und API-Bausteine

## Geplantes Datenmodell

Die bestehenden `briefing`-spezifischen Personal-Connections sind ein Zwischenstand. Ziel ist ein allgemeineres Modell:

### `integration_connections`

Vorgeschlagene Felder:

- `tenant_id`
- `provider`
- `auth_mode`
- `scope`
- `user_id` optional
- `mailbox_address` optional
- `external_account_id`
- `encrypted_token`
- `status`
- `last_error`
- `metadata`

### `integration_connection_capabilities`

Je Verbindung explizit vergebene Capabilities:

- `read_mail`
- `read_calendar`
- `send_mail`
- `mail_actions`

### `mailbox_profiles`

Fachliche Mailboxen fuer Module:

- Anzeigename
- technische Mailbox-Adresse
- Provider
- Standard-Sender
- erlaubte Module / Einsatzbereiche

## Migrationsplan

### Phase 1

- gemeinsames Integration-Paket anlegen
- Microsoft-Graph-Bausteine zentralisieren
- `briefing` nutzt weiterhin die bestehenden Personal-Connection-Tabellen
- AI-Modul-Credentials fuer Provider-Apps werden bereits ueber das gehartete `ModuleInterface`-Credential-Modell gelesen und geschrieben
- Secret-Werte aus diesem Pfad werden redaktiert angezeigt; `system_config`-Werte laufen ueber Tenant-Config

### Phase 2

- allgemeine Tabellen fuer `integration_connections` und Capabilities einfuehren
- bestehende `briefing_account_connections` dorthin migrieren
- `briefing` auf den allgemeinen Integration-Service umstellen

### Phase 3

- `emailmarketing`-O365-Pfad auf den gemeinsamen Microsoft-Graph-Layer umstellen
- Shared-Mailbox-Profile fuer `marketing`, `sales`, `support` einfuehren

### Phase 4

- eigenes Modul fuer Mail-Aktionen / Inbox-Workflows
- Reply, Move, Delete, Assignment, CRM-Verknuepfung

## Entscheidungsregeln

- `briefing` bekommt nur lesende Capabilities
- aktive Mail-Aktionen werden separat freigeschaltet
- Versand an Kunden erfolgt ueber Shared-/Service-Mailboxen, nicht ueber persoenliche Briefing-Connections
- IMAP bleibt optionaler spaeterer Adapter und ist kein Kern der ersten Ausbaustufe
