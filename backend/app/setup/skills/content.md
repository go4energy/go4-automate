# Content Pipeline

## Beschreibung
Automatische Erstellung und Verwaltung von Social-Media-Content. Posts werden per KI generiert, vom Benutzer geprueft und dann automatisch publiziert.

## Konfigurierbare Parameter
| Parameter | Beschreibung | Typ | Beispiel | Default |
|-----------|-------------|-----|---------|---------|
| CONTENT_PLATFORMS | Aktive Plattformen | string | linkedin,facebook,instagram | linkedin |
| POSTS_PER_WEEK | Posts pro Woche | int | 3 | 3 |
| CONTENT_THEMES | Themen-Schwerpunkte | string | Branchennews,Tipps,Erfolgsgeschichten | - |
| CONTENT_TYPES | Bevorzugte Post-Typen | string | text,image,carousel | text |
| HASHTAGS_DEFAULT | Standard-Hashtags | string | #Energie #Nachhaltigkeit | - |
| CTA_DEFAULT | Standard Call-to-Action | string | Mehr erfahren: [link] | - |
| FUNNEL_STAGES | Aktive Funnel-Stufen | string | awareness,consideration,decision | awareness,consideration |
| POSTING_TIMES | Bevorzugte Posting-Zeiten | string | 09:00,12:00,17:00 | 09:00 |
| CONTENT_TONE | Tonalitaet | string | professionell, locker | professionell |
| MAX_HASHTAGS | Max. Hashtags pro Post | int | 5 | 5 |

## Verfuegbare Tools
- `get_current_config` — Aktuelle Content-Konfiguration lesen
- `update_content_config` — Content-Parameter aktualisieren

## Workflow
1. **Generierung**: n8n-Workflow oder manuell → KI erstellt Post-Entwurf
2. **Review**: Post erscheint als "draft" im Content-Dashboard
3. **Freigabe**: Benutzer prueft und gibt frei (Status → approved)
4. **Publishing**: n8n-Workflow publiziert freigegebene Posts via Meta API
5. **Tracking**: Engagement-Daten werden zurueckgeholt

## Typische Fragen fuer den Benutzer
1. Auf welchen Plattformen moechten Sie aktiv sein?
2. Wie viele Posts pro Woche sind realistisch?
3. Welche Themen sollen abgedeckt werden?
4. Sollen Posts eher informativ, unterhaltsam oder verkaufsfoerdernd sein?
5. Gibt es bestimmte Hashtags die immer verwendet werden sollen?
6. Zu welchen Zeiten soll gepostet werden?

## Branchenspezifische Empfehlungen
- **B2B (Energie, IT, Beratung)**: LinkedIn-Fokus, 2-3 Posts/Woche, professioneller Ton, Thought Leadership
- **B2C (Handwerk, Einzelhandel)**: Facebook+Instagram, 3-5 Posts/Woche, lockerer Ton, Bilder wichtig
- **Allgemein**: Mix aus 60% Mehrwert, 30% Engagement, 10% Promotion
