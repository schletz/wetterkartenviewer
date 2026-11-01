---
name: synop
description: Wetterprognose und synoptische 10-Tage-Analyse für Orte in Europa aus ECMWF- und ICON-D2-Daten, im Chat oder als HTML-Bericht. Nur aufrufen, wenn der Nutzer den Skill synop ausdrücklich anfordert (/synop oder "mit dem Skill synop"), nie von dir aus, auch nicht bei Wetterfragen: Der Skill lädt über 1 GB Modelldaten.
---

# Synoptische Analyse aus ECMWF- und ICON-D2-Daten

Der Skill erstellt aus Modelldaten synoptische Analysen und sagt das Wetter am Boden vorher.
Dafür kombiniert er ein hoch aufgelöstes Kurzfristmodell (ICON-D2 des DWD) mit einem globalen
Mittelfristmodell (ECMWF IFS).

| Modell    | Räumliche Auflösung            | Zeitliche Auflösung und Prognosezeitraum             | Abdeckung                                                                                                         |
|-----------|--------------------------------|------------------------------------------------------|-------------------------------------------------------------------------------------------------------------------|
| ECMWF IFS | 0,1° (rund 9 km)               | 3 h bis T+144, danach 6 h bis T+240; Lauf alle 12 h  | Europa (Zuschnitt des globalen Modells)                                                                           |
| ICON-D2   | rund 2,2 km (Ikosaedergitter)  | 1 h bis T+48; Lauf alle 3 h                          | Deutschland, Österreich, Schweiz und Randgebiete (etwa 43–58° N, 4° W–20° E); Karten nur für Österreich und Umgebung |

Das Wetter am Boden – Nebel, Hochnebel, Gewitter, Wind und Temperatur in Tälern – hängt am Gelände
und an Vorgängen von wenigen Kilometern. Ein 9-km-Modell glättet die Täler weg und rechnet Schauer
und Gewitter nur als Näherung. ICON-D2 löst Täler, Gewitterzellen und Nebel direkt auf. Daraus folgt
die Arbeitsteilung:

1. **Wetter am Boden bis T+48 aus ICON-D2.** Bewölkung, Wolkenuntergrenze, Niederschlag mit Art und
   Menge, Nebel, Gewitter, Böen und T2m sind dort Prognosen, die du verwenden kannst. Einzelne
   Schauer- und Gewitterzellen sind aber Möglichkeiten im Raum, keine Ortsprognose: Sag, ob sie in
   der Gegend wahrscheinlich sind, nicht, dass sie genau den Ort treffen.
2. **Großwetterlage und alles nach T+48 aus ECMWF.** Verwende dort nur die Grundparameter der freien
   Atmosphäre: Höhe, Temperatur, Wind und Feuchte der Druckflächen (1000, 925, 850, 700, 600,
   500 hPa). Dazu gehört, was direkt daraus folgt, etwa Schichtdicke, Vertikalbewegung (ω700) und
   der Luftdruck auf Meeresniveau, der der Höhe der 1000-hPa-Fläche entspricht. Das Wetter am Boden
   leitest du daraus mit den Faustregeln unten ab.
3. **Beide Modelle in den ersten 48 h:** Stimmen sie in Lage und Zeitpunkt überein, etwa beim
   Durchzug einer Front, ist die Prognose sicherer. Weichen sie ab, nenne die Abweichung, statt zu
   mitteln. Für die Großwetterlage zählt ECMWF, für das Wetter am Ort ICON-D2, das meist auch der
   jüngere Lauf ist.

Liegt der Ort außerhalb von ICON-D2 (z. B. Rom, Skandinavien), gibt es nur ECMWF und die Regeln
von Punkt 2 gelten für alle Tage.

Die *bodennahen ECMWF-Parameter* (Bewölkung, Niederschlag und seine Art, Temperatur in 2 m) sind
nur zusätzliche Info. Keine Aussage beruht allein auf ihnen, sonst kehren genau die Fehler zurück,
die der Skill vermeiden soll. T2m mit Tmax/Tmin ist nach dem Ende von ICON-D2 der Ausgangspunkt für
die Temperaturen und wird kritisch geprüft (siehe „T2m kritisch prüfen“). Bewölkung und Niederschlag von ECMWF zeigt
nur die Karte `weather_summary`; Ortstabelle und TSV von ECMWF enthalten sie nicht.

Die Analyse beruht auf je einem Lauf pro Modell (Open Data). Daraus folgt zweierlei:
- Alles, was im Text steht, muss sich aus diesen Daten ableiten lassen.
- Die Unsicherheit ab etwa Tag 5 ist aus einem einzelnen Lauf nicht ablesbar.

Zieh deshalb keine anderen Quellen heran (Wetterdienste, Meteogramme, Websuche). Der Nutzer will
sehen, was die Modelle hergeben, und eine Mischung verschleiert, woher eine Aussage stammt.

