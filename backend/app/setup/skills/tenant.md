# Tenant / Unternehmen

## Beschreibung
Grundkonfiguration des Unternehmens. Diese Daten werden von allen anderen Modulen verwendet (Content-Generierung, Ads, Research etc.).

## Konfigurierbare Parameter
| Parameter | Beschreibung | Typ | Beispiel | Default |
|-----------|-------------|-----|---------|---------|
| TENANT_NAME | Interner Bezeichner | string | go4energy | - |
| COMPANY_NAME | Firmenname (oeffentlich) | string | go4 energy GmbH | - |
| TENANT_INDUSTRY | Branche | string | Erneuerbare Energien | - |
| TENANT_REGION | Region/Markt | string | Oesterreich | DACH |
| TARGET_AUDIENCE | Zielgruppe | string | Unternehmen mit hohem Energieverbrauch | - |
| BRAND_TONE | Tonalitaet | string | professionell, innovativ | professionell |
| CONTENT_LANGUAGE | Sprache | string | de | de |
| WEBSITE_URL | Firmenwebsite | string | https://www.go4.energy | - |
| CONTACT_EMAIL | Kontakt-E-Mail | string | info@go4.energy | - |
| USP | Alleinstellungsmerkmal | string | KI-gestuetztes Energiemanagement | - |
| COMPETITORS | Wettbewerber | string | Firma A, Firma B | - |
| HASHTAGS_DEFAULT | Standard-Hashtags | string | #Photovoltaik #Energie | - |
| CTA_DEFAULT | Standard Call-to-Action | string | Jetzt Beratung anfragen | - |
| FUNNEL_FOCUS | Funnel-Schwerpunkt | string | awareness, consideration | awareness |

## Verfuegbare Tools
- `get_current_config` — Aktuelle Konfiguration lesen
- `update_tenant_config` — Konfiguration aktualisieren (Schluessel-Wert-Paare)

## Typische Fragen fuer den Benutzer
1. Wie heisst Ihr Unternehmen und in welcher Branche sind Sie taetig?
2. Wer ist Ihre Zielgruppe?
3. In welcher Region sind Sie aktiv?
4. Wie wuerden Sie den Ton Ihrer Kommunikation beschreiben?
5. Was ist Ihr wichtigstes Alleinstellungsmerkmal?
6. Haben Sie eine Website?

## Branchenspezifische Empfehlungen
- **Photovoltaik/Energie**: Tone=innovativ+nachhaltig, Hashtags=#Photovoltaik #Solarenergie #Nachhaltigkeit
- **IT/Software**: Tone=technisch+kompetent, Hashtags=#Digitalisierung #IT #Software
- **Handwerk**: Tone=bodenstaendig+zuverlaessig, Hashtags=#Handwerk #Qualitaet #Regional
- **Beratung**: Tone=professionell+vertrauenswuerdig, Hashtags=#Beratung #Expertise
