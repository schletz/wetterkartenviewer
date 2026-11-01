# HTML-Bericht

Lies diese Datei nur, wenn der Nutzer eine Analyse als Bericht will (siehe „Chat oder Bericht“ in
`SKILL.md`). Sie setzt voraus, dass die Analyse fertig ist: Tabellen und TSV liegen im
Arbeitsverzeichnis, die Tage sind gedeutet, und die Regeln unter „Ausgabe“ in `SKILL.md` (Tage
einteilen, Absatz für Endkunden, Unsicherheit) gelten auch hier.

Das Ergebnis ist eine eigenständige HTML-Datei. Sie enthält die Analyse und ein eingebettetes
SVG-Diagramm von T850 und Schichtdicke, darunter die Datentabelle zum Aufklappen. Du schreibst nur
den Text als Markdown, Diagramm und HTML erzeugen Skripte deterministisch. So bleibt der Bericht bei
jedem Aufruf gleich aufgebaut, und das SVG muss nicht durch deinen Kontext. Bei einer Region nimm
für Diagramm und Tabelle den wichtigsten Punkt.

## Text schreiben

Schreib die Analyse nach `<arbeitsverzeichnis>/analyse_<ort>.md`:

```
# Synoptische Analyse <Ort> – ECMWF <TT.MM.JJJJ HH>z, ICON-D2 <TT.MM. HH>z

<Absatz für Endkunden: das Wetter am Boden für die 10 Tage>

<2–4 Sätze synoptischer Überblick: welche Großwetterlagen in welcher Abfolge, wichtigste Umstellung>

## <Wochentag, TT.MM.>

<Fließtext, ein bis zwei Absätze>
```

Jeder Tagestext behandelt der Reihe nach:

1. die Großwetterlage in der Höhe und am Boden und wo der Ort darin liegt,
2. die Luftmasse mit Werten aus der Tabelle (T850, Dicke),
3. das daraus folgende Wetter am Ort: Bewölkung, Niederschlag und seine Art, Wind, Höchstwerte als
   Spanne, bei Bedarf das Bergwetter,
4. bei Ereignissen auch den Zeitpunkt.

Der Konverter kennt nur die Elemente der Vorlage: Überschriften `#` bis `###`, Absätze, Listen mit
`- ` sowie `**fett**` und `*kursiv*`. Tabellen, Links und Bilder lässt du weg.

## Diagramm

```
python <skill-dir>/scripts/generate_diagram.py <arbeitsverzeichnis>/data_<ort>_ecmwf.tsv --climate <data>/era5_means --lat 48.21 --lng 16.37 --out <arbeitsverzeichnis>/diagram_<ort>.svg
```

Die x-Achse zeigt Tage in UTC mit Strichen alle 3 h, links T850, rechts die Schichtdicke.

Eine graue Linie zeigt das Mittel von T850 der Klimatologie am Ort, für Tageszeit und Kalendertag jedes
Termins. Die Fläche zwischen ihr und der Vorhersage ist rot, wo die Vorhersage wärmer ist, und
blau, wo sie kälter ist. Jenseits von 1, 2 und 3 σ wird sie jeweils eine Stufe kräftiger, der
Tooltip nennt die Abweichung in σ. So sieht der Leser auf einen Blick, ob die Luftmasse für die
Jahreszeit ungewöhnlich ist. Deshalb braucht das Skript Breite und Länge des Ortes, bei einer
Region die des Punkts aus der Tabelle.

Mittel und Streuung stammen aus der Klimatologie derselben Tageszeit wie der Termin
(`lib/t850_climate.py`). Die Tagesmittel nimmt das Skript nicht, weil sie den Tagesgang wegmitteln.

Beide Skalen sind gekoppelt: 1,6 dam pro K, 0 °C entspricht 544 dam. Bei typischen Luftmassen
liegen deshalb beide Kurven übereinander. Liegt die Dicke deutlich unter der T850-Kurve, ist die
Luftsäule im Mittel kälter, als T850 vermuten lässt. Das ist typisch für Kaltluft in der Höhe unter
einem Höhentief. Liegt sie darüber, ist die Säule wärmer.

Ohne Parameter passt das Skript die Skala an die Daten an, auf volle 4 K gerundet, sodass keine der
beiden Kurven abgeschnitten wird. Mit `--min-850`, `--max-850`, `--min-thickness` und
`--max-thickness` legst du Grenzen fest. Das braucht es nur, wenn mehrere Berichte dieselbe Skala
haben sollen, etwa um Orte zu vergleichen. Eine nicht angegebene Dickegrenze folgt über die Kopplung
aus der T850-Grenze.

## HTML zusammenbauen

```
python <skill-dir>/scripts/build_report.py --markdown <arbeitsverzeichnis>/analyse_<ort>.md --svg <arbeitsverzeichnis>/diagram_<ort>.svg --tsv <arbeitsverzeichnis>/data_<ort>_ecmwf.tsv --caption "<Bildunterschrift>" --table-summary "<Datentabelle>" --lang de --out <ziel>/synop_<ort>_<base-time>.html
```

- `--caption` und `--table-summary` schreibst du in der Sprache des Nutzers. Die Bildunterschrift
  nennt den Ort und sagt, dass die Zeitachse in UTC läuft, während der Text Ortszeit verwendet.
- Das Diagramm landet nach dem synoptischen Überblick, vor dem ersten Tag. Der Absatz für Endkunden
  ist hervorgehoben.
- Als `<ziel>` nimmst du das Arbeitsverzeichnis des Nutzers, sofern er keinen anderen Ort nennt. Nur
  Rohdaten und Zwischendateien gehören in den Scratchpad.
- **Karten:** Will der Nutzer die Karten haben, kopierst du die markierten Kopien (`marked_<ort>`)
  nach `<ziel>/synop_charts_<YYYYMMDDHH>/`. Die unmarkierten liegen ohnehin im Datenordner.

Zeig den Bericht danach dem Nutzer, wenn deine Umgebung Dateien anzeigen kann, und nenn in jedem
Fall den Pfad der HTML-Datei. Dazu kommt der Überblick in zwei bis drei Sätzen. Die Tagestexte
stehen im Bericht und müssen nicht noch einmal in den Chat.
