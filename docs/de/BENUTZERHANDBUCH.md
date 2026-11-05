# Benutzerhandbuch: Fähigkeiten, Workflows & Parameter

Das **AlexandriaSandwich-System** ist eine spezialisierte Digitalisierungs- und Editionspipeline für historische Bücher, wissenschaftliche Editionen und Handschriften. Es verbindet vier Schritte zu einem durchgängigen Arbeitsablauf:

1. **Scan-Restaurierung**: Beseitigt Vergilbung, Schattenwurf und Scan-Rauschen, ohne feine Schriftlinien oder diakritische Punkte zu beschädigen.
2. **Hybride KI-Texterkennung (OCR)**: Kombiniert pixelgenaue lokale Koordinaten mit modernen multimodalen Bild-Sprach-Modellen (Vision-Language Models / VLM wie Mistral OCR) für fehlerfreie Transkription selbst komplexer Schriften (z. B. Devanāgarī, IAST-Diakritika, Fraktur, Polytonisches Griechisch).
3. **1:1 Sandwich-PDF**: Erzeugt ein durchsuchbares Faksimile, bei dem eine unsichtbare Vektor-Textebene exakt hinter dem bereinigten Originalscan liegt.
4. **Digitaler Neusatz (Typst)**: Generiert gestochen scharfe Vektor-Ausgaben mit exakter Seiten- und Zeilentreue zur historischen Erstausgabe.

??? info "Glossar: Zentrale Fachbegriffe auf einen Blick (Klicken zum Aufklappen)"
    - **VLM (Vision-Language Model)**: Ein multimodales KI-Modell, das Bildinhalte (Scans) und Sprache gleichzeitig versteht und dadurch selbst schwierigste historische Schriften, Zeilenumbrüche und Tabellenstrukturen fehlerfrei liest.
    - **OCR (Optical Character Recognition)**: Automatische optische Zeichenerkennung zur Umwandlung von Bildtext in maschinenlesbaren Volltext.
    - **Sandwich-PDF**: Ein PDF-Dokument, das den sichtbaren Scan als Bildseite zeigt, dahinter jedoch eine unsichtbare, passgenau ausgerichtete Textebene für Volltextsuche und Textmarkierung enthält.
    - **Typst**: Ein modernes, schnelles Satzsystem (zeitgemäße Alternative zu LaTeX) für hochwertige wissenschaftliche Buch- und Druckausgaben.
    - **IAST (International Alphabet of Sanskrit Transliteration)**: Das akademische Standard-Umschriftsystem für indische Schriften in lateinischen Buchstaben mit diakritischen Zeichen (z. B. *ś*, *ṣ*, *ṛ*, *ṃ*, *ḥ*).
    - **Devanāgarī**: Die traditionelle indische Schrift für Sanskrit, Hindi und Marathi.
    - **Deskewing**: Automatisches Geraderichten schräg eingescannter Buchseiten anhand von Projektionsprofilen.
    - **Despeckling**: Entfernen isolierter Staub- und Scan-Flecken im Weißraum unter partiellem Schutz diakritischer Punkte nahe den Schriftzeilen.
    - **TEI-P5 XML**: Standard der *Text Encoding Initiative* zur digitalen Langzeitarchivierung geisteswissenschaftlicher Texte.
    - **EPUB 3**: Standardformat für digitale Bücher mit dynamisch anpassbarem Fließtext (*Reflowable*) und eingebetteten Schriften.

---

## 1. Das Gesamtspektrum der erworbenen Fähigkeiten

Über zahlreiche Fallstudien und Quellengattungen hinweg (Böhtlingk 1887 *Pāṇini*, Cardona 1976 *Recent Research in Pāṇinian Studies*, Thieme 1952 *Bráhman*, Abhinavagupta 1918 *Tantrasāra*, William James *Principles of Psychology*) wurden spezialisierte Module entwickelt:

```
┌────────────────────────────────────────────────────────────────────────┐
│                   ALEXANDRIASANDWICH FÄHIGKEITSMATRIX                  │
├─────────────────────────┬────────────────────────┬─────────────────────┤
│ 1. Bild & Faksimile     │ 2. Text & Geometrie    │ 3. Digitaler Satz   │
├─────────────────────────┼────────────────────────┼─────────────────────┤
│ • Verso/Recto Deskew    │ • Tesseract BBoxes     │ • Typst Vektor-PDF  │
│ • Illumination-Subtract │ • Mistral VLM Token-AI │ • 1:1 Seitentreue   │
│ • Distance Despeckle    │ • Fuzzy Token-Anchor   │ • Interlinear-Stack │
│ • Margin Border Wipe    │ • Indic Normalizer     │ • Logische Labels   │
│ • Colophon Blanking     │ • Apparatus Expansion  │ • EPUB 3 & TEI-P5   │
└─────────────────────────┴────────────────────────┴─────────────────────┘
```

