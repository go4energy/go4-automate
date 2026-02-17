# Meta Developer & API Setup

Diese Anleitung beschreibt die vollständige Einrichtung des Meta-Ökosystems für go4.automate: Business Manager, Developer App, Graph API, Conversion API und Marketing API.

## Übersicht: Was wird gebraucht?

```
Meta Business Manager
├── Facebook Page (z.B. "go4.energy")
├── Instagram Business Account (@go4_energy)
├── Meta Pixel (für Conversion-Tracking)
├── Ad Account (für Werbeanzeigen)
└── System User (für API-Zugriff)
     └── System User Token (mit allen Berechtigungen)

Meta Developer Portal
└── Business App ("go4-marketing-automation")
    ├── App ID
    ├── App Secret
    └── Products: Marketing API, Instagram Graph API
```

## Schritt 1: Meta Business Manager

**URL:** https://business.facebook.com/settings

1. Business Manager erstellen (falls nicht vorhanden)
2. Facebook Page hinzufügen: Einstellungen → Accounts → Pages → Add
3. Instagram Account verknüpfen: Einstellungen → Accounts → Instagram Accounts → Add
4. Ad Account erstellen/hinzufügen: Einstellungen → Accounts → Ad Accounts
5. Pixel erstellen: Events Manager → Connect Data Sources → Web → Meta Pixel

**Wichtig:** Die Facebook Page muss als "Owner" dem Business Manager gehören, nicht nur "Linked" sein.

## Schritt 2: Meta Developer App

**URL:** https://developers.facebook.com/apps/

1. "Create App" → Business Type → "Other"
2. App Type: "Business"
3. Name: `go4-marketing-automation`
4. Business Manager Account auswählen
5. App erstellen

**Products hinzufügen:**
- Marketing API → Set Up
- Instagram Graph API → Set Up (wenn Instagram verknüpft)

**App Settings → Basic:**
- App ID notieren
- App Secret notieren (Show → kopieren)

## Schritt 3: System User erstellen

**URL:** https://business.facebook.com/settings/system-users

1. "Add" → Name: `go4-automation-bot` → Role: Admin
2. "Add Assets" → Pages → eure Facebook Page → Full Control
3. "Add Assets" → Ad Accounts → euer Ad Account → Full Control
4. "Add Assets" → Instagram Accounts → euer Instagram Account → Full Control
5. "Generate New Token" → App: `go4-marketing-automation`

**Benötigte Berechtigungen beim Token generieren:**
```
pages_manage_posts          # Posts auf Facebook erstellen
pages_read_engagement       # Engagement-Daten lesen
pages_read_user_content     # User-Content auf Page lesen
instagram_basic             # Instagram Basiszugriff
instagram_content_publish   # Instagram Posts erstellen
ads_management              # Werbeanzeigen verwalten
ads_read                    # Werbedaten lesen
business_management         # Business Manager Zugriff
read_insights               # Insights/Analytics lesen
```

6. Token kopieren und sicher speichern (wird nur einmal angezeigt!)

## Schritt 4: IDs sammeln

### Facebook Page ID
```bash
curl "https://graph.facebook.com/v21.0/me/accounts?access_token=DEIN_TOKEN"
```
→ `id` Feld in der Response

### Instagram Business Account ID
```bash
curl "https://graph.facebook.com/v21.0/DEINE_PAGE_ID?fields=instagram_business_account&access_token=DEIN_TOKEN"
```
→ `instagram_business_account.id`

### Ad Account ID
Business Manager → Einstellungen → Ad Accounts → ID kopieren (Format: `act_XXXXXXXXX`)

### Pixel ID
Events Manager → Data Sources → Pixel auswählen → ID kopieren

## Schritt 5: Token testen

```bash
# Token-Info (Ablaufdatum, Berechtigungen)
curl "https://graph.facebook.com/v21.0/debug_token?input_token=DEIN_TOKEN&access_token=DEIN_TOKEN"

# Facebook Page testen
curl "https://graph.facebook.com/v21.0/DEINE_PAGE_ID?fields=name,fan_count&access_token=DEIN_TOKEN"

# Instagram testen
curl "https://graph.facebook.com/v21.0/DEINE_IG_ID?fields=username,followers_count&access_token=DEIN_TOKEN"

# Test-Post auf Facebook (Vorsicht: wird veröffentlicht!)
curl -X POST "https://graph.facebook.com/v21.0/DEINE_PAGE_ID/feed" \
  -d "message=Test-Post via API 🚀" \
  -d "access_token=DEIN_TOKEN"
```

