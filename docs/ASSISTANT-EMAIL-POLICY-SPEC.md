# Assistant Email Policy Spec

Stand: 2026-03-16

## Ziel

Dieses Dokument beschreibt die technische Zielspezifikation fuer die KI-gestuetzte
E-Mail-Verwaltung im `assistant`-Modul mit Microsoft 365 / Microsoft Graph API.

Es uebersetzt das fachliche Regelwerk in:

- ein klares Zustandsmodell
- eine saubere Graph-Abbildung
- konkrete Assistant-Tools
- Persistenz- und Policy-Anforderungen
- Backend- und Frontend-Arbeitsbloecke

Leitprinzip:

- Das LLM interpretiert und formuliert
- das Backend besitzt den Zustand
- die Policy entscheidet ueber Risiko und Ausfuehrung
- der Provider-Adapter fuehrt konkret aus

## Geltungsbereich

Diese Spezifikation gilt fuer:

- eingehende und bestehende E-Mails
- sprach- und textgesteuerte Bedienung
- Outlook-Ordner und Outlook-Categories ueber Microsoft Graph
- spaetere Erweiterbarkeit auf weitere Mail-Provider

Nicht Bestandteil der ersten Ausbaustufe:

- automatische Freigaben mit hohem Risiko
- Unterordner-Management
- vollautomatische Projekt-Lifecycle-Verwaltung ohne Nutzerbeteiligung

## Fachliches Zielmodell

Die Mail-Verwaltung basiert auf zwei Ebenen:

- Status ueber genau 5 flache Ordner
- Thema und Kontext ueber Outlook Categories

Ordner modellieren den Bearbeitungszustand.
Categories modellieren den inhaltlichen Kontext.

### Status-Ordner

Zulaessige Zielordner:

- `INBOX`
- `TODO`
- `WARTEN`
- `TEMP`
- `ARCHIV`

Fachliche Bedeutung:

- `INBOX`: der echte Outlook-Posteingang, neu und noch nicht einsortiert
- `TODO`: Nutzer muss aktiv handeln
- `WARTEN`: externer Ruecklauf oder Zuarbeit steht aus
- `TEMP`: nur zeitlich begrenzt relevant
- `ARCHIV`: erledigt, dokumentiert, dauerhaft aufbewahrt

Wichtige Regeln:

- `INBOX` ist der normale Inbox-Ordner, kein eigener Unterordner
- es wird kein zusaetzlicher Unterordner `INBOX` angelegt
- `INBOX` ist kein Langzeitstatus
- `TEMP` ohne Verfallsdatum ist unzulaessig
- `ARCHIV` ist Default-Fallback bei Unsicherheit
- Loeschen ist keine Ordnerbewegung, sondern eine explizite Aktion

### Categories

Categories ersetzen Unterordner und koennen kombiniert werden.

Es gibt zwei Arten:

- feste thematische Categories
- dynamische Projekt-Categories

Feste Categories:

- `Dringend`
- `Finanzen`
- `Personal`
- `Kunden`
- `Lieferanten`
- `IT`
- `Rechtliches`
- `Intern`

Wichtige Produktentscheidung:

- diese Categories sind nur Default-Vorschlaege
- feste Categories muessen tenantweit konfigurierbar sein
- die Assistant-UI soll sie verwalten koennen
- die Category-Registry ist deshalb Pflichtbestandteil der ersten produktiven Version

Projekt-Categories:

- Namenskonvention: `Projekt: <Name>`
- maximal 15 aktive Projekt-Categories gleichzeitig
- abgeschlossene Projekte bleiben zur Suche erhalten
- fuer inaktive Projekte werden keine neuen Zuordnungen mehr vorgenommen

Category-Regeln:

- jede fachlich einsortierte Mail soll mindestens eine thematische Category haben
- mehrere Categories sind erlaubt
- `Dringend` ist Zusatzmarker, keine Hauptkategorie
- pro Konzept gibt es genau eine Bezeichnung

## Domänenmodell im Assistant

Das fachliche Modell darf nicht direkt an Graph-Details gebunden sein.
Intern wird ein provider-neutrales Mail-Statusmodell benoetigt.

### Kernfelder pro Mail-Kontext

- `status_folder`
- `categories`
- `expires_at`
- `project_category`
- `confidence`
- `reason`
- `needs_confirmation`
- `source_provider`
- `source_mailbox`
- `source_folder_id`
- `source_folder_name`

### Statusmodell

`status_folder` ist immer genau einer der Werte:

- `INBOX`
- `TODO`
- `WARTEN`
- `TEMP`
- `ARCHIV`

### TEMP-Zusatzdaten

Fuer `TEMP` sind zusaetzlich erforderlich:

