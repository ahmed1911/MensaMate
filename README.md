# 🍽️ HWR Mensa Email Bot

> Automatisierter Email-Bot für die HWR Berlin Mensa - Täglich frische Menüpläne direkt ins Postfach

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code Style: Black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

## 📋 Überblick

Ein Python-Bot, der den Mensaplan der HWR Berlin automatisch herunterlädt und täglich per Email verschickt - mit intelligenter Filterung nach Allergenen und Zutaten.

### ✨ Features

- 📥 **Automatischer Download** - Lädt den aktuellen Wochenplan von STW Berlin
- 📧 **Smart Email Versand** - Zeigt nur relevante Gerichte (heute + morgen)
- 🚫 **Flexible Filterung** - Nach Wörtern (z.B. "Schwein", "Rind") und Allergenen
- 🧬 **Intelligente Allergen-Erkennung** - Automatisches Mapping von Namen zu Allergen-Codes
- 🏷️ **Kategorisierung** - Automatische Trennung von Hauptgerichten und Beilagen
- 🔐 **Sichere Konfiguration** - Alle sensiblen Daten in `.env` File
- 🎯 **Objektorientiert** - Saubere Architektur mit `MensaParser` und `EmailNotifier` Klassen

## 📸 Screenshots

<details>
<summary><b>📧 Beispiel Email</b> (Click to expand)</summary>

```
Betreff: Mensa HWR - 20.10

╔════════════════════════════════════╗
║  HWR Mensa Menü                    ║
╚════════════════════════════════════╝

📅 Heute (Montag)
─────────────────────────────
🥗 Hauptgerichte:
  • Pasta mit Tomatensauce
    2.50€
  • Gemüsecurry mit Reis
    3.20€

🥔 Beilagen:
  • Salat der Saison
    0.80€

📅 Morgen (Dienstag)
─────────────────────────────
🥗 Hauptgerichte:
  • Ofenkartoffel mit Quark
    2.80€
  ...
```
</details>

<details>
<summary><b>💻 Terminal Output</b> (Click to expand)</summary>

```bash
$ python3 mensa_email.py
2025-10-20 12:00:00 - INFO - 📥 Downloading latest menu...
2025-10-20 12:00:01 - INFO - ✅ Download complete.
2025-10-20 12:00:01 - INFO - 📄 Parsing PDF to extract dishes...
2025-10-20 12:00:02 - INFO - ✅ Found 35 dishes across all days.
2025-10-20 12:00:02 - INFO - 📧 Sending email to 1 recipient(s)...
2025-10-20 12:00:03 - INFO - ✅ Email sent successfully to: you@gmail.com
```
</details>

## 🚀 Quick Start

### Installation

```bash
# Repository klonen
git clone https://github.com/ahmed1911/MensaMate.git
cd MensaEssen

# Virtuelle Umgebung erstellen (empfohlen)
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# oder
venv\Scripts\activate     # Windows

# Dependencies installieren
pip3 install requests pdfplumber python-dotenv
```

### Konfiguration

1. **Erstelle `.env` Datei:**
```bash
cp .env.example .env
```

2. **Konfiguriere deine Einstellungen:**
```env
# === Email Konfiguration ===
SMTP_EMAIL=deine-email@gmail.com
SMTP_PASSWORD=dein-app-passwort
RECIPIENTS=empfaenger1@gmail.com,empfaenger2@gmail.com

# === Filter (optional) ===
FILTER_WORDS=schwein,rind,lamm
FILTER_ALLERGENS=soja,milch,erdnüsse,sellerie

# === Debug (optional) ===
DEBUG=false
```

#### 🔑 Gmail App-Passwort erstellen

Für Gmail benötigst du ein **App-Passwort** (nicht dein normales Passwort):