## Chat oder Bericht

Entscheide anhand der Anfrage, was der Nutzer braucht. Ein Laie will wissen, wie das Wetter wird;
ein ausführlicher Bericht mit Luftmassen und Diagramm wäre für ihn nur Ballast.

- **Chat** bei Fragen wie von einem Laien: „Wie wird das Wetter in Wien?“, „Wie wird das Wetter
  der kommenden Tage?“, „Kann ich am Wochenende wandern gehen?“. Gib nur den Absatz für Endkunden
  (siehe „Absatz für Endkunden“) im Chat aus, davor eine Zeile mit den beiden Läufen. Keine Datei, kein
  Diagramm. Eine gezielte Einzelfrage („Ist die Kaltluft für Ende März normal?“) beantwortest du
  direkt in wenigen Sätzen.
- **HTML-Bericht**, wenn der Nutzer eine Analyse verlangt: „Erstelle eine synoptische Analyse“,
  „Erstelle eine Analyse“, „Mach mir einen Bericht“. Dann liest du zusätzlich
  `references/html_report.md`.

Im Zweifel nimm den Chat und biete am Ende den Bericht an. Die Analyse dahinter (Schritte 1–5 und
das Deuten) ist in beiden Fällen dieselbe: Der Absatz für Endkunden ist nur so gut wie die Deutung
der einzelnen Tage, auch wenn sie nicht ausgegeben wird.

## Ablauf

Die Skripte liegen in `<skill-dir>/scripts/`, ihre gemeinsamen Klassen in `scripts/lib/`. Sie
brauchen Python 3 mit `eccodes`, `numpy`, `scipy` und `Pillow`, der Klimavergleich zusätzlich
`pandas`. Außer `fetch_data.py`, das den Datenordner aus dem Blob Storage lädt, lesen und zeichnen
sie nur: Ableiten und Rendern erledigt das Programm, das den Datenordner erzeugt.

Vor Änderungen in `scripts/` zuerst `scripts/REFERENCE.md` lesen: Sie beschreibt Klassen,
Datenflüsse und Erweiterungspunkte, sodass du nicht den ganzen Code lesen musst.

Als Arbeitsverzeichnis für Tabellen, markierte Karten und Bericht nimm `synop` im Scratchpad bzw.
im Temp-Verzeichnis. Den Datenordner selbst veränderst du nicht.

### 1. Ort oder Region

- **Ort:** Bestimme Breite und Länge auf zwei Dezimalstellen und die Seehöhe aus deinem Wissen. Die
  Seehöhe brauchst du, um T2m auf die echte Höhe des Ortes zu beziehen. Ist der Name mehrdeutig
  (Frankfurt, Neustadt), frag nach.
- **Region** (z. B. „Prognose für Österreich“): Bestimme eine Bounding Box (Süd, Nord, West, Ost)
  und zwei bis vier typische Punkte darin, etwa Flachland, Becken, Alpental und Gebirge. Für die
  Region markierst du die Box, die Zahlentabellen nimmst du für die Punkte.

Das Gebiet muss in Europa liegen (Atlantik bis Westrussland, Nordafrika bis Nordkap).

### 2. Datenordner

Die Daten liefert ein Datenordner (`<data>`), den ein anderes Programm erzeugt und aktualisiert.
Woher er kommt:

- **Der Nutzer nennt einen Ordner:** Nimm genau diesen und lade nichts. Er will die Prognose aus
  genau diesen Daten, etwa aus einem älteren Lauf.
- **Sonst aus dem Blob Storage:** Das Programm spiegelt seinen Ordner in einen öffentlich lesbaren
  Container. Die URL steht in `<skill-dir>/download_url.txt`. Gibt der Nutzer eine URL an, schreib
  sie als einzige Zeile in diese Datei (auch über eine bestehende), damit spätere Aufrufe sie
  kennen. Fehlt die Datei und nennt er keine, frag ihn danach. Die URL steht nicht hier, weil der
  Skill öffentlich ist. Dann bring den Cache auf den Stand des Containers:

  ```
  python <skill-dir>/scripts/fetch_data.py <url aus download_url.txt>
  ```

  Das Skript listet den Container, lädt nur neue oder geänderte Dateien nach `<skill-dir>/.cache`
  und löscht dort ältere Läufe. Ist der Lauf schon im Cache, ist es in wenigen Sekunden fertig.
  Der erste Abruf dauert länger, weil er rund 3 GB samt Klimatologie lädt. Die letzte Zeile der
  Ausgabe ist `<data>`. Bricht es ab, weil im Container gerade ein neuer Lauf hochgeladen wird,
  warte ein paar Minuten und ruf es erneut auf.

Der Ordner enthält je einen Lauf von ECMWF IFS und ICON-D2:

- `ecmwf_<YYYYMMDDHH>.grb2`: die ECMWF-Vorhersage bis +240 h samt allen abgeleiteten Größen (Werte
  auf 2000–3000 m, Nullgradgrenze, Schneefallgrenze, Inversion, Niederschlagssignal, Tagesextreme)