- `expires_at`
- optional `expiry_reason`
- optional `expiry_policy`

Empfohlene Default-Policy:

- wenn der Nutzer kein Datum nennt, muss der Assistant nachfragen
- optional kann spaeter ein konfigurierbarer Default vorgeschlagen werden
- ohne konkretes Datum darf keine finale `TEMP`-Ablage erfolgen

## Graph-Abbildung

### Ordner

Status-Ordner werden auf echte Outlook-Mailordner gemappt.

Technische Anforderungen:

- Ordner muessen pro Mailbox eindeutig aufloesbar sein
- Ordner duerfen flach bleiben
- der Assistant darf keine Unterordner erzeugen
- bei fehlendem Ordner muss ein klarer Setup-Fehler entstehen

Setup-Regel:

- `INBOX` ist immer der vorhandene Outlook-Posteingang und wird nie neu angelegt
- `TODO`, `WARTEN`, `TEMP` und `ARCHIV` koennen bestehenden Ordnern zugeordnet werden
- falls sie fehlen, duerfen sie ueber Graph angelegt werden
- das Anlegen oder Zuordnen soll sichtbar im Setup erfolgen und nicht still im Hintergrund

Erforderlicher Setup-Wizard:

- beim ersten Verbinden einer Mailbox startet ein einmaliger Ordner-Setup
- der Nutzer sieht, welche 4 Status-Ordner benoetigt werden
- der Wizard bietet an: bestehende Ordner zuzuordnen oder fehlende Ordner anzulegen
- ohne vollstaendige Zuordnung fuer `TODO`, `WARTEN`, `TEMP` und `ARCHIV` gilt die Mailbox nicht als Assistant-ready

Empfohlene technische Konfiguration pro Mailbox:

- Mapping `status_folder -> graph_folder_id`
- Speicherung in `assistant_sources.settings_json` oder vergleichbarer Mailbox-Konfiguration
- Folder-IDs muessen gecacht werden und duerfen nicht pro Aktion erneut per Graph aufgeloest werden

Pflicht:

- Folder-ID-Caching pro Mailbox ist kein optionales Optimierungsdetail, sondern Teil der Kernarchitektur
- `move_to_status(...)` und Batch-Aktionen muessen direkt mit gecachten Folder-IDs arbeiten

Beispiel:

- `INBOX -> echter Graph-Inbox-Ordner`
- `TODO -> <graph folder id>`
- `WARTEN -> <graph folder id>`
- `TEMP -> <graph folder id>`
- `ARCHIV -> archive`

### Categories

Outlook Categories werden ueber das Graph-Feld `categories` gesetzt.

Technische Anforderungen:

- Categories muessen tenantweit konsistent benannt sein
- projektbezogene Categories werden bei Bedarf angelegt
- der Assistant darf nur bekannte oder regelkonforme Category-Namen setzen

Noetige Provider-Faehigkeiten:

- Lesen vorhandener Categories
- Setzen von Categories auf Nachrichten
- optional Anlegen neuer Master Categories

### TEMP-Verfallsdatum

Graph bietet dafuer keine fachlich perfekte Standardabstraktion.

Zulaessige Implementierungsoptionen:

1. bevorzugt: separate Assistant-Tracking-Datenbank
2. alternativ: `singleValueExtendedProperty`
3. nur als Fallback: Category `Verfaellt: YYYY-MM-DD`

Empfehlung:

- `expires_at` in eigener Assistant-Persistenz speichern
- zusaetzlich darf eine lesbare Hilfs-Category gesetzt werden, wenn das fuer User sichtbar gewuenscht ist

Begruendung:

- bessere Suche, Reviews und Batch-Verarbeitung
- provider-neutraler
- kein Missbrauch der Kategorien als Datenspeicher

## Verarbeitungslogik

### Reihenfolge der Bewertung

Jede neue oder manuell aufgerufene E-Mail wird in dieser Reihenfolge bewertet:

1. Relevanz
2. Statusentscheidung
3. Category-Zuweisung
4. TEMP-Verfallsdatum
5. Risikopruefung

### 1. Relevanz

Kandidaten fuer Loeschvorschlag:

- offensichtlicher Spam
- irrelevante Newsletter
- rein automatische Systembenachrichtigungen ohne Handlungsbedarf

Wichtige Regel:

- der Assistant loescht nie eigenstaendig ausserhalb explizit erlaubter Low-Risk-Autopilot-Regeln
- im interaktiven Modus ist Loeschen immer bestaetigungspflichtig

### 2. Statusentscheidung

Statusregeln:

- Aktion durch Nutzer noetig -> `TODO`
- externer Ruecklauf offen -> `WARTEN`
- nur zeitlich begrenzt relevant -> `TEMP`
- dokumentationswichtig, aber ohne Aktion -> `ARCHIV`

