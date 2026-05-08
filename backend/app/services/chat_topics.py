"""Topic registry for context-aware help chats.

Each topic adds a curated docs snippet to the system prompt so Claude
knows the specifics of that screen / feature. Frontend declares which
topics are relevant on the current page; user clicks a topic-chip in
the chat panel to start (or resume) a conversation tagged with it.
"""

from __future__ import annotations

# Topic ID -> (title shown to user, docs snippet appended to system prompt)
TOPICS: dict[str, tuple[str, str]] = {
    "provider-aws-ses": (
        "AWS SES Provider einrichten",
        """Der User richtet einen AWS-SES-Provider für E-Mail-Versand ein.

WICHTIGE SCHRITTE bei der AWS-SES-Einrichtung:
1. AWS-Account anlegen, Region eu-central-1 (Frankfurt) für DSGVO
2. SES Console -> Identities -> Domain verifizieren (smartladen.de)
3. DNS-Records bei Strato/IONOS eintragen:
   - 3 DKIM-CNAMEs (auf abc._domainkey.smartladen.de)
   - SPF-TXT auf smartladen.de: v=spf1 include:amazonses.com ~all (bei mehreren Sendern KOMBINIEREN, nicht zwei Records anlegen)
   - DMARC-TXT auf _dmarc.smartladen.de: v=DMARC1; p=none; rua=mailto:dmarc@smartladen.de
   - MX auf mail.smartladen.de: 10 feedback-smtp.eu-central-1.amazonses.com
4. Production-Access beantragen (sonst nur 200/Tag, nur an verifizierte Adressen)
5. IAM-User mit AmazonSESFullAccess anlegen -> Access Key ID + Secret Access Key
6. In go4-automate die 4 Felder ausfüllen: Access Key ID, Secret Access Key, Region (eu-central-1), optional Configuration Set

HÄUFIGE PROBLEME:
- "Email address is not verified" -> Sandbox-Mode, entweder Empfänger verifizieren oder Production-Access beantragen
- DKIM "Pending" -> DNS-Propagation warten (5-30 Min, manchmal 1-2h)
- Production-Access abgelehnt -> AWS ist streng bei Cold-Outreach. Brevo ist toleranter.

ZUR DSGVO: Region eu-central-1 hostet Mails in Frankfurt. AWS schließt AVV.""",
    ),
    "provider-brevo": (
        "Brevo Provider einrichten",
        """Der User richtet einen Brevo-Provider (ehemals Sendinblue) ein.
Brevo ist EU-gehostet (Paris) und toleranter bei B2B-Outreach als AWS SES.

SETUP-SCHRITTE:
1. Account auf brevo.com anlegen (Free-Tier: 300 Mails/Tag)
2. Senders, Domains & Dedicated IPs -> Domain hinzufügen -> smartladen.de
3. DNS-Records bei Strato/IONOS eintragen (von Brevo angezeigt):
   - brevo-code.smartladen.de  TXT (Verification)
   - mail._domainkey.smartladen.de  TXT (DKIM)
   - SPF-TXT auf smartladen.de mit include:spf.brevo.com (KOMBINIEREN mit existierenden SPF-Records!)
4. SMTP & API -> API Keys -> "Generate a new API key" (Name z.B. "go4-automate")
5. In go4-automate: Provider-Typ "Brevo" wählen, API-Key eintragen (xkeysib-...)

Brevo akzeptiert seriöses B2B-Outreach mit Opt-Out, ist also für Cold-Outreach okay.
Empfänger sieht "Mail von info@smartladen.de" — Brevo signiert mit DKIM für deine Domain.""",
    ),
    "provider-twilio-sendgrid": (
        "Twilio SendGrid Provider einrichten",
        """Der User richtet Twilio SendGrid ein. WICHTIG: SendGrid ist NICHT mehr standalone — seit der Twilio-Akquisition 2019 ist alles in der Twilio-Konsole konsolidiert. Login auf console.twilio.com (NICHT sendgrid.com — leitet zu Twilio um).

VOLLSTÄNDIGE SCHRITT-FÜR-SCHRITT-DOKU:
Liegt unter docs/EMAIL-PROVIDER-TWILIO-SENDGRID-SETUP.md im Repo. Du kennst Sie und kannst den User Schritt für Schritt durchleiten — beziehe dich auf die jeweilige Sektion.

AKTUELLER STATUS für smartladen.de (Stand 2026-05-08):
- Domain Authentication: VERIFIZIERT ✅
- Custom Return Path: sg.smartladen.de ✅
- DKIM s1 + s2: in DNS ✅
- DMARC: v=DMARC1; p=none; (basic, kein RUA noch)
- Microsoft 365 läuft parallel unberührt für inbound + Replies

DNS-RECORDS DIE EXISTIEREN (Snapshot):
CNAME  s1._domainkey.smartladen.de   →  s1.domainkey.u59755304.wl055.sendgrid.net
CNAME  s2._domainkey.smartladen.de   →  s2.domainkey.u59755304.wl055.sendgrid.net
CNAME  sg.smartladen.de              →  u59755304.wl055.sendgrid.net
TXT    _dmarc.smartladen.de           →  v=DMARC1; p=none;

Microsoft 365 (unberührt):
TXT    smartladen.de                  →  v=spf1 include:spf.protection.outlook.com -all
CNAME  selector1._domainkey ...
CNAME  selector2._domainkey ...
MX     smartladen.de                  →  10 smartladen-de.mail.protection.outlook.com

WICHTIGE STRATEGISCHE EMPFEHLUNG:
Falls der User Twilio bereits für SMS / 2FA / Voice nutzt:
**Subaccount für Email anlegen!** In Twilio Console -> Subaccounts -> Create.
Grund: Twilio-AUP-Verstöße bei einem Service können den GANZEN Account treffen.
Wenn SendGrid bei Spam-Beschwerden gelockt wird, kann es die SMS-Verifizierung mit reißen.
Mit Subaccount ist das Risiko isoliert — SendGrid lebt im Subaccount, SMS bleibt im Hauptaccount.

KOMPLETTE SCHRITT-REIHENFOLGE (frage den User wo er steht, dann gezielt weiterleiten):

SCHRITT 1 — Subaccount (empfohlen, ~3 Min):
- console.twilio.com -> "Subaccounts" -> "Create Subaccount"
- Name: "smartladen-email"
- In Subaccount wechseln (Account-Switcher oben links)
- Skip-OK falls User das Risiko bewusst akzeptiert

SCHRITT 2 — Twilio-SendGrid (Console-Switcher) aktivieren (~2 Min):
- In Twilio Console oben rechts Dropdown -> "Twilio SendGrid"
- Welcome-Screen kommt mit "Create new account" Button
  * KEIN Schreck: das ist KEIN getrenntes Konto - Login bleibt Twilio-SSO
  * Es ist ein gekapseltes SendGrid-Profil unter dem Twilio-Account
  * Free-Trial 60 Tage, danach 100 Mails/Tag Free-Tier
- Klick "Create new account" -> landet im SendGrid-Dashboard

SCHRITT 2.5 — VERWECHSLUNGSCHECK:
- Wenn URL jetzt app.sendgrid.com/* ist → Twilio SendGrid (RICHTIG)
- Wenn URL noch console.twilio.com/* mit Email-Channel → falsche Welt (Twilio-Email-Channel, NICHT für unsere Architektur geeignet)

⚠️ KRITISCHE ARCHITEKTUR-WARNUNG:
Twilio hat zwei separate Email-Welten:
- "Twilio Email" Channel direkt in der neuen Twilio Console (gekapselt, kein Direkt-API-Key-Zugriff)
- "Twilio SendGrid" (Console-Switcher rechts oben) - separater SendGrid-Account mit eigenem Dashboard und API-Keys

Unser Backend (sendgrid.py mit api.sendgrid.com/v3) braucht "Twilio SendGrid", NICHT den Twilio-Email-Channel.
Wenn der User Domain-Auth im Twilio-Email-Channel gemacht hat, sind die DNS-Records dort für SendGrid NUTZLOS - er muss Domain-Auth in "Twilio SendGrid" NEU durchlaufen mit anderer Subdomain.

SCHRITT 3 — Domain Authentication in TWILIO SENDGRID (~10 Min inkl. DNS-Propagation):
- WICHTIG: Erst über den Console-Switcher in "Twilio SendGrid" wechseln (siehe Schritt 2.5)
- Settings -> Sender Authentication -> "Authenticate Your Domain"
- Domain: smartladen.de
- ADVANCED SETTINGS:
  * Use custom return path: AN, Subdomain "sg" für ersten Setup, ODER "sg2" wenn "sg" schon vom Twilio-Email-Channel belegt
  * Use custom DKIM selector: AUS (Default s1+s2 reichen)
  * Enable Valimail Monitoring: AN (kostenlos, nützlich)
- DNS-Records: SendGrid kann bei Strato auto-eintragen (Strato-Login angeben)
  Alternativ manuell. Records die entstehen:
    CNAME s1._domainkey.smartladen.de  -> s1.domainkey.u<account_id>.wl055.sendgrid.net
    CNAME s2._domainkey.smartladen.de  -> s2.domainkey.u<account_id>.wl055.sendgrid.net
    CNAME sg.smartladen.de             -> u<account_id>.wl055.sendgrid.net
    TXT   _dmarc.smartladen.de          -> v=DMARC1; p=none;
- 5-15 Min DNS-Propagation warten
- "Verify" klicken -> Verified

SCHRITT 4 — Single Sender Verification (MEISTENS NICHT NÖTIG, überspringen):
- WICHTIG: Wenn Schritt 3 (Domain Auth) verifiziert ist, kannst du jeden @smartladen.de-Sender ohne weitere Verifikation nutzen. Single Sender ist eine ALTERNATIVE zu Domain-Auth, keine ERGÄNZUNG.
- Falls SendGrid es trotzdem verlangt (kommt im Free-Plan-UI manchmal vor): Settings -> Sender Authentication -> Block "Single Sender Verification" (UNTEN). info@smartladen.de + Stammdaten eintragen, Bestätigungs-Link klicken.
- Sonst direkt zu Schritt 5.

SCHRITT 5 — API-Key (~2 Min):
- WICHTIG ZWEI UIs UNTERSCHEIDEN:
  * Twilio Console (console.twilio.com) -> "Account settings -> API keys & auth tokens": das sind TWILIO-Keys für SMS/Voice. Funktionieren NICHT für Email.
  * SendGrid Dashboard (app.sendgrid.com) -> "Settings -> API Keys": das sind SENDGRID-EMAIL-Keys (beginnen mit "SG."). DIESE brauchen wir.
- SCHNELLSTER WEG: Direkt https://app.sendgrid.com/settings/api_keys aufrufen (ggf. einmal Twilio-SSO durchlaufen)
- Alternativ: in Twilio Console linke Sidebar "Email" oder "SendGrid Dashboard" anklicken -> öffnet SendGrid -> dort Settings -> API Keys
- Im SendGrid-Dashboard:
  - Settings (linke Seitenleiste, ⚙️ ganz unten) -> API Keys
  - "Create API Key" (blauer Button oben rechts)
  - Name: go4-automate
  - API Key Permissions: "Restricted Access" (NICHT "Full Access")
  - Scopes: Mail Send Full + Tracking Read + Stats Read (Rest aus)
  - Create & View -> Key SOFORT kopieren (nur einmal sichtbar, beginnt mit "SG.")

SCHRITT 6 — Provider in go4-automate (~1 Min):
- /emailmarketing/providers/new
- Provider-Typ: "Twilio SendGrid"
- API-Key: SG.xxxx einfügen
- Sender-Email: info@smartladen.de
- Sender-Name: "Harry Ketschik · smartladen.de"
- Reply-To: info@smartladen.de
- Tracking Domain: sg.smartladen.de
- Hourly Limit: 100 / Daily Limit: 1000 (für Anfang)
- Speichern -> "Provider testen" -> bei Erfolg "Als Default markieren"

SCHRITT 7 — Event Webhook (~2 Min):
- Settings -> Mail Settings -> "Event Webhook"
- HTTP Post URL: https://automate.go4.energy/api/v1/emailmarketing/webhooks/sendgrid
- Events: Bounced, Dropped, Spam Reports, Unsubscribed, Group Unsubscribe
- Test Your Integration -> 200 OK
- Save

SCHRITT 8 — Erster Test-Send (~1 Min):
- Engagement -> Pipeline 19 (Test-Outreach intern) -> Aktionen-Tab
- 1 Draft markieren -> "Freigeben + senden"
- In Inbox prüfen: Anrede, llm_body, Pitch, Footer mit Impressum, Tracking-Link

WICHTIG ZUR COMPLIANCE:
- Twilio AUP verlangt "consent" — Cold-Outreach ist Graubereich.
- Beschwerderate-Schwellen: 0,1% Warning, 0,3% Account-Review, 0,5% Lock.
- Hard-Bounce-Schwellen: 5% Warning, 10% Lock.
- Domain Authentication ist Pflicht — sonst landet alles im Spam.

VOLUME-RAMPING (NICHT von 0 auf 200/Tag springen):
- Woche 1: 20/Tag
- Woche 2: 50/Tag
- Woche 3: 100/Tag
- Woche 4+: 200-500/Tag
Bei Problemen: zurück eine Stufe.

BEI PROBLEMEN:
- "Authentication failed" -> API-Key falsch oder fehlende Permissions
- "Mail to address rejected: unverified" -> Single Sender nicht verifiziert
- DNS "Pending" -> mit `dig` aus mehreren Resolvern prüfen (Cloudflare 1.1.1.1 oft schneller als Google 8.8.8.8 oder Quad9 9.9.9.9). Manchmal 30+ Min Propagation.
- Account-Lock -> Subaccount rettet Hauptaccount; bei Hauptaccount-Lock SMS auch betroffen
- Mail in Spam -> mail-tester.com nutzen, DKIM/SPF/DMARC-Alignment prüfen

PHASE 2 (später, bei stabilem Betrieb):
- DMARC tightening: nach 4 Wochen p=none -> p=quarantine, RUA mailto:dmarc@smartladen.de
- Signed Event Webhook (Authentizität)
- Dedicated IP bei >5k/Monat
- Newsletter-Subdomain (news.smartladen.de) mit eigenem Domain-Auth""",
    ),
    "provider-list": (
        "E-Mail-Provider auswählen",
        """Der User schaut sich die Provider-Liste an und überlegt welchen Provider er nutzen soll.

PROVIDER-EMPFEHLUNG für `smartladen.de`:
- **Brevo (EU-Paris, DSGVO)**: Empfohlen für **Cold-Outreach**. Tolerant bei B2B-Outreach mit Opt-Out, kein Approval-Prozess. 300/Tag free, 25€/Monat für 20k.
- **Office 365 (Microsoft Graph)**: Empfohlen für **Replies + transaktionale Mails**. Kommt aus echtem Postfach, saubere Thread-Continuity.
- **AWS SES (Frankfurt)**: Für transaktional / hohes Volumen. Für Cold-Outreach oft abgelehnt von Trust & Safety.
- **SendGrid**: Industry-Standard Marketing. US-hosted (EU Data Residency Add-On verfügbar).
- **Mailgun**: Dev-fokussiert, gute Webhooks. US oder EU-Region wählbar.

Für deutschen B2B-Outreach: Brevo ist die sicherste Wahl.""",
    ),
    "llm-settings": (
        "LLM-Modelle konfigurieren",
        """Der User konfiguriert die LLM-Modell-Klassen.

Es gibt drei Klassen:
- 🚀 **Premium** (z.B. Opus 4.7): für interaktive, kreative Tasks — Setup-Assistent, Template-Designer-Chat. Selten genutzt, beste Qualität.
- ⚡ **Standard** (z.B. Sonnet 4.6): für Personalisierung pro Empfänger — {{llm_body}}, Subject-Personalisierung, Reply-Drafts. Häufig genutzt, gut + bezahlbar.
- 🪙 **Bulk** (z.B. Haiku 4.5): für Klassifikation und Analyse — Sentiment, Intent, Webseiten-Scraping, Lead-Scoring. Sehr häufig genutzt, spottbillig.

KOSTEN-RICHTWERT für 10k Mail-Bodies (Standard-Klasse):
- Opus 4.7: ~$30
- Sonnet 4.6: ~$3
- Haiku 4.5: ~$0.60

Die Klassen werden im Code hartcodiert pro Use-Case zugewiesen — der User wählt nur welches Anthropic-Modell hinter jeder Klasse steht.

EMPFEHLUNG: Opus für Premium, Sonnet 4.6 für Standard, Haiku 4.5 für Bulk. Einmalig setzen, bei neuen Anthropic-Releases per "Auf neueste Modelle prüfen" updaten.""",
    ),
    "pipeline-setup": (
        "Engagement-Pipeline einrichten",
        """Der User richtet eine Engagement-Pipeline ein.

KONZEPT: Pipeline = Strategie. Sie definiert das Ziel (Demo, Erstkontakt, Termin), die Tonalität, die Zielgruppe und die aktiven Outreach-Kanäle. Das Engagement Brain (LLM) entscheidet pro Lead in der Pipeline, was als nächstes passiert.

WICHTIGE FELDER:
- Name: Sprechender Name (z.B. "Lastmanagement MFH")
- Slug: URL-tauglich (auto-generiert)
- Goal: Was ist das Ziel? (demo, erstkontakt, kalt-akquise, termin)
- Channels: Welche Kanäle aktivieren? (linkedin, email, letter, whatsapp, phone)
- Tonalität: Formal, locker, technisch
- min_days_between_touches: Mindestens X Tage zwischen Mails an einen Lead

WICHTIG: Pipelines werden ZENTRAL im Engagement-Modul angelegt. Andere Module (Letter, LinkedIn, Email) zeigen die Pipeline-Daten basierend auf dem global gewählten Pipeline-Selector im Header.""",
    ),
    "leadgen-source": (
        "Leadgen-Quelle einrichten",
        """Der User konfiguriert eine Leadgen-Quelle.

Leadgen läuft in mehreren Stages:
1. Source-Discovery (welche Firmen finden? Google-Maps, OSM, manueller Import)
2. Impressum-Scraping (Adresse + Geschäftsführer extrahieren)
3. LLM-Insights (Firmen-Segment, Personalization-Hook, Red-Flags)
4. Handoff in eine Engagement-Pipeline

Quellen-Typen:
- google_maps_places: Google-Suche nach Branche + Ort
- osm: OpenStreetMap-basierte Suche (kostenlos, weniger Daten)
- csv_import: Manueller Import einer Liste
- linkedin_search: Über Sales Navigator (braucht LinkedIn-Account)

Tipp: Klein anfangen mit ~100 Leads und sehen ob die Insights gut sind, bevor 5000 importiert werden.""",
    ),
}


def get_topic(topic: str | None) -> tuple[str, str] | None:
    """Return (title, docs_snippet) for a topic, or None if unknown."""
    if not topic:
        return None
    return TOPICS.get(topic)


def list_topics() -> list[dict]:
    """List all available topics — for debugging / admin UI."""
    return [{"id": k, "title": v[0]} for k, v in TOPICS.items()]


_SECRET_HINTS = ("secret", "key", "password", "token", "credential")


def mask_secrets(data: dict | None) -> dict | None:
    """Mask values in form_state whose key looks secret-ish."""
    if not data:
        return data
    masked: dict = {}
    for k, v in data.items():
        kl = str(k).lower()
        if any(h in kl for h in _SECRET_HINTS):
            masked[k] = "<gesetzt>" if v else "<leer>"
        elif isinstance(v, dict):
            masked[k] = mask_secrets(v)
        else:
            masked[k] = v
    return masked
