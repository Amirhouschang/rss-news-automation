# RSS Daily News — Lokale KI und automatisierte Nachrichten per E-Mail

[English](README.md)

Dieses Projekt verbindet RSS-Sammlung, PostgreSQL, Zufallsauswahl, lokale KI-Zusammenfassung und zeitgesteuerten E-Mail-Versand mit n8n.

Ich habe es gebaut, um Nachrichten verschiedener Herausgeber und auch Themen außerhalb meiner eigenen Interessen zu lesen. Die Auswahl erfolgt **zufällig** und nicht anhand persönlicher Interessen oder der Empfehlungen sozialer Medien. Eine Quelle zu lesen bedeutet nicht, ihr zuzustimmen.

## Endgültiger Ablauf

Der veröffentlichte n8n-Workflow startet täglich um **12:30 Uhr, Europe/Berlin**:

1. Die englischsprachigen Feeds werden abgerufen und die Veröffentlichungsdaten mit dem aktuellen Kalendertag verglichen.
2. Alle verfügbaren, passenden und eindeutigen RSS-Einträge werden in PostgreSQL archiviert.
3. Python wählt pro Quelle zufällig **bis zu fünf Nachrichten** aus. Innerhalb dieser Auswahl wird derselbe Eintrag nicht mehrfach gezogen; jeder Kandidat der Quelle hat dieselbe Auswahlchance.
4. Für ausgewählte Einträge wird der Text aufbereitet und mit **`mistral-small3.1:latest`** über lokales Ollama kurz auf Englisch zusammengefasst. Bereits erfolgreiche Zusammenfassungen können wiederverwendet werden.
5. n8n erstellt und versendet eine gemeinsame E-Mail mit Originaltiteln, Zusammenfassungen und Links.

Bei weniger als fünf passenden Einträgen werden alle verfügbaren Kandidaten ausgewählt. Mit fünf Quellen enthält eine E-Mail höchstens 25 Nachrichten. Neu archivierte, nicht ausgewählte RSS-Einträge erhalten in diesem Lauf keine KI-Zusammenfassung. Bereits in früheren Läufen gespeicherte Zusammenfassungen bleiben erhalten.

| Herausgeberland | Endgültige Quelle | Eingabesprache |
|---|---|---|
| Deutschland | DW | Englisch |
| Iran | IRNA | Englisch |
| China | CGTN — World | Englisch |
| Russland | TASS | Englisch |
| Ukraine | Ukrinform | Englisch |

Das Land ist das Land des Herausgebers; das Thema der Nachricht ist oft ein anderes. Originaltitel bleiben unverändert, und die endgültige Pipeline übersetzt nicht. ECNS wurde in Stage 4 getestet und für den täglichen Betrieb durch CGTN ersetzt.

## Entwicklung und Nachweise

| Stage | Inhalt | Dokumentation |
|---|---|---|
| 1 | Mehrsprachige RSS-Sammlung, Textextraktion und Zugriffsdiagnose | [Stage 1](stage1/README.md) |
| 2 | Textaufbereitung und Ersatz durch RSS-Inhalte | [Stage 2](stage2/README.md) |
| 3 | Lokale Modelle mit englischen und deutschen Ausgaben | [Stage 3](stage3/README.md) |
| 4 | Englische Quellen und Vergleich lokaler Zusammenfassungen | [Stage 4](stage4/README.md) |
| 5 | Optionaler Cloud-Vergleich mit eingefrorenen englischen Eingaben | [Stage 5](stage5/README.md) |
| 6 | Datenbank, Zufallsauswahl und automatisierter E-Mail-Versand | [Stage 6](stage6/README.md) |

Der [Entwicklungsbericht zu Stage 1–5](RSS_Project_Stages_1_to_5.md) dokumentiert die Versuche und manuellen Vergleiche mit den Quelltexten vom **7. Oktober 2026**, einschließlich der Entscheidung für den ursprünglichen Mistral-Prompt. Sein letzter Abschnitt beschreibt den damals geplanten nächsten Schritt; die anschließend umgesetzte Automatisierung steht in [Stage 6](stage6/README.md).

Jeder Stage-Ordner enthält seinen Code und datierte Testergebnisse. Stage 1–3 enthalten außerdem exportierte Ollama-Modelfiles mit dem Coding-Dialog der lokalen Sitzungen. Ich habe durchgehend vorhandene Modelle verwendet; es wurde kein Modell trainiert oder feinabgestimmt.

Die wichtigsten Läufe in Zahlen:

- Stage 3: Der größere Qwen-Test akzeptierte 50 Ausgaben, 25 auf Englisch und 25 auf Deutsch.
- Stage 4: Die beibehaltene Mistral-Baseline akzeptierte 25 englische Ausgaben.
- Stage 5: Die endgültigen Cloud-Läufe mit Sol und Astra akzeptierten jeweils 25 Ausgaben.

„Akzeptiert" heißt, dass das Skript eine gültige Antwort erhalten hat. Ob eine Zusammenfassung dem Quelltext entspricht, ist eine eigene Frage. Ich habe sie auf zwei Wegen geprüft: mit einer automatischen Prüfung und mit einem manuellen Vergleich mit dem Quelltext. Die automatische Prüfung lieferte Fehlalarme und übersah auch echte Abweichungen; deshalb stehen beide Ergebnisse getrennt. Die Stage-READMEs verlinken die zugehörigen Dateien und kennzeichnen, welche Läufe vollständig waren und welche abgebrochen wurden.