## Schritt 6: Meta Pixel installieren

### Option A: Manuell (auf Kunden-Website)
```html
<!-- Im <head> der Website -->
<script>
  !function(f,b,e,v,n,t,s)
  {if(f.fbq)return;n=f.fbq=function(){n.callMethod?
  n.callMethod.apply(n,arguments):n.queue.push(arguments)};
  if(!f._fbq)f._fbq=n;n.push=n;n.loaded=!0;n.version='2.0';
  n.queue=[];t=b.createElement(e);t.async=!0;
  t.src=v;s=b.getElementsByTagName(e)[0];
  s.parentNode.insertBefore(t,s)}(window, document,'script',
  'https://connect.facebook.net/en_US/fbevents.js');
  fbq('init', 'DEINE_PIXEL_ID');
  fbq('track', 'PageView');
</script>
```

### Option B: Über go4.automate (empfohlen)
Das System generiert ein erweitertes Snippet das zusätzlich zum Browser-Pixel auch Server-Side Events sendet:
```bash
curl https://automate.deine-domain.de/api/ads/pixel-snippet?tenant_id=go4energy
```
Dieses Snippet enthält das Standard-Pixel PLUS automatisches Server-Event-Forwarding an die Conversion API.

### Events auf der Website auslösen
```html
<!-- Automatisch via data-Attribute -->
<button data-track="Lead" data-value="Konfigurator abgeschlossen">
  Anfrage senden
</button>

<a href="/konfigurator" data-track="InitiateCheckout" data-value="PV Konfigurator">
  Konfigurator starten
</a>

<!-- Oder manuell via JavaScript -->
<script>
  // Nach Formular-Absendung
  window.go4Track('Lead', {
    content_name: 'Kontaktformular',
    value: 15000,
    currency: 'EUR'
  });
</script>
```

## Schritt 7: Conversion API testen

```bash
# Test-Event senden
curl -X POST "https://graph.facebook.com/v21.0/DEINE_PIXEL_ID/events" \
  -d "access_token=DEIN_TOKEN" \
  -d 'data=[{
    "event_name": "Lead",
    "event_time": 1700000000,
    "action_source": "website",
    "user_data": {
      "em": ["309a0a5c3e211326ae75ca18196d301a9bdbd1a882a4d2569511033da23f0abd"]
    },
    "custom_data": {
      "value": 15000,
      "currency": "EUR"
    }
  }]'
```

**Prüfen:** Events Manager → Data Sources → Pixel → Events → "Server" Events sollten erscheinen.

## Häufige Probleme

| Problem | Lösung |
|---|---|
| Token abgelaufen | System User Tokens laufen nicht ab (anders als User Tokens). Falls doch: neuen generieren. |
| "Invalid OAuth access token" | Token kopieren und im Debugger prüfen: https://developers.facebook.com/tools/debug/accesstoken/ |
| Instagram "Login needed" | Instagram Account muss über die Instagram App mit der Facebook Page verknüpft werden. Einstellungen → Accounts Center → Add Facebook Account. |
| "Unsupported post request" | Berechtigungen prüfen – fehlt `pages_manage_posts`? |
| Pixel Events kommen nicht an | Browser-Adblocker deaktivieren. Server-Events prüfen in Events Manager → Test Events. |
| Ad Account Spending Limit | Business Manager → Ad Accounts → Spending Limit erhöhen/entfernen. |

## Nützliche URLs

| Tool | URL |
|---|---|
| Business Manager | https://business.facebook.com/settings |
| Developer Portal | https://developers.facebook.com/apps/ |
| Graph API Explorer | https://developers.facebook.com/tools/explorer/ |
| Access Token Debugger | https://developers.facebook.com/tools/debug/accesstoken/ |
| Events Manager (Pixel) | https://business.facebook.com/events_manager/ |
| Meta Marketing API Docs | https://developers.facebook.com/docs/marketing-apis/ |
| Conversion API Docs | https://developers.facebook.com/docs/marketing-api/conversions-api/ |