Konfliktregel:

- wenn unklar zwischen `TODO` und `WARTEN`, rueckfragen
- wenn unklar zwischen `TEMP` und `ARCHIV`, `ARCHIV` bevorzugen

### 3. Category-Zuweisung

Es gilt:

- mindestens eine thematische Category
- optional zusaetzlich `Dringend`
- optional Projekt-Category

Der Assistant soll Category-Vorschlaege begruenden koennen.

### 4. TEMP-Verfallsdatum

Fuer `TEMP` ist immer ein Datum noetig.

Zulaessige Herleitungen:

- explizit vom Nutzer genannt
- eindeutig aus Mailinhalt ableitbar
- bei Unsicherheit Rueckfrage

Ohne belastbares Datum:

- keine finale TEMP-Aktion
- stattdessen Nachfrage oder Vorschlag

### 5. Risikopruefung

Risikostufen:

- `low`: markieren, kategorisieren, in Statusordner verschieben
- `medium`: TEMP mit Datum, projektbezogene Category anlegen
- `high`: loeschen, senden, grosse Batch-Aktionen

Policy-Regeln:

- `delete` immer bestaetigungspflichtig
- Batch-Cleanup immer bestaetigungspflichtig
- neue Projekt-Category optional bestaetigungspflichtig, wenn Namenskonflikt besteht

## Sprachbefehl-zu-Tool-Mapping

Die natuerliche Sprache wird auf explizite Tools gemappt.

### Status-Aktionen

- `Archivieren`, `Erledigt`, `Fertig` -> `move_to_status(status='ARCHIV')`
- `TODO`, `Muss ich noch machen` -> `move_to_status(status='TODO')`
- `Nachverfolgen`, `Warte auf Antwort` -> `move_to_status(status='WARTEN')`
- `Temp bis Ende Juni` -> `move_to_status(status='TEMP', expires_at=...)`
- `Loeschen`, `Weg damit` -> `delete_email(confirmed=false)`

### Category-Aktionen

- `Dringend`, `Ist eilig` -> `add_category(name='Dringend')`
- `Ist eine Rechnung`, `Buchhaltung` -> `add_category(name='Finanzen')`
- `Gehoert zu Projekt Alpha` -> `assign_project_category(name='Projekt: Alpha')`

### Retrieval-Aktionen

- `Zeig mir alles zu Projekt Alpha` -> `search_emails(category='Projekt: Alpha')`
- `Was liegt noch auf TODO?` -> `list_by_status(status='TODO')`
- `Worauf warte ich noch?` -> `list_by_status(status='WARTEN')`
- `Raeum TEMP auf` -> `review_expired_temp()`

### Batch- und Review-Aktionen

- `Verarbeite die neuesten Mails` -> `triage_batch(...)`
- `Pruefe WARTEN` -> `review_waiting()`
- `Wem muss ich nachfassen?` -> `review_waiting_followups()`
- `Pruefe ueberfaellige TEMP-Mails` -> `review_expired_temp()`
- `Zeig vergessene TODOs` -> `review_stale_todos()`

## Ziel-Toolset fuer den Assistant

Das aktuelle Toolset sollte in diese Zielstruktur ueberfuehrt oder erweitert werden.

### Bestehende Tools, die wiederverwendet werden koennen

- `list_emails`
- `search_emails`
- `read_email`
- `read_thread`
- `move_email`
- `delete_email`
- `list_folders`
- `list_mailboxes`
- `count_emails`
- `preview_cleanup`
- `execute_cleanup`
- `undo_last_action`

### Neue oder fachlich klarere Tools

- `move_to_status(status, email_index, confirmed=false)`
- `add_category(email_index, category)`
- `remove_category(email_index, category)`
- `assign_project_category(email_index, project_name)`
- `set_temp_expiry(email_index, expires_at)`
- `classify_email(email_index)`
- `triage_batch(limit, folder='INBOX')`
- `list_by_status(status, mailbox=None)`
- `review_expired_temp(mailbox=None)`
- `review_waiting(mailbox=None)`
- `review_waiting_followups(mailbox=None, older_than_days=5)`
- `review_stale_todos(mailbox=None, older_than_days=7)`
- `search_by_category(category, status=None, query=None)`
- `summarize_batch_result()`

### Tool-Design-Regeln

- Tools bleiben klein und eindeutig
- das LLM darf nicht direkt Folder-IDs oder Graph-Details kennen
- riskante Tools muessen Pending-Intent-Pfade verwenden
- alle Status-Aktionen laufen ueber das interne Statusmodell, nicht direkt ueber freien Zielordnertext

