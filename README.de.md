# RSS Daily News — Lokale KI und automatisierte Nachrichten per E-Mail

[English](README.md)

Dieses Projekt verbindet RSS-Sammlung, PostgreSQL, Zufallsauswahl, lokale KI-Zusammenfassung und zeitgesteuerten E-Mail-Versand mit n8n.

Das Ziel ist, Nachrichten verschiedener Herausgeber und auch Themen außerhalb der eigenen Interessen zu lesen. Die Auswahl erfolgt zufällig und nicht anhand persönlicher Interessen oder der Empfehlungen sozialer Medien. Eine Quelle zu lesen bedeutet nicht, ihr zuzustimmen.

## Endgültiger Ablauf

Der veröffentlichte n8n-Workflow startet täglich um **12:30 Uhr, Europe/Berlin**:

1. Die englischsprachigen Feeds werden abgerufen und die Veröffentlichungsdaten mit dem aktuellen Kalendertag verglichen.
2. Alle verfügbaren, passenden und eindeutigen RSS-Einträge werden in PostgreSQL archiviert.
3. Python wählt pro Quelle zufällig **bis zu fünf Nachrichten** aus. Innerhalb dieser Auswahl wird derselbe Eintrag nicht mehrfach gezogen; jeder Kandidat der Quelle hat dieselbe Auswahlchance.
4. Für ausgewählte Einträge wird der Text aufbereitet und mit **`mistral-small3.1:latest`** über lokales Ollama kurz auf Englisch zusammengefasst. Bereits erfolgreiche Zusammenfassungen können wiederverwendet werden.
5. n8n erstellt und versendet eine gemeinsame E-Mail mit Originaltiteln, Zusammenfassungen und Links.

Bei weniger als fünf passenden Einträgen werden alle verfügbaren Kandidaten ausgewählt. Mit fünf Quellen beträgt die maximale Auswahl 25 Nachrichten. Neu archivierte, nicht ausgewählte RSS-Einträge erhalten in diesem Lauf keine KI-Zusammenfassung. Bereits in früheren Läufen gespeicherte Zusammenfassungen bleiben erhalten.

| Herausgeberland | Endgültige Quelle | Eingabesprache |
|---|---|---|
| Deutschland | DW | Englisch |
| Iran | IRNA | Englisch |
| China | CGTN — World | Englisch |
| Russland | TASS | Englisch |
| Ukraine | Ukrinform | Englisch |

Das Land bezeichnet den Herausgeber, nicht zwangsläufig das Thema der Nachricht. Originaltitel bleiben unverändert. Die endgültige Pipeline übersetzt nicht. ECNS wurde in Stage 4 getestet und für den täglichen Betrieb durch CGTN ersetzt.

## Entwicklung und Nachweise

| Stage | Inhalt | Dokumentation |
|---|---|---|
| 1 | Mehrsprachige RSS-Sammlung, Textextraktion und Zugriffsdiagnose | [Stage 1](stage1/README.md) |
| 2 | Textaufbereitung und Ersatz durch RSS-Inhalte | [Stage 2](stage2/README.md) |
| 3 | Lokale Modelle mit englischen und deutschen Ausgaben | [Stage 3](stage3/README.md) |
| 4 | Englische Quellen und Vergleich lokaler Zusammenfassungen | [Stage 4](stage4/README.md) |
| 5 | Optionaler Cloud-Vergleich mit eingefrorenen englischen Eingaben | [Stage 5](stage5/README.md) |
| 6 | Datenbank, Zufallsauswahl und automatisierter E-Mail-Versand | [Stage 6](stage6/README.md) |

Die Stage-Ordner enthalten Code und datierte Testergebnisse. Stage 1–3 enthalten außerdem exportierte Ollama-Modelfiles mit gespeicherten Dialognachrichten. Diese dokumentieren die gespeicherten lokalen Coding-Sitzungen, nicht zwingend sämtliche Gespräche des Projekts. Modelle wurden weder trainiert noch feinabgestimmt.

Im größeren Qwen-Test von Stage 3 wurden 50 Ausgaben akzeptiert: 25 auf Englisch und 25 auf Deutsch. Die beibehaltene Mistral-Baseline aus Stage 4 akzeptierte 25 englische Ausgaben. Die endgültigen Cloud-Läufe mit Sol und Astra aus Stage 5 akzeptierten jeweils 25 Ausgaben. Eine akzeptierte Antwort ist kein Nachweis inhaltlicher Richtigkeit.

Automatische Qualitätsprüfungen und dokumentierte Vergleiche mit den Quelltexten werden getrennt dargestellt. Automatische Warnungen können Fehlalarme sein; tatsächliche Abweichungen können unbemerkt bleiben. Die Stage-READMEs verlinken die zugehörigen Dateien und unterscheiden vollständige von abgebrochenen Läufen.

## Menschliche Arbeit und KI-Unterstützung

Ich bestimmte Ziel, Quellenanforderungen, Auswahlverfahren, Prüfungsfragen und endgültige Entscheidungen, führte die Versuche aus und bewertete den Workflow und die E-Mail. Prompts entstanden im Dialog mit ChatGPT. ChatGPT und lokale Modelle unterstützten Codeentwicklung, Fehlerbehebung, Prüfung und Dokumentation. Lokale Modelle erzeugten außerdem die experimentellen und endgültigen Zusammenfassungen.