- `opencharts_europe/` und `opencharts_central_europe/`: die ECMWF-Karten beider Fenster mit
  Kontaktabzügen
- `icon-d2_<YYYYMMDDHH>.grb2`: der ICON-D2-Lauf bis +48 h, nur Rohfelder des Modells
- `icon-d2/`: die ICON-D2-Karten für Österreich und Umgebung mit Kontaktabzügen
- `era5_means/`: die Klimatologie für den Klimavergleich
- `charts.md`: was im Ordner liegt, welche Felder die GRIBs haben und wie man jede Karte liest

Lies aus `charts.md` zuerst „Dateien“ und „Allgemeines“, für ICON-D2 „ICON-D2-Datei“ und „Produkte
im Fenster icon-d2“, später die Abschnitte der Karten, die du ansiehst. Die Namen der GRIBs nennen
die Läufe (Basiszeit in UTC). Nenn beide dem Nutzer. Ist der ECMWF-Lauf älter als etwa 24 h oder der
ICON-D2-Lauf älter als etwa 12 h, sag dazu, dass die Daten nicht aktuell sind: Bei einem eigenen
Ordner frag, ob er ihn zuerst aktualisieren will; beim Blob Storage aktualisiert das Programm den
Container offenbar gerade nicht. Verwende für die ganze Analyse genau diese zwei Läufe.

Die Fenster der Karten:
- Mitteleuropa (ECMWF) reicht von 35,7 bis 57,4° N und von 23° W bis 37° E. Liegt der Ort außerhalb,
  etwa in Skandinavien, nimm die Karten des Europafensters: Dort gibt es alle Produkte.
- `icon-d2` reicht von 45,3 bis 49,6° N und 5,7 bis 18,2° E (Burgund bis Bratislava, Mailand bis
  Würzburg). ICON-D2 rechnet ein größeres Gebiet als dieses Fenster: Für München oder Berlin gibt
  es die ICON-Zahlentabelle, aber keine ICON-Karten.

### 3. Ort markieren

```
python <skill-dir>/scripts/mark_location.py --data <data> --out <arbeitsverzeichnis>/marked_<ort> --lat 48.21 --lng 16.37 --label Wien
python <skill-dir>/scripts/mark_location.py --data <data> --out <arbeitsverzeichnis>/marked_<region> --bbox 46.4 49.0 9.5 17.2 --label Österreich
```

Das Skript kopiert alle Karten aller Fenster samt Kontaktabzügen mit Punkt bzw. Box, das dauert
etwa 25 s. Die Karten haben Grenzen, aber keine Ortsnamen. Ohne Markierung verschätzt man leicht,
ob ein Trog oder ein Feuchteband den Ort gerade trifft. Sieh dir deshalb immer die markierten Kopien
an.

### 4. Zahlentabellen am Ort

```
python <skill-dir>/scripts/location_table.py <data>/ecmwf_<YYYYMMDDHH>.grb2 --lat 48.21 --lng 16.37 --elevation 170 --label Wien --tsv <arbeitsverzeichnis>/data_<ort>_ecmwf.tsv
python <skill-dir>/scripts/location_table.py <data>/icon-d2_<YYYYMMDDHH>.grb2 --lat 48.21 --lng 16.37 --elevation 170 --label Wien --tsv <arbeitsverzeichnis>/data_<ort>_icon.tsv
```

Das Skript erkennt das Modell an der Datei, liest die Werte direkt aus dem GRIB und gibt Markdown
aus. Es rechnet nur Einheiten um. Liegt der Ort außerhalb von ICON-D2, bricht der zweite Aufruf mit
einer Meldung ab; dann gibt es nur ECMWF.

Starte `mark_location.py` und die Tabellen **nacheinander**, auch bei mehreren Orten. Jedes Skript
verteilt sich schon auf alle Prozessorkerne; parallel bremsen sie sich gegenseitig auf ein
Vielfaches der Zeit aus.

**ECMWF** (etwa 12 KB, 20–30 s pro Ort): bilinear zwischen den Gitterpunkten. Alle abgeleiteten
Werte stehen fertig im GRIB.

- **Kopf:** Modellhöhe des Ortes, Rauigkeit des Geländes (`sdor`) und der Abstand zur echten
  Höhe. Das ist die Grundlage für die Prüfung von T2m.
- **Warnung bei 850 hPa knapp über dem Boden:** Liegt 850 hPa im Mittel weniger als 500 m über dem
  Modellboden, etwa an inneralpinen Orten wie Innsbruck, steht das im Kopf. Dort erwärmt der Boden
  die Fläche tagsüber und kühlt sie nachts. T850, ΔT850/12h und die Bergwerte knapp darüber
  schwanken dann im Tagesgang um mehrere Kelvin, ohne dass die Luftmasse wechselt. Vergleiche dort
  gleiche Tageszeiten (12z mit 12z) oder nimm einen Gitterpunkt im Vorland.