Prioritaetsregel:

- `move_to_status(...)` ist das zentrale Kern-Tool der Mail-Policy
- es soll vor weiteren Spezial-Tools gebaut werden
- langfristig ersetzt es freie `move_email(folder=...)`-Aufrufe fuer Statusbewegungen

## Persistenzanforderungen

Neben den bereits vorhandenen Assistant-Tabellen wird zusaetzliche Persistenz fuer die Mail-Policy benoetigt.

### 1. Mailbox-Status-Konfiguration

Noetig pro Mailbox:

- Zuordnung der 5 Status-Ordner
- optional Name/Farbe/Sichtbarkeit
- Validierungsstatus der Ordner
- gecachte Folder-IDs pro Status
- Setup-Status der Mailbox

Empfohlene Speicherung:

- in `assistant_sources.settings_json`
- spaeter optional als eigene Tabelle

### 2. TEMP-Tracking

Noetig pro TEMP-Mail:

- `message_id`
- `connection_id`
- `expires_at`
- `decision_status`
- `last_reviewed_at`
- `suggested_next_action`

Empfohlene neue Tabelle:

- `assistant_temp_tracking`

### 3. Category-Registry

Noetig:

- bekannte feste Categories pro Tenant
- aktive Projekt-Categories
- Status aktiv/inaktiv
- optional Farbe / Anzeige
- Typ `fixed` oder `project`
- Default-/Systemmarker fuer initiale Vorschlagswerte

Empfohlene neue Tabelle:

- `assistant_category_registry`

### 4. Review-Marker

Noetig fuer wiederkehrende Reviews:

- letzte Pruefung von `WARTEN`
- letzte Pruefung von `TEMP`
- letzte Pruefung von `TODO`

Dies kann spaeter in Scheduler- oder Review-Tabellen aufgehen.

## Policy und Sicherheitsregeln

### Harte Regeln

- nur die 5 Status-Ordner sind zulaessig
- `TEMP` ohne `expires_at` ist verboten
- Loeschen nie ohne serverseitige Bestaetigung
- Category-Namen muessen kanonisch sein
- mehr als 15 aktive Projekt-Categories sind nicht zulaessig

### Weiche Regeln

- bei Unsicherheit nachfragen
- im Zweifel `ARCHIV` statt `DELETE`
- `INBOX` nach Triagierung moeglichst leeren
- woechentliche Reviews aktiv anbieten

### Confirmation-Regeln

Pending-Intent erforderlich fuer:

- `delete_email`
- groessere Cleanup-Batches
- optionale Batch-Loeschvorgaenge
- spaeter auch Massenverschiebungen

Direkt ausfuehrbar:

- Category setzen oder entfernen
- Status nach `TODO`, `WARTEN`, `ARCHIV`
- `TEMP` nur wenn Datum vorhanden

## Lern- und Autopilot-Modell

Das System soll aus wiederkehrenden manuellen Nutzeraktionen lernen.
Lernen bedeutet hier nicht sofortige Vollautomatik, sondern ein gestuftes Vertrauensmodell.

### Ziel

Das System soll:

- wiederkehrende Muster erkennen
- daraus Regelvorschlaege ableiten
- den Nutzer nach einer Regel fragen
- spaeter stabile Regeln automatisch ausfuehren
- alle automatischen Entscheidungen sichtbar und korrigierbar halten

### Lernquellen

Als Beobachtungen zaehlen insbesondere:

- manuelle Verschiebung in `TODO`, `WARTEN`, `TEMP`, `ARCHIV`
- manuelles Loeschen in den Papierkorb
- manuelles Setzen oder Entfernen von Categories
- manuelles Setzen einer Projekt-Category
- manuelles Setzen eines TEMP-Verfallsdatums
- spaetere Korrekturen durch den Nutzer

### Vergleichssignale fuer Muster

Regelbildung darf nicht nur auf einem einzelnen Merkmal beruhen.

Zulaessige Signale:

- gleicher Absender
- gleiche Absender-Domain
- aehnlicher Betreff
- aehnlicher Body-/Snippet-Inhalt
- gleicher Mailtyp
- gleiche bestehende Categories
- gleiche Zielaktion

Negative Signale:

- Nutzer lehnt Vorschlag ab
- Nutzer korrigiert die Aktion spaeter
- Undo / Wiederherstellung nach Autopilot-Aktion
- deutliche inhaltliche Abweichung trotz gleichem Absender

### Vertrauensstufen

#### Stufe 0: Beobachtung

- nur manuelle Aktion
- System speichert Merkmale und Aktion
- keine Regel sichtbar

#### Stufe 1: Vorschlag

Empfohlene Schwelle:

