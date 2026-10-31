# Datenordner: Karten und GRIB

Diesen Ordner erzeugt der Wetterkartenviewer (`scripts/update_maps.py`) für einen Lauf des
ECMWF-Modells IFS und einen Lauf des DWD-Modells ICON-D2. Er enthält die Vorhersagedateien (IFS mit
allen abgeleiteten Größen), die Karten aller Fenster und die Klimatologie. Die Datei hier beschreibt, was drinsteht und wie man es
liest. Lies nur die Abschnitte, die du gerade brauchst.

## Inhalt

- [Dateien](#dateien) und [GRIB-Datei](#grib-datei): was im Ordner liegt, welche Felder es gibt
- [Allgemeines](#allgemeines): Fenster, Legende, Zahlen, Masken, Kontaktabzüge
- Großwetterlage (Europa): [z500_t850](#z500_t850), [z700_t700](#z700_t700), [z850_rh700](#z850_rh700),
  [thickness_mslp](#thickness_mslp), [dt850_24h](#dt850_24h)
- Mitteleuropa: [t850_mslp](#t850_mslp), [t850_anomaly](#t850_anomaly), [rh700_wind700](#rh700_wind700),
  [vt_rh700](#vt_rh700), [inversion](#inversion), [t2m_wind1000](#t2m_wind1000), [wind10m](#wind10m),
  [tmax, tmin](#tmax-tmin), [weather_summary](#weather_summary)
- Bergwetter (Mitteleuropa): [mountain_2000](#mountain_2000), [freezing_level](#freezing_level),
  [snow_line](#snow_line)
- Statisch: [orography](#orography)
- ICON-D2 (Österreich, stündlich bis +48 h): [ICON-D2-Datei](#icon-d2-datei),
  [Produkte im Fenster icon-d2](#produkte-im-fenster-icon-d2), [icon-d2/weather_summary](#icon-d2weather_summary)

## Dateien

| Pfad | Inhalt |
|---|---|
| `ecmwf_<YYYYMMDDHH>.grb2` | Vorhersage eines Laufs mit abgeleiteten Feldern ([GRIB-Datei](#grib-datei)) |
| `opencharts_europe/` | alle Produkte im Europafenster |
| `opencharts_central_europe/` | die Produkte für Mitteleuropa (Liste unter [Allgemeines](#allgemeines)) |
| `icon-d2_<YYYYMMDDHH>.grb2` | ICON-D2-Lauf auf dem Modellgitter ([ICON-D2-Datei](#icon-d2-datei)) |
| `icon-d2/` | die ICON-D2-Produkte für Österreich und Umgebung |
| `<fenster>/<produkt>/<YYYYMMDDHH>.webp` | Karte zur Gültigkeitszeit in UTC (Tmax/Tmin: `<YYYYMMDD>.webp`) |
| `<fenster>/sheets/<produkt>.webp` | Kontaktabzug: 12-UTC-Karte jedes Tages (ICON-D2: 03, 09, 15, 21 UTC) |
| `<fenster>/orography.webp` | Modellorografie, statisch |
| `<fenster>/geometry.json` | Modell, Lauf, Projektion und Kachelpositionen der Kontaktabzüge, zum Markieren eines Orts |
| `era5_means/*.grb2` | Klimatologie 1991–2020: `HHz` je Tageszeit, `daily`, `monthly` |

Der Ordner hält genau einen Lauf je Modell. Ein neuer Lauf ersetzt GRIB und Karten seines Modells.
ICON-D2 rechnet alle 3 h, IFS alle 12 h; die Läufe der beiden Modelle sind also meist verschieden.

## GRIB-Datei

Ein Lauf des IFS mit 0,1° (Open Data), zugeschnitten auf 11–76° N und 71° W–77° E. Zeitschritte
bis +144 h alle 3 h, dann bis +240 h alle 6 h. Die abgeleiteten Felder rechnet der Viewer mit
demselben Code wie die Karten. Karte und Zahl am Ort passen deshalb zusammen.

**Felder des Modells**

| Name | Ebenen | Einheit | Bedeutung |
|---|---|---|---|
| `t`, `gh`, `r` | 1000, 925, 850, 700, 600, 500 hPa | K, gpm, % | Temperatur, Geopotential, relative Feuchte |
| `u`, `v` | 1000, 925, 850, 700 hPa | m/s | Wind |
| `w` | 700 hPa | Pa/s | Vertikalbewegung ω, negativ heißt Hebung |
| `thick` | 1000–500 hPa | gpm | Schichtdicke |
| `msl`, `2t` | Boden | Pa, K | Luftdruck auf Meeresniveau, Temperatur in 2 m |
| `10u`, `10v` | 10 m | m/s | Wind in 10 m über dem Modellboden (nur `wind10m`) |
| `mx2t3`, `mn2t3`, `mx2t6`, `mn2t6` | 2 m | K | Extreme der letzten 3 h (bis +144 h) bzw. 6 h |
| `z`, `sdor`, `lsm` | Boden, nur T+0 | m²/s², m, 0–1 | Orografie als Geopotential, ihre Rauigkeit, Landanteil |
| `tcc`, `tp`, `ptype` | Boden | 0–1, m, Code | Bewölkung, Niederschlag seit T+0, Niederschlagsart (nur `weather_summary`) |

**Abgeleitete Felder**

| Name | Ebenen | Einheit | Bedeutung |
|---|---|---|---|
| `t`, `r`, `u`, `v` | 2000, 2500, 3000 m über NN | K, %, m/s | linear zwischen den beiden Druckflächen um die Höhe |
| `deg0l` | — | m | Nullgradgrenze. Gesucht wird von oben, über einem Kaltluftsee zählt also die Obergrenze der warmen Schicht. Ist die ganze Säule gefroren, steht dort die Höhe des Modellbodens. |
| `snowl` | — | m | Schneefallgrenze = Nullgradgrenze − 350 m, mindestens der Modellboden |
| `inv` | — | K | stärkste Temperaturzunahme über 1000–925 oder 925–850 hPa. Über 0 heißt Inversion. |
| `rhbl` | — | % | höchste Feuchte auf 925 oder 1000 hPa, also die Feuchte der Grenzschicht |
| `psig` | — | 0/1 | Niederschlagssignal: RH auf 850 oder 700 hPa ≥ 90 % und Hebung auf 700 hPa |
| `uf`, `vf` | 1000, 925 hPa | m/s | Wind dieser Fläche, nur wo sie über dem Modellboden liegt |
| `orog` | nur T+0 | m | Höhe des Modellbodens |
| `mx2t`, `mn2t` | 2 m | K | Tmax 06–18 UTC und Tmin 18 UTC des Vortags bis 06 UTC. Der Endschritt fällt auf den Tag selbst. |

- **Fehlende Werte:** Wo `inv`, `rhbl`, `uf` und `vf` einen fehlenden Wert haben, liegt die
  Fläche unter dem Modellboden. Dort extrapoliert das Modell die Druckflächen aus dem Boden, die
  Werte wären keine freie Atmosphäre.
- **Lokale Parameter:** `inv`, `rhbl`, `psig`, `snowl`, `uf` und `vf` haben keinen WMO-Parameter.
  Sie stehen in Disziplin 0, Kategorie 192 unter `parameterNumber` 0 bis 5 in dieser Reihenfolge.
  ecCodes nennt sie `unknown`, der Leser des Skills benennt sie selbst.
- **Höhen:** Werte auf 2000/2500/3000 m haben den Ebenentyp `heightAboveSea`.

## Allgemeines

**Fenster.** Die beiden IFS-Fenster haben dieselbe polarstereografische Projektion wie ECMWF open
charts, `icon-d2` eine Lambert-Kegelprojektion (Standardparallelen 46° und 49° N, Zentralmeridian
13°20′ E wie die österreichische Lambert-Projektion). Alle haben eine Kartenfläche von 1200×600 px,
darunter liegt ein Legendenstreifen von 90 px. `geometry.json` gibt die Formel mit `cone` und `lon0`;
bei den IFS-Fenstern ist `cone` 1 und `lon0` 0.

| Fenster | Bereich | km pro Pixel | Standardprodukte |
|---|---|---|---|
| `opencharts_europe` | Atlantik bis Westrussland, Nordafrika bis Nordkap | 7,6 (35° N) bis 9,4 (70° N) | alle Produkte |
| `opencharts_central_europe` | 35,7–57,4° N, 23° W–37° E (Irland bis Rumänien, Dänemark bis Sizilien) | etwa 3,2 | alle außer `z500_t850`, `z700_t700`, `z850_rh700`, `thickness_mslp`, `dt850_24h` |
| `icon-d2` | 45,3–49,6° N, 5,7–18,2° E (Burgund bis Bratislava, Mailand bis Würzburg) | 0,75 | `t2m_wind1000`, `wind10m`, `mountain_2000`, `weather_summary`, `tmax`, `tmin`, `orography` (ICON-D2) |

Europa zeigt, was stromauf liegt und in den nächsten Tagen ankommt. Mitteleuropa zeigt Fronten
etwa zwei Tage im Voraus und die Grenzschicht im Detail. Für einen Ort nördlich von 57° N oder
sonst außerhalb Mitteleuropas nimm die Produkte des Europafensters.

**Legendenstreifen.**
- Links oben steht die Gültigkeitszeit in UTC mit Step und Lauf, rechts der Titel.
- Darunter folgt die Farbskala mit beschrifteten Grenzen.
- Rechts davon sind die Linien, Schraffuren und Masken der Karte erklärt.

Eine Karte lässt sich damit ohne weitere Datei lesen.

**Zahlen.** Auf Mitteleuropa-Karten stehen Werte über Land in einem Raster von etwa 250 km. Eine
Zahl ist exakt, ein Farbband deckt 4 K oder 300 m ab. Für den Ort selbst nimm die Werte aus
`location_table.py`.

**L/H** markiert Tief- und Hochzentren mit Kernwert, auf der Bodendruckkarte und in 500 bzw. 700 hPa.

**Grau** heißt: Der Modellboden liegt über der Fläche oder Höhe dieser Karte, der Wert ist dort
extrapoliert oder gibt es nicht. Die Schwelle steht in der Legende.

**Kontaktabzüge** (`sheets/<produkt>.webp`) zeigen die 12-UTC-Karte jedes Tages (Tmax/Tmin: jeden
Tag) als Kacheln in halber Größe.
- **Lesbar:** Muster, Verlagerung von Trögen und Rücken, Trends.
- **Nicht lesbar:** Beschriftungen und Linienwerte.
- **Kosten:** Ein Abzug kostet etwa 2400 Tokens, eine Einzelkarte etwa 1100.

**Markierte Kopien.** Sieh dir immer die Kopien aus `mark_location.py` an, nicht die Originale. Die
Karten haben Grenzen, aber keine Ortsnamen, und ohne Markierung verschätzt man leicht, ob ein
Feuchteband oder eine Warmluftzunge den Ort trifft.

**Modellauflösung.** Das Gitter hat 0,1° (etwa 9 km). Effektiv aufgelöst sind Strukturen von
einigen 10 km. Täler, die schmaler sind, gibt es im Modell nicht, die Gipfel sind abgeflacht
(siehe [orography](#orography)).

## z500_t850

Europa. Schwarze Isohypsen 500 hPa alle 4 dam, fett 528/552/576. Farben: T850 in 4-K-Stufen
(etwa 1500 m), braune Isothermen alle 4 K.

- Strömung parallel zu den Isohypsen, tiefe Werte links (Nordhalbkugel). Enge Linien heißen
  Höhenwind bzw. Jet.
- **Trog:** Ausbuchtung der Isohypsen nach Süden.
- **Rücken:** Ausbuchtung nach Norden.
- **Höhentief (Cut-off):** abgeschlossene Isohypsen abseits der Westströmung, mit L markiert.
- **Omega-Lage:** Rücken zwischen zwei Trögen.
- **Advektion:** Wo die Isohypsen die Isothermen schneiden, findet Advektion statt.
- Dafür ist der Kontaktabzug die erste Karte jeder Analyse.

## z700_t700

Europa, nach ECMWF medium-t-z auf 700 hPa. Schwarze Isohypsen 700 hPa alle 5 dam, fett
270/290/310, L/H mit Kernwert. Farben: T700 in 4-K-Stufen (etwa 3000 m), braune Isothermen alle 4 K.

- **Lenkung:** 700 hPa ist die Lenkungsebene für Fronten und Niederschlagsgebiete. Sie ziehen etwa
  parallel zu den Isohypsen.
- **Advektion:** Wo die Isohypsen die Isothermen schneiden, findet Advektion statt, hier in der
  Schicht der Frontbewölkung und damit näher am Wetter als in 500 hPa.
- **Bergwetter:** T700 entspricht etwa der Temperatur auf 3000 m, also dem Gipfelniveau der
  Hochalpen.

## z850_rh700

Europa. Schwarze Isohypsen 850 hPa alle 4 dam, fett alle 12 dam (140/152/164), L/H mit Kernwert. Farben: RH auf
700 hPa wie bei [rh700_wind700](#rh700_wind700), grün 65–80 %, türkis 80–95 %, blau > 95 %, darunter
Land beige und Meer weiß. Grau gestrichelt: Modellboden 1300 m, innerhalb davon ist Z850
extrapoliert.

- **Fronten im Großen:** Die Feuchtebänder zeigen die Frontbewölkung über ganz Europa, die
  Isohypsen die Strömung knapp über der Grenzschicht, die sie verlagert. So sieht man, welches Band
  stromauf liegt und wann es ankommt; den Zeitpunkt am Ort liefern die Mitteleuropa-Karten.
- **Tiefs:** Ein Feuchtekomma um ein Tief in 850 hPa zeigt ein aktives System mit Warmfront und
  Kaltfront. Ein Tief in 850 hPa ohne Feuchte bringt meist nur Wind.
- Die Isohypsen verlaufen ähnlich wie die Isobaren am Boden: 4 dam entsprechen etwa 5 hPa.

## thickness_mslp

Europa. Isobaren alle 5 hPa, L/H mit Kerndruck. Farben: Schichtdicke 1000–500 hPa in 4-dam-Stufen,
also die Mitteltemperatur der unteren 5,5 km.

- Lage und Zugbahn der Bodentiefs und -hochs, Fronten als Knicke in den Isobaren.
- Die Dicke ist als Luftmassenmaß weitgehend redundant zu T850. Liegt sie deutlich tiefer, als T850
  erwarten lässt, ist die Säule oben kalt (Höhentief, labil).
- Für die Niederschlagsart siehe [snow_line](#snow_line) und die Faustregeln in SKILL.md.

## dt850_24h

Europa, ab T+24. Farben: Änderung von T850 gegenüber 24 h vorher. Blau heißt Abkühlung, Rot
Erwärmung, Weiß ±2 K. Schwarze Isohypsen 500 hPa zur Orientierung.

- Kalt- und Warmluftvorstöße und ihre Richtung auf einen Blick; im Kontaktabzug der Weg einer
  Luftmasse über die Tage.
- Die Änderung enthält neben der Advektion auch Absinken (Erwärmung im Hoch) und Strahlung. Der
  Tagesgang fällt durch den 24-h-Abstand heraus.
- Über Gebirgen, wo der Modellboden nahe 850 hPa liegt, wirkt die Bodenerwärmung mit. Dort ist die
  Änderung keine reine Advektion.

## t850_mslp

Mitteleuropa. Isobaren alle 2 hPa, L/H. Farben und Zahlen: T850. Grau gestrichelt: Modellboden
1300 m. Innerhalb dieser Linie liegt 850 hPa im Boden, T850 ist dort extrapoliert.

- **Föhn:** Zwei Merkmale zusammen. Erstens ein Bündel von Isobaren quer über dem Alpenhauptkamm
  (Druckdifferenz Luv–Lee 4–8 hPa und mehr). Zweitens eine warme Zunge in T850 auf der Leeseite.
  Südföhn heißt Lee im Norden (Inntal, Alpenvorland), Nordföhn heißt Lee im Süden (Tessin,
  Lombardei, Südtirol). Bestätigung liefert [rh700_wind700](#rh700_wind700): Pfeile quer zum Kamm,
  trockene Luft und Absinken im Lee.
- **Bodenwind:** etwa parallel zu den Isobaren, leicht zum tiefen Druck hin abgelenkt. Enge
  Isobaren heißen Wind. Bei schwachem Gradienten (weniger als eine Isobare auf 300 km) ist die
  Luft kaum durchmischt, das ist die Voraussetzung für Inversion und Hochnebel.

## t850_anomaly

Mitteleuropa. Farben: Abweichung von T850 vom Mittel der Klimatologie (1991–2020) desselben
Kalendertags und derselben Tageszeit, in Standardabweichungen σ. Weiß ±1 σ, dann je eine Stufe pro
σ, rot wärmer, blau kälter. Zahlen: dieselbe Abweichung in K. Schwarze Isohypsen 500 hPa. Grau:
Modellboden über 1300 m.

- **Lesart:** Ab |σ| ≈ 1 ist die Luftmasse für die Jahreszeit auffällig, ab 2 ungewöhnlich, ab 3
  selten. Die Zahlen sagen, wie viel das in Grad ist. Im Winter ist σ größer als im Sommer, dieselben
  5 K sind im Juli ungewöhnlicher als im Jänner.
- **Ursache:** Die Isohypsen zeigen, welche Strömung die Anomalie bringt, etwa Kaltluft im Kern
  eines Höhentiefs oder Warmluft vor einem Trog. Der Kontaktabzug zeigt, wie lange sie bleibt.
- **Bezugszeitraum:** Das heutige Klima ist grob 0,5 K wärmer als 1991–2020. Leichte Wärme ist
  deshalb fast schon normal, leichte Kälte heute etwas ungewöhnlicher, als die Karte sagt.
- **Fallstricke:** Wo 850 hPa nahe am Modellboden liegt (Alpenvorland, Mittelgebirge), wirkt der
  Tagesgang des Bodens mit. Ein Hochnebeltag mit milder Höhenluft erscheint rot, obwohl es am Boden
  kalt ist. Die Karte bewertet die Luftmasse, nicht das Wetter am Boden.

## rh700_wind700

Mitteleuropa. Farben: RH auf 700 hPa (etwa 3 km), grün 65–80 %, türkis 80–95 %, blau > 95 %.
Darunter ist Land beige und Meer weiß, also trockener. Pfeile: Wind auf 700 hPa, Länge proportional
zur Geschwindigkeit. Rote Linien: Hebung ω700 von −0,2 und −0,6 Pa/s. Lila gestrichelt: Absinken
+0,2 Pa/s.

- Zusammenhängende Bänder hoher Feuchte mit Hebung markieren Fronten und Aufgleitbereiche: dichte
  Bewölkung, Niederschlag wahrscheinlich.
- Absinken trocknet die Luft aus und verstärkt Inversionen. In Hochdrucklagen ist es oft
  großflächig zu sehen.
- Die Pfeile zeigen die Anströmung in Kammhöhe, wichtig für Stau und Föhn. Stau heißt feucht mit
  Hebung im Luv, Föhn heißt trocken mit Absinken im Lee.
- Im Kontaktabzug sieht man, wann ein Feuchteband den Ort erreicht. Den genauen Zeitpunkt liefern
  die 3-h-Karten bzw. die Spalten RH700 und ω700 der Ortstabelle.

## vt_rh700

Mitteleuropa. Farben: Vertical Totals T850 − T500. Grüne Linien: RH700 70 und 90 %. Grau: Modellboden
über 1300 m.

- Ab etwa 28 K sind Schauer und Gewitter möglich, ab 32 K kräftige, wenn Feuchte vorhanden ist
  (RH700 ≥ 70 %) und ein Auslöser (Trog, Front, Hebung).
- Hohe Werte über trockener Luft (Wüste) bringen nichts.

## inversion

Mitteleuropa. Farben: stärkste Temperaturzunahme über die Schicht 1000–925 oder 925–850 hPa (je etwa
650 m). Über 0 heißt Inversion. Durchmischte Luft gibt etwa −6 K, die Standardatmosphäre −4 K.
Schraffiert: RH auf 925 oder 1000 hPa ≥ 90 %, also eine feuchte Grenzschicht. Blaue Linie: Wind auf
925 hPa 5 m/s, schwächer heißt kaum Durchmischung. Grau: Modellboden über 700 m.

- Die Karte verwendet nur Druckflächen, kein T2m. Eine Fläche zählt nur, wo sie über dem
  Modellboden liegt. Darunter extrapoliert ECMWF aus der Bodentemperatur, und damit würde der
  Bodenfehler, den diese Karte vermeiden soll, zurückkommen.
- **Hochnebel** wird wahrscheinlich, wenn Inversion (orange), Schraffur und schwacher Wind
  zusammenfallen, im Winterhalbjahr und über mehrere Termine, auch um 12 UTC. Nebel und Hochnebel
  selbst sieht man auf keiner Karte. Das Modell bildet sie schlecht ab, die Karte zeigt die
  Bedingungen.
- Abgehobene Absinkinversionen unter Hochs erscheinen ebenfalls, auch über dem Meer.
- Eine Inversion über trockener Luft heißt sonnig und in Becken kalt. Eine Inversion über feuchter
  Grenzschicht heißt grau und trüb.

## t2m_wind1000

Mitteleuropa. Farben und Zahlen: T2m (Modellwert für die Modellhöhe), blaue Linie 0 °C. Pfeile: Wind
auf 1000 hPa als Näherung für den Bodenwind. Keine Pfeile über 500 m Modellhöhe, dort liegt 1000 hPa
im Boden.

- T2m ist ein bodennaher Parameter mit allen Schwächen des groben Modells. Wie du ihn prüfst,
  steht in SKILL.md unter „T2m kritisch prüfen“.

## wind10m

Mitteleuropa. Farben: Windgeschwindigkeit in 10 m in km/h, die Stufen sind die Grenzen der
Beaufortskala (bis 6 km/h Stärke 0–1, ab 118 km/h Orkan). Graue Linien mit Pfeilen: Stromlinien des
10-m-Winds. Schwarze Linien: Isobaren alle 4 hPa mit Hoch und Tief.

- Der 10-m-Wind ist der Bodenwind des Modells: anders als 1000 hPa liegt er überall gleich hoch über
  dem Modellboden, auch im Gebirge, und enthält die Bodenreibung.
- Durch die Reibung kreuzen die Stromlinien die Isobaren schräg zum tiefen Druck hin. Laufen sie
  zusammen, ist dort Konvergenz (Front, Konvergenzlinie), laufen sie auseinander, Divergenz.
- Der Abstand der Stromlinien sagt nichts über die Geschwindigkeit, die zeigen nur die Farben.
- Täler und Kanalisierung schmaler als das 9-km-Gitter fehlen, ebenso Böen. Grün und mehr an
  Küsten und Pässen (Bora, Mistral, Föhn) ist dagegen ein deutliches Signal.

## tmax, tmin

Mitteleuropa, eine Karte pro Tag (UTC). Tmax ist das Maximum über 06–18 UTC, Tmin das Minimum über
18 UTC des Vortags bis 06 UTC. Farben und Zahlen in °C, blaue Linie 0 °C.

- Der Kontaktabzug zeigt den Temperaturtrend über 10 Tage.
- Es sind dieselben Modellwerte wie T2m mit denselben Schwächen.
- Tag 1 fehlt beim 00z-Lauf für Tmin, weil die Nacht vor dem Lauf liegt.

## mountain_2000

Mitteleuropa. Farben und Zahlen: Temperatur auf 2000 m, linear zwischen den Druckflächen
interpoliert. Pfeile: Wind auf 2000 m. Schraffiert: RH ≥ 95 %, die Gipfel um 2000 m stecken in
Wolken. Grau: Modellboden über 2000 m.

- Bergwetter für Schigebiete, Hütten und Wanderer: Frost, Wind auf Kammhöhe, Sicht.
- Werte für 2500 und 3000 m und den Wind in 3000 m liefert die Ortstabelle.

## freezing_level

Mitteleuropa. Farben in 300-m-Stufen, Zahlen auf 100 m gerundet. Die Suche läuft von oben nach unten.
Bei einer warmen Schicht über einem Kaltluftsee ergibt das die Obergrenze der warmen Schicht. Ist
die ganze Säule gefroren, steht dort die Höhe des Modellbodens.

- Wichtig für Schifahrer (Schnee bis wohin, Firn, Regen auf der Piste) und für die
  Niederschlagsart.
- Der Kontaktabzug zeigt den Verlauf über 10 Tage.

## snow_line

Mitteleuropa. Farben und Zahlen: Schneefallgrenze = Nullgradgrenze − 350 m, mindestens der
Modellboden. Eingefärbt ist sie nur dort, wo die Höhe ein Niederschlagssignal zeigt: RH auf 850 oder
700 hPa ≥ 90 % und Hebung auf 700 hPa. Sonst ist die Fläche grau.

- Das Signal sagt, dass Niederschlag wahrscheinlich ist, nicht wie viel.
- Bei kräftigem Niederschlag liegt die Schneefallgrenze tiefer (Schmelzabkühlung), bei schwachem
  höher.
- Steht dort die Höhe des Modellbodens, heißt das nur „Schnee bis zum Modellboden“. In Tälern
  unter dem Modellboden entscheidet die Temperatur dort, ob Schnee oder Regen fällt.

## orography

Mitteleuropa (statisch, `orography.webp`). Farben und Zahlen: Höhe des Modellbodens. Schraffiert:
Standardabweichung der Orografie innerhalb der Gitterbox (`sdor`) ≥ 200 m, dort weichen Täler und
Gipfel um mehrere 100 m von der Modellhöhe ab.

- Beispiele: Wien real 170 m, im Modell 220 m. Innsbruck real 574 m, im Modell 1306 m
  (`sdor` 500 m).
- In schraffierten Gebieten sind T2m, Tmax und Tmin besonders unsicher. Gib dort breite Spannen an
  und sag dazu, dass das Globalmodell die Orografie nur grob abbildet.
- Was das Modell nicht sieht: Kaltluftseen, Talwinde, die genaue Föhnreichweite, Stau an einzelnen
  Ketten.

## weather_summary

Mitteleuropa, ab T+3. Grau: Gesamtbewölkung ab 40 %. Grün bis Rot: Niederschlag der letzten 6 h
(bei T+3 der letzten 3 h). Symbole: Niederschlagsart zum Termin (Schnee, Schneeregen, gefrierender
Regen), Regen ohne Symbol. Schwarze Linien: Isobaren alle 4 hPa mit Hoch und Tief.

- Bewölkung, Niederschlag und Niederschlagsart sind Bodenparameter des Modells mit allen Schwächen
  der groben Auflösung. Wie du sie gewichtest, steht in SKILL.md unter „Zweck des Skills“.
- Der Niederschlag ist eine Summe über die Stunden vor dem Termin, die Niederschlagsart gilt zum
  Termin selbst.
- Der Kontaktabzug zeigt die Phasen mit Wolken und Niederschlag über 10 Tage.

## ICON-D2-Datei

Ein Lauf von ICON-D2 (DWD Open Data, etwa 2,2 km) auf dem Ikosaeder-Gitter des Modells: ein Wert
je Zelle, kein reguläres Gitter. Die Lage der Zellen steht in `clat`/`clon`. Stündlich von T+0
bis T+48, ohne abgeleitete Felder. Die Namen sind die von ecCodes; in Klammern der Name, unter dem
der Viewer das Feld liest.

| Name | Schritte | Einheit | Bedeutung |
|---|---|---|---|
| `tlat`, `tlon` (`clat`, `clon`) | nur T+0 | ° | Mittelpunkt jeder Zelle |
| `HSURF` (`hsurf`), `lsm` | nur T+0 | m, 0–1 | Modellorografie, Landanteil |
| `CLCT` (`tcc`) | 0–48 | % | Gesamtbewölkung (nicht 0–1 wie bei IFS) |
| `tp` | 0–48 | kg/m² = mm | Niederschlag seit T+0 (nicht m wie bei IFS) |
| `prmsl` (`msl`) | 0–48 | Pa | Luftdruck auf Meeresniveau |
| `WW` (`ww`) | 1–48 | Code | signifikantes Wetter zum Termin, WMO-Tafel 4677 (45/48 Nebel, 5x Niesel, 6x Regen, 7x Schnee, 8x Schauer, 95/96 Gewitter, 96 mit Hagel) |
| `max_i10fg` (`gust`) | 0–48 | m/s | stärkste Böe in 10 m während der Stunde vor dem Termin |
| `2t` | 0–48 | K | Temperatur in 2 m |
| `max_2t`, `min_2t` (`tmax_2m`, `tmin_2m`) | 0–48 | K | Extreme in 2 m seit dem letzten Neustart; ICON startet sie alle 6 h ab Laufbeginn neu, obwohl der Kopf „seit T+0“ angibt |
| `10u`, `10v` | 0–48 | m/s | Wind in 10 m |
| `u`, `v` | 1000, 850, 700 hPa | m/s | Wind |
| `t`, `r`, `z` | 850, 700 hPa | K, %, m²/s² | Temperatur, relative Feuchte, Geopotential (nicht gpm wie `gh` bei IFS) |

Zellen im Randstreifen der Domain haben fehlende Werte (Bitmap). 925 hPa gibt es bei ICON-D2 nicht.

## Produkte im Fenster icon-d2

ICON-D2 für Österreich und Umgebung, stündlich von T+1 (`weather_summary`) bzw. T+0 bis T+48.
Die Karten lesen sich wie ihre IFS-Gegenstücke im Mitteleuropafenster, mit diesen Unterschieden:

- [t2m_wind1000](#t2m_wind1000), [wind10m](#wind10m): gleich; Täler und Becken sind etwa viermal
  feiner aufgelöst, Kaltluftseen und Talwinde zeigen sich deshalb deutlich.
- [mountain_2000](#mountain_2000): das Profil kommt nur aus 850 und 700 hPa (IFS: sechs Flächen).
  2000 m liegen immer dazwischen, der Wert ist linear interpoliert.
- [tmax, tmin](#tmax-tmin): Fenster wie bei IFS (06–18 UTC bzw. 18–06 UTC), meist ein Tmax-Tag und
  zwei Tmin-Nächte je Lauf. Bei Läufen um 03, 09, 15 und 21 UTC kommen die ersten drei Stunden
  eines Fensters aus der stündlichen 2-m-Temperatur statt aus den Modellextremen, ein Maximum am
  Morgen oder ein Minimum am Abend kann dort etwas zu schwach sein.
- Alle Karten färben grau, was außerhalb der Domain liegt; das Fenster liegt derzeit ganz darin.

## icon-d2/weather_summary

ICON-D2 für Österreich und Umgebung, stündlich von T+1 bis T+48. Inhalt wie
[weather_summary](#weather_summary), aber:

- Der Niederschlag ist die Summe der **letzten Stunde**, nicht der letzten 6 h.
- Die Niederschlagsart kommt aus `ww` und ist auf dieselben Symbole abgebildet wie bei IFS.
- **Zusätzlich:** Gewitter (Blitz, ww 95), Gewitter mit Hagel (Dreieck, ww 96), Nebel (drei
  Striche, ww 45/48) und Sturmböen ab 75 km/h (Bft 9) als Zahl in km/h. ICON-D2 rechnet Konvektion
  und Nebel aufgelöst; IFS kennt diese Felder nicht.
- Landesgrenzen schwarz, Bundesländergrenzen gestrichelt; sie helfen beim Verorten.
- Hintergrund und Wolken wie bei IFS: Jede Farbe ist genau eine der Legende.

- Das Modell löst Strukturen ab etwa 10 km auf, auf der Karte rund 13 px. Einzelne Schauer und
  Gewitterzellen sind Möglichkeiten im Raum, keine Ortsprognose.
- Der Kontaktabzug zeigt die Karten um 03, 09, 15 und 21 UTC, also 8 Kacheln über 48 h: den
  Tagesgang mit Gewittern am Nachmittag (15 UTC) und Nebel in der Nacht und am Vormittag.
- `icon-d2/orography.webp` zeigt, wie fein ICON-D2 Täler und Gipfel auflöst (ohne Schraffur, ICON
  liefert keine Subgitter-Rauigkeit). Vergleiche sie mit der IFS-Orografie, bevor du Talwetter
  aus einer der beiden Karten liest.
