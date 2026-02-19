# Integrationen

## Beschreibung
Externe Dienste die mit go4-automate verbunden werden koennen. Jede Integration hat eigene Credentials und Konfigurationsparameter.

## Verfuegbare Integrationen

### Meta API (Facebook/Instagram)
Fuer Content-Publishing und Ad-Management.
| Parameter | Beschreibung | Env-Variable |
|-----------|-------------|-------------|
| System User Token | Langlebiger API-Token | META_SYSTEM_USER_TOKEN |
| Page ID | Facebook-Seiten-ID | META_PAGE_ID |
| Instagram Business ID | Instagram-Account-ID | META_INSTAGRAM_BUSINESS_ID |
| Ad Account ID | Werbekonto-ID | META_AD_ACCOUNT_ID |
| Pixel ID | Facebook-Pixel-ID | META_PIXEL_ID |

### SMTP (E-Mail)
Fuer E-Mail-Benachrichtigungen und Reports.
| Parameter | Beschreibung | Env-Variable |
|-----------|-------------|-------------|
| Host | SMTP-Server | SMTP_HOST |
| Port | SMTP-Port | SMTP_PORT |
| User | Benutzername | SMTP_USER |
| Password | Passwort | SMTP_PASSWORD |
| From | Absender-Adresse | SMTP_FROM |

### OpenWeather API
Fuer Weather-Boost im Ad-Management.
| Parameter | Beschreibung | Env-Variable |
|-----------|-------------|-------------|
| API Key | OpenWeather API Key | OPENWEATHER_API_KEY |

### Serper API (Web-Suche)
Fuer Research-Modul Web-Suchen.
| Parameter | Beschreibung | Env-Variable |
|-----------|-------------|-------------|
| API Key | Serper API Key | SERPER_API_KEY |

### n8n (Workflow-Automatisierung)
Workflow-Engine fuer automatische Pipelines.
| Parameter | Beschreibung | Env-Variable |
|-----------|-------------|-------------|
| URL | n8n-Server-URL | N8N_URL |
| API Key | n8n API Key | N8N_API_KEY |

## Verfuegbare Tools
- `check_integration_status` — Pruefen welche Integrationen konfiguriert sind
- `get_current_config` — Aktuelle Konfiguration lesen

## Typische Fragen fuer den Benutzer
1. Haben Sie bereits eine Facebook-Seite und/oder einen Instagram-Business-Account?
2. Moechten Sie automatisch auf Social Media posten?
3. Benoetigen Sie E-Mail-Benachrichtigungen?
4. Moechten Sie Weather-Boost fuer Ihre Ads nutzen?

## Hinweise
- API-Keys und Tokens werden aus Sicherheitsgruenden nicht im Chat angezeigt
- Der Status-Check zeigt nur ob eine Integration konfiguriert ist, nicht die Credentials selbst
- Credentials muessen manuell in der .env-Datei oder ueber die Verwaltung eingetragen werden