- mindestens 2 aehnliche manuelle Entscheidungen

Verhalten:

- beim naechsten passenden Fall wird ein Vorschlag angezeigt
- der Nutzer bestaetigt oder lehnt ab
- noch keine automatische Ausfuehrung

Beispiel:

- `Ich habe ein Muster erkannt. Solche Mails von X archivierst du meist. Soll ich das tun und eine Regel daraus lernen?`

#### Stufe 2: Vertrauenswuerdige Regel

Empfohlene Schwelle:

- insgesamt 4 bis 5 bestaetigte gleiche Entscheidungen
- keine oder kaum Korrekturen

Verhalten:

- Regel erscheint als `trusted`
- Nutzer kann explizit `autopilot` fuer diese Regel aktivieren
- ohne explizite Freigabe bleibt es bei Vorschlag oder stiller Vorankuendigung

#### Stufe 3: Autopilot

Empfohlene Schwelle:

- explizite Freigabe durch den Nutzer
- stabile positive Historie
- keine haeufigen Korrekturen

Verhalten:

- Regel wird automatisch ausgefuehrt
- Aktion wird im Aktivitaets- und Undo-Kontext sichtbar protokolliert
- optional taegliche oder woechentliche Zusammenfassung

### Risikoklassen fuer Lernregeln

#### Low Risk

- Category setzen oder entfernen
- nach `ARCHIV` verschieben
- nach `TODO` verschieben
- nach `WARTEN` verschieben

Diese Regeln duerfen frueh in `trusted` uebergehen.

#### Medium Risk

- nach `TEMP` verschieben
- TEMP-Datum setzen
- neue Projekt-Category erzeugen oder zuweisen

Diese Regeln brauchen mehr bestaetigte Faelle.

#### High Risk

- in Papierkorb verschieben
- groessere Batch-Cleanup-Aktionen

Diese Regeln duerfen nur mit eigener Nutzerfreigabe auf Autopilot.

### Sonderregel fuer Loeschen

Auch wenn Loeschen zunaechst nur in den Papierkorb verschiebt, bleibt es eine High-Risk-Aktion.

Deshalb:

- Loeschvorschlaege sind lernbar
- Auto-Loeschen in den Papierkorb ist zulaessig
- aber nur mit eigener Freigabe `autopilot_delete_to_trash`
- und nur bei engen, stabilen Mustern

Zusaetzliche Anforderungen:

- taegliche Review oder Report ueber automatisch geloeschte Mails
- Undo / Wiederherstellungspfad soweit technisch moeglich
- Regel wird bei Korrekturen automatisch herabgestuft oder deaktiviert

### Regel-Lebenszyklus

Jede gelernte Regel hat einen expliziten Lebenszyklus:

- `observed`
- `suggested`
- `trusted`
- `autopilot_active`
- `paused`
- `disabled`

Uebergaenge:

- `observed -> suggested`
- `suggested -> trusted`
- `trusted -> autopilot_active`
- `autopilot_active -> paused`
- `paused -> trusted`
- `trusted -> disabled`

### Noetige Regel-Metadaten

Fuer lernbasierte Regeln werden mindestens benoetigt:

- `origin = learned`
- `autonomy_level`
- `risk_level`
- `match_count`
- `confirm_count`
- `reject_count`
- `correction_count`
- `last_matched_at`
- `last_executed_at`
- `last_corrected_at`
- `requires_confirmation`
- `autopilot_allowed`
- `autopilot_active`

### Lernlogik im Produkt

Empfohlene Grundlogik:

- 2 aehnliche manuelle Faelle -> Vorschlag erzeugen
- weitere 2 bis 3 bestaetigte Faelle -> Regel als `trusted`
- danach explizite Freigabe fuer Autopilot moeglich

Wichtige Regel:

- `2x gleich -> beim 3. Mal Vorschlag`
- nicht `2x gleich -> beim 3. Mal automatisch`

### Anpassung bestehender Assistant-Regeln

Der bestehende Regelmechanismus soll in zwei Klassen getrennt werden:

- manuelle Regeln
- gelernte Regeln

Beide sollen im selben Regelbestand sichtbar sein, aber klar gekennzeichnet werden:

- `origin = manual`
- `origin = learned`

Zusaetzlich benoetigt die UI Statusmarker:

- `Vorschlag`
- `Vertrauenswuerdig`
- `Autopilot`
- `Pausiert`

## Regeln-Reiter im Frontend

Ja, der bestehende Reiter `Regeln` ist der richtige Ort fuer:

- Anzeige aller aktiven und inaktiven Regeln
- Anzeige gelernter Regelvorschlaege
- Nachjustieren von Kriterien und Aktionen
- Aktivieren oder Deaktivieren
- Loeschen
- Autopilot-Freigabe pro Regel

