# draw_cities.py — Entwickler- und Agent-Dokumentation

Diese Datei beschreibt das Python-Werkzeug [draw_cities.py](draw_cities.py) so, dass Erweiterungen ohne vorheriges vollständiges Lesen des Quellcodes möglich sind. Sie ist bewusst redundant zu den Docstrings im Code gehalten, ergänzt aber Datenfluss, Kalibrierung, Invarianten und typische Erweiterungspunkte.

## 1. Zweck

Das Skript nimmt eine ECMWF-Wetterkarte (500 hPa Geopotential + 850 hPa Temperatur, Europa-Ausschnitt) und legt darüber:

- Punktmarker samt Beschriftung für europäische Hauptstädte,
- die Gültigkeitszeit der Karte (oben links),
- den Modelllauf (unten links, nur wenn bekannt),
- eine Temperatur-Farblegende (unten rechts),
- optional ein darüber gestapeltes ENS-Meteogramm.

Die Quellbilder können lokal vorliegen oder direkt von `charts.ecmwf.int` geladen werden. Das Ergebnis ist ein einzelnes Bild (`map.webp` bzw. die überschriebene Eingabedatei).

## 2. Modulüberblick

| Datei | Zeilen | Verantwortung |
| --- | --- | --- |
| [draw_cities.py](draw_cities.py) | 394 | CLI, Projektion, sämtliches Rendering, Bildkomposition |
| [ecmwf_api.py](ecmwf_api.py) | 126 | HTTP-Zugriff auf die ECMWF Open-Charts-API (Karte + Meteogramm) |
| [legend.py](legend.py) | 101 | Datenmodell der Farblegende, Parsen der API-Legende, Fallback-Werte |
| [upscale.py](upscale.py) | 91 | Magic-Kernel-Sharp-Resampling (nur für den Meteogramm-Streifen) |

Externe Abhängigkeiten: `requests`, `Pillow` (PIL), `numpy`. Es gibt keine `requirements.txt`; die Pakete werden global erwartet. Standardbibliothek: `math`, `os`, `sys`, `datetime`, `io`, `typing`, `msvcrt` (nur Windows, mit Fallback).

Der restliche Repository-Inhalt ist der JavaScript-Client (siehe [README.md](README.md)); das Python-Werkzeug ist davon unabhängig und wird nicht vom Browser aufgerufen.

## 3. Aufrufmodi

```
python draw_cities.py <YYYYMMDDHH>                       # Download-Modus
python draw_cities.py <karte> <YYYYMMDDHH>               # lokale Karte, kein Meteogramm
python draw_cities.py <karte> <diagramm> <YYYYMMDDHH>    # lokale Karte + lokales Diagramm
```

