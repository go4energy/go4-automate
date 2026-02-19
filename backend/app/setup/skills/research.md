# Research Agent

## Beschreibung
Automatische Recherche relevanter Brancheninformationen. Findet aktuelle Artikel, Trends und Nachrichten. Generiert daraus Themenvorschlaege fuer die Content-Pipeline.

## Quellen-Typen
| Typ | Beschreibung | Beispiel |
|-----|-------------|---------|
| rss | RSS/Atom Feed | https://www.pv-magazine.de/feed/ |
| website | Website-Scraping | https://www.energieinstitut.at/aktuelles |
| websearch | Web-Suche via Serper API | Keywords: Photovoltaik Foerderung 2025 |

## Konfigurierbare Parameter pro Quelle
| Parameter | Beschreibung | Typ | Default |
|-----------|-------------|-----|---------|
| name | Name der Quelle | string | - |
| url | URL (RSS/Website) oder leer bei websearch | string | - |
| source_type | rss, website, websearch | string | rss |
| keywords | Filter-Keywords | list[string] | [] |
| fetch_interval_hours | Abruf-Intervall in Stunden | int | 24 |
| active | Quelle aktiv? | bool | true |

## Verfuegbare Tools
- `list_research_sources` — Alle Quellen auflisten
- `create_research_source` — Neue Quelle anlegen
- `delete_research_source` — Quelle entfernen

## Typische Fragen fuer den Benutzer
1. Welche Branchenportale oder Nachrichtenquellen lesen Sie regelmaessig?
2. Gibt es bestimmte Themen oder Keywords, die Sie verfolgen moechten?
3. Wie oft sollen neue Inhalte gesucht werden?
4. Moechten Sie auch Web-Suchen fuer bestimmte Begriffe einrichten?

## Branchenspezifische Empfehlungen
- **Photovoltaik/Energie**:
  - RSS: pv-magazine.de, energiezukunft.eu, solarserver.de
  - Keywords: Photovoltaik, Solarenergie, Speicher, Foerderung, EEG, Waermepumpe
  - Websearch: "Photovoltaik Foerderung [Region] [Jahr]"
- **IT/Software**:
  - RSS: heise.de, golem.de, t3n.de
  - Keywords: Digitalisierung, KI, Cloud, Security
- **Handwerk**:
  - RSS: handwerk-magazin.de, deutsche-handwerks-zeitung.de
  - Keywords: Fachkraeftemangel, Foerderung, Ausbildung
- **Immobilien**:
  - RSS: immobilienscout24.de/magazin, haufe.de/immobilien
  - Keywords: Immobilienmarkt, Zinsen, Bauvorschriften