- **Freie Atmosphäre und Grenzschicht:** T850 und seine Änderung in 12 h, Schichtdicke,
  Bodendruck, Wind auf 1000 und 925 hPa, Inversion, Feuchte der Grenzschicht und auf 700 hPa,
  Vertikalbewegung ω700, Niederschlagssignal, T2m.
- **Bergwetter:** Temperatur auf 2000/2500/3000 m, Wind auf 2000 und 3000 m, Feuchte auf 2000 m,
  Nullgradgrenze, Schneefallgrenze bei Niederschlagssignal.
- **Tagesextreme:** Tmax 06–18 UTC und Tmin 18–06 UTC.

Ein Strich steht für eine Druckfläche unter dem Modellboden. Deren Werte extrapoliert das Modell
aus dem Boden, sie wären keine freie Atmosphäre.

Die Tabelle liefert die zeitliche Auflösung und die genauen Werte, damit du dafür nicht jede Karte
ansehen musst. Sie zeigt Luftmassenwechsel (|ΔT850/12h| ≥ 3–4 K), feuchte Phasen und den
Tagesgang der Ereignisse.

**ICON-D2** (etwa 6 KB, 10 s pro Ort): linear im Dreieck der drei Zellen um den Ort. Wetterschlüssel
und Wolkenuntergrenze kommen aus der nächsten Zelle, weil ein Mittel aus Codes oder aus 800 m und
„keine Wolke“ (20 km) keinen Wert ergibt, den es gibt.

- **Kopf:** Modellhöhe (meist nahe an der echten Höhe) und Abstand zur echten Höhe.
- **Wetter am Boden, stündlich:** T2m, Wind in 10 m, Böen, Bodendruck, Bewölkung,
  Wolkenuntergrenze (m über NN), Niederschlag der letzten Stunde, Wetterschlüssel `ww` mit
  Bedeutung (Nebel, Regen, Schauer, Gewitter usw.).
- **Freie Atmosphäre, alle 3 h:** Wind auf 1000 hPa, Höhe, Temperatur, Feuchte und Wind auf 850 und
  700 hPa. Mehr Druckflächen hat die Datei nicht; 925 hPa, 500 hPa und die Schichtdicke kommen von
  ECMWF.
- **Tagesextreme:** Tmax 06–18 UTC und Tmin 18–06 UTC, soweit der Lauf das Fenster abdeckt.

Zwei TSV, eines je Modell: Gitter, Zeitschritte und Parameter sind verschieden, eine gemeinsame
Tabelle hätte für die Hälfte der Zeilen leere Spalten und mischte die Herkunft der Werte. Jedes TSV
enthält pro Zeitschritt alle Parameter seiner GRIB-Datei am Ort, mit denselben Namen und Einheiten
wie dort (Listen in `charts.md`, „GRIB-Datei“ und „ICON-D2-Datei“):
- **Spalten:** `valid_utc`, `step_h`, dann der Name des Felds, auf Druckflächen mit Level
  (`t850`, `gh500`, `uf1000`), auf festen Höhen mit Level und `m` (`t2000m`, `u3000m`), sonst ohne
  (`msl`, `2t`, `thick`, `deg0l`, `inv`, `psig`, `mx2t`, `orog`; bei ICON `tcc`, `tp`, `ww`, `gust`,
  `ceiling`, `tmax_2m`, `hsurf`).
- **Einheiten:** wie im GRIB, also K, gpm, %, m/s, Pa/s, Pa, m. Bei ICON abweichend: `tcc` in %, `tp`
  in mm seit T+0 (die Stundenmenge ist die Differenz zweier Zeilen), `z850`/`z700` als Geopotential
  in m²/s² (÷ 9,81 = m).
- **Lücken:** Felder nur zu T+0 (`orog`, `z`, `sdor`, `lsm`, `hsurf`) stehen in jeder Zeile.
  Parameter, die es zu einem Zeitschritt nicht gibt (`mx2t3` nach +144 h, `mx2t` außer am Ende
  seines Tagesfensters, `ww` zu T+0), bleiben leer, ebenso `uf`, `vf`, `inv` und `rhbl` unter dem
  Modellboden. Die Felder des Modells auf Druckflächen unter dem Modellboden (`t1000`, `u925`, bei
  ICON `u1000` in Alpentälern) stehen extrapoliert da.
- **Nur im ECMWF-TSV fehlen** Bewölkung und Niederschlag (siehe oben); im ICON-TSV stehen sie.

Das ECMWF-TSV ist die Datenquelle für Diagramm und Bericht, beide TSV dienen eigenen Auswertungen
wie dem Klimavergleich.

### 5. Karten ansehen

