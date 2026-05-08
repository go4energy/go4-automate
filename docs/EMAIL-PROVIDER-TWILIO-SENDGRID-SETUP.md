# Twilio SendGrid einrichten — vollständige Anleitung für `smartladen.de`

> **Status (2026-05-08):** Live für Tenant `go4energy`, Domain `smartladen.de` ist authentifiziert (`sg.smartladen.de`), Provider in go4-automate eingetragen.
>
> **Wer wartet das?** Harry Ketschik (Geschäftsführer go4.energy GmbH).
> **Wo liegt diese Doku?** `/opt/go4-automate/docs/EMAIL-PROVIDER-TWILIO-SENDGRID-SETUP.md`
> **Spiegelung im KI-Assistenten:** `app/services/chat_topics.py` Topic `provider-twilio-sendgrid`.

---

## 0. WICHTIG — Twilio Email Channel vs Twilio SendGrid (Falle!)

Twilio hat zwei voneinander getrennte Email-Welten in der neuen Console:

1. **Twilio Console „Email" Channel** — UI direkt in `console.twilio.com`. Praktisch, aber nutzt im Hintergrund einen **gekapselten, isolierten** SendGrid-Backend-Account, an den DU keinen direkten API-Key-Zugriff hast. Domain-Auth gemacht hier landet auf Account-ID `u<N>.wl055.sendgrid.net`, ABER dieses Konto ist NICHT der „Twilio SendGrid"-Account.

2. **Twilio SendGrid** (über den Console-Switcher rechts oben in der Twilio Console) — **separater** SendGrid-Account mit eigenem Domain-Auth-Bereich, eigenen API-Keys, eigenem Dashboard. Login via Twilio-SSO, KEIN extra Passwort, aber „Create new account"-Aktivierung nötig beim ersten Mal.

**Konsequenz:** Wenn du Domain-Auth im **Email-Channel** machst, sind diese DNS-Records für den **„Twilio SendGrid"-Account NUTZLOS** — du musst Domain-Auth dort NEU machen mit anderen Records.

**Für unsere Architektur (Backend nutzt SendGrid v3 API mit `SG.`-Keys):**
→ Wir nutzen **„Twilio SendGrid"** (Console-Switcher), NICHT den Twilio-Email-Channel. Domain-Auth muss DORT durchlaufen werden.

**Empfohlene Subdomain bei der zweiten Domain-Auth:**
- Erste (Twilio Email Channel, ungenutzt): hat möglicherweise `sg` belegt
- Zweite (Twilio SendGrid, das was wir nutzen): **`sg2`** als Custom Return Path
- Alte Twilio-Email-Channel-Records (auf `sg.smartladen.de`) später bei Strato löschen, wenn der Channel definitiv nicht genutzt wird

---

## 1. Was diese Doku abdeckt

End-to-End-Setup für ausgehende E-Mails über Twilio SendGrid mit:
- **Domain Authentication** (DKIM für `smartladen.de`)
- **Custom Return Path** (`sg.smartladen.de`) für DMARC-Alignment
- **Single Sender Verification** für `info@smartladen.de`
- **API-Key + Restricted Permissions**
- **Event Webhook** für Bounce-/Complaint-Auto-Suppression
- **Anbindung an go4-automate** (Provider-UI)
- **Erste Test-Mails über Engagement-Pipeline**

Voraussetzung: aktiver Twilio-Account (vorhanden — wird auch für SMS-Verifizierung genutzt).

**Wichtige strategische Vorab-Entscheidung:**

Twilio AUP gilt für ALLE Twilio-Services — wenn ein AUP-Verstoß bei SendGrid auftritt (z.B. Beschwerderate > 0,3 %), kann das den **gesamten Twilio-Account** unter Review stellen. Das würde auch eure SMS-Verifizierung treffen.

**Mitigation:** Subaccount-Setup (siehe Schritt 2). Wenn ihr das skippt, bewusst Risiko akzeptieren.

---

## 2. (Empfohlen) Twilio-Subaccount für Email anlegen

**Warum:** Email-Risiko isolieren von SMS-Verifizierung.

