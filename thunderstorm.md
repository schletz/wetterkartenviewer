# Gewitter und Unwetter im Skill synop: Notizen für später (im Sommer, wenn Karten zur Verfügung stehen)

Kontextdokument für einen Agenten, der den Skill `synop` und das Kartenangebot um Gewitter- und Unwetterparameter
erweitern soll. Stand: 29.10.2026. Umgesetzt ist davon nur die Karte `vt_rh700`. Der Rest wurde
zurückgestellt, weil Ende Oktober keine Gewitterlage vorlag, an der sich die Karten prüfen ließen.
Greif das Thema auf, sobald ein Lauf zwischen Mai und September eine Gewitterlage über
Mitteleuropa zeigt.

Das Dokument berücksichtigt nur ECMWF Daten, für Zeiträume bis t+48h wird die Kurzfristprognose ICON-D2 mit hoher Auflösung verwendet.


## Grundsatz des Nutzers

Die Prognose soll nur auf Parametern der **freien Atmosphäre** beruhen (Druckflächen). Bodennahe
Größen des Globalmodells sind gerade dort schwach, wo es darauf ankommt. Ausnahme ist T2m, und
auch T2m soll der Agent kritisch hinterfragen. Daraus folgt für Gewitter:

- **Bevorzugt:** Indizes, die sich aus `t`, `r`, `gh`, `u`, `v`, `w` auf Druckflächen
  berechnen lassen. Das Modell liefert sie nicht fertig, sie müssen in den Skripten berechnet
  werden.
- **Mit Vorbehalt:** `mucape`, die CAPE des labilsten Luftpakets (most unstable). Ist in Open Data
  verfügbar (`sfc`, jeder Step) und kein Bodenwetterparameter, sondern ein Modellindex. Er hängt
  aber an der Feuchte und Temperatur der Grenzschicht im Modell. Mit dem Nutzer klären, ob er
  zulässig ist.
- **Ausgeschlossen:** `cp` und `tp` (konvektiver und Gesamtniederschlag), `10fg` (Böen) und
  `ptype`. Das wären die bodennahen Parameter, die bei 0.1° Auflösung aber sehr kritisch zu hinterfragen sind.

## Was es schon gibt

- Karte `vt_rh700` (Mitteleuropa): Vertical Totals VT = T850 − T500 mit RH700-Linien bei 70 und
  90 %. Ab etwa 28 K sind Schauer und Gewitter möglich, wenn Feuchte vorhanden ist. Bisher nur an
  Herbstfällen gesehen (Adria, Süditalien 28–30 K), noch nicht an einer echten Gewitterlage.
- Im GRIB vorhanden: `t` und `gh` auf 500/700/850/925/1000 hPa, `r`/`u`/`v` auf
  700/850/925/1000 hPa, `w` auf 700 hPa.

## Kandidaten

| Index | Formel / Quelle | Schwellen (Faustwerte) | Fehlt im Download |
|---|---|---|---|
| K-Index | (T850 − T500) + Td850 − (T700 − Td700) | > 30 Gewitter wahrscheinlich, > 35 verbreitet | nichts (Td aus `t` und `r`) |
| Total Totals | VT + (Td850 − T500) | > 50 Gewitter, > 55 kräftig | nichts |
| Showalter-Index | T500 − T(Paket von 850 hPa pseudoadiabatisch auf 500 hPa) | < 0 labil, < −3 kräftig | nichts |
| Scherung 0–6 km | Betrag (V500 − V1000 bzw. V925) | > 15 m/s organisierte Zellen, > 20 m/s Superzellen möglich | `u`/`v` 500 hPa |
| Scherung 0–3 km | Betrag (V700 − V1000 bzw. V925) | > 10 m/s | nichts |
| Hebung | ω700 (schon da), ggf. ω500/850 | negativ = Hebung | `w` 500/850 optional |
| MUCAPE | `mucape` | > 500 J/kg Gewitter möglich, > 1500 kräftig | `mucape` (sfc) |

Für den Taupunkt aus T und RH reicht die Magnus-Formel. Für den Showalter-Index braucht es eine
kleine Pseudoadiabaten-Routine (iterativ auf 500 hPa heben). Beides gehört in ein eigenes Modul
neben `diagnostics.py`.

## Vorschlag für die Karten

- **`convection`** (Mitteleuropa): K-Index oder Showalter-Index als Farbe, Scherung 0–6 km als
  Linien (15/20 m/s), Hebung ω700 als Schraffur. Damit sieht man Labilität, Organisationsgrad und
  Auslöser zusammen.
- Die Zahlentabelle `location_table.py` bekommt dazu Spalten für K-Index, Showalter-Index und
  Scherung. Für den Tagesgang (Maximum am Nachmittag) die Werte um 12 und 15 UTC ansehen.

## Prüfen, bevor es in den Skill kommt

1. Einen Sommerlauf mit Gewitterlage laden (z. B. Kaltfront mit schwülwarmer Vorderseite).
2. Die Karten ansehen und prüfen, ob Lage und Zeitpunkt der labilen Zone zur synoptischen Situation
   passen (Trogvorderseite, Konvergenz, Höhentief).
3. Schwellen gegen das Klima prüfen: Die Faustwerte stammen aus den USA bzw. aus Mitteleuropa und
   streuen. Bei Bedarf die CFSR-Klimatologie in `references/` um K-Index oder VT erweitern
   (`d:\CFSR\build_cfsr_grib.py`).
4. Download-Volumen: `u`/`v` 500 hPa kosten etwa 2 × 100 MB roh, `mucape` etwa 100 MB.