Eine Einzelkarte kostet etwa 1100 Tokens, ein Kontaktabzug etwa 2400. Gute Analysen brauchen
meist 8–14 Kontaktabzüge und 10–30 Einzelkarten, verteilt nach der Wetterlage statt gleichmäßig:

1. **Überblick mit Kontaktabzügen** (`sheets/`):
   - Europa: `z500_t850` für die Abfolge der Großwetterlagen. Achte auch auf das, was stromauf liegt
     (Atlantik, Nordsee), denn das kommt in den nächsten Tagen an. Dazu `dt850_24h` für die Wege der
     Luftmassen.
   - Mitteleuropa: `t850_mslp`, `rh700_wind700`, `weather_summary`, `tmax`, `tmin`. Dazu
     `t850_anomaly`: Wie ungewöhnlich die Luftmasse für die Jahreszeit ist, gehört in den Überblick
     des Berichts.
   - Im Winterhalbjahr `inversion`, im Gebirge `freezing_level`.
   - ICON-D2 (`icon-d2/sheets/`, Ort im Fenster): `weather_summary`. Der Abzug zeigt 03, 09, 15 und
     21 UTC, also Gewitter am Nachmittag und Nebel in der Nacht und am Morgen. Dazu `tmax` und
     `tmin`.
2. **Die ersten zwei Tage mit ICON-D2:** Rund um Ereignisse (Front, Gewitter, Nebel, Föhn) stündliche
   Einzelkarten `icon-d2/weather_summary`; welche Stunden, zeigt die ICON-Tabelle. `t2m_wind10m`
   und `wind10m` für Kaltluftseen und Talwind, `mountain_2000` fürs Bergwetter.
3. **Ruhige, stationäre Lage** (Hoch, kaum Änderung in der Tabelle): pro Tag eine Karte
   `t850_mslp` und eine `inversion` zur Mittagszeit. Lass auch bei mehrtägigem Hoch keinen Tag aus.
   Gradient, Inversion und Feuchte der Grenzschicht entscheiden über Hochnebel und Höchstwerte und
   ändern sich auch bei gleicher Höhenlage.
4. **Umstellung oder Ereignis:** Trogdurchgang, Höhentief in weniger als etwa 1000 km,
   Frontdurchgang, |ΔT850/12h| ≥ 3, Niederschlagssignal, Föhn. Dann die passenden Produkte in 3-
   bzw. 6-h-Schritten rund um das Ereignis. Nur so lässt sich sagen, ob die Front in der Nacht oder
   am Nachmittag durchzieht.
5. **Gebirge und Bergwetter:** `mountain_2000`, `freezing_level` und `snow_line` zu den Terminen
   mit Niederschlag oder Wetterwechsel. Einmal `orography.webp` und `icon-d2/orography.webp`, um zu
   sehen, wie grob bzw. fein die beiden Modelle das Gelände um den Ort abbilden.
6. **Tage 7–10:** Kontaktabzüge und einzelne 12z-Karten reichen fast immer. Feinere Schritte
   täuschen dort eine Genauigkeit vor, die ein einzelner Lauf nicht hat.

Hör auf, weitere Karten zu laden, sobald das Bild eines Tages klar ist.

## Deuten: Faustregeln

Die Regeln geben die Richtung vor, ersetzen aber nicht den Blick auf die konkrete Lage.

- **Trogvorderseite** (Trogachse 500–1500 km westlich): Südwestströmung, Warmluftadvektion und
  Hebung. Bei RH700 über 80 % und Hebung (ω700 < 0) ist mit dichten Wolken und Niederschlag zu
  rechnen.
- **Trogrückseite:** Nordwest- bis Nordströmung, Kaltluftadvektion (T850 fällt) und Schauer. Im
  Stau der Gebirge regnet es länger, im Lee lockert es auf.
- **Rücken bzw. Hoch:** Absinken, trocken.
  - Im Sommerhalbjahr ist es sonnig und warm.
  - Von Oktober bis März führen schwacher Druckgradient und eine Inversion über feuchter
    Grenzschicht zu Nebel und Hochnebel in Becken und Niederungen. Das gilt auch bei trockener
    700-hPa-Luft, denn Hochnebel liegt unterhalb von 850 hPa.
  - In diesem Fall sagt T850 nichts über die Temperatur am Boden: oben mild, unten kalt.
- **Höhentief (Cut-off):** Es zieht langsam und ist schwer vorherzusagen. Niederschlag fällt vor
  allem auf der Ost- und Nordflanke.
  - Zieht mit dem Höhentief ein Bodentief vom Mittelmeer nach Nordosten (Vb-Zugbahn), bringt es dem
    Alpenostrand und Mitteleuropa ergiebigen Niederschlag.
  - Ob ein Bodentief mitzieht, zeigt die Bodendruckkarte. Ein reines Höhentief ohne Bodentief bringt
    meist nur Schauer oder ein schmales Niederschlagsband.