Das letzte Argument ist immer die Gültigkeitszeit in `YYYYMMDDHH` (Stunde in UTC). Sie wird in [draw_cities.py:362](draw_cities.py#L362) validiert, **bevor** ein Download startet.

| Modus | Quelle Karte | Quelle Meteogramm | `base_time` | Legende | Annotationspause | Ausgabe |
| --- | --- | --- | --- | --- | --- | --- |
| 1 Argument | API | API | von der API | von der API | ja | `DEFAULT_OUTPUT` (`map.webp`) |
| 2 Argumente | lokal | — | `None` | `FALLBACK_LEGEND` | nein | Eingabedatei wird überschrieben |
| 3 Argumente | lokal | lokal | `None` | `FALLBACK_LEGEND` | nein | Karten-Eingabedatei wird überschrieben |

Im Dateimodus wird **kein** HTTP-Request abgesetzt; die Legende kommt dort ausschließlich aus den fest hinterlegten Werten.

Rückgabewert von `main()`: `0` bei Erfolg, `1` bei falscher Argumentanzahl, ungültigem Zeitstempel oder fehlgeschlagenem Abruf.

## 4. Datenfluss

```
main(argv)                                     draw_cities.py:347
 ├─ Argumente parsen + Zeitstempel validieren
 ├─ load_sources(map_path, chart_path, ts)     draw_cities.py:271
 │    ├─ lokal:    Image.open(...) -> MapChart(image, None, FALLBACK_LEGEND)
 │    └─ Download: ecmwf_api.fetch_map(ts)        -> MapChart(image, base_time, legend)
 │                    └─ legend.parse_legend(result)   legend.py:72
 │                 ecmwf_api.fetch_meteogram()    -> Image
 ├─ [nur Download] pause_for_annotations(...)  draw_cities.py:309
 │    └─ Karte croppen -> map.png schreiben -> Tastendruck abwarten
 │       -> zurücklesen -> map.png löschen
 ├─ draw_cities(map_image, ts, base_time, legend)  draw_cities.py:211
 │    ├─ convert("RGBA") + crop((0,0,*CROP_SIZE))
 │    ├─ pro Stadt: latlon_to_xy() -> Ellipse + Text
 │    ├─ render_timestamp()                    draw_cities.py:133
 │    ├─ render_base_time()   (nur wenn base_time)  draw_cities.py:154
 │    └─ render_legend()                       draw_cities.py:172
 ├─ [wenn chart_image] combine_with_meteogram()   draw_cities.py:246
 │    └─ crop(METEOGRAM_BOX) -> magic_kernel_sharp_resize() -> stapeln
 └─ image.save(output_path, lossless=True)
```

Wichtige Reihenfolge-Invarianten:

1. **Handannotationen vor den Overlays.** `pause_for_annotations()` schreibt die *nackte* Karte heraus, damit Tiefdruckgebiete, Fronten usw. im Bildeditor eingezeichnet werden können; die Marker, Beschriftungen und die Legende landen anschließend *darüber* und werden nicht verdeckt.
2. **Legende vor der Meteogramm-Komposition.** `render_legend()` bekommt die Größe der Karte (1000×600), nicht die des kombinierten Bildes. Wird das geändert, verschiebt sich die Legende in den Meteogramm-Streifen.
3. **Crop vor allem Zeichnen.** Der Zuschnitt behält die linke obere Ecke, deshalb bleiben die Projektionsparameter gültig (siehe Abschnitt 5).

## 5. Projektion

Die Karte ist polarstereographisch mit senkrechtem Nullmeridian. Das Vorwärtsmodell in `latlon_to_xy()` ([draw_cities.py:124](draw_cities.py#L124)) lautet, in Bildkoordinaten mit Ursprung links oben und nach unten zeigender y-Achse:

```
rho = SCALE_K * tan(45° − lat/2)
x   = POLE_X + rho * sin(lon)
y   = POLE_Y + rho * cos(lon)
```

Parameter ([draw_cities.py:51-53](draw_cities.py#L51-L53)): `POLE_X = 481.0`, `POLE_Y = -180.8`, `SCALE_K = 1320.8`. Der Nordpol liegt also oberhalb des sichtbaren Bildausschnitts.

Herkunft: einmaliger Least-Squares-Fit an neun gemessene Kontrollpunkte, RMS-Fehler 0,45 px. Die gefittete Kegelkonstante 0,9983 wurde auf den exakten stereographischen Wert 1 gerundet und ist deshalb nicht als Konstante vorhanden.

**Neukalibrierung** (nötig, sobald ECMWF Ausschnitt oder Projektion des Produkts ändert): mehrere gut identifizierbare Punkte (Küstenlinien, bekannte Städte) im Quellbild ausmessen und die drei Parameter numerisch anpassen. Solange nur oben links zugeschnitten wird, bleibt die Kalibrierung gültig — jeder Crop, der links oder oben Pixel entfernt, macht sie ungültig.

Eine Rückwärtstransformation (Pixel → lat/lon) existiert nicht; sie wäre `lat = 90 − 2·atan(rho/SCALE_K)`, `lon = atan2(x−POLE_X, y−POLE_Y)`.

## 6. Konstanten-Referenz

### draw_cities.py

| Konstante | Zeile | Wert / Bedeutung |
| --- | --- | --- |
| `POLE_X`, `POLE_Y`, `SCALE_K` | 57–59 | Projektionsparameter (Abschnitt 5) |
| `CROP_SIZE` | 63 | `(1000, 600)` — Zielgröße nach dem Zuschnitt links oben |
| `METEOGRAM_BOX` | 67 | `(25, 547, 605, 680)` — Ausschnitt des Temperatur-Meteogramms im Diagrammbild (left, upper, right, lower) |
| `DEFAULT_OUTPUT` | 71 | `map.webp` — Ausgabe im Download-Modus |
| `ANNOTATION_FILE` | 77 | `map.png` — Arbeitsdatei für die Handannotation; PNG bewusst, um keine Generationsverluste einzuführen |
| `METEOGRAM_GAP` | 83 | `11` px Abstand zwischen Meteogramm und Karte |
| `LABEL_FILL`, `LABEL_STROKE` | 87–88 | helle Füllung auf dunkler Kontur, damit Text über jeder Temperaturschattierung lesbar bleibt |
| `WEEKDAYS_DE`, `MONTHS_DE` | 92–94 | deutsche Bezeichner, bewusst unabhängig vom System-Locale |
| `CITIES` | 97–111 | `Name -> (lat °N, lon °E)`, 13 Einträge |

### ecmwf_api.py

| Konstante | Zeile | Bedeutung |
| --- | --- | --- |
| `API_BASE` | 19 | `https://charts.ecmwf.int/opencharts-api/v1` |
| `MAP_PRODUCT` | 22 | `medium-z500-t850` |
| `MAP_PROJECTION` | 23 | `opencharts_europe` |
| `METEOGRAM_TYPE` | 27 | `classical_15d_with_climate` — genau dieses Layout meint `METEOGRAM_BOX` |
| `METEOGRAM_LOCATION` | 28–33 | Traiskirchen, 48.0 °N / 16.4 °E |
| `TIMEOUT` | 37 | 60 s pro Request (die API rendert on demand) |

### legend.py

| Konstante | Zeile | Bedeutung |
| --- | --- | --- |
| `Legend` | 16 | `NamedTuple(title, values, colors)`; **Invariante:** `len(values) == len(colors) - 1` |
| `FALLBACK_LEGEND` | 32 | Legende von `medium-z500-t850`, wie sie die API liefert: 30 Farbbänder, 29 Grenzwerte, Titel `850 hPa temperature (C)` |

## 7. API-Zugriff

Beide Produkte werden zweistufig geholt: eine Metadaten-Anfrage liefert JSON mit der URL des frisch gerenderten Bildes auf dem Streaming-Host, diese URL wird anschließend als Bild geladen (`_download_image()`, [ecmwf_api.py:48](ecmwf_api.py#L48)). Keine Authentifizierung nötig.

**Karte** — `fetch_map(timestamp)` ([ecmwf_api.py:65](ecmwf_api.py#L65)):

```
GET {API_BASE}/packages/opencharts/products/medium-z500-t850/axis/valid_time/
    ?projection=opencharts_europe&values=<YYYYMMDDHH00>
```

Der Achsen-Endpunkt erwartet Minutengenauigkeit, deshalb wird `"00"` angehängt. Die Bild-URL steht in `results[<value>].url`, der Modelllauf in `values.base_time` (Format `YYYYMMDDHHmm`), die Legende in `results[<value>].legend` (Abschnitt 7.1). Fehlt das Ergebnis, wird `LookupError` geworfen — typischerweise, weil die API für diese Gültigkeitszeit keine Karte kennt (zu weit in der Zukunft/Vergangenheit oder kein gültiger Zeitschritt).

**Meteogramm** — `fetch_meteogram(location=None)` ([ecmwf_api.py:99](ecmwf_api.py#L99)):

```
POST {API_BASE}/features/epsgrams/
{"location": {...}, "axis": {}, "epsgrams": "classical_15d_with_climate"}
```

Bild-URL in `result.url`, sonst `LookupError`. Das Meteogramm ist **nicht** an den Zeitstempel gebunden — es zeigt immer den aktuellen Lauf.

`MapChart` ([ecmwf_api.py:40](ecmwf_api.py#L40)) ist ein `NamedTuple` aus `image`, `base_time` (`str | None`) und `legend` (immer gesetzt). Auch der Dateimodus liefert dieses Tupel, damit `main()` nur einen Weg kennt.

### 7.1 Legende aus der API

`results[<value>].legend` ist eine Liste, die *jede* geplottete Größe beschreibt — für dieses Produkt die Temperaturschattierung (`data.type == "colorbar"`) und die Geopotential-Isolinien (`data.type == "double-line"`). `parse_legend()` ([legend.py:72](legend.py#L72)) nimmt den ersten `colorbar`-Eintrag:

```json
{"data": {"type": "colorbar", "title": "850 hPa temperature  (C)",
          "entries": [{"min-range": "-80", "max-range": "-70",
                       "colour": "RGBA(255,255,255,1)"}, ...]}}
```

Abbildung auf `Legend`: `colors` = eine Farbe je Eintrag (Alpha wird verworfen, die Legende sitzt auf einer opaken weißen Box), `values` = `max-range` aller Einträge **außer dem letzten**, also genau die Grenzen zwischen benachbarten Bändern. Die Grenzwerte bleiben Strings und werden unverändert gezeichnet. Der Titel wird auf einfache Leerzeichen normalisiert, weil die API doppelte liefert.

Ist die Antwort unbrauchbar (kein `colorbar`, leere `entries`, unparsbare Farbe), liefert `parse_legend()` `None` und `fetch_map()` setzt `FALLBACK_LEGEND` ein — es gibt also keinen Zustand ohne Legende. `FALLBACK_LEGEND` entspricht Stand heute exakt der API-Antwort für `medium-z500-t850`.

Die erste Farbe (`< −70 °C`) ist reines Weiß und damit auf der weißen Legendenbox unsichtbar; das ist genau so von ECMWF geliefert und in deren eigener Legende nicht anders.

## 8. Meteogramm-Komposition

`combine_with_meteogram()` ([draw_cities.py:251](draw_cities.py#L251)) schneidet `METEOGRAM_BOX` aus dem Diagrammbild (580×133 px), skaliert es mit `magic_kernel_sharp_resize()` auf die Kartenbreite (1000×229 px) und setzt es mit `METEOGRAM_GAP` Abstand über die Karte.

Magic Kernel Sharp wird statt Lanczos/Bicubic verwendet, weil die sehr kleinen Achsenbeschriftungen des Meteogramms sonst verwaschen. Die Implementierung ([upscale.py](upscale.py)) schärft bei Vergrößerung zuerst auf dem groben Quellgitter und interpoliert dann; die Filtertaps `SHARP_TAPS` ([upscale.py:21](upscale.py#L21)) summieren sich zu eins, die Helligkeit bleibt also erhalten.

**Achtung bei Änderungen:** Die Gesamthöhe ist aktuell `229 + 11 + 600 = 840` und damit ein Vielfaches von 8, was blockbasierten Bildformaten entgegenkommt. Wer `METEOGRAM_BOX` oder `CROP_SIZE` ändert, muss `METEOGRAM_GAP` nachziehen, um diese Eigenschaft zu erhalten.

## 9. Rendering-Details

- `load_font(size, bold)` ([draw_cities.py:121](draw_cities.py#L121)) probiert Arial, dann DejaVu, dann PILs Bitmap-Default. Der Default ignoriert die Größenangabe — auf Systemen ohne die beiden TrueType-Fonts sieht die Ausgabe deutlich anders aus.
- Städte: Kreis mit Radius 4 px, schwarz gefüllt mit weißer Kontur; Beschriftung schwarz, linksbündig neben dem Marker (`anchor="lm"`).
- Zeitstempel: zwei Zeilen bei y=8 und y=34, Schriftgröße 26, in `LABEL_FILL`/`LABEL_STROKE`.
- Lauf: eine Zeile 10 px über dem unteren Rand (`anchor="ls"`), Schriftgröße 16 — klein genug, dass auch der längste Monatsname nicht in die Legende läuft.
- Legende: weiße Box unten rechts, ein Farbfeld à 19 px je Band (aktuell 30 Bänder, Balken 570 px breit, Box 590×74 px), Grenzwerte mittig zwischen benachbarten Feldern (`anchor="ms"`). Breite und Position ergeben sich aus `len(legend.colors)`, die Box wächst also nach links, wenn die API mehr Bänder liefert.
- Gespeichert wird mit `lossless=True`. WebP wäre sonst verlustbehaftet und würde dünne Isolinien und die kleinen Meteogramm-Labels ausfransen; verlustfreie Formate ignorieren das Argument.

## 10. Fehlerbehandlung

| Situation | Verhalten |
| --- | --- |
| Falsche Argumentanzahl | Usage nach stderr, Exit 1 |
| Zeitstempel nicht `YYYYMMDDHH` | Meldung nach stderr, Exit 1, **kein** Request |
| `requests.RequestException` / `LookupError` beim Abruf | Meldung nach stderr, Exit 1 |
| API-Antwort ohne brauchbare Legende | stillschweigend `FALLBACK_LEGEND`, Rendering läuft weiter |
| Lokale Datei fehlt/defekt | **nicht** abgefangen — `PIL.UnidentifiedImageError` bzw. `FileNotFoundError` als Traceback |
| `map.png` nach der Annotation nicht löschbar (Editor hält Lock) | Warnung nach stderr, Rendering läuft weiter |
| Kein `msvcrt` (Nicht-Windows) | `wait_for_keypress()` liest stattdessen eine Zeile, der Tastendruck muss mit Enter bestätigt werden |

Alle Benutzermeldungen sind deutsch, der Code und die Kommentare englisch.

## 11. Erweiterungspunkte

**Stadt hinzufügen/entfernen** — Eintrag in `CITIES` ([draw_cities.py:97](draw_cities.py#L97)). Die Position ergibt sich rein aus der Projektion; Punkte außerhalb des 1000×600-Ausschnitts werden von PIL stillschweigend abgeschnitten (kein Fehler, aber auch keine Warnung). Bei dichter liegenden Städten überlappen die Labels — eine Kollisionsvermeidung existiert nicht.

**Legende anpassen** — im Download-Modus gibt es nichts anzupassen, die Werte kommen von der API. Für den Dateimodus `FALLBACK_LEGEND` ([legend.py:32](legend.py#L32)) ändern und dabei die Invariante `len(values) == len(colors) - 1` einhalten. Die Boxbreite skaliert automatisch über `sw * len(legend.colors)`; bei deutlich mehr als 45 Bändern muss `sw` in `render_legend()` verkleinert werden, sonst läuft die Box aus dem 1000 px breiten Bild.

**Anderes ECMWF-Produkt** — `MAP_PRODUCT`/`MAP_PROJECTION` in [ecmwf_api.py:22-23](ecmwf_api.py#L22-L23). Achtung: anderes Produkt bzw. andere Projektion heißt in aller Regel neue Projektionsparameter (Abschnitt 5) und neuer `CROP_SIZE`. Die Legende zieht im Download-Modus automatisch nach, `FALLBACK_LEGEND` jedoch nicht — dann ist auch sie aus der neuen API-Antwort zu übernehmen.

**Anderer Meteogramm-Standort** — `METEOGRAM_LOCATION` ([ecmwf_api.py:28](ecmwf_api.py#L28)) oder das `location`-Argument von `fetch_meteogram()`. Ein anderer `METEOGRAM_TYPE` ändert das Layout und macht `METEOGRAM_BOX` ungültig; der Ausschnitt muss dann am tatsächlich gelieferten Bild neu ausgemessen werden.

**Weitere Overlays** — neue `render_*(draw, ...)`-Funktion nach dem Muster der bestehenden anlegen und in `draw_cities()` ([draw_cities.py:211](draw_cities.py#L211)) nach den Städten aufrufen. Die Funktionen bekommen eine `ImageDraw`-Instanz und die Bildmaße, sie öffnen und speichern nichts selbst.

**Neuer Ausgabeort/Format** — `DEFAULT_OUTPUT` bzw. `output_path` in `main()`. Das Format ergibt sich aus der Dateiendung; `lossless=True` ist für verlustbehaftete Formate außer WebP wirkungslos.

## 12. Fallstricke

- Im 2-/3-Argument-Modus wird die **Eingabekarte überschrieben**. Ein zweiter Lauf auf derselben Datei zeichnet die Overlays erneut darüber.
- Der Download-Modus blockiert auf einen Tastendruck. Für nicht-interaktive Läufe (Cron, CI) ist er ungeeignet; dort erst herunterladen und dann im Dateimodus rendern, oder `pause_for_annotations()` umgehen.
- Zeitstempel werden mit `datetime.strptime()` naiv geparst; es gibt keine Zeitzonenbehandlung, alle Zeiten sind per Konvention UTC.
- `base_time` erscheint nur im Download-Modus. Bei lokalen Karten ist der Lauf nicht rekonstruierbar, die Zeile unten links fehlt dann ersatzlos.
- Im Dateimodus kann die gezeichnete Legende von der Schattierung des Bildes abweichen, sobald ECMWF die Farbskala ändert: dort gilt immer `FALLBACK_LEGEND`. Die Abweichung fällt nicht auf, sie muss durch Abgleich mit einer frischen API-Antwort gefunden werden.
- Es gibt keine Tests und kein Logging-Framework; Statusausgaben laufen über `print()`.