### Zielinhalt des Reiters `Regeln`

Der Reiter soll mindestens vier Bereiche enthalten:

#### 1. Aktive Regeln

- alle aktiven manuellen und gelernten Regeln
- Filter nach `manual`, `learned`, `autopilot`
- Status, Prioritaet, Risiko, letzter Treffer

#### 2. Vorschlaege

- neue lernbasierte Regelvorschlaege
- Button `Uebernehmen`
- Button `Ablehnen`
- Button `Nur einmal anwenden`

#### 3. Regel-Details

Beim Oeffnen einer Regel sichtbar:

- Kriterien
- Zielaktion
- Risikostufe
- Herkunft
- Vertrauensstufe
- Trefferanzahl
- Ablehnungen / Korrekturen
- letzter Treffer

#### 4. Autopilot-Verwaltung

- welche Regeln automatisch laufen
- getrennte Schalter fuer `low`, `medium`, `delete_to_trash`
- schnelle Deaktivierung einzelner Regeln

### Bearbeitungsmoeglichkeiten im Reiter `Regeln`

Noetig sind:

- aktivieren / deaktivieren
- pausieren
- loeschen
- Prioritaet aendern
- Match-Kriterien aendern
- Zielaktion aendern
- Risikostufe pruefen
- Autopilot erlauben oder entziehen

## Assistant-Einstellungen

Ja, die vorgeschlagenen Lern- und Autopilot-Parameter gehoeren auch in die Einstellungen.

Sie sollten nicht nur implizit im Code leben, sondern explizit fuer den Nutzer sichtbar sein.

### Empfohlene Einstellungsparameter

#### Lernen allgemein

- `learning_enabled`
- `suggest_rules_enabled`
- `suggest_after_similar_actions`
- `trust_after_confirmed_actions`
- `downgrade_after_corrections`

#### Autopilot allgemein

- `autopilot_enabled`
- `autopilot_low_risk_enabled`
- `autopilot_medium_risk_enabled`
- `autopilot_delete_to_trash_enabled`
- `autopilot_requires_explicit_rule_activation`

#### TEMP- und Review-Logik

- `temp_default_days`
- `temp_review_enabled`
- `waiting_review_enabled`
- `todo_review_enabled`
- `weekly_review_day`

#### Transparenz und Kontrolle

- `daily_autopilot_summary_enabled`
- `show_rule_suggestions_in_chat`
- `show_rule_suggestions_in_rules_tab`
- `auto_pause_rule_on_correction`

### Empfohlene Defaultwerte

- `learning_enabled = true`
- `suggest_rules_enabled = true`
- `suggest_after_similar_actions = 2`
- `trust_after_confirmed_actions = 5`
- `downgrade_after_corrections = 2`
- `autopilot_enabled = false`
- `autopilot_low_risk_enabled = false`
- `autopilot_medium_risk_enabled = false`
- `autopilot_delete_to_trash_enabled = false`
- `autopilot_requires_explicit_rule_activation = true`
- `daily_autopilot_summary_enabled = true`
- `auto_pause_rule_on_correction = true`

## Backend-Erweiterungen fuer Lernen und Regeln

### Neue oder erweiterte Persistenz

Empfohlen:

- bestehende `assistant_rules` um Lern- und Autopilot-Felder erweitern
- eigene Tabelle fuer Regelbeobachtungen oder Verdichtungen
- optionale Tabelle fuer Regelvorschlaege

Moegliche neue Tabellen:

- `assistant_rule_observations`
- `assistant_rule_suggestions`
- optional `assistant_rule_execution_stats`

### Noetige Services

- `RuleObservationService`
- `RuleSuggestionService`
- `RuleTrustService`
- `AutopilotExecutionService`

### Noetige API-Funktionen

- Regelvorschlaege listen
- Vorschlag uebernehmen
- Vorschlag ablehnen
- Regel pausieren
- Autopilot fuer Regel aktivieren
- Autopilot fuer Regel deaktivieren
- Lernstatistiken pro Regel lesen

## Nächste Umsetzungsschritte fuer diesen Bereich

1. bestehende `assistant_rules` um Lern-/Autopilot-Metadaten erweitern
2. Beobachtungslogik aus manuellen Mailaktionen ableiten
3. Vorschlagsmechanik `2x gleich -> Vorschlag` bauen
4. Regeln-Reiter um Vorschlaege, Herkunft und Autopilot-Status erweitern
5. Assistant-Einstellungen um Lern- und Autopilot-Parameter erweitern
6. taegliche und woechentliche Review-Zusammenfassungen integrieren

## Suche und Retrieval

Suche soll drei Ebenen kombinieren:

- Statusfilter
- Category-Filter
- Volltext

### Fachliche Suchparameter

- `status`
- `category`
- `project_category`
- `mailbox`
- `query`
- `unread_only`
- `since`
- `expires_before`

Archiv-spezifische Anforderung:

- Suche in `ARCHIV` muss fuer grosse Datenmengen gesondert optimiert werden
- dafuer sind Statusfilter, Category-Filter und Zeitraumfilter Pflicht
- Graph-`$search` allein reicht fuer grosse Archivmengen nicht als einziges Muster

### Beispiel

Anfrage:

- `Zeig mir alle offenen TODOs zum Projekt Website`

Interne Aufloesung:

- `status='TODO'`
- `category='Projekt: Website'`
- optional `query='Website'`

## Batch- und Review-Funktionen

### Batch-Triage

Ziel:

- mehrere neue Mails aus `INBOX` halbautomatisch einsortieren

Pflichtgrenze:

- maximal 10 Mails pro Batch-Turn
- danach muss der Assistant fragen, ob die naechsten 10 bearbeitet werden sollen

Ablauf:

1. Kandidaten laden
2. fuer jede Mail Status + Categories + optional `expires_at` bestimmen
3. riskante Faelle separieren
4. Batch-Zusammenfassung ausgeben
5. Bestaetigung fuer riskante Teilmengen einholen

### TEMP-Review

Tagesroutine:

- alle abgelaufenen `TEMP`-Mails finden
- je Mail Vorschlag `ARCHIV` oder `DELETE`
- Nutzerbestaetigung bei Loeschvorschlaegen

### WARTEN-Review

Wochenroutine:

- `WARTEN`-Mails nach Alter, letzter Antwort und Dringlichkeit priorisieren
- Rueckfrage oder Erinnerung anbieten

Phase-1-Erweiterung:

- `WARTEN` soll aktive Follow-up-Vorschlaege liefern
- Beispiel: `Du wartest seit 5 Tagen auf Antwort von X. Soll ich dich erinnern oder einen Follow-up-Entwurf vorbereiten?`
- diese Logik gehoert in die erste produktive Version und nicht nur in spaetere Ausbaustufen

### TODO-Review

Wochenroutine:

- alte `TODO`-Mails ohne Bewegung hervorheben
- auflisten und optional neu priorisieren

## Frontend-Anforderungen

Das Frontend braucht neben dem Voice-Chat gezielte Assistenz-Ansichten.

### Im Voice-/Chat-Panel

- sichtbarer aktueller Status der Mail
- sichtbare Categories
- sichtbares `TEMP`-Verfallsdatum
- Pending-Actions fuer Delete und Batch-Cleanup
- Batch-Zusammenfassung nach Verarbeitung

### Zusätzliche Views oder Panels

- `TODO`
- `WARTEN`
- `TEMP Review`
- `Projekt-Categories`
- `Mailbox Policy Settings`

### Nutzerinteraktionen

- Status direkt aendern
- Categories direkt setzen oder entfernen
- TEMP-Datum setzen oder korrigieren
- Projekt-Category bestaetigen oder korrigieren
- Batch-Vorschlaege annehmen oder verwerfen

## Backend-Arbeitsbloecke

### Block 1: Mailbox-Policy-Konfiguration

- 5 Status-Ordner pro Mailbox definieren
- Validierung gegen Graph
- Fehlerbild fuer unvollstaendige Mailbox-Struktur
- Setup-Wizard fuer Zuordnung oder Anlegen der 4 Assistant-Ordner
- Folder-ID-Caching verpflichtend einbauen

### Block 2: Status- und Category-Services

- interne Statusaktionen von rohen Folder-Aktionen trennen
- Category-Service fuer feste und Projekt-Categories einfuehren
- Graph-Zugriffe kapseln
- konfigurierbare Tenant-Categories ueber Registry statt Hardcoding

### Block 3: TEMP-Tracking

- Persistenz fuer `expires_at`
- Review-Query fuer ueberfaellige TEMP-Mails
- Voice- und UI-Aktionen fuer TEMP-Datum

### Block 4: Voice- und Tool-Mapping

- vorhandene Tools auf Statusmodell ausrichten
- neue Tools fuer `move_to_status`, `add_category`, `assign_project_category`
- Batch-Triage-Tools ergaenzen
- `move_to_status(...)` hat Prioritaet vor generischen Folder-Moves

### Block 5: Review-Logik und Scheduler

- Wochenreview fuer `WARTEN`
- aktive Follow-up-Vorschlaege fuer `WARTEN`
- Wochenreview fuer alte `TODO`
- Tagesreview fuer `TEMP`

### Block 6: Frontend-Haertung