- **Blockierende Lage (Omega):** Sie hält oft viele Tage an. Das Wetter entscheidet sich daran, ob
  der Ort unter dem Rücken oder an einer Trogflanke liegt.
- **Frontdurchgang:** Er zeigt sich an mehreren Stellen gleichzeitig: Sprung in ΔT850/12h, RH700
  steigt mit Hebung, Knick in den Isobaren, Wechsel der Windrichtung.
- **Föhn:** Isobarenbündel quer über dem Alpenhauptkamm (4–8 hPa Differenz und mehr), warme Zunge in
  T850 und trockene Luft mit Absinken im Lee, Wind auf Kammhöhe quer zum Kamm. Südföhn bringt
  Inntal und Alpenvorland Wärme, Sturmböen in den Föhntälern und Auflockerung, am Alpensüdrand
  Stauniederschlag. Nordföhn ist das Spiegelbild.
- **Niederschlag:** Bis T+48 zeigt ICON-D2 Menge, Art und Zeitpunkt direkt (Karte und Tabelle,
  stündlich). Danach gibt es keine Mengen:
  - Wahrscheinlich ist er dort, wo die Tabelle bzw. `snow_line` ein Niederschlagssignal zeigt
    (gesättigte Luft auf 850/700 hPa mit Hebung).
  - Schauer und Gewitter sind möglich, wo Vertical Totals ≥ 28 K und RH700 ≥ 70 % mit einem
    Auslöser (Trog, Front) zusammenfallen.
  - Wie lange es regnet, folgt aus der Dauer von Signal und Hebung.
- **Niederschlagsart:** Nimm die Schneefallgrenze aus Tabelle oder `snow_line` und vergleiche sie
  mit der Seehöhe des Ortes.
  - Bei kräftigem Niederschlag liegt die Grenze tiefer, bei schwachem höher.
  - Zur Gegenprobe im Flachland bis etwa 300 m: T850 ≤ −4 °C oder Dicke ≤ 528 dam heißt Schnee
    wahrscheinlich. −4…−2 °C bzw. 528–536 dam heißt Schneeregen oder nasser Schnee.
- **Wind am Boden:** Richtung etwa parallel zu den Isobaren, leicht zum tiefen Druck hin abgelenkt.
  Die Stärke folgt aus dem Isobarenabstand und dem Wind auf 1000 bzw. 925 hPa der Tabelle. In
  Tälern lenkt das Gelände den Wind um. ECMWF sieht das nicht, ICON-D2 in größeren Tälern schon
  (Wind in 10 m und Böen der ICON-Tabelle, Karte `wind10m`).
- **Bergwetter:**
  - Temperatur und Wind auf 2000–3000 m stehen in der Tabelle.
  - RH ≥ 95 % auf 2000 m heißt: Gipfel in Wolken, schlechte Sicht.
  - Wind ab etwa 15 m/s auf Kammhöhe ist stürmisch und gibt Liftsperren und Windchill.
  - Die Nullgradgrenze sagt, bis wohin Schnee liegen bleibt und ob es auf der Piste regnet.
  - Bei Föhn ist es im Lee mild und stürmisch, im Luv bleibt es in Wolken.

### T2m kritisch prüfen

T2m, Tmax und Tmin von ECMWF sind Modellwerte für den Modellboden eines 0,1°-Gitters. Nimm sie als
Ausgangspunkt, nicht als Prognose, und prüf sie in dieser Reihenfolge. Für ICON-D2 gilt dieselbe
Prüfung, aber mit weniger Abstand: Sein Modellboden liegt meist nahe an der echten Höhe, und
Kaltluftseen in größeren Becken und Tälern bildet es ab.

1. **Höhe:** Der Kopf der Tabelle nennt den Abstand zwischen Modellhöhe und echter Höhe. Bei
   durchmischter Luft entspricht das etwa 0,65 K pro 100 m. Innsbruck liegt im Modell 730 m zu
   hoch, das allein macht T2m dort rund 5 K zu kalt. In einem Kaltluftsee gilt diese Korrektur
   nicht.
2. **Gelände:** Hohe `sdor` (über 200 m, schraffiert auf `orography.webp`) heißt, dass Täler und
   Gipfel kräftig vom Modellwert abweichen. In klaren Nächten bilden sich in Tälern und Becken
   Kaltluftseen, die das Modell nicht auflöst, Tmin ist dort oft deutlich tiefer. Tagsüber erwärmen
   sich Täler im Sommer stärker.
3. **Inversion und Hochnebel:** Zeigt die Tabelle eine Inversion (Inv > 0), eine feuchte
   Grenzschicht (RH BL ≥ 90 %) und schwachen Wind auf 925 hPa, ist Hochnebel möglich. Das Modell
   löst ihn oft zu früh auf oder bildet ihn gar nicht und ist dann tagsüber zu warm. Unter
   beständigem Hochnebel bleibt Tmax nahe Tmin, oft nur wenige Grad darüber.
