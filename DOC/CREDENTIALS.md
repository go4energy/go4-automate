# Zugangsdaten & API-Keys

Übersicht aller externen Accounts und Credentials die für go4.automate benötigt werden.

> **Sicherheitshinweis:** Diese Datei enthält KEINE echten Credentials. Alle Zugangsdaten werden ausschließlich in `config/.env` gespeichert und NIEMALS ins Git-Repository committed.

## Status-Übersicht (Go4 Energy)

| Service | Account | Status | Wo gespeichert |
|---|---|---|---|
| Meta Business Manager | Go4 Energy GmbH | ✅ Eingerichtet | – |
| Meta Developer App | go4-marketing-automation | ✅ App ID + Secret vorhanden | config/.env |
| Meta System User Token | go4-automation-bot | ✅ Token generiert | config/.env |
| Facebook Page | go4.energy (ID: 429505256907828) | ✅ Posting funktioniert | config/tenants/go4energy.env |
| Instagram Business | @go4_energy (ID: 17841470139313765) | ⚠️ Login-Problem, nicht verknüpft | config/tenants/go4energy.env |
| Meta Pixel | – | ❌ Noch nicht erstellt | config/tenants/go4energy.env |
| Meta Ad Account | – | ❌ ID noch nicht dokumentiert | config/tenants/go4energy.env |
| Anthropic (Claude) | – | ❌ API-Key noch anlegen | config/.env |
| OpenAI | – | ❌ API-Key noch anlegen | config/.env |
| OpenWeather | – | ❌ Account noch anlegen | config/.env |
| Hetzner Cloud | – | ❌ Server noch nicht aufgesetzt | – |
| Brevo (E-Mail) | – | ❌ Account noch anlegen | config/.env |
| Domain / DNS | go4.energy | ✅ Vorhanden | DNS-Provider |

## Benötigte Credentials pro Service

### Meta (Facebook/Instagram/Ads)
```
META_APP_ID=               # Developer Portal → App → Settings → Basic
META_APP_SECRET=           # Developer Portal → App → Settings → Basic → Show
META_SYSTEM_USER_TOKEN=    # Business Manager → System Users → Generate Token
META_PAGE_ID=              # Graph API: /me/accounts
META_INSTAGRAM_BUSINESS_ID=# Graph API: /{page_id}?fields=instagram_business_account
META_PIXEL_ID=             # Events Manager → Data Sources → Pixel ID
META_AD_ACCOUNT_ID=        # Business Manager → Ad Accounts (Format: act_XXXXXXX)
META_API_VERSION=v21.0     # Aktuellste stabile Version
```

**Wie Token erneuern:** System User Tokens laufen nicht ab. Falls ein neuer Token nötig ist: Business Manager → System Users → go4-automation-bot → Generate New Token (alter Token wird ungültig).

### Anthropic (Claude API)
```
ANTHROPIC_API_KEY=sk-ant-...  # console.anthropic.com → API Keys
```
**Kosten:** ~$3/1M Input Tokens, ~$15/1M Output Tokens (Claude Sonnet). Geschätzt €20-50/Monat bei 5 Posts/Woche + Analyse.

### OpenAI (optional)
```
OPENAI_API_KEY=sk-...  # platform.openai.com → API Keys
```
**Verwendung:** Nur für günstige Aufgaben (Lead-Scoring, Klassifikation). GPT-4o-mini: ~$0.15/1M Input Tokens.

### OpenWeather
```
OPENWEATHER_API_KEY=...  # openweathermap.org → API Keys
```
**Kosten:** Kostenlos bis 1.000 Calls/Tag (wir brauchen ~10/Tag).

**Registrierung:** https://home.openweathermap.org/users/sign_up → nach Login unter "API Keys".

### Brevo (E-Mail-Versand)
```
SMTP_HOST=smtp-relay.brevo.com
SMTP_PORT=587
SMTP_USER=...            # Brevo Login-E-Mail
SMTP_PASSWORD=...        # Brevo → Settings → SMTP → Key generieren
```
**Kosten:** Kostenlos bis 300 E-Mails/Tag. Starter: €9/Monat für 5.000 E-Mails.

**Registrierung:** https://www.brevo.com/

### Hetzner Cloud
```
# Kein API-Key nötig für Basis-Setup
# Optional für automatisiertes Server-Management:
HETZNER_API_TOKEN=...    # Hetzner Cloud Console → API Tokens
```
**Kosten:** CX31 (4 vCPU, 8 GB RAM): ~€10.59/Monat

### Domain & DNS
- Domain vorhanden: go4.energy
- Subdomain für Plattform: automate.go4.energy
- A-Record auf Server-IP setzen

## Checkliste für neuen Tenant

Wenn ein neuer Kunde ongeboardet wird, sind folgende Credentials nötig:

- [ ] Facebook Page erstellt/vorhanden
- [ ] Instagram Business Account erstellt/vorhanden
- [ ] Beides im Business Manager verknüpft
- [ ] System User hat Zugriff auf Page + Instagram + Ad Account
- [ ] Page ID notiert
- [ ] Instagram Business ID notiert
- [ ] Meta Pixel erstellt und ID notiert
- [ ] Ad Account erstellt/vorhanden und ID notiert
- [ ] Pixel auf Kunden-Website installiert
- [ ] Tenant-Config erstellt (config/tenants/[id].env)
- [ ] Tenant in DB registriert
- [ ] n8n Workflows konfiguriert
- [ ] Test-Post veröffentlicht
- [ ] Conversion-Tracking getestet