1. [console.twilio.com](https://console.twilio.com) → links unten **„Subaccounts"** → **„Create Subaccount"**
2. Name: `smartladen-email`
3. Bestätigen → in den Subaccount wechseln (Account-Switcher oben links)
4. Bei Twilio Free-Plan: Subaccount erbt das Free-Plan-Quota; bei bezahltem Plan kann jeder Subaccount eigene Limits haben

**Hinweis:** Wenn der Subaccount geblockt wird, ist nur Email betroffen. SMS bleibt im Hauptaccount aktiv.

---

## 3. SendGrid in Subaccount aktivieren

1. In den Subaccount eingeloggt → linke Seitenleiste **„Email"** oder **„SendGrid Dashboard"**
2. Wenn noch kein SendGrid-Konto: Free-Plan starten (100 Mails/Tag — reicht für initiale Tests)
3. Bei späterer Skalierung Bezahl-Plan:
   - **Essentials** $19,95/Monat — 50.000 Mails/Monat
   - **Pro** $89,95/Monat — 100.000 Mails/Monat + dedizierte IP

---

## 4. Domain Authentication

### 4.1 Setup starten
1. SendGrid Dashboard → **Settings → Sender Authentication**
2. **„Authenticate Your Domain"** klicken
3. **DNS host:** Strato (oder eurer DNS-Provider)
4. **Domain:** `smartladen.de`

### 4.2 Advanced Settings (wichtig!)

| Option | Wert | Begründung |
|---|---|---|
| **Use custom return path** | ✅ **AN**, Subdomain: `sg` | Bessere Deliverability + DMARC-Alignment. Resultat: `sg.smartladen.de` als Return-Path. |
| **Use custom DKIM selector** | ❌ AUS | Default-Selectoren `s1` + `s2` reichen. Nur an, wenn ihr mehrere Email-Provider parallel mit DKIM für die gleiche Domain habt. |
| **Enable Valimail Monitoring** | ✅ AN | Kostenlos. Zeigt im Dashboard wer in eurem Namen sendet, ob DMARC/SPF/DKIM passen. |

⚠️ **NICHT `mail` als Subdomain wählen** — kollidiert oft mit existierenden Microsoft-365-MAIL-FROM-Records.

### 4.3 DNS-Records (was SendGrid generiert)

Bei aktivem Custom-Return-Path `sg`:

```
CNAME  s1._domainkey.smartladen.de   →  s1.domainkey.u59755304.wl055.sendgrid.net
CNAME  s2._domainkey.smartladen.de   →  s2.domainkey.u59755304.wl055.sendgrid.net
CNAME  sg.smartladen.de              →  u59755304.wl055.sendgrid.net
TXT    _dmarc.smartladen.de           →  v=DMARC1; p=none;
```

> Die `u59755304`-ID variiert pro SendGrid-Account. Bei euch: `u59755304.wl055.sendgrid.net`.

### 4.4 Eintragen — zwei Wege

**Weg A: SendGrid-API-Integration (empfohlen, wenn Strato unterstützt wird)**

SendGrid bietet bei Strato/IONOS direkte Eintragung:
1. „Strato" als Provider auswählen
2. Strato-Login (Username + Passwort) bei SendGrid eintragen
3. SendGrid trägt die CNAMEs automatisch ein

**Weg B: Manuell**

Strato-Webinterface → Domain → DNS-Verwaltung → 4 Records anlegen:
- 3× CNAME (DKIM s1, DKIM s2, Custom Return Path sg)
- 1× TXT (DMARC) — falls noch nicht vorhanden

### 4.5 Verify

1. 5–15 Min auf DNS-Propagation warten
2. SendGrid → **„Verify"** klicken
3. Status sollte zu **Verified ✅** wechseln

**DNS-Diagnose von einer Linux-Shell aus:**
```bash
dig +short CNAME s1._domainkey.smartladen.de
dig +short CNAME s2._domainkey.smartladen.de
dig +short CNAME sg.smartladen.de
dig +short TXT _dmarc.smartladen.de
```

Alle 4 müssen Werte zurückgeben — nicht alle DNS-Resolver brauchen gleich lange (Cloudflare meist schneller als Google).

---

## 5. Koexistenz mit Microsoft 365

`smartladen.de` hat **zwei Sender parallel**:
- **Microsoft 365** — für eingehende Mails (`info@smartladen.de`-Postfach) und manuelle Replies
  - DKIM-Selectoren: `selector1._domainkey`, `selector2._domainkey`
  - MX: `smartladen-de.mail.protection.outlook.com`
  - SPF (auf `smartladen.de`): `v=spf1 include:spf.protection.outlook.com -all`
- **SendGrid** — für outbound Cold-Outreach + Newsletter
  - DKIM-Selectoren: `s1._domainkey`, `s2._domainkey`
  - Return-Path: `sg.smartladen.de` (eigene Subdomain)
  - SPF läuft implizit über Subdomain (CNAME zu SendGrid liefert `v=spf1 include:sendgrid.net ~all`)

**Wichtig:** SPF auf der Hauptdomain (`smartladen.de`) bleibt **unverändert**, weil SendGrid den Return-Path über `sg.smartladen.de` setzt — DMARC-Alignment passt damit automatisch (organizational domain match).

**Falls jemand jemals direkt von `info@smartladen.de` ohne SendGrid sendet** (z.B. aus Outlook): SPF schlägt für SendGrid-Mails fehl, da `-all` (hard-fail) auf der Hauptdomain. Aber das passiert hier nicht, weil go4-automate alle Outbound-Mails über die SendGrid-API schickt.

---

## 6. Single Sender Verification — meistens NICHT nötig

**Wenn Domain Authentication (Schritt 4) verifiziert ist, brauchst du Single-Sender NICHT.** Das ist eine **Alternative**, keine Ergänzung. Domain-Auth deckt jeden `@smartladen.de`-Sender automatisch ab.

Single-Sender-Verification nur nötig, wenn:
- DNS-Zugriff auf die Sender-Domain fehlt (selten)
- Du von einer fremden Domain senden willst (z.B. `harry@gmail.com` als Absender) — nicht empfohlen
- SendGrid das im Free-Plan trotzdem verlangt (UI-Variante, kommt vor)

**Wenn SendGrid es trotzdem verlangt:**
1. Settings → Sender Authentication → Block „Single Sender Verification" (unten)
2. „Verify a Single Sender" → `info@smartladen.de` + Stammdaten eintragen
3. Bestätigungs-Mail in Outlook → Link klicken

---

## 7. API-Key erstellen

> **WICHTIG — zwei UIs nicht verwechseln:**
> - **Twilio Console** (`console.twilio.com`) hat „Account settings → API keys & auth tokens" — das sind **Twilio-Keys** für SMS/Voice. Funktionieren NICHT für SendGrid Email.
> - **SendGrid Dashboard** (`app.sendgrid.com`) hat „Settings → API Keys" — das sind die **SendGrid-Email-Keys** (beginnen mit `SG.`). **Diese brauchen wir.**
>
> **Schnellster Weg:** [https://app.sendgrid.com/settings/api_keys](https://app.sendgrid.com/settings/api_keys) direkt aufrufen — landet auf der richtigen Seite (ggf. einmal Twilio-SSO durchlaufen).

1. SendGrid Dashboard → linke Seitenleiste unten **Settings → API Keys** → **„Create API Key"**
2. **Name:** `go4-automate`
3. **Permissions:** **„Restricted Access"** (NICHT Full Access — Sicherheit)
4. Scopes:
   - **Mail Send** → Full Access
   - **Tracking** → Read Access
   - **Stats** → Read Access
   - Rest aus
5. **„Create & View"**
6. Key beginnt mit `SG.xxxx...` — sofort kopieren (nur **einmal** sichtbar)

**Wenn der Key verloren geht:** alten löschen, neuen generieren, in go4-automate aktualisieren.

---

## 8. Provider in go4-automate eintragen

1. `https://automate.go4.energy/emailmarketing/providers/new`
2. Provider-Typ: **„Twilio SendGrid – Konsolidiert mit eurem Twilio-Account..."**
3. Felder:
   - **API Key:** `SG.xxxx...` einfügen
   - **Sender Email:** `info@smartladen.de`
   - **Sender Name:** `Harry Ketschik · smartladen.de`
   - **Reply-To:** `info@smartladen.de`
   - **Tracking Domain:** `sg.smartladen.de` (optional, aber sinnvoll)
   - **Hourly Limit:** 100 (für Anfang)
   - **Daily Limit:** 1000
   - **Status:** active
4. **Speichern**
5. Auf der Detail-Seite: **„Provider testen"** → Test-Mail an Sender-Email
6. Wenn grün: **„Als Default markieren"**

---

## 9. Event Webhook konfigurieren

Damit Bounces + Beschwerden automatisch in unsere DB landen + Empfänger in der Suppression-List:

1. Settings → **Mail Settings** → **Event Webhook** (oder direkt **Settings → Event Notifications**)
2. **HTTP Post URL:**
   ```
   https://automate.go4.energy/api/v1/emailmarketing/webhooks/sendgrid
   ```
3. **Authorization Method:** None (für Start) — später Signed Event Webhook für mehr Sicherheit
4. **Events anschalten:**
   - ✅ Bounced
   - ✅ Dropped
   - ✅ Spam Reports
   - ✅ Unsubscribed
   - ✅ Group Unsubscribe
   - (optional, später) Delivered, Opened, Clicked
5. **„Test Your Integration"** — SendGrid schickt einen Mock-Event an unseren Endpoint, sollte 200 OK zurückgeben
6. **Save**

---

## 10. Erster Test-Send

1. go4-automate → **Engagement → Pipeline 19 „Test-Outreach (intern)"**
2. **Aktionen-Tab** → eine Draft-Zeile markieren (z.B. für `harry.ketschik@go4.energy`)
3. **„Freigeben + senden"**
4. Email-Worker pickt innerhalb von 5 Sek auf, sendet via SendGrid
5. In Outlook-Inbox prüfen:
   - Anrede `Sehr geehrter Herr Kraus,` ✅
   - LLM-Eröffnung individuell ✅
   - Pitch + CTA ✅
   - Footer mit Impressum + Werbewiderspruch ✅
   - Tracking-Link führt zu `smartladen.de/fachpartner?ref=...`
   - Mail-Header: `Return-Path: bounces@sg.smartladen.de`
   - Header `Authentication-Results`: spf=pass, dkim=pass, dmarc=pass

---

## 11. Compliance-Schwellen Twilio SendGrid

Twilio überwacht automatisch:

| Metrik | Schwelle | Reaktion |
|---|---|---|
| **Spam Complaint Rate** | < 0,1 % normal, **0,1 % Warning, 0,3 % Account Review** | Bei 0,3 % → Account-Lock (Subaccount oder Hauptaccount) |
| **Hard Bounce Rate** | < 5 % normal, **5 % Warning, 10 % Lock** | Bei 10 % → Sending pausiert |
| **Soft Bounce Rate** | < 8 % | Internes Throttling |

**Praxis-Erwartung für sauber kuratierte B2B-Listen:**
- Beschwerden: 0,02–0,05 %
- Hard Bounces: 1–3 %

Wenn Schwellen überschritten: SendGrid-Compliance-Team meldet sich, verlangt Listen-Audit. Bei wiederholtem Verstoß → Subaccount-Lock.

**Schutz vor Account-Lock:** Subaccount-Setup (Schritt 2) — falls SendGrid-Subaccount blockiert, läuft SMS-Verifizierung im Hauptaccount weiter.

---

## 12. Suppression-List

Verwaltet automatisch von SendGrid + parallel in `email_recipients` Tabelle (über Webhook):

- **Hard Bounces** → permanent unterdrückt
- **Spam Reports** → permanent unterdrückt
- **Unsubscribes** (über One-Click + Footer-Link) → permanent unterdrückt
- **Soft Bounces** → 3 Versuche, dann unterdrückt

In SendGrid einsehbar: Suppressions → Bounces / Spam Reports / Unsubscribes / Invalid Emails.

In go4-automate: später Dashboard-Tab in `/emailmarketing/freigabe` zeigen (TODO).

---

## 13. Volume-Ramping

Nicht von 0 auf 200/Tag springen — Domain-Reputation ist wie ein Bankkonto, muss aufgebaut werden:

| Woche | Tagesvolumen | Beobachten |
|---|---|---|
| 1 | 20/Tag | Bounce + Complaint = 0 |
| 2 | 50/Tag | dito |
| 3 | 100/Tag | dito |
| 4+ | 200–500/Tag | Beobachten ob Inbox-Placement-Rate stabil |

Wenn in einer Woche Probleme: zurück eine Stufe.

**Beobachten** geht über:
- SendGrid Dashboard → Stats
- Google Postmaster Tools (wenn Domain dort registriert)
- go4-automate Engagement-Pipeline-Statistiken

---

## 14. Was tun bei Problemen

| Symptom | Ursache | Fix |
|---|---|---|
| `Authentication failed` | API-Key falsch oder gelöscht | In SendGrid neuen Key generieren, in go4-automate eintragen |
| `Mail to address rejected: unverified` | Sender Identity nicht bestätigt | Single Sender Verification durchgehen |
| `Provider testen` schlägt fehl | API-Key ohne Mail-Send-Permission | Key löschen, neuen mit Mail Send Full erstellen |
| DNS „Pending" (auch nach 30 Min) | Strato-API-Eintrag unvollständig oder DNS-Cache | `dig` mit verschiedenen Resolvern prüfen, ggf. Records manuell ergänzen |
| Mail kommt in Spam | DKIM/SPF/DMARC nicht alignted | DNS-Records prüfen, DMARC-Alignment via mail-tester.com checken |
| Account unter Review | Beschwerden > 0,3 % | Sofort pausieren, Liste auditieren, an SendGrid Compliance schreiben |
| Subaccount gesperrt | AUP-Verstoß | Hauptaccount + SMS sind sicher (Subaccount-Vorteil); im Subaccount neu starten oder anderen Provider |

---

## 15. Cross-Referenzen

| Was | Wo |
|---|---|
| Tenant-Stammdaten (Impressum, Disclaimer) | `/settings/stammdaten` (Tab in Settings) |
| Email-Templates | `/emailmarketing/templates` |
| KI-Designer-Chat | im Template-Edit-View, rechte Sidebar |
| Engagement-Pipelines | `/engagement/pipelines` |
| Test-Pipeline 19 | `/engagement/pipelines/19/uebersicht` |
| Provider-UI | `/emailmarketing/providers` |
| Webhooks-Endpoint | `https://automate.go4.energy/api/v1/emailmarketing/webhooks/sendgrid` |
| Backend-Code Provider | `backend/app/emailmarketing/providers/sendgrid.py` |
| Backend-Code Webhook-Handler | `backend/app/emailmarketing/webhooks_router.py` |
| Renderer (Merge-Tags) | `backend/app/emailmarketing/template_renderer.py` |
| KI-Helper-Topic | `backend/app/services/chat_topics.py` → `provider-twilio-sendgrid` |

---

## 16. Aktuelle DNS-Records (Snapshot 2026-05-08)

```
CNAME  s1._domainkey.smartladen.de   →  s1.domainkey.u59755304.wl055.sendgrid.net      [Enabled, Verified]
CNAME  s2._domainkey.smartladen.de   →  s2.domainkey.u59755304.wl055.sendgrid.net      [Enabled, Verified]
CNAME  sg.smartladen.de              →  u59755304.wl055.sendgrid.net                  [Enabled, Verified]
TXT    _dmarc.smartladen.de           →  v=DMARC1; p=none;                             [Enabled]
```

Microsoft 365 (parallel, unberührt):
```
TXT    smartladen.de                  →  v=spf1 include:spf.protection.outlook.com -all
CNAME  selector1._domainkey...         →  selector1-smartladen-de._domainkey.goforenergy.w-v1.dkim.mail.microsoft
CNAME  selector2._domainkey...         →  selector2-smartladen-de._domainkey.goforenergy.w-v1.dkim.mail.microsoft
MX     smartladen.de                  →  10 smartladen-de.mail.protection.outlook.com
```

---

## 17. Phase-2 Optimierungen (später)

- **DMARC tightening:** Nach 4 Wochen sauberen Sendings auf `p=quarantine` oder `p=reject`. RUA-Reports an `dmarc@smartladen.de` einrichten.
- **Signed Event Webhook:** Webhook-Authentizität via SendGrid-Signatur prüfen.
- **Dedicated IP:** Bei Volumen >5k/Monat über SendGrid Pro ($89,95) eigene IP — eigene Reputation, unabhängig von SendGrid-Pool.
- **Sub-Domain für Newsletter:** Eigene Subdomain `news.smartladen.de` mit eigenem Domain-Auth → trennt Newsletter-Reputation von Outreach-Reputation.
- **Google Postmaster Tools:** Domain dort registrieren → Inbox-Placement-Rate, Spam-Rate, Authentication-Results sichtbar.
- **DMARC-Reporting-Tool:** dmarcian.com, postmark-dmarc.com — RUA-Reports automatisch parsen.
- **One-Click-Newsletter-Anmeldung:** Public-Endpoint + DOI für `smartladen.de/newsletter` (nötig für späteren AWS-SES-Newsletter-Antrag, falls AWS für Newsletter freigeschaltet werden soll).