1. Gehe zu [Google Account](https://myaccount.google.com/)
2. Sicherheit → 2-Faktor-Authentifizierung aktivieren (falls nicht aktiv)
3. Sicherheit → App-Passwörter → Neues App-Passwort erstellen
4. Wähle "Mail" und "Anderes Gerät"
5. Kopiere das 16-stellige Passwort in `.env`

### Verwendung

```bash
# Einmalig ausführen
python3 mensa_email.py
```

**Erwartete Ausgabe:**
```
2025-10-20 12:00:00 - INFO - 📥 Downloading latest menu...
2025-10-20 12:00:01 - INFO - ✅ Download complete.
2025-10-20 12:00:01 - INFO - 📄 Parsing PDF to extract dishes...
2025-10-20 12:00:02 - INFO - ✅ Found 35 dishes across all days.
2025-10-20 12:00:02 - INFO - 📧 Sending email to 1 recipient(s)...
2025-10-20 12:00:03 - INFO - ✅ Email sent successfully to: you@gmail.com
```

## ⚙️ Konfiguration im Detail

### Filter-Optionen

#### 1. Wort-Filter (`FILTER_WORDS`)
Filtert Gerichte, die bestimmte Wörter im Titel enthalten:

```env
# Keine tierischen Produkte
FILTER_WORDS=schwein,rind,lamm,huhn,fisch

# Einzelne Zutaten
FILTER_WORDS=spinat,rosenkohl
```

- **Case-insensitive** - Groß-/Kleinschreibung egal
- **Komma-getrennt** - Mehrere Filter möglich
- **Teilstring-Match** - "schwein" filtert auch "Schweinefleisch", "Schweinebraten"

#### 2. Allergen-Filter (`FILTER_ALLERGENS`)

⚠️ **WICHTIG:** Verwende **Namen**, nicht Nummern!

```env
# ✅ RICHTIG - Namen verwenden
FILTER_ALLERGENS=soja,milch,erdnüsse,sellerie,senf

# ❌ FALSCH - Keine Nummern
FILTER_ALLERGENS=28,30,25
```

**Wie funktioniert's?**
1. Bot lädt PDF und liest automatisch die Allergen-Liste von der letzten Seite
2. Erstellt Mapping: `soja` → `28`, `milch` → `30`, etc.
3. Filtert alle Gerichte mit diesen Allergen-Codes

**Verfügbare Allergene:**
```
Getreide: weizen, roggen, gerste, hafer, dinkel, kamut
Nüsse: erdnüsse, mandeln, haselnüsse, walnüsse, cashew, pekan, paranüsse, pistazien, macadamianüsse
Andere: soja, milch, eier, fisch, krebstiere, sellerie, senf, sesam, schwefeldioxid, lupinen, weichtiere
```

#### 3. Debug-Modus (`DEBUG`)

Zeigt alle gefundenen Allergene aus der PDF an:

```env
DEBUG=true
```

Ausgabe:
```
🔍 DEBUG: Gefundene Allergene aus PDF:
==================================================
   1  → weizen
  21a → weizen
  21b → roggen
  28  → soja
  30  → milch und milchprodukte
  30  → milch
==================================================
```

## 🤖 Automatisierung

### Linux / macOS - Cron

Tägliche Email um 8:00 Uhr (Montag bis Freitag):

```bash
# Crontab öffnen
crontab -e

# Diese Zeile hinzufügen:
0 8 * * 1-5 cd /pfad/zum/projekt && /pfad/zum/python3 mensa_email.py >> /tmp/mensa_bot.log 2>&1
```

**Beispiel mit virtuellem Environment:**
```bash
0 8 * * 1-5 cd /home/user/MensaEssen && ./venv/bin/python3 mensa_email.py >> /tmp/mensa_bot.log 2>&1
```

**Crontab Syntax:**
```
0 8 * * 1-5
│ │ │ │ │
│ │ │ │ └─── Wochentag (1-5 = Montag-Freitag)
│ │ │ └───── Monat (1-12)
│ │ └─────── Tag (1-31)
│ └───────── Stunde (0-23)
└─────────── Minute (0-59)
```

## 🏗️ Architektur

Das Projekt folgt objektorientierten Prinzipien und ist in mehrere Module aufgeteilt:

```
mensa_email.py
├── Config                    # Dataclass für Konfiguration
├── Dish                      # Dataclass für Gericht
├── MensaParser              # PDF Download & Parsing
│   ├── download()           # Lädt PDF vom Server
│   ├── _extract_allergen_mapping()  # Liest Allergen-Liste
│   ├── _resolve_filter_allergens()  # Konvertiert Namen → Codes
│   ├── _merge_table_cells() # Merged mehrzeilige Gerichte
│   ├── _parse_dish_from_cell()      # Parst einzelnes Gericht
│   └── get_all_dishes()     # Orchestriert das Parsing
└── EmailNotifier            # Email Formatierung & Versand
    ├── _format_dish_section() # HTML für Kategorie
    ├── _format_html_body()    # Kompletter Email-Body
    └── send()                 # SMTP Versand
```

### Design

Das Projekt verwendet objektorientiertes Design mit klaren Verantwortlichkeiten:

- **Dataclasses** für strukturierte Daten (`Config`, `Dish`)
- **Separation of Concerns** - Parser und Email-Versand getrennt
- **Type Hints** für bessere Code-Qualität
- **Logging** statt Print-Statements
- **Environment-based Configuration** für Sicherheit

### Debug-Modus

```bash
# .env anpassen
DEBUG=true

# Script ausführen
python3 mensa_email.py
```

Zeigt alle Allergen-Mappings an, die aus der PDF gelesen wurden.

## 📊 Technologie-Stack

| Komponente | Technologie | Version | Zweck |
|-----------|-------------|---------|-------|
| **Sprache** | Python | 3.9+ | Hauptsprache |
| **PDF Parsing** | pdfplumber | 0.11.7 | Extrahiert Text und Tabellen aus PDF |
| **HTTP Requests** | requests | 2.32.3 | Lädt PDF vom Server |
| **Config Management** | python-dotenv | 1.0.1 | Lädt `.env` Variablen |
| **Email** | smtplib | stdlib | SMTP Email-Versand (built-in) |
| **Logging** | logging | stdlib | Strukturierte Logs (built-in) |
| **Dataclasses** | dataclasses | stdlib | Strukturierte Daten (built-in) |

## 🤝 Contributing

Contributions sind willkommen! Bitte beachte:

1. **Fork** das Repository
2. **Branch** erstellen: `git checkout -b feature/AmazingFeature`
3. **Commit** changes: `git commit -m 'Add some AmazingFeature'`
4. **Push** to branch: `git push origin feature/AmazingFeature`
5. **Pull Request** öffnen

### Code Style
- Folge PEP 8 Guidelines
- Nutze Type Hints
- Schreibe Docstrings für alle Funktionen
- Verwende `logging` statt `print()`

## 📜 Lizenz

Dieses Projekt ist unter der **MIT License** lizenziert - siehe [LICENSE](LICENSE) file für Details.

```
MIT License - Copyright (c) 2025 Ahmed Bauer

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:
[...]
```

## 📞 Support & Kontakt

- **Issues:** [GitHub Issues](https://github.com/ahmed1911/MensaMate/issues)
- **Email:** demha.bauer@gmail.com
- **HWR Berlin:** [Mensa Website](https://www.stw.berlin/mensen/einrichtungen/hochschule-f%C3%BCr-wirtschaft-und-recht-berlin/mensa-hwr-badensche-stra%C3%9Fe.html)

## 🙏 Acknowledgments

- **STW Berlin** - Für die öffentliche PDF-API
- **pdfplumber** - Awesome PDF parsing library
- **HWR Berlin Students** - Für Feedback und Testing

---

**⭐ Wenn dir dieses Projekt gefällt, gib ihm einen Star auf GitHub!**

Made with ❤️ by Ahmed Bauer