### A. Scan-Restaurierung & Bildbearbeitung
- **Unabhängiges Rotations-Deskewing**: Automatische Ermittlung des Drehwinkels für linke (Verso) und rechte Seiten (Recto) via Projektionsprofil.
- **Adaptive Hintergrund-Normalisierung**: Division durch morphologische Schließungsmasken entfernt Vergilbung, Schattenwurf und Durchscheinen (*Bleed-Through*), ohne dünne Haarstriche zu beschädigen.
- **Diakritika-schonendes Distance-Transform Despeckling**: Zweizonen-Filterung: Während die Seitenränder vollständig geweißt werden, prüft das System innerhalb des Satzspiegels die Distanz zur nächsten echten Textzeile. Punkte (Anusvāra, Visarga, Candrabindu, Akzente) nahe der Grundlinie bleiben zu 100 % erhalten; isolierter Staub im Zwischenraum wird getilgt.
- **Kolophon-Bereinigung**: Automatisches oder manuelles Weißblenden unbedruckter Restflächen am Kapitelende.

### B. Hybride OCR & Token-Geometrie
- **Lokale Geometrie (Tesseract)**: Schnelle pixelgenaue Wort-Bounding-Boxes für die unsichtbare Suchschicht.
- **Multimodales VLM (Mistral OCR)**: Höchste Erkennungsgenauigkeit für anspruchsvolle Schriften (Devanāgarī, Polytonisches Griechisch, Fraktur, komplexe Ligaturen).
- **Fuzzy Token-Anchor Alignment**: Dynamische Abstimmung zwischen VLM-Volltext und Scan-Koordinaten verhindert Phantom-Suchtreffer im Weißraum.

### C. Digitaler Neusatz & Typst-Architektur
- **1:1 Seiten- und Zeilentreue**: Jeder Zeilenumbruch und jeder Seitenwechsel entspricht exakt der historischen Vorlage.
- **Das Interlinear-`#stack`-System**: Eine feste typografische Hierarchie stellt sicher, dass der Abstand zwischen zusammengehörigen Sprachzeilen (Intra-Paar: ca. 2,6 pt) stets deutlich kleiner ist als der Abstand zur nächsten Einheit (Inter-Paar: ca. 7,2 pt).
- **Federnde Fußnoten-Verankerung**: Fußnoten werden via `#v(1fr, weak: true)` bündig an den unteren Satzspiegelrand gesetzt, getrennt durch eine 30%-Haarlinie.
- **Birchville Scholarly Synthesis Standard**: Einheitliche Titelblätter mit Reihenwappen, Kolumnentitel mit Wechsel zwischen geraden und ungeraden Seiten.

### D. Archiv- & Leseformate
- **1:1 Sandwich-PDF**: Originalscan mit unsichtbarer, perfekt ausgerichteter Vektor-Textebene.
- **EPUB 3**: Reflowable eBook mit eingebetteten Schriften (*STIX Two Text*, *Devanagari MT*).
- **TEI-P5 XML**: Standardisierte Langzeitarchivierung nach Richtlinien der Digital Humanities.
- **Strukturiertes AST**: `book.json` (maschinenlesbare Hierarchie mit BBoxes) und `book.md` (Markdown-Extrakt).

---

## 2. Die Editions-Matrix: Vier synchrone Ausgabeformen

Aus einem kanonischen Datensatz generiert die Pipeline vier synchrone Ausgaben:

1. **Monolingual Original (`original`)**: Reiner Neusatz der Originalschrift (z. B. Devanāgarī).
2. **Interlinear Umschrift (`interlinear`)**: Originalschrift oben, wissenschaftliche Transliteration (IAST) direkt darunter.
3. **Monolingual Umschrift (`transliteration`)**: Reines IAST mit vergrößertem Schriftgrad für optimale Lesbarkeit.
4. **Interlinear Übersetzung (`bilingual`)**: IAST oben, zeilenweise deutsche oder englische Übersetzung in kursiver Schieferoptik darunter.

---

## 3. Parameter-Katalog für den Nutzer (Service-Portal)

