# go4-automate Plattform

## Beschreibung
go4-automate ist eine Marketing-Automatisierungsplattform fuer kleine und mittlere Unternehmen. Sie automatisiert Content-Erstellung, Social-Media-Publishing, Ad-Management und Lead-Generierung.

## Module

### 1. Tenant / Unternehmen
Grundkonfiguration des Unternehmens: Name, Branche, Zielgruppe, Tonalitaet, Sprache. Bildet die Basis fuer alle anderen Module.

### 2. Research Agent
Automatische Recherche relevanter Brancheninformationen. RSS-Feeds, Website-Scraping, Web-Suche. Generiert Themenvorschlaege fuer Content.

### 3. Content Pipeline
Automatische Erstellung von Social-Media-Posts. Unterstuetzt LinkedIn, Facebook, Instagram. Workflow: Generieren → Pruefen → Freigeben → Publizieren.

### 4. Ad Management
Verwaltung von Meta Ads (Facebook/Instagram). Budget-Optimierung, Weather-Boost, Performance-Tracking, automatische Reports.

### 5. Integrationen
Externe Dienste: Meta API (Publishing + Ads), SMTP (E-Mail), n8n (Workflow-Automatisierung), Serper (Web-Suche), OpenWeather (Wetter-Daten).

### 6. Prompt Registry
Verwaltung der KI-Prompts fuer Content-Generierung und Analyse. Versioniert, pro Tenant konfigurierbar.

## Empfohlene Setup-Reihenfolge
1. Unternehmensdaten konfigurieren (Tenant)
2. Research-Quellen einrichten
3. Content-Strategie definieren
4. Integrationen verbinden (Meta API etc.)
5. Ad-Management konfigurieren (optional)

## Allgemeine Regeln fuer den Setup-Assistenten
- Immer auf Deutsch antworten
- Sinnvolle Defaults vorschlagen basierend auf Branche
- Vor jeder Aenderung kurz bestaetigen lassen
- Nach Abschluss eines Moduls zum naechsten ueberleiten
- Technische Details nur wenn gefragt