Das Projekt dokumentiert die Anwendung und Bewertung vorhandener Modelle. Es beansprucht weder eigene Modellentwicklung noch ein blindes Benchmark-Verfahren oder vollständig manuell geschriebenen Code. Die Zusammenfassung soll den gelieferten Quelltext wiedergeben; sie überprüft nicht unabhängig die Wahrheit der Meldung.

## Ausführung

Die endgültige Pipeline liegt in [stage6/daily_news.py](stage6/daily_news.py). Sie importiert Hilfsfunktionen aus Stage 4; dieser Ordner muss erhalten bleiben.

Für das endgültige Skript wird Python **3.12 oder neuer** benötigt. Die wichtigsten Python-Abhängigkeiten sind `requests`, `feedparser`, `trafilatura` und `psycopg[binary]`:

```bash
python -m pip install requests feedparser trafilatura "psycopg[binary]"
```

PostgreSQL, Ollama mit dem verwendeten Modell und die Datenbankstruktur samt Quellenkonfiguration müssen bereits eingerichtet sein. Aus dem Hauptordner lässt sich Sammlung und Zusammenfassung manuell starten:

```bash
python stage6/daily_news.py --sample-per-source 5
```

Dieser Befehl speichert in PostgreSQL. **Die E-Mail wird vom n8n-Workflow versendet.** Für unbeaufsichtigte Läufe werden `--non-interactive` und eine externe libpq-Passwortdatei verwendet.

Die verwendete Datenbank heißt `rss_news` und enthält `sources`, `runs`, `news` sowie die Sicht `news_overview`. DBeaver dient zur Ansicht und Abfrage. Eine bereinigte n8n-Workflow-Vorlage ist enthalten. Datenbankschema, exportierte Quellenkonfiguration und Datenbankdiagramm sind enthalten. Zur Einrichtung werden außerdem die lokalen Dienste, Modellgewichte und eigene Zugangsdaten benötigt. Einzelheiten stehen in [Stage 6](stage6/README.md).

## Getesteter Betrieb und Grenzen

Ich bestätigte am **8. Oktober 2026** einen erfolgreichen zeitgesteuerten Lauf mit E-Mail-Versand bei geschlossener Browserseite. Ein vorheriger vollständiger manueller Lauf dauerte etwa zehn Minuten. Auf Grundlage dieses Tests schätze ich die Laufzeit auf zehn bis fünfzehn Minuten; dieser Bereich ist keine garantierte Höchstdauer.

- Der Rechner muss eingeschaltet, wach und online sein; die benötigten Dienste müssen laufen. Die Browserseite darf geschlossen sein.
- Ein Feed ist ein veränderlicher Ausschnitt und kein vollständiges Tagesarchiv. Um 12:30 Uhr fehlen später veröffentlichte Artikel. Unbrauchbare Datumsangaben werden nicht stillschweigend als heutiges Datum behandelt.
- Extrahierter Artikeltext kann unvollständig sein. RSS-Zusammenfassungen enthalten weniger Kontext. Zufall garantiert keine Themenvielfalt und beseitigt nicht die Vorauswahl des Herausgebers.
- Neue Läufe am selben Tag können erneut bereits ausgewählte Nachrichten ziehen. Ein garantiert einmaliger E-Mail-Versand ist nicht implementiert.
- Englische Ausgaben können andere Inhalte als Originalsprachen enthalten. Zwischen Stage 3 und 4 änderten sich auch Quellen und Texte; der Vergleich isoliert daher nicht ausschließlich Übersetzungsleistung.
- Stage 5 dokumentiert damals funktionierenden, accountspezifischen Cloud-Zugang. Daraus folgt kein allgemeiner API-Anspruch für jedes Abo und keine garantierte künftige Modellverfügbarkeit. Der tägliche Betrieb bleibt lokal.
- Gmail-Autorisierung und Dienstverfügbarkeit müssen für langfristigen Betrieb berücksichtigt werden. Ein erfolgreicher Test belegt keine unbegrenzte Zuverlässigkeit.

## Veröffentlichung

Zugangsdaten und private Notizen gehören nicht zum öffentlichen Projekt. Die veröffentlichten Dateien wurden vor der Veröffentlichung geprüft. Persönliche Zugangsdaten-Verweise wurden aus dem Workflow-Export entfernt. Gespeicherte Meldungen und KI-Ausgaben sind Versuchsmaterial, keine unabhängig verifizierten Tatsachenberichte. Historische Ergebnisse gehören zu ihren damaligen Eingaben und Prompts; heutiger Code reproduziert nicht zwangsläufig ältere Promptvarianten oder veränderte Feeds.

## Urheberrecht

© 2026 Amirhoushang Rahmannejad. Alle Rechte vorbehalten.

Sofern nicht anders angegeben, dürfen der für dieses Projekt erstellte Code und die Dokumentation ohne meine Zustimmung nicht weiterverwendet, verändert oder weiterverbreitet werden. Nachrichteninhalte, Software und Modelle Dritter unterliegen den jeweiligen Rechten und Lizenzen.