Nicht alle Entscheidungen können vollautomatisch getroffen werden. Das Service-Portal stellt daher folgende Wahlmöglichkeiten bereit:

| Parameter | Werte / Optionen | Standard | Beschreibung & Empfehlung |
| :--- | :--- | :--- | :--- |
| **`target_edition`** | `all`, `sandwich`, `original`, `interlinear`, `transliteration`, `bilingual` | `all` | Bestimmt, welche Dokumente der Multi-Edition-Matrix kompiliert werden. |
| **`spread_mode`** | `auto`, `split_spreads`, `single_page`, `raw` | `auto` | Trennt 2-seitige Buchscans (Doppelseiten) automatisch an der Mittellinie in Verso und Recto. |
| **`despeckle_mode`** | `safe_philological`, `aggressive`, `off` | `safe_philological` | `safe_philological` schützt Akzente und Punkte; `aggressive` für grobe Kopien; `off` für historische Originalstrukturen. |
| **`colophon_blank`** | `true`, `false` | `false` | Blendet leere Seitenbereiche nach dem finalen Kapitel-Kolophon weiß ein. |
| **`font_family`** | `stix`, `libertine`, `noto_deva` | `stix` | **STIX Two Text** deckt IAST und indologische Diakritika vollständig ab; **Libertine** für westliche Standardtexte. |
| **`body_start_page`** | Ganze Zahl (z. B. `10`) | `1` | Start-Seitenzahl des Haupttextes für native PDF Page Labels bei Kapitelauszügen. |
| **`title_page_style`** | `birchville`, `minimal`, `none` | `birchville` | Wappen-Titelblatt nach Birchville Scholarly Synthesis Standard oder schlichter Textbeginn. |
| **`apparatus_translit`**| `true`, `false` | `true` | Löst indische Manuskriptsiglen (`पं०`, `ख० पु०`) automatisch in standardisiertes IAST auf. |

---

## 4. Benutzer-Onboarding, 2FA-Autorisierung & Vorformulierte Aufträge

Um GPU- und Serverressourcen zu schützen und Ausführungsprozesse verifizierbar zuzuordnen, ist das AlexandriaSandwich-Portal (`https://alex.birchville.org`) über den **Birchville Onboarding-Meccano** und Authelia (Zwei-Faktor-Authentifizierung) abgesichert.

```
┌────────────────────────────────────────────────────────────────────────┐
│                      4-STUFEN-ONBOARDING-MECCANO                       │
├──────────────────┬──────────────────┬──────────────────┬───────────────┤
│ 1. Antrag        │ 2. Bereitstellung│ 3. 2FA & Login   │ 4. Ausführung │
├──────────────────┼──────────────────┼──────────────────┼───────────────┤
│ • Mail-Generator │ • CLI-Hash gener.│ • auth.birchville│ • Ein-Klick-  │
│   auf Portal     │ • Authelia YAML  │ • TOTP QR-Scan   │   Auftrags-   │
│ • Projekt/Werk   │ • Job-Zuweisung  │   (Bitwarden/    │   Auslösung   │
│   spezifizieren  │ • Einladungsmail │   Aegis/YubiKey) │ • Download    │
└──────────────────┴──────────────────┴──────────────────┴───────────────┘
```

### Der 4-Stufen-Workflow für Benutzer

1. **Antrag über den Onboarding-Meccano (`https://birchville.org/onboarding`)**:
   Der Nutzer ruft die Onboarding-Seite auf. Ein interaktiver Assistent generiert eine formatierte E-Mail-Vorlage mit Angaben zu Name, Institution, gewünschtem Werk, Scan-Material und allfälligen Vorab-Auftrags-IDs, die direkt an die Administration gesendet wird.

2. **Bereitstellung & Einladung durch die Administration**:
   Der Administrator generiert über `scripts/birchville_onboard.py` das Authelia-Konto und weist den vorformulierten Auftrag zu. Der Nutzer erhält eine bilinguale Einladungs-E-Mail mit Initialkennwort und Auftrags-Direktlink.

3. **2-Faktor-Authentifizierung (2FA) auf `auth.birchville.org`**:
   Der Nutzer meldet sich mit seinem Initialpasswort an, verknüpft seine Authenticator-App (Aegis, Bitwarden, Google Authenticator oder YubiKey FIDO2) und wählt ein persönliches Passwort.