## Menschliche Arbeit und KI-Unterstützung

Ich bestimmte Ziel, Quellenanforderungen, Auswahlverfahren, Prüfungsfragen und endgültige Entscheidungen, führte die Versuche aus und bewertete den Workflow und die E-Mail. Prompts entstanden im Dialog mit ChatGPT. ChatGPT und lokale Modelle unterstützten Codeentwicklung, Fehlerbehebung, Prüfung und Dokumentation. Lokale Modelle erzeugten außerdem die experimentellen und endgültigen Zusammenfassungen.

In diesem Projekt geht es um die praktische Anwendung und Bewertung vorhandener Modelle. Der Code entstand mit KI-Unterstützung, und der Vergleich ist ein praktischer Vergleich, kein blindes Benchmark-Verfahren. Die Zusammenfassung gibt den gelieferten Quelltext wieder; sie überprüft nicht, ob die Meldung wahr ist.

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

Dieser Befehl speichert in PostgreSQL. **Die E-Mail wird vom n8n-Workflow versendet.** Für unbeaufsichtigte Läufe werden `--non-interactive` und eine externe libpq-Passwortdatei verwendet; in Git liegt kein Passwort.

Die Datenbank heißt `rss_news` und enthält `sources`, `runs`, `news` sowie die Sicht `news_overview`. Ich nutze DBeaver zur Ansicht und Abfrage; die Pipeline braucht es nicht. Das Repository enthält eine bereinigte n8n-Workflow-Vorlage, das Datenbankschema, die exportierte Quellenkonfiguration und ein Datenbankdiagramm. Zur Einrichtung werden eigene lokale Dienste, Modellgewichte und Zugangsdaten benötigt. Einzelheiten stehen in [Stage 6](stage6/README.md).

## Getesteter Betrieb und Grenzen

Ich bestätigte am **8. Oktober 2026** einen erfolgreichen zeitgesteuerten Lauf mit E-Mail-Versand bei geschlossener Browserseite. Ein vorheriger vollständiger manueller Lauf dauerte etwa zehn Minuten. Auf Grundlage dieses Tests schätze ich die Laufzeit auf zehn bis fünfzehn Minuten; dieser Bereich ist keine garantierte Höchstdauer.

- Der Rechner muss eingeschaltet, wach und online sein; die benötigten Dienste müssen laufen. Die Browserseite darf geschlossen sein.
- Ein Feed zeigt einen veränderlichen Ausschnitt, kein vollständiges Tagesarchiv des Herausgebers. Um 12:30 Uhr fehlen später veröffentlichte Artikel. Einträge ohne brauchbares Veröffentlichungsdatum werden ausgelassen und nicht als heutige Nachricht gezählt.
- Extrahierter Artikeltext kann unvollständig sein, und RSS-Zusammenfassungen enthalten weniger Kontext. Die Zufallsauswahl hängt weiter davon ab, was der Herausgeber in seinen Feed stellt, und sie garantiert keine Themenvielfalt.
- Ein zweiter Lauf am selben Tag kann bereits ausgewählte Nachrichten erneut ziehen. Das System garantiert nicht, dass jede Nachricht nur einmal versendet wird.
- Englische Ausgaben können andere Inhalte als die Originalsprachen enthalten. Zwischen Stage 3 und 4 änderten sich neben der Sprache auch Quellen und Texte; die beiden Stages lassen sich deshalb nicht als reiner Übersetzungstest vergleichen.
- Stage 5 dokumentiert den Cloud-Zugang, der während des Versuchs für mein Konto funktionierte. Andere Abos und die künftige Modellverfügbarkeit können abweichen. Der tägliche Betrieb bleibt lokal.
- Gmail-Autorisierung und Dienstverfügbarkeit müssen für langfristigen Betrieb berücksichtigt werden. Ein erfolgreicher Test zeigt nicht, wie zuverlässig das System über Monate läuft.

## Veröffentlichung

Zugangsdaten und private Notizen gehören nicht zum öffentlichen Projekt. Die veröffentlichten Dateien wurden vor der Veröffentlichung geprüft. Persönliche Zugangsdaten-Verweise wurden aus dem Workflow-Export entfernt. Gespeicherte Meldungen und KI-Ausgaben sind Versuchsmaterial, keine unabhängig verifizierten Tatsachenberichte. Historische Ergebnisse gehören zu ihren damaligen Eingaben und Prompts; heutiger Code reproduziert nicht zwangsläufig ältere Promptvarianten oder veränderte Feeds.

## Urheberrecht

© 2026 Amirhoushang Rahmannejad. Alle Rechte vorbehalten.

Sofern nicht anders angegeben, dürfen der für dieses Projekt erstellte Code und die Dokumentation ohne meine Zustimmung nicht weiterverwendet, verändert oder weiterverbreitet werden. Nachrichteninhalte, Software und Modelle Dritter unterliegen den jeweiligen Rechten und Lizenzen.
