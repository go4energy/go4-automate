# Briefing Multi-Account Plan

Stand: 2026-03-14

## Aktuelle Entscheidung

Fuer den laufenden Testpfad bleibt es vorerst bei genau einer verbundenen E-Mail-Adresse pro Plattform-User.

Ziel fuer den naechsten Ausbau ist aber:

- ein Plattform-User kann mehrere E-Mail-Konten fuer das persoenliche Briefing verbinden
- spaeter optional auch mehrere Kalender-Konten
- persoenliche Konten und Shared-/Service-Mailboxen bleiben fachlich getrennt

## Ist-Zustand

Aktuell gilt im `briefing`-Modul:

- ein Plattform-User meldet sich z. B. als `team@go4.energy` an
- dieser User kann persoenliche OAuth-Verbindungen speichern
- der konkrete Datenabruf erfolgt ueber die verbundene externe Mailbox, z. B. `harry.ketschik@...`
- `personal/run` liest derzeit effektiv nur eine Mail-Connection und eine Kalender-Connection

Technische Einschraenkung:

- die aktuelle Unique-Constraint auf `briefing_account_connections` laesst nur eine Verbindung pro
  `tenant_id + user_id + provider + integration_type` zu

## Zielbild

Ein User soll mehrere persoenliche Mailboxen fuer das Briefing konfigurieren koennen, zum Beispiel:

- privates Microsoft-Postfach
- geschaeftliches Microsoft-Postfach
- zusaetzliches Google-Konto

Der Briefing-Run soll dann:

- alle aktiven Mail-Connections des Users laden
- Inhalte pro Connection abrufen
- Ergebnisse zusammenfuehren
- die Quelle je Item bzw. je Section sichtbar machen

## Ausbau in Phasen

### Phase 0: Jetzt

Ziel:

- bestehende Ein-Konto-Variante stabil testen

Umfang:

- persoenliche Microsoft-Mail-Connection testen
- persoenliche Microsoft-Kalender-Connection testen
- `personal/run` gegen genau einen verbundenen Mail- und Kalender-Account verifizieren

### Phase 1: Mehrere persoenliche Mail-Konten im bestehenden Briefing-Modell

Ziel:

- mehrere Mail-Connections pro User im bestehenden `briefing`-Datenmodell erlauben

Noetige Aenderungen:

- Unique-Constraint von `briefing_account_connections` erweitern oder ersetzen
- zusaetzliches Identifikationsfeld einfuehren, z. B.:
  - `account_key`
  - oder `mailbox_address`
  - oder `external_account_id` als fachlich sichtbarer Schluessel
- `list_personal_connections()` unveraendert mehrere Verbindungen liefern lassen
- `personal/run` von `get_active_personal_connection(...)` auf einen Sammelpfad fuer mehrere Mail-Connections umstellen

Ergebnis:

- mehrere Mailboxen pro User koennen parallel verbunden werden
- Briefing aggregiert Inhalte ueber alle aktiven Mail-Connections

### Phase 2: UI fuer mehrere Konten

Ziel:

- `Mein Briefing` kann mehrere verbundene Konten verwalten

Noetige Aenderungen:

- Connection-Liste im UI erweitern
- weiterer Connect-Button pro Provider
- eindeutige Anzeige je Konto:
  - Provider
  - verbundene Adresse
  - Status
  - Integrationstyp
- Aktivieren/Deaktivieren einzelner Konten
- optional Prioritaet oder Sortierung

### Phase 3: Briefing-Run fachlich verfeinern

Ziel:

- mehrere Konten nicht nur technisch, sondern fachlich sauber auswerten

Noetige Regeln:

- globale vs. mailbox-spezifische Limits
- Duplikat-Erkennung
- Priorisierung pro Mailbox
- Include-/Exclude-Filter
- klare Quellenkennzeichnung im Ergebnis

### Phase 4: Migration in allgemeinen Integration-Layer

Ziel:

- persoenliche Briefing-Connections aus dem `briefing`-Spezialmodell in allgemeine
  `integration_connections` ueberfuehren

Nutzen:

- gleiche Architektur fuer `briefing`, spaeter `emailmarketing`, Inbox-/CRM-Module und Shared-Mailboxen
- bessere Trennung zwischen:
  - persoenlichen Connections
  - Shared-/Service-Mailboxen

## Offene Architekturfragen

Vor Umsetzung von Phase 1 zu klaeren:

1. Mehrere Konten nur fuer Mail oder auch sofort fuer Kalender?
2. Duerfen mehrere Konten desselben Providers verbunden werden?
3. Sollen Shared-Mailboxen schon im Briefing sichtbar sein oder erst im allgemeinen Integration-Layer?
4. Sollen Limits global oder pro Konto gelten?
5. Wie sollen doppelte Nachrichten aus mehreren Postfaechern behandelt werden?

## Empfohlener naechster Schritt

Kurzfristig nichts an Multi-Account bauen.

Stattdessen jetzt zuerst:

1. den bestehenden Ein-Konto-Flow end-to-end testen
2. `personal/run` mit genau einer Mailbox verifizieren
3. danach Phase 1 fuer mehrere persoenliche Mail-Konten umsetzen