4. **Durchmischung:** Bei Wind (enge Isobaren, Wind auf 925 hPa über etwa 5 m/s) und ohne
   Inversion ist T2m im Flachland am verlässlichsten.

Gib Höchst- und Tiefstwerte deshalb immer als Spanne von 3–5 K an, im Gebirge und bei
Inversionslagen breiter. In den ersten zwei Tagen mit ICON-D2 reichen meist 2–3 K. Sag im Text dazu, wenn die Spanne aus Höhenkorrektur oder Hochnebelrisiko
folgt. Ob der Leser dem Wert trauen kann, ist Teil der Prognose.

## Klimavergleich: Ist das ungewöhnlich?

Die Daten zeigen absolute Werte. Ob −6 °C in 850 hPa Ende März normal sind oder ein
Kaltluftvorstoß, sagt erst der Vergleich mit dem Klima. Dafür liegt in `<data>/era5_means/` eine
Klimatologie 1991–2020 aus ERA5 auf einem 0,25°-Gitter über dem Europafenster, pro Kalendertag und
Tageszeit (alle 3 h).

- **T850 als Karte:** Das Produkt `t850_anomaly` zeigt die Abweichung zu jedem Termin.
  Für „wo wird es abnormal kalt“ reicht meist sein Kontaktabzug.
- **T850 am Ort:** Das Diagramm im Bericht zeigt die Abweichung über alle Termine, der Tooltip
  nennt σ.
- **Alles andere** (T2m, Jahresgang, Vergleich von Monaten): Lies die Klimatologie mit der Klasse
  `GribAnalyze` aus `scripts/lib/`. Sie ist bewusst kein fertiges Skript. Schreib dir damit im
  Arbeitsverzeichnis genau die Auswertung, die die Frage braucht.

```python
import sys
sys.path.insert(0, r"<skill-dir>/scripts")
from lib.climate_archive import ClimateArchive
from lib.grib_analyze import GribAnalyze

archive = ClimateArchive(r"<data>/era5_means")
point = GribAnalyze(archive)
point.get_12z_means(850, "avg_t", lat=48.21, lng=16.37, month=1, day=15)   # one value at the location
point.get_daily_means(2, "avg_2t", lat=48.21, lng=16.37)                   # annual cycle at the location

region = GribAnalyze(archive, bbox=(46.4, 49.0, 9.5, 17.2))      # south, north, west, east
region.get_term_means(15, 2, "std_2t", month=1, day=15)          # every point of the region, 15 UTC
```

| Methode | Werte |
|---|---|
| `get_daily_means` | pro Kalendertag, aus Tagesmitteln |
| `get_term_means(hour, …)` | pro Kalendertag, nur diese Tageszeit (`archive.term_hours`) |
| `get_00z_means` … `get_18z_means` | Kurzform für 0, 6, 12 und 18 UTC |
| `get_monthly_means` | pro Monat, aus Tagesmitteln, ohne `day` |

Die Parameter sind `level=850` mit `avg_t` bzw. `std_t` und `level=2` mit `avg_2t` bzw. `std_2t`.

- **Zuschnitt:** `lat`/`lng` und `month`/`day` sind optional. Was du weglässt, kommt vollständig,
  ohne Ort also jeder Gitterpunkt (mit `bbox` nur die darin).
- **Ergebnis:** Jede Abfrage liefert einen DataFrame mit den Spalten
  `month, day, lat, lon, <param>`. Mittel und Streuung führst du deshalb mit `merge` zusammen.
  `avg_*` ist in °C, `std_*` in K. Für einen Punkt nimmt die Klasse den nächsten Gitterpunkt.
- **Glättung:** Die Kalendertage fassen jeweils ±5 Tage zusammen, sonst schwankten Mittel und
  Streuung zufällig um fast 1 K.
- **Vorhersage dazu:** Die Felder liefert `ForecastGrib` aus `lib.forecast_grib`
  (`grib.field("2t", step)` in K, Gitter in `grib.grid`); einen Wert am Ort `GridPointSampler`.

Zum Auswerten:
- **Gleiche Tageszeit:** Vergleiche einen Wert mit dem Klima seiner Tageszeit, also 15z mit
  `get_term_means(15, …)`. T2m hat einen Tagesgang von 5–10 K. Am Tagesmittel gemessen wäre jeder
  Nachmittagswert „zu warm“.
- **Anomalie in σ:** z = (Wert − Mittel) / Streuung. Ab |z| ≈ 1 ist ein Wert auffällig, ab 2
  ungewöhnlich.
- **Bezugszeitraum:** Das heutige Klima ist grob 0,5 K wärmer als 1991–2020. Kälte wirkt gegen
  diesen Bezug etwas schwächer, Wärme etwas stärker. Nenne den Bezugszeitraum, wenn du Anomalien angibst.
