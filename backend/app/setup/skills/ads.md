# Ad Management

## Beschreibung
Verwaltung von Meta Ads (Facebook/Instagram Werbeanzeigen). Budget-Optimierung, Weather-Boost fuer wetterabhaengige Branchen, Performance-Tracking.

## Konfigurierbare Parameter
| Parameter | Beschreibung | Typ | Beispiel | Default |
|-----------|-------------|-----|---------|---------|
| ADS_MONTHLY_BUDGET | Monatsbudget in EUR | float | 500.0 | 0 |
| ADS_TARGET_CPL | Ziel-Cost-per-Lead in EUR | float | 15.0 | 20.0 |
| ADS_WEATHER_BOOST_ENABLED | Weather-Boost aktiv | bool | true | false |
| ADS_WEATHER_BOOST_TEMP_THRESHOLD | Temperatur-Schwelle fuer Boost (Celsius) | int | 20 | 25 |
| ADS_WEATHER_BOOST_MULTIPLIER | Budget-Multiplikator bei gutem Wetter | float | 1.5 | 1.3 |
| ADS_CAMPAIGN_OBJECTIVES | Kampagnen-Ziele | string | lead_generation,traffic | lead_generation |
| ADS_TARGET_LOCATIONS | Ziel-Regionen fuer Ads | string | AT,DE | AT |
| ADS_MIN_AGE | Mindest-Alter Zielgruppe | int | 25 | 18 |
| ADS_MAX_AGE | Hoechst-Alter Zielgruppe | int | 65 | 65 |

## Verfuegbare Tools
- `get_current_config` — Aktuelle Ad-Konfiguration lesen
- `update_ads_config` — Ad-Parameter aktualisieren
- `check_integration_status` — Meta Ads API Status pruefen

## Voraussetzungen
- Meta Business Account mit Ad Account
- Meta API Credentials (System User Token, Ad Account ID, Pixel ID)
- Diese werden unter "Integrationen" konfiguriert

## Typische Fragen fuer den Benutzer
1. Haben Sie bereits ein Meta Ads Konto?
2. Wie hoch ist Ihr monatliches Werbebudget?
3. Was ist Ihr Ziel-CPL (Cost per Lead)?
4. In welchen Regionen soll geworben werden?
5. Ist Ihr Geschaeft wetterabhaengig (z.B. Photovoltaik)?
6. Welche Altersgruppe ist Ihre Zielgruppe?

## Branchenspezifische Empfehlungen
- **Photovoltaik**: Weather-Boost aktivieren (Temp>20°C → mehr Budget), Target CPL 10-20 EUR
- **Waermepumpe**: Weather-Boost invers (kalt → mehr Budget), Target CPL 15-25 EUR
- **IT/Software**: Kein Weather-Boost, LinkedIn Ads bevorzugt, Target CPL variabel
- **Handwerk regional**: Kleine Budgets (200-500 EUR/Monat), enge Geo-Targetierung