4. **Auftrag prüfen & auslösen auf `alex.birchville.org`**:
   Im geschützten Portal sieht der Nutzer seinen vorformulierten Auftrag unter **"Ihre vorformulierten Aufträge (Bereit zur Ausführung)"**. Alle Parameter (DPI, Modell, Despeckle-Modus, Editions-Formate) sind bereits optimal hinterlegt. Ein Klick auf **`▶ Jetzt auslösen`** startet die Digitalisierungsstraße. Nach Abschluss stehen Sandwich-PDF, Neusatz-PDF, TEI-P5 und Markdown zum Download bereit.

### Administrator-Werkzeuge (`scripts/birchville_onboard.py`)

Für Administratoren automatisiert das Tool die Kontenerstellung und das Auftrags-Staging:

```bash
# 1. Benutzer anlegen, Argon2id-Hash erzeugen und Einladungsmail drucken
python3 scripts/birchville_onboard.py create \
  --username scholar1 \
  --display-name "Dr. Maria Muster" \
  --email "maria.muster@example.org" \
  --job boethlingk_sample

# 2. Bestehenden Auftrag einem Benutzer als vorformuliert zuweisen
python3 scripts/birchville_onboard.py stage \
  --job tantrasara_kap3 \
  --user scholar1

# 3. Alle Aufträge und Staging-Status auflisten
python3 scripts/birchville_onboard.py list
```

---

## 5. Nutzung über die Kommandozeile (CLI)

### Multi-Edition aus kanonischem JSON erzeugen
```bash
# Alle 4 Editionen parallel generieren und mit PDF-Labels versehen
python scripts/build_multi_edition.py \
  data/tantrasara_chap3_canonical.json \
  output/tantrasara/ \
  --format all

# Nur die bilinguale Studienausgabe bauen
python scripts/build_multi_edition.py \
  data/tantrasara_chap3_canonical.json \
  output/tantrasara/ \
  --format bilingual
```

### Diakritika-schonendes Scan-Cleaning
```bash
# PDF-Doppelseiten bereinigen und in Einzelseiten trennen
python scripts/image_restoration.py \
  scans/raw_book.pdf \
  output/cleaned_book.pdf \
  --split-spreads \
  --dpi 300
```

### Indische Normalisierung & Transliteration
```bash
# Apparatus-Zeile normalisieren
python scripts/indic_normalizer.py \
  "पं० १० ख० पु० बिम्बप्रतिबिम्बेति पाठः ।" \
  --apparatus
# Ausgabe: paṃ. 10 kha. pu. bimbapratibimbeti pāṭhaḥ .
```

### PDF-Seitenzahlen & Labels nachträglich setzen
```bash
python scripts/postprocess_pdf_metadata.py \
  document.pdf \
  --title-page \
  --body-start 10
```

---

*[VLM]: Vision-Language Model: Ein multimodales KI-Modell, das Bildinhalte (Scans) und Sprache gleichzeitig versteht und dadurch selbst schwierigste historische Schriften fehlerfrei liest.
*[OCR]: Optical Character Recognition: Automatische optische Zeichenerkennung zur Umwandlung von Bildtext in maschinenlesbaren Text.
*[Sandwich-PDF]: Ein PDF, das den sichtbaren Scan als Bildseite zeigt, dahinter jedoch eine unsichtbare, exakt ausgerichtete Textebene für Volltextsuche und Textmarkierung enthält.
*[Typst]: Ein modernes, extrem schnelles Satzsystem (Alternative zu LaTeX) für hochwertige wissenschaftliche Vektor-Druckausgaben.
*[IAST]: International Alphabet of Sanskrit Transliteration: Das akademische Standard-Umschriftsystem für indische Schriften in lateinischen Buchstaben mit Diakritika.
*[Devanāgarī]: Die traditionelle indische Silbenschrift für Sanskrit, Hindi und Marathi.
*[Deskewing]: Automatisches Geraderichten schräg eingescannter Buchseiten.
*[Despeckling]: Entfernung isolierter Staub- und Scan-Punkte im Weißraum unter Erhalt diakritischer Zeichen.
*[TEI-P5]: Text Encoding Initiative: Internationaler XML-Standard für die digitale Langzeitarchivierung geisteswissenschaftlicher Texte.
*[EPUB 3]: Standard-Dateiformat für digitale Bücher mit anpassbarem Fließtext (Reflowable) und eingebetteten Schriften.
*[BBox]: Bounding Box: Die exakten Pixel-Koordinaten (Rechteck) eines Worts oder Buchstabens auf der Scan-Seite.
*[AST]: Abstract Syntax Tree: Strukturierte, hierarchische Baumdarstellung des Buchinhalts (Seiten, Absätze, Zeilen, Wörter).