- **T2m:** Für den Vergleich gilt dieselbe Vorsicht wie oben. Die Klimatologie ist über Gebirgen so
  geglättet wie das Modellgebirge, T850 ist dort der robustere Vergleich.
- **Datenmenge:** Jedes Feld (ein Kalendertag oder Monat) wird beim ersten Zugriff dekodiert, etwa
  7 ms, danach ist es zwischengespeichert. Ein Jahresgang braucht so rund 2,5 s, und für die ganze
  Region hat er Millionen Zeilen. Schneide deshalb früh auf Tag, Monat oder Punkt zu.

## Ausgabe

Schreib in der Sprache des Nutzers. Im Chat gibst du den Absatz für Endkunden aus (siehe „Chat oder
Bericht“). Für den HTML-Bericht lies zusätzlich `references/html_report.md`: Aufbau des Texts,
Tagestexte, Diagramm und HTML. Die folgenden Regeln gelten für beides.

### Tage einteilen

Teile nach Kalendertagen in Ortszeit ein (Daten in UTC, für Mitteleuropa z. B. MEZ = UTC+1, MESZ =
UTC+2).

- **Start:** Beim 00z-Lauf ist Tag 1 der heutige Tag. Beschreib ihn ab der aktuellen Uhrzeit,
  Vergangenes interessiert nicht. Beim 12z-Lauf, der erst abends verfügbar ist, ist Tag 1 morgen.
- **Umfang:** 10 Tage. Der letzte Tag ist eventuell nur teilweise abgedeckt; vermerke das.
- **Wochentage und Feiertage:** Hol sie dir, statt sie zu rechnen:

  ```
  python <skill-dir>/scripts/calendar_days.py --start <Tag 1 als YYYY-MM-DD>
  ```

  Das Skript gibt pro Tag Datum, Wochentag (englisch) und gegebenenfalls den österreichischen
  Feiertag aus. Die österreichischen Feiertage gelten unabhängig vom Ort. Bewegliche Feiertage wie
  Christi Himmelfahrt oder Fronleichnam hängen am Ostertermin, und beim Kopfrechnen passieren dabei
  leicht Fehler.

### Absatz für Endkunden

Der Absatz richtet sich an Leser ohne meteorologisches Vorwissen. Sie wollen wissen, wie das Wetter
wird, nicht warum. Im Bericht steht er ganz oben, im Chat ist er die Antwort. Schreib ihn zuletzt,
wenn die Tage analysiert sind, als einen zusammenhängenden Absatz von etwa 6–10 Sätzen.

- **Gliederung:** nach Wetterabschnitten, nicht Tag für Tag. Eine Phase umfasst die Tage mit
  ähnlichem Wetter, benannt mit Wochentagen in Ortszeit („Am Wochenende …“, „Ab Dienstag …“).
- **Hervorhebung:** Jeder Tag ist bei seiner ersten Nennung fett (`**Dienstag**`), danach nicht
  mehr. So findet der Leser beim Überfliegen sofort den Tag, der ihn interessiert, ohne dass jede
  Wiederholung den Absatz unruhig macht. Gemeint ist der Kalendertag: Ein Wochentag der zweiten
  Woche ist ein neuer Tag und wird bei seiner ersten Nennung wieder fett.
- **Feiertage:** Ist der Tag ein Feiertag, folgt bei dieser ersten Nennung der Name in Klammern,
  nicht fett: „In der Nacht auf **Sonntag** (Allerheiligen) …“. Gerade an Feiertagen planen Leser
  Ausflüge und suchen gezielt nach diesem Tag.
- **Inhalt jeder Phase:**
  - die Wettererscheinungen: Sonne, Wolken, Nebel bzw. Hochnebel, Gewitter
  - Niederschlag mit Art, Schneefallgrenze und Zeitraum; Mengen nur in den ersten zwei Tagen und
    nur grob aus ICON-D2 („wenige Millimeter“, „ergiebig“), weil ein einzelner Lauf am Ort nicht
    genauer ist
  - Wind mit Richtung und Stärke (schwach, mäßig, lebhaft, stürmisch)
  - Höchstwerte als Spanne, z. B. „5 bis 9 Grad“
  - bei Orten im Gebirge oder auf Wunsch das Bergwetter: Temperatur und Wind auf den Bergen,
    Nullgradgrenze, Sicht
- **Sprache:** kein Fachjargon wie T850, Trog, Advektion oder dam.
- **Schluss:** ein Satz, ab wann die Aussagen unsicher werden.

### Unsicherheit

Ab Tag 5 (Tag 1 wie oben definiert) werden die Aussagen unsicherer. Formuliere entsprechend
vorsichtiger („laut diesem Lauf“, „Tendenz“) und beschränke dich in den Tagen 7–10 auf
Großwetterlage, Luftmasse und die Temperaturtendenz. Nenne keine Niederschlagsmengen und keine
exakten Temperaturen, die Daten geben sie nicht her.