- Status/Categories/Expiry im Voice-Panel sichtbar machen
- TEMP-Review und TODO/WARTEN-Listen
- Batch-Ergebnisanzeige

## Test- und Abnahmekriterien

Pflichtfaelle:

- Mail nach `TODO` verschieben
- Mail nach `WARTEN` verschieben
- Mail nach `TEMP` mit Datum verschieben
- `TEMP` ohne Datum wird nicht ausgefuehrt
- Mail nach `ARCHIV` verschieben
- Category `Finanzen` setzen
- Projekt-Category setzen
- Delete erzeugt Pending-Intent
- Suche nach Status + Category funktioniert
- `TEMP`-Review listet abgelaufene Mails
- Batch-Triage liefert Zusammenfassung

Akzeptanzkriterien:

- keine freien Zielordner ausserhalb des 5-Ordner-Modells
- keine `TEMP`-Mail ohne Datum
- keine Loeschung ohne bestaetigten Pending-Intent
- Categories sind konsistent und wiederauffindbar
- Batch-Zusammenfassungen sind nachvollziehbar

## Entscheidungen fuer die erste Umsetzung

Fuer die erste produktive Version werden folgende Entscheidungen empfohlen:

- Microsoft Graph ist der erste voll unterstuetzte Provider
- `TEMP`-Verfallsdatum wird in Assistant-Persistenz gespeichert
- Loeschen bleibt immer bestaetigungspflichtig
- Projekt-Categories werden bei Bedarf dynamisch angelegt, aber bei Namenskonflikten bestaetigt
- `ARCHIV` ist der sichere Default bei Unsicherheit
- feste Categories sind tenantweit konfigurierbar und werden nicht hart kodiert
- Mailboxen werden nur nach erfolgreichem Ordner-Setup als produktiv markiert
- Folder-IDs werden pro Mailbox gecacht
- Batch-Triage arbeitet in festen 10er-Schritten

## Zusätzliche offene Architekturfragen

- soll `Dringend` automatisch wieder entfernt werden koennen, wenn Faelligkeit abgelaufen ist?
- soll `TEMP` optional einen Standardzeitraum pro Mailtyp erhalten?
- sollen Projekt-Categories zentral gepflegt oder aus Nutzung gelernt werden?
- wie sollen Status und Categories mailboxuebergreifend fuer denselben Kontakt oder Thread harmonisiert werden?
- wie reagiert das System auf manuelle Outlook-Aktionen ausserhalb des 5-Ordner-Modells?

## Multi-Mailbox- und Outlook-Konflikte

Diese Spezifikation braucht zusaetzlich klare Regeln fuer zwei reale Betriebsfaelle.

### 1. Multi-Mailbox-Konsistenz

Wenn derselbe Kontakt oder Vorgang ueber mehrere Mailboxen auftaucht, entstehen Fragen wie:

- soll dieselbe Category automatisch in mehreren Mailboxen gesetzt werden?
- soll `TODO` oder `WARTEN` mailboxuebergreifend synchron sein?
- wie werden persoenliche und geteilte Mailboxen gegeneinander priorisiert?

Grundsatz fuer Phase 1:

- Status bleibt zunaechst mailbox-lokal
- Categories koennen spaeter mailboxuebergreifend harmonisiert werden, aber nicht still synchronisiert
- Vorschlaege duerfen mailboxuebergreifende Muster erkennen, automatische Status-Synchronisation erfolgt in Phase 1 jedoch nicht

### 2. Manuelle Outlook-Nutzung ausserhalb des Assistant-Modells

Der Nutzer kann Mails in Outlook manuell in andere Ordner verschieben oder Categories aendern.

Deshalb braucht das System:

- Erkennung unbekannter Zielordner
- Markierung `unknown_status_folder` oder vergleichbares Konfliktsignal
- rueckfuehrbare Re-Synchronisation in das 5-Ordner-Modell
- klare UI-Hinweise statt stiller Inkonsistenz

Grundsatz fuer Phase 1:

- unbekannte manuelle Verschiebungen werden erkannt und sichtbar gemacht
- der Assistant versucht nicht still, den Zustand zu erraten
- der Nutzer kann die Mail wieder einem gueltigen Status zuordnen

## Nächster Umsetzungsschritt

Empfohlener naechster konkreter Schritt im Code:

1. Ordner-Setup-Wizard und Mailbox-Policy-Konfiguration fuer die 5 Status-Ordner einfuehren
2. `move_to_status(...)` als zentrales Assistant-Tool bauen und freie Status-Moves ersetzen
3. Category-Registry fuer tenant-konfigurierbare feste und Projekt-Categories einfuehren
4. TEMP-Tracking-Tabelle und Review-Query anlegen
