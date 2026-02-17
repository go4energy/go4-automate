# Multi-Tenant Konfiguration

## Konzept

go4.automate ist von Grund auf multi-tenant-fähig. Jeder Kunde (Tenant) wird durch eine eigene Konfigurationsdatei unter `config/tenants/` definiert. Das System kann beliebig viele Tenants parallel bedienen – alle auf derselben Installation.

### Wie Tenant-Isolation funktioniert

```
Request kommt rein
  → Header: X-Tenant-ID: go4energy
  → Middleware lädt config/tenants/go4energy.env
  → Alle DB-Queries filtern nach tenant_id = 'go4energy'
  → LLM-Prompts werden mit Tenant-Kontext angereichert
  → Response enthält nur Daten dieses Tenants
```

Jeder Tenant hat:
- Eigene Konfiguration (Tonalität, Zielgruppe, Themen)
- Eigene Daten in der DB (gefiltert per tenant_id)
- Eigene Meta-API-Credentials (Page, Pixel, Ad Account)
- Eigene Content-Themen und Posting-Frequenz
- Eigene Budget-Limits und Optimierungsregeln

## Neuen Tenant anlegen

### 1. Konfigurationsdatei erstellen
```bash
cd /opt/go4.automate
cp config/tenants/default.env config/tenants/mein-kunde.env
nano config/tenants/mein-kunde.env
```

### 2. Tenant in DB registrieren
```bash
curl -X POST https://automate.deine-domain.de/api/tenants \
  -H "Content-Type: application/json" \
  -d '{
    "tenant_id": "mein-kunde",
    "tenant_name": "Mein Kunde GmbH",
    "active": true
  }'
```

### 3. n8n Workflows duplizieren
Für jeden Tenant werden die n8n Workflows dupliziert mit dem jeweiligen `X-Tenant-ID` Header. Alternativ: ein einziger Workflow der alle aktiven Tenants durchläuft.

## Konfigurationsdatei (komplett)

```bash
# ============================================================
# Tenant-Konfiguration: [Firmenname]
# Datei: config/tenants/[tenant-id].env
# ============================================================

# ---- Identifikation ----
TENANT_ID=go4energy
TENANT_NAME="Go4 Energy GmbH"
TENANT_WEBSITE=https://www.go4.energy
TENANT_ACTIVE=true

# ---- Branche & Positionierung ----
TENANT_INDUSTRY=photovoltaik
TENANT_REGION="Unterfranken, Bayern"
TENANT_CITY="Schweinfurt"
TARGET_AUDIENCE="Eigenheimbesitzer, 35-60 Jahre"
TARGET_REGION="Schweinfurt, Würzburg, Bamberg – 50km Radius"
PRODUCT_USP="Regionale Experten seit 2018, über 500 Anlagen installiert"

# ---- Content & Tonalität ----
BRAND_TONE=kompetent-nahbar
# Optionen: kompetent-nahbar, professionell-sachlich, locker-freundlich, premium-exklusiv

CONTENT_LANGUAGE=de
CONTENT_POSTS_PER_WEEK=5
CONTENT_PLATFORMS=facebook,instagram
# Optionen: facebook, instagram, linkedin

CONTENT_THEMES="Referenzprojekte Unterfranken,Strompreis-Updates,KfW Förderung,Speicher ja/nein,Wallbox-Kombi"
# Komma-separiert, werden in Rotation durchlaufen

CONTENT_AVOID="Greenwashing,übertriebene Versprechen,Konkurrenz schlecht reden,Politik"
# Themen/Stile die vermieden werden sollen

CONTENT_CTA_DEFAULT="Jetzt kostenlos beraten lassen"
CONTENT_HASHTAGS_BASE="#photovoltaik #solaranlage #schweinfurt #unterfranken #go4energy"

# ---- Meta / Facebook / Instagram ----
META_PAGE_ID=429505256907828
META_PAGE_NAME="go4.energy"
META_INSTAGRAM_BUSINESS_ID=17841470139313765
META_INSTAGRAM_USERNAME=go4_energy
META_PIXEL_ID=<pixel-id>
META_AD_ACCOUNT_ID=act_XXXXXXXXX
# Token wird zentral in config/.env verwaltet, nicht pro Tenant
# (es sei denn, verschiedene Business Manager)

# ---- Ad-Management ----
ADS_ENABLED=true
ADS_TARGET_CPL=12
ADS_MAX_CPL=22
ADS_DAILY_BUDGET_MIN=20
ADS_DAILY_BUDGET_MAX=100

# ---- Wetter-Boost ----
ADS_WEATHER_BOOST_ENABLED=true
ADS_WEATHER_BOOST_FACTOR=1.5
WEATHER_LAT=50.05
WEATHER_LON=10.23

# ---- Lead-Nurturing ----
NURTURE_ENABLED=true
NURTURE_SEQUENCE=6-step-pv
# Optionen: 6-step-pv, 6-step-waermepumpe, 6-step-generic
NURTURE_FROM_NAME="Thomas von Go4 Energy"
NURTURE_FROM_EMAIL=thomas@go4.energy

# ---- E-Mail ----
EMAIL_REPLY_TO=info@go4.energy
EMAIL_SIGNATURE="Thomas Müller | Go4 Energy GmbH | Tel: 09721 123456"

# ---- Benachrichtigungen ----
NOTIFY_EMAIL=admin@go4.energy
NOTIFY_SLACK_WEBHOOK=<optional>
NOTIFY_ON_NEW_LEAD=true
NOTIFY_ON_AD_ALERT=true
NOTIFY_ON_CONTENT_READY=true

# ---- CRM-Integration (optional) ----
CRM_TYPE=none
# Optionen: none, hubspot, pipedrive, zoho
CRM_API_KEY=<optional>
```

## Branchenspezifische Templates

### Photovoltaik
```bash
TENANT_INDUSTRY=photovoltaik
CONTENT_THEMES="Referenzprojekte,Strompreis-Updates,KfW Förderung,Speicher ja/nein,Wallbox-Kombi,Mieterstrom,Balkonkraftwerk,Wärmepumpe-PV-Kombi"
ADS_TARGET_CPL=12
ADS_MAX_CPL=22
ADS_WEATHER_BOOST_ENABLED=true
```

### Wärmepumpen
```bash
TENANT_INDUSTRY=waermepumpe
CONTENT_THEMES="Referenzprojekte,Förderung BEG,Verbrauchsvergleich,Altbau-Sanierung,Luft-Wasser vs Sole,Hybridheizung,Betriebskosten,Schallschutz"
ADS_TARGET_CPL=18
ADS_MAX_CPL=30
ADS_WEATHER_BOOST_ENABLED=false
```

### Dachdecker
```bash
TENANT_INDUSTRY=dachdecker
CONTENT_THEMES="Referenzprojekte,Sturmschaden,Dachsanierung,Flachdach,Dachfenster,Energieberatung,Fassade,Förderung"
ADS_TARGET_CPL=15
ADS_MAX_CPL=25
ADS_WEATHER_BOOST_ENABLED=false
```

## Tenant-übergreifendes Reporting

Als Plattformbetreiber siehst du im Admin-Dashboard:

| Metrik | Beschreibung |
|---|---|
| Aktive Tenants | Wie viele Kunden sind aktiv |
| Posts diese Woche (gesamt) | Über alle Tenants summiert |
| Gesamte Ad-Ausgaben | Alle Tenants zusammen |
| Durchschnittlicher CPL | Über alle Tenants |
| Alerts | Welche Tenants haben Probleme |
