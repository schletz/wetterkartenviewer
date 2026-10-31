# wetterkartenviewer — Agent-Referenz

Referenz für die React-App und die Python-Datenpipeline (Download, abgeleitete Felder, Karten), damit Erweiterungen ohne vollständiges Lesen des Quellcodes möglich sind. Pfade relativ zum Repository-Root.

## Zweck

- Statische Single-Page-App (React 19, Vite, TypeScript), veröffentlicht auf GitHub Pages: https://schletz.github.io/wetterkartenviewer/
- **Startseite:** ECMWF-ENS-Meteogramme (Opencharts-API, live vom Browser abgefragt) für einen Ort, den der Nutzer einstellt.
- **Kartenseite (`#/maps`):** ein Raster aus Kacheln mit den Karten eines ECMWF-IFS-Laufs (bis +240 h) und eines ICON-D2-Laufs des DWD (Österreich und Umgebung, stündlich bis +48 h), dazu ein Zeitslider von +0 bis +240 h ab dem IFS-Lauf. Jeder Kachel-Pfad ist ein AV1-Video (ein Frame pro Termin), die App springt per `currentTime` zum Frame. Ein Layer kann eine Rückfallkette aus mehreren Pfaden sein (ICON-D2 in seinen 48 h, sonst ECMWF).
- **Datenpipeline** (`scripts/`): lädt einen IFS-HRES-Lauf (0,1°) von ECMWF Open Data, schneidet ihn auf Europa zu, hängt abgeleitete Felder an; lädt einen ICON-D2-Lauf (DWD Open Data, unstrukturiertes Ikosaedergitter ≈ 2,2 km) unverändert. Rendert Karten (WebP) für drei Kartenfenster nach `data/` (zwei IFS, eines ICON-D2), kodiert jeden Kachel-Layer mit ffmpeg als `maps/<fenster>/<produkt>.mp4`, schreibt `maps/manifest.json`, lädt die Videos in ein GitHub-Release und pusht einen Manifest-Commit. IFS und ICON-D2 werden getrennt aktualisiert (IFS alle 12 h, ICON-D2 alle 3 h).
- `data/` ist zugleich das Datenverzeichnis des Skills `synop` (`~/.claude/skills/synop`); siehe Abschnitt *Vertrag mit dem Skill synop*.

## Modulüberblick

### App

| Datei | Zeilen | Verantwortung |
| --- | --- | --- |
| src/main.tsx | 10 | React-Root in StrictMode mounten |
| src/App.tsx | 13 | Route (Hash) und gespeicherten Ort halten, Start- oder Kartenseite zeigen |
| src/config/viewer.config.json | 54 | Kacheln mit Layern (Pfad oder Liste von Pfaden als Rückfallkette) und Meteogrammnamen, von Hand gepflegt |
| src/config/viewerConfig.ts | 32 | JSON typisieren (`ViewerConfig`, `TileConfig`, `LayerConfig`, `ChartPath`), `layerPaths` |
| src/model/ChartIndex.ts | 107 | Manifest abfragen: Frame zu einem Step (null nach `end`), erster/letzter Step, Steps aller Layer, Pfad eines Layers zu einem Step (`resolve`), Video-URL, Seek-Zeit |
| src/model/ChartProjection.ts | 56 | Lat/Lon in Bildpixel der drei Kartenfenster umrechnen |
| src/model/GeoLocation.ts | 13 | Ortstyp, Default-Ort, Validierung |
| src/services/ecmwfMeteogram.ts | 42 | Meteogramm bei ECMWF rendern lassen und die Bild-URL holen (mit Retry) |
| src/services/videoLoader.ts | 23 | Video einmal ganz laden → Object-URL; Promise (URL oder null) pro URL gecacht; nur `video/*` zählt |
| src/hooks/useChartIndex.ts | 28 | `maps/manifest.json` laden |
| src/hooks/useHashRoute.ts | 23 | Route `start`/`maps` aus `location.hash` |
| src/hooks/useLoadedVideo.ts | 39 | Voriges Video zeigen, bis das neue geladen ist; Ladefehler melden |
| src/hooks/useStoredLocation.ts | 28 | Ort in localStorage lesen und schreiben |
| src/components/StartPage.tsx | 29 | Kopfzeile mit Ortsformular, Meteogramme |
| src/components/LocationForm.tsx | 38 | Eingabe von Breite und Länge |
| src/components/Meteogram.tsx | 44 | Ein Meteogramm samt Lade- und Fehlerzustand |
| src/components/MapViewer.tsx | 21 | Manifest laden, dann `ChartGrid` |
| src/components/ChartGrid.tsx | 69 | Step-, Layer- und Großansicht-State, Tastatur, Raster |
| src/components/ChartTile.tsx | 33 | Kachel: Pfad des Layers per `index.resolve`, Linksklick nächster Layer, Rechtsklick Großansicht |
| src/components/ChartImage.tsx | 75 | Stummes `<video>` auf den Frame des Steps setzen bzw. Platzhalter („ab +N h“, „bis +N h“), Ortsmarker |
| src/components/LargeView.tsx | 69 | Verschiebbares Fenster mit der Karte in 1:1-Größe |
| src/components/StepSlider.tsx | 23 | Range-Input 0–240 h mit Tagesmarken |
| src/components/*.module.css | je 4–41 | CSS-Module pro Komponente |
| src/index.css | 28 | Globale CSS-Variablen (`--bg`, `--accent`, `--gap` …) |
| .github/workflows/deploy.yml | 39 | Bei Push auf `main`: bauen, Manifest und Videos aus dem Release nach `dist/maps` (`fetch_maps.py`), Pages deployen |
| vite.config.ts | 13 | `base: './'`, `data/` und `maps/` vom Watcher ausnehmen |

### Skripte und Steuerdateien

Jedes Pipeline-Skript parst nur Argumente und verdrahtet Klassen aus `scripts/lib/`. `download_ecmwf_data.py`, `download_icon_d2.py`, `render_charts.py` und `make_icon_test_grib.py` setzen ihr eigenes Verzeichnis in `sys.path`, damit `python -I` funktioniert. `update_maps.py`, `maps_manifest.py`, `publish_maps.py` und `fetch_maps.py` importieren ihre Nachbarmodule (`maps_manifest`, `maps_release`, `tile_videos`) über das Skriptverzeichnis in `sys.path`, also ohne `-I`.

| Datei | Zeilen | Verantwortung |
| --- | --- | --- |
| scripts/update_maps.py | 199 | Orchestrierung: Klimatologie prüfen, beide Downloads, alte Läufe löschen, je Modell entscheiden, welche Fenster nach `data/` gerendert werden, fehlende Kachel-Videos kodieren, Manifest |
| scripts/maps_manifest.py | 140 | Layer-Pfade aus der Config (Listen aufgelöst), Frame-Reihenfolge eines Layers (`chart_frames`), Lauf eines Fensters aus `geometry.json`, Manifest erzeugen, Run, Fenster-Runs und Videoliste lesen |
| scripts/tile_videos.py | 56 | `encode_video`: WebP-Karten als rohes RGB an ffmpeg, AV1-MP4 schreiben (Modul ohne CLI) |
| scripts/publish_maps.py | 126 | Manifest prüfen, geänderte Videos ins Release laden, überzählige Assets löschen, Manifest committen, pushen (`gh`, `git`) |
| scripts/fetch_maps.py | 48 | Im Deploy: Manifest und dessen Videos aus dem Release nach `dist/maps` (nur Standardbibliothek, ohne Token) |
| scripts/maps_release.py | 20 | `TAG` des Releases, Asset-Name und Download-URL eines Videos |
| scripts/download_ecmwf_data.py | 145 | IFS: Lauf wählen, Gruppen parallel laden, zuschneiden, abgeleitete Felder anhängen |
| scripts/download_icon_d2.py | 113 | ICON-D2: Lauf wählen (`IconRuns`), Dateien parallel laden (`IconDownloader`), zu einer GRIB2-Datei verbinden |
| scripts/render_charts.py | 234 | Modell am Gittertyp erkennen, Produkte eines Fensters im Prozesspool rendern, Kontaktabzüge, `geometry.json` |
| scripts/build_borders.py | 131 | Einmalig, von Hand: `lib/borders_austria.geojson` aus BEV-Shapefile + world_countries.geojson bauen (braucht pyshp, shapely ≥ 2.1, pyproj; die Pipeline nicht) |
| scripts/make_icon_test_grib.py | 108 | Testwerkzeug: Kopie einer ICON-Datei mit künstlicher Szene (Gewitterlinie, Hagel, Nebel, Sturmböen) zum Prüfen der Symbole; **nie veröffentlichen** |
| data/charts.md | 420 | Deutsche Beschreibung von Ordner, GRIB-Feldern und Produkten **für den Skill**; einzige committete Datei in `data/`, wird nur in einen anderen Datenordner kopiert |
| download_data.cmd | 5 | `update_maps.py data maps %*` und bei Erfolg `publish_maps.py maps` |
| download_data.sh | 5 | dasselbe für macOS/Linux mit `python3`; im Index ausführbar (100755) |

### Paket `scripts/lib/` (29 Klassen, eine öffentliche Klasse pro Datei)

Alle Abhängigkeiten werden über den Konstruktor injiziert. Ohne Klasse: `__init__.py`, constants.py, local_params.py, chart_styles.py, fonts.py.

| Datei | Zeilen | Klasse | Verantwortung |
| --- | --- | --- | --- |
| constants.py | 19 | — | `KELVIN`, `KMH_PER_MS`, `GRAVITY`, `WEATHER_PARAMS`, `PROFILE_LEVELS`, `ICON_NAMES` |
| local_params.py | 20 | — | Nummern der lokalen GRIB-Parameter (Kategorie 192) ↔ Namen |
| projection.py | 139 | Projection (frozen dataclass) | Konforme Kegelprojektion eines Kartenfensters (cone = 1: polarstereografisch), `lambert()`, `km_per_px`, `north_east`; `EUROPE`, `CENTRAL_EUROPE`, `ICON_D2`, `PROJECTIONS` |
| icon_run.py | 11 | IconRun (frozen dataclass) | Ergebnis von IconRuns: Lauf und URLs aller Dateien |
| icon_runs.py | 109 | IconRuns | DWD-Verzeichnislistings lesen (ein Listing je Ordner): neuester kompletter ICON-D2-Lauf, URLs aller Dateien; Parameter `<ordner>@<hPa>` |
| icon_downloader.py | 67 | IconDownloader | bz2-Dateien mit Retries laden, nur Nachrichten auf vollen Stunden behalten, zu einer Datei verbinden |
| open_data_runs.py | 52 | OpenDataRuns | Neuester kompletter Lauf; Hinweis, wenn ein neuerer erst mit 0,25° da ist |
| request_plan.py | 69 | RequestPlan | Request-Gruppen eines Laufs, erwartete Nachrichtenzahlen; Funktion `count_messages` |
| group_downloader.py | 52 | GroupDownloader | Eine Gruppe mit Retries laden, Anzahl prüfen |
| grib_cropper.py | 88 | GribCropper | Globale Nachrichten auf die Box schneiden und neu kodieren |
| forecast_writer.py | 141 | ForecastWriter | Rohdateien im Prozesspool zuschneiden, in Rohdatei-Reihenfolge in eine Datei schreiben, `thick` je Step |
| derived_writer.py | 147 | DerivedWriter | Abgeleitete Felder an die Vorhersagedatei anhängen (Prozesspool) |
| extreme_windows.py | 45 | ExtremeWindows | Welche 3-/6-h-Extreme ein Tagesfenster lückenlos abdecken; Steps eines Fensters (`window`, auch für ICON) |
| forecast_grib.py | 179 | ForecastGrib | Byte-Offset-Index der Vorhersagedatei (IFS oder ICON, Namens-Aliasse), gecachtes Dekodieren, Tagesextreme |
| model_surface.py | 21 | ModelSurface | Statische T+0-Felder des IFS: `height` (m), `sdor`, `land` |
| icon_surface.py | 25 | IconSurface | Statische Felder von ICON je Zelle: `lat`, `lon`, `height`, `sdor` = None, `land` (Anteil), `valid` |
| height_profile.py | 68 | HeightProfile | Druckflächenprofil → Wert in fester Höhe, Nullgradgrenze; Höhenfeld wählbar (`gh` oder `z` × Faktor) |
| diagnostics.py | 70 | Diagnostics | Diagnosen der freien Atmosphäre (Inversion, feuchte Grenzschicht, Niederschlagssignal, Schneefallgrenze) |
| climate_archive.py | 200 | ClimateArchive | Klimatologie-GRIBs über die Bytes der Kopfteile indizieren, Felder dekodieren, Gitter, nächster Punkt |
| t850_climate.py | 50 | T850Climate | T850-Mittel (°C) / Std (K) je Gültigkeitszeit, als Feld oder Punkt |
| pixel_grid.py | 39 | PixelGrid | Reguläres Lat/Lon-Gitter auf 1200×600 Pixel resamplen; Wind in Pixelvektoren |
| triangle_grid.py | 78 | TriangleGrid | Unstrukturiertes Gitter (ICON-Zellmittelpunkte) per Delaunay/baryzentrisch auf die Pixel; gleiche Schnittstelle wie PixelGrid + `covered` |
| base_map.py | 64 | BaseMap | Projizierte Länder- und Bundesländerringe (`projection.borders`) und Gradnetz |
| colour_scale.py / contour_style.py / symbol_style.py | 27 / 27 / 28 | ColourScale / ContourStyle / SymbolStyle | Frozen dataclasses für Farbbänder, Konturlinien, Punktsymbole (`marker` auch Vertices oder matplotlib-`Path`) |
| chart_styles.py | 240 | — | Alle Farbskalen, Konturstile, Schwellen (auch von Diagnostics benutzt), ww-Zuordnung und -Symbole von ICON |
| fonts.py | 18 | — | `load_font`: Arial (Dateinamen von Windows und macOS) → DejaVu Sans → PIL-Default in Größe `size` |
| chart_canvas.py | 314 | ChartCanvas | Eine matplotlib-Figur: Kartenlayer + Legendenstreifen, verlustfrei als WebP speichern |
| chart_products.py | 467 | ChartProducts | Produktregister (`STEP`, `DAY`, `STATIC`, `ALL`, `CLIMATE`, `DEFAULTS`, `MODEL`, `PRECIP_HOURS`, `SHEET_HOURS`), eine Methode pro Produkt, Hooks `profile`, `summit_cloud`, `extreme_days`, `daily_extreme_field`, `cloud_cover`, `precipitation`, `precipitation_type` |
| icon_products.py | 94 | IconProducts(ChartProducts) | ICON-D2-Produkte `t2m_wind1000`, `wind10m`, `mountain_2000`, `weather_summary` (+ Gewitter, Hagel, Nebel, Sturmböen), `tmax`, `tmin`, `orography`; Grau außerhalb des Gebiets in jeder Karte |
| icon_extremes.py | 55 | IconExtremes | Tagesmax/-min von ICON aus den 6-stündlich neu startenden `tmax_2m`/`tmin_2m` (+ stündliche `2t` vor dem ersten Neustart im Fenster) |
| contact_sheet.py | 67 | ContactSheet | Kontaktabzüge bauen, Kachelursprünge liefern |
| world_countries.geojson | 8,7 MB, eine Zeile | — | Ländergrenzen, Esri „World Countries (Generalized)“ (https://hub.arcgis.com/datasets/esri::world-countries-generalized), lokal gelesen; `borders` der IFS-Fenster |
| borders_austria.geojson | 3,5 MB, eine Zeile | — | `borders` von `icon-d2`: Länder in Europa (Nachbarn Österreichs entlang der genauen Grenze zugeschnitten) + Österreich + 9 Bundesländer (10 Polygone, Tirol zweiteilig) aus BEV VGD 1:50 000; erzeugt von build_borders.py. Liegt in `scripts/lib/` und ist nicht von `.gitignore` erfasst |

Python gesamt 4.416 Zeilen (Skripte 1.320, lib 3.096).

Externe Abhängigkeiten: npm (`package.json`), Laufzeit nur `react`/`react-dom`, Entwicklung `vite`, `@vitejs/plugin-react`, `typescript ~7.0`, `oxlint`. Kein Router, kein State-Management, keine UI-Bibliothek. npm-Skripte: `dev`, `build` (`tsc -b && vite build`), `lint` (oxlint, .oxlintrc.json), `preview`.
Python-Pakete (keine requirements-Datei): `ecmwf-opendata`, `eccodes`, `numpy`, `scipy` (`ndimage`, `spatial.Delaunay`), `matplotlib` (Agg, erzwungen in scripts/lib/chart_canvas.py:14), `Pillow`, `requests`; nur für build_borders.py zusätzlich `pyshp`, `shapely` ≥ 2.1 (`coverage_simplify`), `pyproj`. `update_maps.py` ruft die drei Pipeline-Skripte (beide Downloader, Renderer) als Subprozess mit `sys.executable` auf. `tile_videos.py` braucht Pillow und **ffmpeg mit dem Encoder `libaom-av1` im PATH**.
Die App kennt die Pipeline nicht, sie liest nur `maps/manifest.json` und die MP4-Videos.

## Verzeichnisse

| Ordner | Git | Inhalt |
| --- | --- | --- |
| `data/` | ignoriert (`/data/*`) bis auf `charts.md` | genau ein Lauf je Modell: `ecmwf_<run>.grb2`, `opencharts_europe/` (**alle** Produkte), `opencharts_central_europe/` (Default-Produkte), `icon-d2_<run>.grb2`, `icon-d2/` (alle ICON-Produkte); je Fenster `sheets/`, `orography.webp`, `geometry.json`; dazu `era5_means/` und `charts.md` (committet, von Hand gepflegt) |
| `data/era5_means/` | ignoriert | `era5_means.grb2` (422 MB, 13 224 Felder, ERA5 1991–2020). Kein Skript erzeugt oder lädt sie: einmal von Hand von Google Drive laden (Link in README.md, Abschnitt Klimatologie; laut User). `update_maps.py` prüft vor dem Download, dass ein `*.grb2` da ist, und lässt es stehen |
| `maps/` | nur `manifest.json` committet (`/maps/*`, `!/maps/manifest.json`) | `manifest.json` und je Kachel-Layer ein Video `<fenster>/<produkt>.mp4`, kodiert aus `data/<fenster>/<produkt>/`; dazu Videos von Layern, die seit dem letzten neuen Lauf aus der Config entfernt wurden (siehe Fallstricke). Die Videos des Manifests liegen als Assets im Release `tile-videos` |

Größen beim Lauf 2026103000: GRIB 1,54 GB (Lauf 2026103100: 1617 MB), `data/opencharts_europe` 266 MB, `data/opencharts_central_europe` 125 MB, `maps/` ≈ 52 MB (10 Videos, 2,5–7,3 MB je Video). ICON-D2 (Lauf 2026103109): GRIB 820 MB (1130 Nachrichten), 4 ICON-Videos 2,2–5,5 MB; `maps/` gesamt ≈ 67 MB (14 Videos).

### Vertrag mit dem Skill synop

Der Skill liest `data/` als Datenverzeichnis (Docstrings scripts/update_maps.py:3-14, scripts/lib/local_params.py:1-8). Laut User bilden diese Punkte die Schnittstelle; Änderungen daran brechen den Skill, der im Skill-Ordner nachgezogen werden muss:

| Element | Erzeuger | Was der Skill erwartet |
| --- | --- | --- |
| `data/charts.md` | von Hand gepflegt, committet; in einen anderen Datenordner kopiert (scripts/update_maps.py:173-174) | Beschreibung der Dateien, GRIB-Felder (inkl. Einheiten, lokale Nummern) und aller Produkte; von Hand gepflegt |
| `data/<fenster>/geometry.json` | `write_geometry` (scripts/render_charts.py:160) | Schlüssel `window`, `model` (`ChartProducts.MODEL`: `ECMWF IFS` / `ICON-D2`), `run` (YYYYMMDDHH), `image.width/height` (= Kartenfläche 1200×600, ohne Legende), `projection.pole_x/pole_y/scale_k/cone/lon0/formula`, `sheets.scale`, `sheets.tiles.<produkt>` = Liste `[x, y]` der Kachel-Ecken oben links. `run` liest auch `maps_manifest.window_run` |
| GRIB-Layout | download_ecmwf_data.py + `DerivedWriter` | shortNames, Ebenen, Einheiten, `stepRange` der Tagesextreme und vor allem die lokalen `parameterNumber` 0–5 in Kategorie 192 (`LOCAL_NAMES`, scripts/lib/local_params.py:12) — der Skill benennt sie selbst nach Nummer |
| Ordner-/Dateinamen | `ChartProducts.path` (scripts/lib/chart_products.py:97), `ClimateArchive` | `<fenster>/<produkt>/<YYYYMMDDHH>.webp`, Tagesprodukte `<YYYYMMDD>.webp`, `sheets/<produkt>.webp`, `orography.webp`, `era5_means/*.grb2`, ein Lauf `ecmwf_<run>.grb2`; daneben `icon-d2_<run>.grb2` und `icon-d2/` |

**Projektionsformel:** `geometry.json` enthält die allgemeine Kegelformel mit `cone` und `lon0` (siehe *Projektion und Ortsmarker*). `ChartGeometry` im Skill (`~/.claude/skills/synop/scripts/lib/chart_geometry.py:47-51`) rechnet noch die polarstereografische Formel ohne `cone`/`lon0`: Für `opencharts_*` (cone 1, lon0 0) stimmt das, für `icon-d2` landen Ortsmarker des Skills falsch, bis der Skill nachgezogen ist.

## Schnittstelle (CLI)

```
update_maps.py <data> <maps> [--base YYYYMMDDHH] [--icon-run YYYYMMDDHH] [--force]
maps_manifest.py <data> <maps> --run YYYYMMDDHH
publish_maps.py <maps>                     (gh und git laufen im Repo-Root)
fetch_maps.py <maps> <target> --repository owner/name
download_ecmwf_data.py <out file|existing dir> [--base YYYYMMDDHH] [--max-step N] [--keep-raw]
download_icon_d2.py <out file|existing dir> [--run YYYYMMDDHH] [--keep-raw]
render_charts.py <grib> <outdir> [--climate DIR] [--projection icon-d2|opencharts_central_europe|opencharts_europe]
                 [--products a,b|all] [--workers N]
build_borders.py <VGD_50_generalisiert.shp> [target.geojson]     (Default scripts/lib/borders_austria.geojson)
make_icon_test_grib.py <source.grb2> <target.grb2> [--step N]    (Default 12)
```

| Skript | Ausgabe | Exit ≠ 0 bei | Hinweise |
| --- | --- | --- | --- |
| update_maps | `data/…`, `maps/<fenster>/<produkt>.mp4`, `maps/manifest.json` | ECMWF-Download-, Render-Fehler, IFS-Layer ohne Karten in `data/` (`sys.exit` mit Meldung); ffmpeg-Fehler (Traceback) | `--force` erzwingt Rendern und Neukodieren aller Layer beider Modelle (ICON nur, wenn sein Download geklappt hat), nicht den Download. Ein gescheiterter ICON-Download ist nur eine Warnung. Ohne neuen Lauf ≈ 3,5 s (gemessen) |
| maps_manifest | `maps/manifest.json`, Pfad auf stdout | — | rendert/kodiert nichts; Steps aus den Kartennamen in `data/`, listet nur Layer mit vorhandenem Video (sonst `warning: no video for …`) |
| publish_maps | Release-Assets, Commit „Data update <run>z[, <fenster> <run>z …]“, Push | kein Manifest oder keine Videos darin, Video des Manifests fehlt, jeder gh-/git-Fehler (`sys.exit` mit stderr) | legt das Release beim ersten Aufruf an (`--latest=false`); lädt nur geänderte Videos hoch (`changed_videos`); committet nur das Manifest und nur, wenn es sich geändert hat; pusht immer (auch lokale Code-Commits) |
| fetch_maps | `<target>/manifest.json`, `<target>/<fenster>/<produkt>.mp4` | kein Manifest oder keine Videos darin, Download-Fehler (`sys.exit` mit URL) | lädt anonym über `https://github.com/<repo>/releases/download/tile-videos/<asset>`; das Repo muss öffentlich sein |
| download | `<dir>/ecmwf_<YYYYMMDDHH>.grb2` (bei existierendem Ordner) oder die genannte Datei; letzte stdout-Zeile = absoluter Pfad | Lauf nicht publiziert (404), Gruppe unvollständig | `--base` nur 00/12 UTC (argparse-Fehler, Exit 2); vollständiges Ziel → „already on disk“, Exit 0 |
| download_icon_d2 | `<dir>/icon-d2_<YYYYMMDDHH>.grb2` oder die genannte Datei; letzte stdout-Zeile = absoluter Pfad | kein kompletter Lauf, `--run` nicht (mehr) komplett publiziert (`RuntimeError` → stderr, Exit 1), Nachrichtenzahl ≠ Dateizahl (Exit 1); Netzfehler nach den Retries und HTTP-Fehler eines Parameter-Listings → Traceback | `--run` nur Läufe, die DWD noch hat (≈ 1 Tag: 8 Stundenordner mit je dem neuesten Lauf); Ziel mit genau einer Nachricht je Datei des Laufs → „already on disk“, Exit 0 (fragt vorher die Listings ab). Gemessen: 1130 Dateien, 820 MB GRIB, 138 s (Netz schwankt; 1081 Dateien davor in 43 s) |
| render_charts | `<outdir>/<fenster>/…` (siehe Verzeichnisse) | unbekanntes Produkt (argparse, Exit 2) | erkennt ICON an `gridType` `unstructured_grid` der ersten Nachricht (`is_icon`) → `IconProducts`, sonst `ChartProducts`; `--projection` Default `icon-d2` bzw. `opencharts_europe`; ohne `--products`: `DEFAULTS[fenster]` der gewählten Klasse; `--climate` Default `<grib-Ordner>/era5_means` (`DIRECTORY` in climate_archive.py); Workers Default = CPU-Zahl. Gemessen ICON (alle Produkte): 199 Karten + 6 Kontaktabzüge ≈ 43 s mit warmem Dateicache, ≈ 148 s direkt nach dem Download (kalter Cache) |
| build_borders | GeoJSON, eine Zeile Statistik | ungefangene Ausnahmen | liest world_countries.geojson aus `scripts/lib/`; nur bei neuen Quelldaten nötig |
| make_icon_test_grib | Kopie mit Szene ab `--step` | ungefangene Ausnahmen | Ausgabe ist eine normale Eingabe für render_charts.py; Dateiname sollte `icon-d2_<run>.grb2` bleiben (Hilfetext) |

Status auf stdout, Fehler auf stderr; Meldungen englisch.

## Datenfluss

### Karten erzeugen und veröffentlichen (lokal)

```
download_data.cmd | download_data.sh [--base YYYYMMDDHH] [--icon-run YYYYMMDDHH] [--force]
 ├─ update_maps.py data maps                    scripts/update_maps.py:151
 │    ├─ check_climate(data)                    :59   ohne data/era5_means/*.grb2 sys.exit, vor Download und Löschen
 │    ├─ download("download_ecmwf_data.py", …)  :74   Subprozess, Ausgabe live; letzte nichtleere Zeile = GRIB-Pfad
 │    │    [Exit ≠ 0] None -> sys.exit("ECMWF download failed")
 │    ├─ remove_old_runs(data, grib, "ecmwf_")  :88   löscht data/ecmwf_*.grb2* (Datei, .raw/, .part) anderer Läufe
 │    ├─ download("download_icon_d2.py", …)     :74
 │    │    ├─ [Exit ≠ 0] Warnung auf stderr, icon_grib = None (ICON-Fenster bleibt, wie es ist)
 │    │    └─ sonst remove_old_runs(data, icon_grib, "icon-d2_")
 │    ├─ [anderer Datenordner] data/charts.md -> <data>/charts.md
 │    ├─ published = read_window_runs(maps)     scripts/maps_manifest.py:104   (vor dem Löschen des Manifests)
 │    ├─ same_run  = read_run(maps) == ECMWF-Run und kein --force
 │    ├─ icon_same = kein icon_grib oder (published[icon-d2] == ICON-Run und kein --force)
 │    ├─ maps/manifest.json löschen             (immer)
 │    ├─ stale_windows(data, maps, WINDOWS, same_run, run)       :112
 │    │  [icon_grib] stale_windows(data, maps, ICON_WINDOWS, icon_same, run)
 │    │    ├─ [nicht same] maps/<fenster>/ der Fenster dieses Modells löschen (alle Videos), alle rendern
 │    │    └─ [same] nur Fenster, deren data/<fenster>/ fehlt oder bei denen ein Kachel-Pfad
 │    │              dieses Fensters keine Karten in data/ hat (chart_frames leer)
 │    ├─ data/<fenster>/ löschen, render(grib des Modells, data, fenster) × alle parallel (Threads)   :100
 │    │      WINDOWS: opencharts_europe -> --products all, opencharts_central_europe -> Defaults
 │    │      ICON_WINDOWS: icon-d2 -> Defaults (IconProducts.ALL)
 │    ├─ encode_missing(data, maps, ECMWF-Run)  :127
 │    │    ├─ Pfade der Config (Listen aufgelöst) ohne maps/<pfad>.mp4
 │    │    ├─ [ICON-Layer ohne Karten in data/] Warnung, übersprungen
 │    │    ├─ [anderer Layer ohne Karten in data/] sys.exit, vor dem ersten Kodieren
 │    │    └─ ThreadPool(PARALLEL_ENCODES) × encode_video(chart_frames(data, layer, run), maps/<layer>.mp4)
 │    │         scripts/tile_videos.py:31   Karten als rohes RGB über stdin an ffmpeg -> <layer>.mp4.part -> rename
 │    └─ write_manifest(data, maps, ECMWF-Run)  scripts/maps_manifest.py:122
 │         └─ build_manifest :79   je Pfad steps (ab ECMWF-Run), run (window_run :71 aus geometry.json), end
 └─ publish_maps.py maps                        scripts/publish_maps.py:102
      ├─ [kein Manifest, keine Videos darin oder ein Video fehlt] Abbruch
      ├─ ensure_release()                       :43   gh release view, sonst create tile-videos --latest=false
      ├─ changed_videos(maps, files)            :51   gh release view --json assets; Asset fehlt, Größe anders oder updatedAt < mtime
      ├─ [geänderte da] upload_videos(maps, changed)   :63   Kopie unter Asset-Namen in ein Temp-Verzeichnis, gh release upload --clobber
      ├─ prune_assets(files)                    :75   gh release delete-asset für Assets, die das Manifest nicht nennt
      ├─ commit_manifest(maps, run)             :90   git add + git commit -- maps/manifest.json, nur bei Änderung
      │    └─ commit_message :84   "Data update <run>z" + ", <fenster> <run>z" je Fenster mit anderem Run (sortiert)
      └─ git push origin HEAD  (immer, ohne Force)
           └─ GitHub Actions: npm ci, npm run build, fetch_maps.py maps dist/maps, deploy-pages
```

### Download und abgeleitete Felder

```
download_ecmwf_data.main                         scripts/download_ecmwf_data.py:96
 ├─ OpenDataRuns.latest() [ohne --base]          scripts/lib/open_data_runs.py:28   (Netz)
 ├─ pending_notice(run) -> stderr [ohne --base]  scripts/lib/open_data_runs.py:32
 ├─ RequestPlan(STEPS ≤ max_step, run)           scripts/lib/request_plan.py:20
 ├─ [output_complete(out)] "already on disk", Pfad, Exit 0            :59
 ├─ ThreadPool(4) × GroupDownloader.retrieve     scripts/lib/group_downloader.py:22  -> <out>.raw/<gruppe>.grib2
 │     (stderr für den ganzen Block nach devnull)
 ├─ GribCropper.for_windows(PROJECTIONS)         scripts/lib/grib_cropper.py:26
 ├─ ForecastWriter.write(raw, <out>.part)        scripts/lib/forecast_writer.py:89
 │    ├─ message_spans(raw) je Datei             :34   (Datei, Offset, Länge) aus den GRIB2-Indicator-Sections
 │    ├─ cropper.fit(erste Nachricht)            scripts/lib/grib_cropper.py:37   im Hauptprozess, setzt cropper.grid
 │    ├─ ProcessPool(min(CPU, MAX_WORKERS), init_worker(cropper)) × crop_message(span), chunksize CHUNK_SIZE   :67
 │    │    Worker liest die Nachricht selbst, liefert zugeschnittene Bytes (+ Werte bei gh 500/1000)
 │    └─ Hauptprozess: Ergebnisse in Reihenfolge von pool.map schreiben, thick nach dem zweiten gh500/gh1000
 ├─ DerivedWriter.append(<out>.part)             scripts/lib/derived_writer.py:115
 │    ├─ ProcessPool(min(CPU, 8), init_worker) × step_messages(step)   :86   21 Nachrichten je Step
 │    └─ anhängen: alle Steps, dann orog, dann mx2t je Tag, mn2t je Tag
 ├─ <out>.part -> <out>  (rename)
 └─ rmtree(<out>.raw) [ohne --keep-raw]
```

### ICON-D2-Download

```
download_icon_d2.main                            scripts/download_icon_d2.py:77
 ├─ IconRuns(FORECAST_PARAMS, STATIC_PARAMS)     scripts/lib/icon_runs.py:24
 │    ├─ [--run] run(run)                        :53   Ordner run[8:10]; anderer Lauf darin -> RuntimeError
 │    └─ [sonst] latest()                        :41
 │         ├─ RUN_HOURS sortiert nach _folder_time (:93) absteigend   8 Listings
 │         └─ erster complete_run(hour) != None  :64   ein Listing je Ordner (_split :88: "t@850" -> Ordner t,
 │              Ebene 850), Dateien nach Ebene im Namen gefiltert; 20 Listings je Stundenordner
 ├─ [Ziel existiert und len(message_spans) == len(urls)] "already on disk", Pfad, Exit 0
 ├─ ThreadPool(PARALLEL_REQUESTS=8) × IconDownloader.fetch(url)   scripts/lib/icon_downloader.py:29
 │    ├─ [<out>.raw/<datei>.grib2 existiert] übernehmen
 │    ├─ requests.get (3 Versuche) -> bz2.decompress -> .part
 │    └─ nur Nachrichten mit _on_full_hour (:51) -> .part neu schreiben -> rename
 ├─ IconDownloader.join(raw_files, <out>.part)   :62   in URL-Reihenfolge aneinanderhängen, Nachrichten zählen
 ├─ [Anzahl != len(urls)] stderr, Exit 1 (.part und .raw/ bleiben)
 ├─ <out>.part -> <out>  (rename)
 └─ rmtree(<out>.raw) [ohne --keep-raw]
```

### Rendern

```
render_charts.main                               scripts/render_charts.py:213
 ├─ parse_args: is_icon(grib) (:95) wählt IconProducts/ChartProducts und das Default-Fenster
 ├─ build_products(...) im Hauptprozess          :105  (für keys(), Kontaktabzüge, geometry.json)
 │    ├─ [ICON] ForecastGrib(grib, ICON_NAMES), IconSurface, BaseMap,
 │    │         TriangleGrid(surface.lat, surface.lon, projection, surface.valid) -> IconProducts
 │    └─ [IFS]  ForecastGrib, ModelSurface, BaseMap, PixelGrid(grib.grid)
 │              [+ ClimateArchive, T850Climate, PixelGrid(archive.grid) nur wenn ein ChartProducts.CLIMATE-Produkt verlangt ist]
 ├─ tasks = (produkt, key, out_dir) für key in products.keys(produkt)
 ├─ ProcessPool(workers, init_worker -> build_products je Prozess), chunksize 2
 │    └─ render: products.draw -> ChartCanvas.save                     :127
 │         [ICON] IconProducts.draw: + uncovered (grau außerhalb) über jeder Karte
 ├─ write_sheets -> ContactSheet.build (liest die geschriebenen WebPs)  :136   Karten mit Stunde in products.SHEET_HOURS
 └─ write_geometry -> geometry.json (model, run, Projektion, Kacheln)   :160
```

Invarianten der Reihenfolge:

1. **Manifest wird vor allem Löschen und Rendern gelöscht** (scripts/update_maps.py:182) und erst nach dem Kodieren geschrieben; die Runs daraus liest `main` vorher (`read_run`, `read_window_runs`, :176-177). „Gleicher Lauf“ heißt, getrennt je Modell: das Manifest nennt den ECMWF-Lauf oben (`run`) bzw. den ICON-Lauf an den Layern von `icon-d2` (`charts[…].run`). Ein abgebrochener Aufruf hinterlässt kein Manifest und zählt beim nächsten Mal für beide Modelle als neuer Lauf. Neuer Lauf oder `--force` → die Fenster dieses Modells in `maps/` leeren, rendern, ihre Layer kodieren. Gleicher Lauf → ein Fenster nur rendern, wenn sein Ordner in `data/` fehlt oder ein Kachel-Pfad dieses Fensters dort keine Karten hat (`stale_windows`, scripts/update_maps.py:112), und nur Pfade ohne Video kodieren. Ein gescheiterter ICON-Download zählt als gleicher ICON-Lauf. `stale_windows`, `encode_missing` und das Manifest laufen bei jedem Aufruf; ein in viewer.config.json ergänzter Layer greift also ohne `--force`, auch mit einem Produkt, das noch nicht gerendert ist (das Fenster wird dann ganz neu gerendert).
2. **Frame-Reihenfolge und Manifest-Steps kommen aus derselben Quelle:** `chart_frames` (scripts/maps_manifest.py:59) sortiert die Karten eines Layers in `data/` nach Step; `encode_video` schreibt sie in dieser Reihenfolge, `build_manifest` (:71) übernimmt deren Steps. Das Manifest liest die Steps bei jedem Aufruf neu aus `data/`, das Video kann aus einem vorigen Aufruf stammen — `len(steps)` muss der Frame-Zahl des Videos entsprechen, sonst zeigt die App stillschweigend falsche Termine. Beides gehört zum selben Lauf, solange `data/` nur durch `update_maps.py` geändert wird.
3. **`DerivedWriter` läuft auf der fertigen `.part`-Datei**: Er indiziert sie neu und braucht alle Modellfelder. Die Reihenfolge der angehängten Nachrichten ist Teil von `expected_total` (scripts/lib/request_plan.py:48).
4. **`ForecastWriter` schreibt `thick` direkt nach dem zweiten von gh500/gh1000 eines Steps**; die Reihenfolge 500/1000 innerhalb eines Steps wird nicht vorausgesetzt. Nur der Hauptprozess schreibt, und `pool.map` liefert in Eingabereihenfolge — die Datei ist deshalb byte-gleich mit einem Lauf ohne Pool. Wer auf `as_completed`/`imap_unordered` umstellt, bricht diese Reihenfolge.
5. **`GribCropper` berechnet Zeilen/Spalten aus der ersten Nachricht** (`fit`) und nutzt sie für alle weiteren; `cropper.grid` existiert erst nach dem ersten `fit`/`crop`. `ForecastWriter.write` ruft `fit` vor dem Pool auf, damit die Worker einen fertigen Cropper bekommen und `download_ecmwf_data` danach `cropper.grid` lesen kann.
6. **Einzelkarten vor Kontaktabzügen.** `write_sheets` öffnet die von den Workern geschriebenen WebPs; die Farbskala des Abzugs stammt aus dem Legendenstreifen der ersten Karte.
7. **ChartCanvas-Layer** werden in Aufrufreihenfolge innerhalb ihres zorder-Bands gezeichnet; `save` muss zuletzt kommen, weil dort Notizspalte und Symbolzeile entstehen (scripts/lib/chart_canvas.py:305). `IconProducts.draw` ruft `uncovered` nach der Produktmethode, das Grau liegt also im Band `Z_SHADING` über jeder Flächenfarbe.
8. **Erst hochladen, dann Manifest pushen:** `publish_maps.py` ersetzt die geänderten Assets, bevor der Manifest-Commit gepusht wird, und löscht überzählige Assets vor dem Push. Der Deploy des neuen Manifests findet so alle Videos. Die Asset-Namen enthalten keinen Lauf: Ein Deploy eines älteren Manifests, der während eines Uploads läuft, kann Videos des neuen Laufs holen; der Push danach startet einen neuen Deploy, `concurrency` (`cancel-in-progress`) bricht den alten ab. Die Historie wächst nur um das Manifest (≈ 20 KB je Lauf).
9. **Lauf eines Layers kommt aus `geometry.json`:** `write_geometry` schreibt `run` am Ende jedes Render-Laufs, `window_run` liest es beim Manifest; fehlt die Datei oder der Schlüssel, steht der ECMWF-Run am Layer. Beim nächsten Aufruf entscheidet dieser Wert, ob ICON als gleicher Lauf gilt. Ein `icon-d2/` ohne `geometry.json` wird deshalb bei jedem Aufruf neu gerendert.
10. **ICON-Steps zählen ab dem ECMWF-Run:** Bei neuem ECMWF-Lauf und gleichem ICON-Lauf bleibt das ICON-Video, das Manifest verschiebt nur dessen Steps. Karten vor dem ECMWF-Run klemmt `file_step` auf 0 (mehrere Frames mit Step 0; `frame` nimmt den letzten).

### App

```
App                                             src/App.tsx:6
 ├─ useHashRoute()        '#/maps' -> 'maps', sonst 'start'
 ├─ useStoredLocation()   localStorage 'wetterkartenviewer.location'
 ├─ [start] StartPage -> LocationForm, Meteogram × meteograms
 │                         └─ fetchMeteogramUrl(...)          src/services/ecmwfMeteogram.ts:28
 └─ [maps]  MapViewer -> useChartIndex() (fetch maps/manifest.json, cache: no-cache)
             └─ ChartGrid  state: step, layers[], enlarged     src/components/ChartGrid.tsx:23
                  ├─ StepSlider
                  ├─ ChartTile × tiles                             src/components/ChartTile.tsx:27
                  │    path = index.resolve(tile.layers[layer], step)   src/model/ChartIndex.ts:83
                  ├─ ChartImage(path)                               src/components/ChartImage.tsx:33
                  │    ├─ index.frame(path, step)   -> ChartFrame {index, step} oder null (auch nach end)
                  │    ├─ index.videoUrl(path)      -> <BASE_URL>maps/<file>?run=<video.run ?? manifest.run> oder null
                  │    ├─ useLoadedVideo(url)       src/hooks/useLoadedVideo.ts:21
                  │    │    │   -> { shown: {url, objectUrl} des zuletzt geladenen Videos, failed }
                  │    │    └─ loadVideo(url)       src/services/videoLoader.ts:13  fetch ganz -> Blob -> Object-URL
                  │    ├─ time = index.frameTime(frame), nur wenn shown.url === url
                  │    ├─ placeholderText(...)      src/components/ChartImage.tsx:18
                  │    ├─ <video muted playsInline preload="auto">; currentTime = time
                  │    │    (Effect ab readyState HAVE_METADATA, sonst onLoadedMetadata)
                  │    └─ projectionOf(path).toPixel(location) -> Marker
                  └─ [enlarged] LargeView(index.resolve(…, step)) -> ChartImage (1200 px breit; dieselbe URL,
                                also dasselbe gecachte Video)   src/components/ChartGrid.tsx:63
```

Während ein neuer Layer lädt, bleibt das Video des vorigen Layers mit seinem letzten Frame stehen (`time` ist `null`, der Slider bewegt es nicht). Dasselbe passiert, wenn eine Rückfallkette beim Schieben den Pfad wechselt (z. B. ICON → ECMWF nach `end`): das neue Video wird erst beim ersten Wechsel geladen. Erst wenn das neue Video da ist, wechselt `src`, und `onLoadedMetadata` setzt den Frame. Videos werden nur für angezeigte Layer geladen, es gibt kein Vorausladen anderer Layer.

## Kernkonzept: Manifest, Frames und Step-Auflösung

`maps/manifest.json` (Typ `Manifest`, src/model/ChartIndex.ts:22) ist die einzige Schnittstelle zwischen Pipeline und App:

```json
{ "run": "2026103012", "fps": 10,
  "charts": { "opencharts_europe/thickness_mslp":
                { "file": "opencharts_europe/thickness_mslp.mp4", "steps": [0, 3, 6, ..., 240],
                  "run": "2026103012", "end": 240 },
              "icon-d2/weather_summary":
                { "file": "icon-d2/weather_summary.mp4", "steps": [22, 23, ..., 69],
                  "run": "2026103109", "end": 69 } } }
```

- **`run` oben** ist der ECMWF-Lauf; der Slider und alle `steps` zählen ab ihm, auch die der ICON-Layer.
- **`charts[…].run`** ist der Lauf des Modells, aus dem das Video stammt (`window_run`, scripts/maps_manifest.py:71, aus `data/<fenster>/geometry.json`, sonst der ECMWF-Run). Er steht im Cache-Parameter der Video-URL und ist für `update_maps.py` die Erkennung des ICON-Laufs. Im TS-Typ optional (`ChartVideo`, src/model/ChartIndex.ts:4).
- **`end`** steht an jedem Pfad mit Karten: Step des letzten Frames, bei einer Tageskarte (`YYYYMMDD`) zusätzlich `HOURS_PER_DAY − 1` = 23 h (`build_manifest`, scripts/maps_manifest.py:79), sodass eine Tageskarte genau ihren Tag abdeckt (IFS-Steps meist 240, ICON z. B. 69, ICON-`tmax` bis 23 Uhr seines letzten Tages). `ChartIndex.frame` (src/model/ChartIndex.ts:54) liefert für `step > end` null; `ChartImage` zeigt „bis +N h“ statt des letzten Frames eines kurzen Laufs, in einer Rückfallkette greift stattdessen der nächste Pfad.
- **Rückfallkette (COALESCE):** Ein Layer in viewer.config.json ist ein Pfad oder eine Liste von Pfaden in Vorzugsreihenfolge (`LayerConfig`, src/config/viewerConfig.ts:10). `ChartIndex.resolve(layer, step)` (src/model/ChartIndex.ts:83) nimmt den ersten Pfad mit `frame(path, step)`, sonst den letzten Pfad mit Video, sonst den letzten Pfad (dessen Platzhalter erklärt dann, warum nichts da ist). So zeigt `[icon-d2/…, opencharts_central_europe/…]` ICON in dessen 48 h und davor/danach ECMWF. `ChartTile` und die Großansicht rufen `resolve` bei jedem Step; jeder Pfad hat sein eigenes Video und seinen eigenen Manifest-Eintrag.
- **Schlüssel** sind die Pfade aus `viewer.config.json` (`fenster/produkt`, Listen aufgelöst), dedupliziert in Config-Reihenfolge (`tile_chart_paths`, scripts/maps_manifest.py:35). Dieselbe Liste bestimmt, welche Videos `encode_missing` kodiert. Ein Pfad der Config ohne Video in `maps/` fehlt im Manifest (Warnung auf stdout); die App zeigt dann „keine Karten in diesem Lauf“. Videos in `maps/`, deren Layer nicht in der Config steht, fehlen ebenfalls.
- **`file`** ist relativ zu `maps/` (`video_file`, scripts/maps_manifest.py:66: `<pfad>.mp4`).
- **`steps[i]`** ist der Step von Frame `i`. Die Steps stammen aus den Kartennamen in `data/<pfad>/` (Gültigkeitszeiten): `file_step` (scripts/maps_manifest.py:46) rechnet `YYYYMMDDHH` in Stunden ab dem ECMWF-Run um, `YYYYMMDD` (Tagesprodukte `tmax`/`tmin`) ab 00 UTC des Tages, negative Werte auf 0 geklemmt; andere Namen werden ignoriert. Sortiert nach Step = Frame-Reihenfolge (`chart_frames`, :59).
- **Steps sind unregelmäßig:** IFS bis +144 h alle 3 h, danach alle 6 h (65 Frames); Produkte beginnen unterschiedlich (`weather_summary` ab +3 mit 64 Frames, `dt850_24h` ab +24). ICON-D2 stündlich, 49 Frames (T+0…T+48 des ICON-Laufs; `weather_summary` 48 ab T+1), versetzt um den Abstand der beiden Läufe (beim Lauf 2026103109 gegen 2026103012: +21…+69); `tmax`/`tmin` je ein Frame pro Tag.
- **`fps`** stammt aus `FPS` (scripts/maps_manifest.py:31), den auch `encode_video` verwendet, und gilt für alle Videos; die App rechnet nur mit dem Manifestwert.
- **Der Slider läuft in 1-h-Schritten** (0…`MAX_STEP`). `ChartIndex.frame` (src/model/ChartIndex.ts:54) liefert den letzten Frame mit `step <= slider` (lineare Suche), null nach `end`; liegt der Slider vor dem ersten Frame, zeigt `ChartImage` einen Platzhalter „ab +N h“, nach `end` „bis +N h“ (`placeholderText`, src/components/ChartImage.tsx:18).
- **Seek:** `frameTime` (src/model/ChartIndex.ts:100) = `(index + 0.5) / fps`, die Mitte des Frames, damit Rundung im Browser nie auf dem Nachbarframe landet. Mit einem Keyframe alle 8 Frames dekodiert ein Seek höchstens 7 Frames nach.
- **Ganzes Video statt Streaming:** `loadVideo` (src/services/videoLoader.ts:13) lädt die Datei per `fetch` komplett und spielt sie als Object-URL ab, damit jeder Slider-Seek lokal dekodiert statt auf Range-Requests zu warten. Das Promise bleibt pro URL für die Lebensdauer der Seite gecacht (auch ein Fehlschlag), Object-URLs werden nie freigegeben.
- **Pfeiltasten** springen zum nächsten/vorigen Step, den irgendein Pfad eines *sichtbaren* Layers hat (`index.steps(visible)` über alle Pfade einer Rückfallkette, src/components/ChartGrid.tsx:34-48); auf dem fokussierten Slider (Event-Target `HTMLInputElement`) bleibt die native 1-h-Bewegung. Escape schließt die Großansicht.
- **Start-Step** ist die aktuelle Stunde seit Run, abgerundet und auf 0…240 geklemmt (`currentStep`, src/components/ChartGrid.tsx:17).
- **Cache:** Video-URLs tragen `?run=<run des Layers>` (`videoUrl`, src/model/ChartIndex.ts:94; ohne `charts[…].run` der Manifest-Run), weil jeder Lauf dieselben Dateinamen wiederverwendet. Ein neuer ECMWF-Lauf lässt so die URL eines unveränderten ICON-Videos gleich. Das Manifest selbst wird mit `cache: 'no-cache'` geladen.

### Tile-Videos (scripts/tile_videos.py)

`encode_video(frames, target)` (scripts/tile_videos.py:31) öffnet jede Karte mit Pillow, konvertiert sie nach RGB und schreibt die Bytes als `rawvideo rgb24` 1200×690 über stdin an ffmpeg. Ausgabe zuerst nach `<target>.part`, bei Erfolg per `replace` nach `target`.

| Einstellung | Wert | Zweck / Herkunft |
| --- | --- | --- |
| Codec | `libaom-av1`, `-crf 20 -b:v 0` (konstante Qualität), `-cpu-used 6` | Aus einem Encodervergleich auf `z500_t850` gegen die verlustfreien Karten: libaom CRF 20 mit Screen-Tuning ≈ 7 MB bei gleicher PSNR wie WebP q90 mit 17 MB (laut User) |
| `tune-content=screen` | über `-aom-params` | schaltet Palettenmodus und Intra Block Copy ein, passend für flache Farben und Linien (Modul-Docstring) |
| `KEYFRAME_INTERVAL` (`-g`) | 8 | hält jeden Seek kurz |
| Pixelformat, Farbe | 4:2:0 (`yuv420p`), BT.709 Matrix/Primaries/Transfer, TV-Range | Die Karten sind sRGB; die BT.709-Tags lassen den Browser die Farben so zurückrechnen, wie sie kodiert wurden (Kommentar :26) |
| `FPS` | 10 | nur Zeitbasis für die Frame-Adressierung, das Video wird nie abgespielt |
| Container | MP4, `+faststart`, ohne Ton (`-an`) | |

Gemessen (laut User): Kodieren aller 10 Kachel-Videos ≈ 1:45 min mit 3 parallel, ein Video ≈ 27 s.

## Projektion und Ortsmarker

`Projection` (scripts/lib/projection.py:40) und `ChartProjection` (src/model/ChartProjection.ts:18) bilden dasselbe Modell: konforme Kegelprojektion auf der Kugel, Zentralmeridian `lon0` senkrecht durch die Kegelspitze (`pole_x`, `pole_y`, = Nordpol), Ursprung oben links, y nach unten, Kartenfläche 1200×600. `cone` = 1 ist die polarstereografische Projektion der Opencharts-Fenster, 0 < `cone` < 1 Lambert mit zwei Standardparallelen.

```
rho = scale_k * tan(45° - lat/2) ** cone
x = pole_x + rho*sin(cone*(lon - lon0));  y = pole_y + rho*cos(cone*(lon - lon0))
(lon - lon0 auf -180…180 gebracht: _relative_lon, scripts/lib/projection.py:123; TS ebenso)
```

| Fenster | pole_x | pole_y | scale_k | cone | lon0 | Gradnetz / Beschriftung (lon, lat) | `borders` |
| --- | --- | --- | --- | --- | --- | --- | --- |
| opencharts_europe | 481.0 | −180.8 | 1320.8 | 1 | 0 | 10° / 0°, 40° | world_countries |
| opencharts_central_europe | 435.35 | −1021.0 | 3493.4 | 1 | 0 | 5° / 0°, 40° | world_countries |
| icon-d2 | 733.24… | −7464.41… | 15611.89… | 0.73736… | 13.333… (13° 20′) | 2° / 7°, 46° | borders_austria |

Die Werte stehen doppelt: scripts/lib/projection.py:128-139 und `PROJECTIONS` (src/model/ChartProjection.ts:46-51), außerdem in jeder `geometry.json`. Opencharts: laut Modul-Docstring Least-Squares-Fits an gemessene Passpunkte der ECMWF-Opencharts-Fenster (RMS 0,45 bzw. 0,4 px); Mitteleuropa = Rechteck x 316–770, y 205–432 des Europafensters, 2,645-fach vergrößert. Sie sind für die Europafenster statisch und werden sich nicht ändern (laut User). Die verallgemeinerte Formel liefert für cone 1 / lon0 0 pixelgleiche Ergebnisse wie die polarstereografische (geprüft an je einer Karte von fünf Produkten).

**`icon-d2`** entsteht aus `Projection.lambert` (scripts/lib/projection.py:69): Standardparallelen 46°/49° und lon0 13° 20′ wie die österreichische Lambert-Projektion (EPSG:31287), Bildmitte 47,6° N 12,0° E, 0,75 km/px auf den Standardparallelen (dazwischen minimal mehr). Kommentar :131-135: 0,75 km/px ≈ 8 px je Modellzelle, so dicht wie ECMWF im Mitteleuropafenster; die Mitte liegt westlich der Österreichs, weil das Modellgebiet bei ≈ 18,3° E endet, und zeigt das von Westen kommende Wetter. Der Bildrand reicht über 5,72–18,19° E und 45,36–49,63° N, ganz im ICON-D2-Gebiet. **In TypeScript stehen die von Python berechneten Zahlen als Literale** (`print(ICON_D2)`); jede Änderung an `lambert`-Argumenten muss dort von Hand nachgezogen werden.

`km_per_px(lat)` (:99) = Erdradius 6371 km · cos(lat) / (cone · rho); `north_east()` (:104) liefert die Einheitsvektoren Nord (zur Kegelspitze) und Ost je Pixelmitte, Form (2, height, width); `PixelGrid` und `TriangleGrid` drehen damit u/v. Die Kegelspitze liegt über jedem Bild; `GribCropper.for_windows` verlässt sich darauf (Extreme liegen auf dem Bildrand). `download_ecmwf_data.py` übergibt alle `PROJECTIONS`, also auch `icon-d2`; das liegt im Europafenster und ändert die Box nicht. Python hat `pixel_to_latlon`, die App keine Rückwärtstransformation.

App: `toPixel` liefert `null` außerhalb der Kartenfläche 1200×600; die Legende (90 px) zählt nicht dazu. Der Marker wird in Prozent von 1200×690 positioniert (src/components/ChartImage.tsx:65-68) und hat feste Bildschirmgröße (10 px), damit er auf verkleinerten Kacheln sichtbar bleibt. Unbekanntes Fenster → kein Marker.

## GRIB-Vorhersagedatei (IFS)

Ein GRIB2-File pro Lauf, 0,1° reguläres Lat/Lon-Gitter, Zeilen Nord → Süd. Box aus `GribCropper.for_windows`: Bildränder beider Fenster ± `BOX_MARGIN_DEG` (1°), auf ganze Grad ab-/aufgerundet → **11–76° N, 71° W–77° E, 651 × 1481 Punkte**. Steps: `STEPS` (scripts/download_ecmwf_data.py:75) = 0…141 alle 3 h (48) + 144…240 alle 6 h (17) = **65**.

| Gruppe (Rohdatei) / Quelle | Inhalt | Nachrichten |
| --- | --- | --- |
| t, gh, r | je × `PROFILE_LEVELS` 1000/925/850/700/600/500 × 65 | 3 × 390 |
| uvw700 | u, v, w × 700 × 65 | 195 |
| uv_low | u, v × 850/925/1000 × 65 | 390 |
| sfc | msl, 2t, 10u, 10v × 65 | 260 |
| static | z, sdor, lsm (levtype sfc), nur T+0 | 3 |
| minmax3 / minmax6 | mx2t3, mn2t3 × 3…144 (48) / mx2t6, mn2t6 × 150…240 (16) | 96 / 32 |
| weather | tcc, tp, ptype × 65 | 195 |
| ForecastWriter | `thick` = gh500 − gh1000, GRIB2 0/3/12, isobaricLayer 1000–500 | 65 |
| DerivedWriter je Step (`PER_STEP` = 21) | t, r, u, v auf heightAboveSea 2000/2500/3000 (12); `deg0l` (paramId 228024; ecCodes setzt den Ebenentyp isothermal, level 273); `inv`, `rhbl`, `psig`, `snowl` (lokal, surface); `uf`, `vf` auf 1000/925 hPa (lokal) | 65 × 21 = 1365 |
| DerivedWriter einmalig | `orog` (paramId 228002, m, surface) | 1 |
| DerivedWriter je vollständigem Tag | `mx2t` (201) / `mn2t` (202), `stepRange` = ganzes Fenster | 10 + 9 |
| **Summe** (00z wie 12z) | | **3791** |

`RequestPlan.expected_total` (scripts/lib/request_plan.py:48) rechnet genau diese Summe; `output_complete` vergleicht sie mit der Nachrichtenzahl der Zieldatei. Jeder Request ist ein kartesisches Produkt param × levelist × step; `expected` setzt das voraus, weil Open Data fehlende Parameter stillschweigend weglässt.

**Lokale Parameter** (`LOCAL_NAMES`, scripts/lib/local_params.py:12): Disziplin 0, Kategorie 192, `parameterNumber` 0 `inv`, 1 `rhbl`, 2 `psig`, 3 `snowl`, 4 `uf`, 5 `vf`. ecCodes liest sie als shortName `unknown`; `ForecastGrib._name` (scripts/lib/forecast_grib.py:62) ersetzt das durch den Namen (unbekannte Nummer → `local<n>`). Die Nummern sind Vertrag mit dem Skill.

**Fehlende Werte:** `encode` (scripts/lib/derived_writer.py:48) schreibt NaN als Bitmap-Missing; `ForecastGrib._read` macht daraus wieder NaN. NaN entsteht bei `inv`/`rhbl`/`uf`/`vf` unter dem Modellboden, bei Höhenwerten außerhalb der Profil-Ebenen (Wind auf 3000 m überall dort, wo gh700 < 3000 m, weil u/v nur bis 700 hPa reichen) und bei `deg0l`/`snowl`, wo 500 hPa noch > 0 °C hat. `snowl` ist überall gesetzt, nicht nur bei `psig` (die Karte `snow_line` maskiert selbst).

`WEATHER_PARAMS` (`tcc`, `tp`, `ptype`; scripts/lib/constants.py:10) speisen nur `weather_summary`; die abgeleiteten Felder lassen sie aus, weil ein 9-km-Globalmodell Nebel, Hochnebel und deren Niederschlag falsch trifft (Kommentar dort). `tp` akkumuliert ab T+0 in m.

**Index** von `ForecastGrib` (scripts/lib/forecast_grib.py:19): Schlüssel `(Name, level, endStep)` → `(startStep, Byte-Offset)`, **ohne typeOfLevel**. Name = lokaler Name (Kategorie 192), sonst `aliases.get(shortName, shortName)`; `stepUnits` wird beim Indizieren auf Stunden gesetzt (ICON liefert seine statischen Felder als „0m“). Base-Time und Gitter stammen aus der ersten Nachricht; `grid` ist None, wenn deren `gridType` nicht `regular_ll` ist, Felder sind dann 1-D (eine Zahl je Zelle). `t` auf 850 hPa und `t` auf 2000 m unterscheiden sich nur über `level`. `field()`/`message()` mit `level=None` liefern den ersten Treffer in Dateireihenfolge (nur für Einzelebenen-Parameter sicher). Arrays sind float32 und **read-only** (über `lru_cache` geteilt, `CACHED_FIELDS` = 64 pro Instanz ≈ 250 MB, pro Prozess).

### Gitter und Koordinaten

`ForecastGrib.grid` (IFS) und `ClimateArchive.grid` teilen die Schlüssel `lat0, lon0 (−180…180), dlat, dlon, ni, nj` (Archiv zusätzlich flache Arrays `lat`, `lon`). `PixelGrid` rechnet `row = (lat0 − lat)/dlat`, `col = ((lon − lon0) % 360)/dlon`, setzt also reguläre Gitter mit Zeilen Nord → Süd voraus. Resampling bilinear (`map_coordinates` order 1, `mode="nearest"`: außerhalb des Quellgitters Randwert), optional Gauß-Glättung in km (zonal exakt bei `SMOOTH_REF_LAT` 50°); `nearest()` (order 0) für Codes (`ptype`); `wind_vectors` dreht u/v mit `projection.north_east()`.

### Freie Atmosphäre (Diagnostics)

Alle Diagnosen nutzen nur Druckflächen; eine Fläche zählt nur, wo ihr Geopotential mehr als `ABOVE_GROUND_MARGIN` = 20 gpm über dem Modellboden liegt (`above_ground`, scripts/lib/diagnostics.py:31), sonst NaN (`free`). Dieselben Klassen rechnen die abgeleiteten GRIB-Felder **und** die Karten (ChartProducts liest die abgeleiteten Felder nicht aus der Datei, sondern rechnet neu).

| Diagnose | Definition | Ort |
| --- | --- | --- |
| inversion (`inv`) | `fmax(t925 − t1000, t850 − t925)`, t1000/t925 per `free` maskiert; > 0 = Inversion | diagnostics.py:39 |
| moist_boundary_layer (`rhbl`) | `fmax(r925, r1000)`, beide maskiert | :51 |
| precipitation_signal (`psig`) | `max(r850, r700) ≥ PRECIP_RH` (90) und Gauß-geglättetes (σ 4 Gitterpunkte) `w700 < 0`; unmaskiert | :55 |
| freezing_level (`deg0l`) | `HeightProfile.freezing_level`: 0-°C-Durchgang von oben gesucht (Obergrenze einer Warmschicht über Kaltluftsee); ganz gefroren oder Durchgang unter Grund → Bodenhöhe; 500 hPa > 0 °C → NaN | height_profile.py:50 |
| snow_line (`snowl`) | `max(freezing_level − 350 m, ground)` | diagnostics.py:68 |

`HeightProfile(grib, step, height="gh", height_factor=1.0)` (scripts/lib/height_profile.py:20): Flächenhöhen aus dem Feld `height` × `height_factor` (IFS `gh` in gpm, ICON `z` × 1/g). `at_height` (:40) interpoliert linear in gpm zwischen den Nachbarflächen, die den Parameter **und** das Höhenfeld haben (`_stack`, :32); NaN außerhalb. `ChartProducts.profile(step)` (scripts/lib/chart_products.py:125) baut es für `mountain_2000` und `diagnostics()`. `mountain_2000` (:340) schraffiert `summit_cloud(profile, step, height)` (:361; Basis: RH in der Höhe + Legendennotiz) über `canvas.hatch(resample(…, smooth_km=10), SUMMIT_CLOUD_RH, …)`. IFS-Karten sind mit beiden Hooks pixelgleich (geprüft an 10 Produkten bzw. gegen Lauf 2026103100). `PRECIP_RH` und `SNOW_LINE_BELOW_FREEZING_M` stehen in chart_styles.py und wirken auf Karten und GRIB gleichzeitig.

### Tagesextreme

`EXTREME_WINDOWS` (scripts/lib/extreme_windows.py:8): Max 06–18 UTC des Tages, Min 18 UTC Vortag – 06 UTC (gilt auch für ICON, siehe *Tagesextreme (IconExtremes)*). `ExtremeWindows.parts` sammelt alle `mx2t3/mx2t6` (bzw. `mn…`)-Intervalle innerhalb des Fensters und akzeptiert sie nur, wenn ihre Längen exakt die Fensterlänge ergeben; sonst fehlt der Tag. Dieselbe Klasse dient `ForecastGrib` (vorhandene Datei) und `RequestPlan` (Zählung vor dem Download). Tage sind UTC-Kalendertage; der `endStep` der `mx2t`/`mn2t`-Nachricht liegt auf dem Tag selbst.

### Klimatologie

`ClimateArchive` (scripts/lib/climate_archive.py:45) indiziert **jedes** `<dir>/*.grb2`, egal wie die Felder auf Dateien verteilt sind; `PERIOD` = `1991–2020` (nur Beschriftung). Schlüssel `(kind, statistic, level, month, day)`, abgefragt mit `field(kind, statistic, level, month, day)`, `keys(kind)` liefert `(statistic, level, month, day)` einer Art (für `GribAnalyze` im Skill): kind `HHz` (Terminstunden aus den vorhandenen Nachrichten), `daily`, `monthly`; statistic `mean`/`std`; level 850 (T850) oder 2 (T2m); day None bei `monthly`; Werte in K. Der Index entsteht beim ersten Zugriff ohne ecCodes aus den Bytes jeder Nachricht (`_headers`, `_key`, scripts/lib/climate_archive.py:163-200): Sektion 1 Monat/Tag/Stunde der Referenzzeit (Jahr ignoriert), Template 4.8 erste Fläche (Typ 100 Pa → hPa, Typ 103 m), Anzahl Zeitbereiche (1 = Termin, 2 = `daily`, 3 = `monthly`) und statistischer Prozess des **äußersten** Bereichs (0 = Mittel, 6 = Streuung). Grund: ecCodes braucht für die 13 224 Kopfteile ≈ 4,8 s, die Bytes ≈ 0,09 s, und jeder Render-Worker baut sein eigenes Archiv (`init_worker`). Nicht über `shortName` unterscheiden: ecCodes nennt bei `daily`/`monthly` auch die Streuung `avg_t`/`avg_2t`. Der Byte-Index ist gegen den ecCodes-Index geprüft (gleiche Schlüssel und Offsets). Ein anderes Template als 4.8 oder ein Kopfteil über `HEADER_BYTES` (512) bricht mit `ValueError` ab. Felder werden bei Bedarf aus der Datei gelesen und dekodiert (Cache unbegrenzt). `T850Climate` braucht für **jede** Stunde der Gültigkeitszeiten ein `HHz`-Kind, sonst `ValueError` aus `term_kind`. Im Repo nutzt nur `t850_anomaly` die Klimatologie (`period` steht im Kartentitel).

### Kontaktabzüge und geometry.json

`ContactSheet` (scripts/lib/contact_sheet.py:26): 2 Spalten × 580 px (Skalierung 0,4833), Kachelhöhe 290, Kopf 26 px, darunter die Legende der ersten Karte ohne ihre ersten 26 px, 62 px hoch. Höhe = 26 + Zeilen × 290 + 62: IFS 10 Kacheln (00z-Lauf) → 1538 px, 11 Kacheln (12z-Lauf, T+0…T+240) → 1828 px; ICON-D2 8 Kacheln (`weather_summary`, T+1…T+48) → 1248 px, 9 Kacheln bei Produkten ab T+0, wenn die Laufstunde in `SHEET_HOURS` liegt (03/09/15/21z-Läufe) → 1538 px, `tmax`/`tmin` 1–2 Kacheln → 378 px. `STEP`-Produkte: Karten, deren Gültigkeitsstunde in `SHEET_HOURS` der Produktklasse liegt (IFS `(12,)`, ICON `(3, 9, 15, 21)`: 15 UTC für Nachmittagsgewitter, 03/09 für Nebel; Titel „<produkt>: 03/09/15/21 UTC of every day, run …“); `DAY`-Produkte: jeder Tag; `orography` keinen Abzug. Ein dreistündlicher ICON-Abzug (16 Kacheln, 2408 px) würde von Bildlesern der Modelle verkleinert (> 1568 px lange Kante). `origins(n)` liefert die Kachel-Ecken, die `write_geometry` unter `sheets.tiles.<produkt>` ablegt. `write_geometry` übernimmt Einträge anderer Produkte aus einer vorhandenen Datei, damit Einzelprodukt-Läufe ergänzen statt überschreiben.

## ICON-D2

### Quelle und Datei

DWD Open Data `https://opendata.dwd.de/weather/nwp/icon-d2/grib/<HH>/<ordner>/`, je Lauf, Parameter, Ebene und Step eine Datei `icon-d2_germany_icosahedral_<typ>_<YYYYMMDDHH>_<SSS>_<ebene>_<…>.grib2.bz2`, ohne Auth. `<ebene>` ist `2d` bei Einzelebenen-Feldern, `0` bei zeitunabhängigen, hPa auf Druckflächen, eine Zahl auf Modellflächen (Kommentar scripts/lib/icon_runs.py:17-18). Lauf alle 3 h (Ordner 00…21), stündlich bis T+48; jeder Stundenordner hält nur den neuesten Lauf dieser Stunde, insgesamt also ≈ 1 Tag. Felder bleiben auf dem Ikosaedergitter (542 040 Zellen, unstrukturiert; Randzone ohne Werte = Bitmap-Missing → NaN).

**Laufwahl** (`IconRuns`, scripts/lib/icon_runs.py:24): Die Zeitstempel der Stundenordner ändern sich nie, die der Parameterordner darin bei jedem neuen Lauf; deren Maximum ordnet die Stundenordner nach Alter (`_folder_time`, Fehler → `datetime.min`). Ein Ordner gilt als komplett, wenn alle Parameter-Listings genau einen Lauf zeigen (sonst wird er gerade überschrieben) und jeder Vorhersageparameter Step 48 hat (DWD schreibt die Steps in Reihenfolge, Kommentar :79). Sonst nimmt `latest` den nächstälteren Ordner. Parameter heißen wie die DWD-Ordner, auf Druckflächen `<ordner>@<hPa>` (`t@850`); `_split` (:88) liefert (Ordner, Ebenentoken), ohne `@` `0` für statische und `2d` für alle anderen. Jeder Ordner wird pro Stundenordner einmal gelistet (Ordner `u` dient `u@1000`, `u@850`, `u@700`), die Dateien nach dem Ebenentoken im Namen gefiltert. URL-Reihenfolge: statische Felder zuerst, dann nach (Step, Parameterreihenfolge).

**Laden** (`IconDownloader`, scripts/lib/icon_downloader.py:17): bz2 entpacken, nur Nachrichten auf vollen Stunden behalten (`endStep` in Minuten mit `m`-Suffix, durch 60 teilbar; `tot_prec`-Dateien enthalten zusätzlich die Summen zu :15/:30/:45, die `ForecastGrib` in Stunden nicht unterscheiden könnte). Rohdatei via `.part` geschrieben, eine vorhandene Rohdatei gilt als vollständig → Wiederaufnahme. Jede Datei liefert danach genau eine Nachricht; `download_icon_d2.py` prüft das als „Nachrichten = Dateien“.

| DWD-Parameter | shortName → Name im Index (`ICON_NAMES`, scripts/lib/constants.py:18) | Inhalt | Steps |
| --- | --- | --- | --- |
| clat, clon | tlat → `clat`, tlon → `clon` | Zellmittelpunkte (°) | 0 |
| hsurf | HSURF → `hsurf` | Modellorografie (m) | 0 |
| fr_land | `lsm` | Landanteil 0…1 | 0 |
| clct | CLCT → `tcc` | Gesamtbedeckung in **%** (IFS: 0…1) | 0…48 |
| tot_prec | `tp` | Niederschlag ab T+0 in **kg/m² = mm** (IFS: m) | 0…48 |
| pmsl | prmsl → `msl` | Bodendruck (Pa) | 0…48 |
| vmax_10m | max_i10fg → `gust` (level 10) | max. 10-m-Böe der letzten Stunde (m/s) | 0…48 |
| ww | WW → `ww` | signifikantes Wetter, WMO-Tabelle 4677 | 1…48 |
| t_2m | `2t` | 2-m-Temperatur (K) | 0…48 |
| tmax_2m, tmin_2m | max_2t → `tmax_2m`, min_2t → `tmin_2m` | 2-m-Extrem seit dem letzten 6-h-Neustart (K), siehe *Tagesextreme (IconExtremes)* | 0…48 |
| u_10m, v_10m | `10u`, `10v` | 10-m-Wind (m/s) | 0…48 |
| ceiling | ceil → `ceiling` | Wolkenuntergrenze: Basis der untersten Schicht mit > 50 % Bedeckung, m über NN (geprüft: immer ≥ hsurf + 10 m, auch über 2500 m Gelände); ≈ 20 km, wo es keine gibt | 0…48 |
| u@1000, v@1000 | `u`, `v` (level 1000) | Wind 1000 hPa für `t2m_wind1000` | 0…48 |
| t, relhum, fi, u, v @850 und @700 (`PROFILE_LEVELS`) | `t`, `r`, `z`, `u`, `v` | Profil für `mountain_2000`: K, %, Geopotential m²/s², m/s; ICON-D2 hat kein 925 hPa | 0…48 |

Summe 4 + 22 × 49 + 48 = **1130** Nachrichten (23 Vorhersageparameter, `FORECAST_PARAMS`, scripts/download_icon_d2.py:61-62; Modul-Docstring: ≈ 610 MB Download; gemessen 820 MB GRIB). Die Aliasse geben ICON-Feldern die Namen der IFS-Datei, damit die Zeichenmethoden von `ChartProducts` greifen; Einheiten unterscheiden sich trotzdem (siehe Tabelle) und werden in `IconProducts` behandelt.

### Pixelabbildung (TriangleGrid)

`TriangleGrid` (scripts/lib/triangle_grid.py:13) ersetzt `PixelGrid` für unstrukturierte Gitter: Zellen, die höchstens `MARGIN_PX` (20) außerhalb des Bildes liegen, werden im Pixelraum trianguliert (Delaunay); jedes Pixel bekommt die baryzentrischen Gewichte der drei Ecken seines Dreiecks, einmal pro Prozess berechnet. `covered` = Pixel liegt in einem Dreieck und alle drei Ecken sind `valid`; sonst NaN. `resample(values, smooth_km)` glättet mit einem Gauß im Pixelraum, normiert auf das Gewicht der abgedeckten Pixel (der Domänenrand zieht Werte nicht gegen 0); σ = smooth_km / km_per_px der Bildmitte (Pixelgröße schwankt im Fenster um < 2 %). `nearest` nimmt die Ecke mit dem größten Gewicht (für `ww`). `wind_vectors` wie PixelGrid.

### Produkte (IconProducts)

`IconProducts` (scripts/lib/icon_products.py:13) erbt von `ChartProducts` und wird mit `IconSurface` und `TriangleGrid` verdrahtet. `STEP` = `t2m_wind1000`, `wind10m`, `mountain_2000`, `weather_summary`; `DAY` = `tmax`, `tmin`; `STATIC` = `orography`; `CLIMATE` leer; `DEFAULTS = {"icon-d2": ALL}`; `MODEL` „ICON-D2“, `PRECIP_HOURS` 1, `SHEET_HOURS` (3, 9, 15, 21) (:30-40). `keys` kommt aus `ChartProducts`: Step-Produkte die `t`-Steps (T+0…T+48, hier aus 850/700 hPa), `weather_summary` die `tp`-Steps > 0, Tagesprodukte `extreme_days`. Mit `IconProducts.STEP` = 3 Produkten ab T+0 + `weather_summary` ergibt ein Lauf 3 × 49 + 48 Step-Karten, typisch 1 `tmax` und 2 `tmin`, dazu `orography` = 199 Karten und 6 Kontaktabzüge.

Die Zeichenmethoden sind die von `ChartProducts`; überschrieben werden nur Datenquellen (Hooks) und `draw`:

| Methode | Zeile | Abweichung von IFS |
| --- | --- | --- |
| `draw` | :42 | ruft die Produktmethode und danach `canvas.uncovered(self.pixels.covered, OUTSIDE_RGB, …)`: jede Karte grau außerhalb des Modellgebiets |
| `profile` | :47 | `HeightProfile(grib, step, "z", 1 / GRAVITY)`: Flächenhöhen aus dem Geopotential, nur 850/700 hPa (für `mountain_2000`) |
| `summit_cloud` | :50 | Wolke auf 2000 m (`mountain_2000`): RH in der Höhe nur dort, wo `ceiling` ≤ Höhe, sonst 0; Legende „hatched: in cloud at 2000 m (RH ≥ 95 %, cloud base ≤ 2000 m)“. Grund siehe unten |
| `extreme_days`, `daily_extreme_field` | :62, :65 | `IconExtremes` statt `ForecastGrib.extreme_days`/`daily_extreme` |
| `weather_summary` | :68 | zusätzlich `WW_SYMBOLS` (95 Gewitter = Blitz, 96 Gewitter mit Hagel = Dreieck, 45/48 Nebel = drei Striche) auf Raster 20 px, **ohne** Kopplung an Niederschlag; Böen ≥ `STORM_GUST_KMH` (75 km/h, Bft 9 = „Sturmböen“ der DWD-Warnungen) als Zahlen in km/h auf Raster 60 px |
| `cloud_cover` | :79 | tcc direkt in %, NaN → 0 |
| `precipitation` | :83 | tp-Differenz der letzten Stunde ohne ×1000 |
| `precipitation_type` | :88 | ww per `nearest`, über `WW_PTYPE` in IFS-ptype-Codes übersetzt (5 Schnee, 7 Schneeregen, 3 gefrierender Regen/Niesel, 8 Eiskörner, alles andere 0) — dieselben Symbole und Legende wie IFS |

**Warum `summit_cloud` die Wolkenuntergrenze braucht:** Die RH auf 2000 m ist linear über die ≈ 1500 m zwischen 850 und 700 hPa interpoliert und meldet Wolke auch dort, wo die Basis höher liegt; `ceiling` ist die modelleigene Basis, darunter kann die Höhe nicht in Wolken liegen (Docstring :51-57). ICONs Schichtbedeckungen `clcl`/`clcm` helfen nicht: ihre Grenze bei 800 hPa liegt nahe 2000 m, und Nebel/Hochnebel (`clcl` 100 %) lässt die Gipfel frei. Die 3-D-Bedeckung `clc` gibt es nur auf Modellflächen (zu teuer zum Laden).

`t2m_wind1000` (2t, u/v 1000 hPa), `wind10m` (10u/10v, msl) und `orography` laufen unverändert; `orography` ohne Schraffur, weil `IconSurface.sdor` None ist (`ChartProducts.orography` prüft das). Andere `ChartProducts`-Produkte brauchen Felder, die die ICON-Datei nicht hat (gh, 925 hPa, w, ptype …), und stehen nicht in `IconProducts.ALL`. `ChartProducts.detail` ist für `icon-d2` wahr (`km_per_px(50)` kleiner als Europa): dichtere Isobaren außer in `weather_summary`/`wind10m` (fest `MSLP_SUMMARY`) und gedruckte Werte.

### Tagesextreme (IconExtremes)

`IconExtremes` (scripts/lib/icon_extremes.py:17) liefert `tmax`/`tmin` in denselben Fenstern wie IFS (`EXTREME_WINDOWS`: Max 06–18 UTC, Min 18–06 UTC; `ExtremeWindows.window`, scripts/lib/extreme_windows.py:40). ICONs `max_2t`/`min_2t` starten alle `RESTART_HOURS` = 6 h ab Laufbeginn neu, obwohl der GRIB-Kopf `stepRange 0-N` angibt (Kommentar :10-12; geprüft an Daten: die Werte fallen nach jedem 6. Step und entsprechen dem Extrem der stündlichen `2t` seit dem Neustart). `field(kind, day)` (:40) reduziert für jeden Step im Fenster `(start, end]` mit `fmax`/`fmin`: `tmax_2m`/`tmin_2m`, wenn der letzte Neustart vor dem Step (`_restart`, :53) ≥ Fensterbeginn liegt, sonst die stündliche `2t`. Bei 00/06/12/18z-Läufen fallen Neustarts auf die Fenstergrenzen (exakt); bei 03/09/15/21z-Läufen decken die ersten 3 h im Fenster stündliche Werte ab, die Spitzen zwischen vollen Stunden verpassen (Morgen beim Maximum, Abend beim Minimum; Docstring). `days(kind)` (:33) nimmt jeden UTC-Tag, dessen Fenster ganz in `0…letzter 2t-Step` liegt; typisch 1 Maximum und 2 Minima je Lauf. `IconExtremes` wird bei jedem Aufruf neu gebaut (kein Cache außer dem von `ForecastGrib`).

### Grenzen und Gradnetz (BaseMap)

`BaseMap` (scripts/lib/base_map.py:14) liest `projection.borders`. Features mit `properties.LEVEL == "state"` werden `state_rings` (in `ChartCanvas.outlines`, scripts/lib/chart_canvas.py:114, gestrichelt `#303030`, 0,4 px, unter den Ländergrenzen), alle anderen `rings` (Küsten/Grenzen 0,6 px schwarz, Landflächen). Ringe ohne Punkt ≤ `MARGIN_PX` vom Bild fallen weg. Gradnetzbeschriftung entlang `projection.label_lon` (Breiten) und `label_lat` (Längen).

`borders_austria.geojson` baut `build_borders.py` einmalig: BEV VGD 1:50 000 (Katastralgemeinden in MGI/Austria Lambert, EPSG:31287) zu Bundesländern vereinigt, Splitter < 0,5 km² entfernt, als Coverage vereinfacht (`coverage_simplify`, 150 m ≈ 0,2 px, gemeinsame Grenzen bleiben deckungsgleich), nach WGS84; Länder aus world_countries.geojson, soweit sie in `KEEP_BOX` (= Zuschnittbox des Europafensters, 71° W–77° E, 11–76° N) reichen; die Nachbarn Österreichs entlang der genauen Grenze zugeschnitten und die Lücken zwischen beiden Österreich-Umrissen dem Nachbarn mit der längsten gemeinsamen Kante zugeschlagen; das Esri-Österreich durch das BEV-Österreich ersetzt. Eigenschaften `COUNTRY`, `ISO`, `LEVEL` (`country`/`state`), bei Bundesländern zusätzlich `NAME`; Koordinaten auf 5 Nachkommastellen (≈ 1 m).

### Testszene (make_icon_test_grib.py)

Gewitter, Hagel, Nebel und Sturmböen sind selten und DWD hält nur ≈ 1 Tag Läufe vor; das Skript kopiert eine ICON-Datei und setzt ab `--step` eine Szene ein: Gewitterlinie westlich von München (ww 95, 8–25 mm/h, bedeckt, Böen 90–125 km/h im 1,5-fachen Radius), Hagelkern an deren Ostende (ww 96, 45 mm/h), Nebel bei Linz und im Wiener Becken (ww 45, bedeckt). Niederschlag wird zu `tp` ab `--step` und allen späteren Steps addiert (Akkumulation bleibt monoton), tcc/ww/gust nur in `--step`; Randzonenzellen behalten ihren Missing-Wert. Die Ausgabe ist eine normale Eingabe für render_charts.py und hat mit der Vorhersage nichts zu tun.

## Konstanten-Referenz

### App

| Konstante | Ort | Wert / Bedeutung |
| --- | --- | --- |
| `IMAGE_WIDTH`, `IMAGE_HEIGHT`, `MAP_HEIGHT` | src/model/ChartProjection.ts:4-6 | 1200, 690, 600 — Kartenbild (Karte + 90 px Legende) |
| `aspect-ratio: 1200 / 690` | src/components/ChartImage.module.css:4 | **muss zu `IMAGE_WIDTH`/`IMAGE_HEIGHT` passen**, hält die Kachelhöhe stabil, solange noch kein Video da ist |
| `.chart { width: 1200px }` | src/components/LargeView.module.css:39 | Großansicht 1:1 |
| `MAX_STEP` | src/components/StepSlider.tsx:3 | 240 — Reichweite der 00z/12z-Läufe; Tagesmarken alle 24 h |
| `DEFAULT_LOCATION` | src/model/GeoLocation.ts:7 | 48 °N, 16,4 °E |
| `STORAGE_KEY` | src/hooks/useStoredLocation.ts:4 | `wetterkartenviewer.location` |
| `EPSGRAM_API` | src/services/ecmwfMeteogram.ts:3 | `https://charts.ecmwf.int/opencharts-api/v1/features/epsgrams/` |
| `ATTEMPTS`, `RETRY_MS` | src/services/ecmwfMeteogram.ts:4-5 | 5 Versuche, 3000 ms Pause |
| Kachelbreite | src/components/ChartTile.module.css:4-6 | drei pro Zeile, min 480 px, max 1200 px |
| Meteogrammbreite | src/components/Meteogram.module.css:3-5 | drei pro Zeile, min 420 px |
| Hash-Route | src/hooks/useHashRoute.ts:6 | nur `#/maps` ist die Kartenseite |

### Steuerung und Download

| Konstante | Ort | Wert / Bedeutung |
| --- | --- | --- |
| `WINDOWS` | scripts/update_maps.py:52 | IFS-Fenster: `opencharts_europe` → `"all"`, `opencharts_central_europe` → None (Defaults) |
| `ICON_WINDOWS` | scripts/update_maps.py:53 | ICON-Fenster: `icon-d2` → None (Defaults); entscheidet auch, welche Layer `encode_missing` ohne Karten nur warnt |
| `ECMWF_PREFIX`, `ICON_PREFIX` | scripts/update_maps.py:54 | `ecmwf_`, `icon-d2_`: Dateipräfix der Läufe; `remove_old_runs` löscht `<präfix>*.grb2*` |
| `CHARTS_DOC` | scripts/update_maps.py:50 | data/charts.md im Repo |
| `PARALLEL_ENCODES` | scripts/update_maps.py:56 | 3 ffmpeg-Prozesse gleichzeitig; libaom nutzt je mehrere Threads |
| `CONFIG`, `MANIFEST` | scripts/maps_manifest.py:28-29 | Pfad der Viewer-Config, `manifest.json` |
| `FPS` | scripts/maps_manifest.py:31 | 10; Bildrate beim Kodieren und `fps` im Manifest |
| `HOURS_PER_DAY` | scripts/maps_manifest.py:32 | 24; `end` einer Tageskarte = ihr Step + 23 |
| `WIDTH`, `HEIGHT` | scripts/tile_videos.py:21 | 1200, 690 — **müssen der Kartengröße entsprechen**; ffmpeg zerlegt den Bytestrom nur nach dieser Angabe |
| `KEYFRAME_INTERVAL`, `CODEC`, `COLOUR` | scripts/tile_videos.py:22-28 | siehe Tile-Videos |
| `TAG` | scripts/maps_release.py:10 | `tile-videos`, Tag und Name des Releases mit den Videos; Asset-Name = Videopfad mit `/` → `.` (`asset_name`) |
| `TIMEOUT_S` | scripts/fetch_maps.py:21 | 60 s je Download |
| `STEPS`, `PARALLEL_REQUESTS` | scripts/download_ecmwf_data.py:75-76 | Step-Liste (s. o.); 4 Gruppen gleichzeitig |
| `MAX_STEP` | scripts/lib/open_data_runs.py:9 | 240; `latest()` fragt nach Step 240 von t850, das schließt 06z/18z aus (enden bei +144) |
| `LISTING_URL`, `RUN_INTERVAL` | scripts/lib/open_data_runs.py:12-13 | `https://data.ecmwf.int/forecasts/{YYYYMMDD}/{HH}z/ifs/`; Zeitstempel des `0p1/`-Ordners + 12 h = erwartete Ankunft des nächsten Laufs |
| `PROFILE_LEVELS` | scripts/lib/constants.py:14 | 500…1000 hPa für t, r, gh und das Höhenprofil; 600 hPa halbiert die Lücke über 700 hPa. Die u/v-Ebenen stehen getrennt in den Gruppen `uvw700`/`uv_low` (scripts/lib/request_plan.py:28-29) |
| `RETRIES`, `RETRY_DELAY` | scripts/lib/group_downloader.py:12-13 | 3 Versuche, 30 s × Versuchsnummer |
| `BOX_MARGIN_DEG` | scripts/lib/grib_cropper.py:10 | 1° Rand für Glättung und Interpolation bis zum Bildrand |
| `THICKNESS_PARAM` | scripts/lib/forecast_writer.py:19 | 0/3/12 (Schichtdicke, gpm); Flächen Typ 100 bei 100000/50000 Pa |
| `INDICATOR_LENGTH` | scripts/lib/forecast_writer.py:21 | 16 Byte GRIB2-Section 0; Länge der Nachricht in Byte 8–15 (big endian). Rohdateien müssen lückenlos aufeinanderfolgende GRIB2-Nachrichten sein, sonst `ValueError` |
| `CHUNK_SIZE` | scripts/lib/forecast_writer.py:23 | 8 Nachrichten je Pool-Aufgabe |
| `MAX_WORKERS` | scripts/lib/forecast_writer.py:26 | 8; gemessen 15,8 ms/Nachricht mit 8, 14,3 mit 20 Workern, 79,5 mit einem — darüber begrenzt der schreibende Hauptprozess |
| `CACHED_FIELDS` | scripts/lib/forecast_grib.py:16 | 64 Felder ≈ 250 MB pro `ForecastGrib` (IFS), pro Prozess |
| `PROFILE_LEVELS` (ICON) | scripts/download_icon_d2.py:60 | (850, 700): umschließen 2000 m (`mountain_2000`) überall; ICON-D2 hat kein 925 hPa. Getrennt von `constants.PROFILE_LEVELS` |
| `FORECAST_PARAMS`, `STATIC_PARAMS` | scripts/download_icon_d2.py:61-63 | 23 ICON-Parameter (Ordnername, auf Druckflächen `<ordner>@<hPa>`): `clct`, `tot_prec`, `pmsl`, `ww`, `vmax_10m`, `t_2m`, `tmax_2m`, `tmin_2m`, `u_10m`, `v_10m`, `ceiling`, `u@1000`, `v@1000`, je `t`/`relhum`/`fi`/`u`/`v` @850 und @700; statisch `clat`, `clon`, `hsurf`, `fr_land` |
| `PARALLEL_REQUESTS`, `PREFIX` | scripts/download_icon_d2.py:64-65 | 8 Downloads gleichzeitig; `icon-d2_` |
| `BASE_URL`, `RUN_HOURS`, `MAX_STEP`, `TIMEOUT_S` | scripts/lib/icon_runs.py:10-14 | DWD-Basis-URL; `00`…`21` alle 3 h; 48 (Lauf komplett, wenn jeder Vorhersageparameter Step 48 hat); 30 s je Listing |
| `FOLDER`, `FILE` | scripts/lib/icon_runs.py:16-19 | Regex auf das nginx-Listing (Ordnername + Zeitstempel `%d-%b-%Y %H:%M:%S`) bzw. auf `…_icosahedral_…_<run>_<step>_<ebene>_….grib2.bz2` (Gruppen: Name, Lauf, Step, Ebenentoken). Ändert DWD das Listing-Format, findet `latest` keinen Lauf |
| `SINGLE_LEVEL`, `TIME_INVARIANT` | scripts/lib/icon_runs.py:21 | `2d`, `0`: Ebenentoken eines Parameters ohne `@` (Vorhersage- bzw. statischer Parameter) |
| `RETRIES`, `RETRY_DELAY`, `TIMEOUT_S` | scripts/lib/icon_downloader.py:12-14 | 3 Versuche, 10 s × Versuchsnummer, 60 s je Datei |

### Abgeleitete Felder und Diagnosen

| Konstante | Ort | Wert / Bedeutung |
| --- | --- | --- |
| `MOUNTAIN_HEIGHTS` | scripts/lib/derived_writer.py:30 | 2000, 2500, 3000 m (heightAboveSea) |
| `PROFILE_PARAMS`, `FREE_LEVELS`, `SURFACE_FIELDS` | :31-33 | t/r/u/v; 1000/925 hPa für uf/vf; inv/rhbl/psig/snowl |
| `PER_STEP` | :35 | 21 Nachrichten je Step; **importiert von `RequestPlan`** für `expected_total` |
| `PARAM_IDS` | :37 | deg0l 228024, orog 228002, max 201, min 202 |
| `SURFACE` | :39 | Ebene Boden (Code-Tabelle 4.5: 1) |
| `MAX_WORKERS` | :41 | 8 Prozesse (je bis ~250 MB Cache) |
| `LOCAL_CATEGORY` | scripts/lib/local_params.py:10 | 192 |
| `EXTREME_WINDOWS`, `EXTREME_PARAMS` | scripts/lib/extreme_windows.py:8-9 | siehe Tagesextreme |
| `RESTART_HOURS`, `FIELDS` | scripts/lib/icon_extremes.py:13-14 | 6 h Neustartintervall von ICONs `max_2t`/`min_2t` (an Daten bestimmt, nicht aus dem GRIB-Kopf); Indexnamen `tmax_2m`/`tmin_2m` |
| `ABOVE_GROUND_MARGIN`, `OMEGA_SIGMA` | scripts/lib/diagnostics.py:19-21 | 20 gpm; 4 Gitterpunkte Glättung von w700 (verrauscht über Gebirge) |

### Karten

| Konstante | Ort | Wert / Bedeutung |
| --- | --- | --- |
| `STEP`, `DAY`, `STATIC`, `ALL`, `CLIMATE` | scripts/lib/chart_products.py:41-46 | Produktregister; `ALL` = alle drei Gruppen. `IconProducts` (scripts/lib/icon_products.py:30-34) überschreibt alle |
| `MODEL`, `PRECIP_HOURS`, `SHEET_HOURS` | scripts/lib/chart_products.py:47-51 | Klassenattribute: Modellname in Legende und `geometry.json` (`ECMWF IFS`); Niederschlagsintervall von `weather_summary` 6 h (3 h bei T+3); Gültigkeitsstunden im Kontaktabzug `(12,)`. ICON: `ICON-D2`, 1 h, `(3, 9, 15, 21)` (scripts/lib/icon_products.py:35-39) |
| `DEFAULTS` | scripts/lib/chart_products.py:52-59 | Europa: `z500_t850`, `z700_t700`, `z850_rh700`, `thickness_mslp`, `dt850_24h`; Mitteleuropa: `t850_mslp`, `t850_anomaly`, `rh700_wind700`, `vt_rh700`, `t2m_wind1000`, `wind10m`, `inversion`, `mountain_2000`, `freezing_level`, `snow_line`, `tmax`, `tmin`, `orography`, `weather_summary`. Kein Eintrag für `icon-d2`; der steht in `IconProducts.DEFAULTS` (scripts/lib/icon_products.py:40) |
| `CHANGE_HOURS`, `TCC_PERCENT` | scripts/lib/chart_products.py:22-24 | 24 h für `dt850_24h`; tcc 0–1 → % |
| `EARTH_RADIUS_KM` | scripts/lib/projection.py:34 | 6371 km, Kugel für `lambert` und `km_per_px` |
| `WORLD_COUNTRIES`, `AUSTRIA_BORDERS` | scripts/lib/projection.py:35-36 | GeoJSON-Pfade; Default von `Projection.borders` ist `WORLD_COUNTRIES` |
| `MARGIN_PX` | scripts/lib/triangle_grid.py:10 | 20 px: Zellen so weit außerhalb des Bildes werden mittrianguliert, damit Randpixel in einem Dreieck liegen |
| `LEGEND_HEIGHT` | scripts/lib/chart_canvas.py:31 | 90 px unter 1200×600 → Bilder 1200×690 |
| `BAR`, `NOTES_X` | scripts/lib/chart_canvas.py:33-34 | Farbskala (8, 760); Notizspalte ab x 800, eine Notiz pro 13-px-Zeile |
| `WEBP_QUALITY` | scripts/lib/chart_canvas.py:37 | 90, nur für Kontaktabzüge; Einzelkarten verlustfrei |
| `EXTREMA_BORDER_PX` | scripts/lib/chart_canvas.py:41 | kein L/H näher als 20 px am Rand |
| `STREAMLINE_GRID_PX` | scripts/lib/chart_canvas.py:43 | `streamlines` integriert auf jedem 4. Pixel (300 × 150 Punkte) |
| `WIND10M` | scripts/lib/chart_styles.py:184 | km/h, Bandgrenzen = Beaufortgrenzen 6/12/20/29/39/50/62/75/89/103/118 km/h |
| `STREAMLINE_SMOOTH_KM`, `STREAMLINE_DENSITY` | scripts/lib/chart_styles.py:190-192 | 15 km Glättung von u/v nur für die Stromlinien (die Farben bleiben ungeglättet); `density` 3 von `streamplot`. Beides nach Augenmaß gewählt |
| `COLUMNS`, `TILE_WIDTH` | scripts/lib/contact_sheet.py:19-20 | 2 × 580 px, damit 10 Kacheln unter 1568 px Höhe bleiben (darüber verkleinern Modelle Bilder) |
| `LEGEND_SKIP` | scripts/lib/contact_sheet.py:23 | erste 26 px der Legende (Gültigkeitszeit) nicht übernommen |
| `MARGIN_PX` | scripts/lib/base_map.py:11 | Ringe bleiben, wenn ein Punkt ≤ 50 px vom Bild entfernt liegt |
| `SIMPLIFY_M`, `MIN_PART_KM2`, `KEEP_BOX`, `DECIMALS`, `SOURCE_CRS` | scripts/build_borders.py:39-48 | 150 m = 0,2 px bei 0,75 km/px; Splitter < 0,5 km²; Box der behaltenen Länder; 5 Nachkommastellen; EPSG:31287 |
| `CELLS`, `FOG`, `KM_PER_DEG` | scripts/make_icon_test_grib.py:35-39 | Testszene (lat, lon, Radius km, ww, mm, Böe m/s) bzw. Nebelscheiben; 111,2 km/° |

Literale in den Produktmethoden, alle empirisch bestimmt (laut User): Z500- und Z700-Zentren (scripts/lib/chart_products.py:171, :183) L-Fenster 121 px, H-Fenster 181 px, `min_depth` 2 dam, 60 km Vorglättung; MSLP-Zentren (`isobars`, :234) 81/161 px, 2 hPa, 60 km; Pfeile `rh700_wind700` (:268) Raster 30 px, 1,2 px pro m/s, Referenz 20 m/s; `t2m_wind1000` (:302) 30 px, 2,5 px pro m/s, 10 m/s; `mountain_2000` (:355-356) 30 px, 1,5 px pro m/s, 20 m/s. Die Z850-Zentren von `z850_rh700` (:201) verwenden dieselben Literale wie Z500.

### chart_styles.py (Schwellen; Begründungen aus den Code-Kommentaren)

| Konstante | Zeile | Wert / Bedeutung |
| --- | --- | --- |
| `T850`, `T700`, `THICKNESS`, `RH700` | 17, 31, 56, 69 | aus den ECMWF-Opencharts-Legenden kopiert (medium-z500-t850, medium-t-z 700, medium-thickness-mslp, medium-uv-rh) |
| `T2M`, `MOUNTAIN_T` | 53, 238 | Bänder von T850: eine Farbe = eine Temperatur auf allen Karten |
| `T850_ANOMALY` | 47 | σ-Bänder; ≥ 1 auffällig, ≥ 2 ungewöhnlich |
| `ROUGH_TERRAIN_SDOR` | 118 | 200 m sdor: echte Tal-/Gipfelhöhen weichen um mehrere 100 m ab |
| `HIGH_GROUND_M`, `ABOVE_1000HPA_M`, `ABOVE_850HPA_M` | 121-123 | 700 / 500 / 1300 m Modellhöhe: Inversionskarte grau, keine 1000-hPa-Pfeile, T850-basierte Flächen maskiert bzw. gestrichelte Linie in `t850_mslp`/`z850_rh700` |
| `PRECIPITATION`, `CLOUD_COVER` | 136, 141 | nach den ogimet-Bodenkarten; ungefärbt unter 0,2 mm / 40 % (Titel „6 h“ ersetzt `weather_summary` per `replace` durch das tatsächliche Intervall) |
| `PRECIP_TYPES` | 150 | ptype 5 Schnee; 6/7 nasser Schnee, Schneeregen; 3/8/12 gefrierender Regen/Niesel, Eiskörner; Regen (1) ohne Symbol |
| `PRECIP_BAR`, `CLOUD_BAR` | 158-159 | zwei Farbskalen nebeneinander (links, Breite px) |
| `OUTSIDE_RGB` | 162 | (190, 190, 190): Pixel außerhalb eines Ausschnittsmodells |
| `WW_PTYPE` | 167 | ww (WMO 4677) → IFS-ptype: 5 ← 70–75, 77, 85, 86; 7 ← 68, 69, 83, 84; 3 ← 56, 57, 66, 67; 8 ← 79; Regen/Niesel ohne Code |
| `LIGHTNING`, `FOG_LINES`, `WW_SYMBOLS`, `WW_SYMBOL_SPACING_PX` | 169-177 | Blitz-Vertices (gelb, Rand dunkelrot), Nebel-`Path` (drei Striche, Halo); ww 95 Gewitter, 96 Gewitter mit Hagel (weißes Dreieck), 45/48 Nebel; Raster 20 px |
| `STORM_GUST_KMH`, `GUST_SPACING_PX` | 179-180 | 75 km/h (Bft 9, „Sturmböen“ der DWD-Warnungen); Raster 60 px |
| `Z500`, `Z700`, `Z850`, `MSLP`, `MSLP_DETAIL`, `MSLP_SUMMARY` | 195-204 | 4 dam (fett 528/552/576); 5 dam (fett 270/290/310); 4 dam (fett 140/152/164); 5 hPa Europa; 2 hPa Detailfenster (schwache Gradienten entscheiden Inversion/Föhn); 4 hPa `weather_summary` |
| `ISOTHERM_850` | 206 | 4-K-Isothermen an den Bandgrenzen, für `z500_t850` und `z700_t700` |
| `MOIST_LAYER_RH`, `WIND925_CALM` | 214, 216 | 90 % Nebel-/Hochnebelschicht; 5 m/s, darunter wird eine Inversion kaum ausgeräumt |
| `ASCENT_LINES`, `SUBSIDENCE_LINES` | 221-222 | ω700 −0,6/−0,2 und +0,2 Pa/s |
| `PRECIP_RH` | 228 | 90 %, Niederschlagssignal (auch Diagnostics/`psig`) |
| `SNOW_LINE_BELOW_FREEZING_M` | 231 | 350 m Schmelzstrecke (300–400 m) (auch `snowl`) |
| `MOUNTAIN_HEIGHT_M`, `SUMMIT_CLOUD_RH` | 235-236 | 2000 m Kartenhöhe (getrennt von `MOUNTAIN_HEIGHTS` definiert), 95 % = in Wolken |
| `VALUE_SPACING_PX` | 240 | 80 px (~250 km bei Mitteleuropa) Raster gedruckter Werte, nur Detailfenster |

## Externe Systeme

**ECMWF Opencharts epsgrams** (`fetchMeteogramUrl`, src/services/ecmwfMeteogram.ts:28): `POST` ohne Auth, `mode: 'cors'`, Body `{"location":{"type":"latlon","lat":…,"lon":…,"station_name":""},"axis":{},"epsgrams":"<name>"}`. Antwort `result.url` ist die Bild-URL; das Bild existiert erst nach diesem Request. Fehlt `result`, wird nach 3 s bis zu 5-mal wiederholt. Gültige Namen in `viewer.config.json`: `classical_10d`, `classical_15d_with_climate`, `classical_plume`.

**ECMWF Open Data** über `ecmwf.opendata.Client(source="ecmwf", resol="0p1" | "0p25")`: `latest(type="fc", stream="oper", step=240, param="t", levelist=850)` findet den Lauf; `retrieve(date, time, type="fc", stream="oper", target, **gruppe)` lädt eine Gruppe (Byte-Ranges). Ohne Auth. HTTP 404 → „not (or no longer) published“. Die Fortschrittsbalken der Bibliothek lassen sich nicht abschalten, daher die stderr-Umleitung.

**data.ecmwf.int Verzeichnislisting** (`requests.get`, Timeout 30 s) nur für den Ankunftshinweis; jeder Fehler → kein Hinweis.

**DWD Open Data** (`opendata.dwd.de/weather/nwp/icon-d2/grib/`, ohne Auth): nginx-Verzeichnislistings (Timeout 30 s; ein Lauf kostet ohne `--run` 8 Listings der Stundenordner + je geprüftem Stundenordner 20 Ordner-Listings), dann 1130 bz2-Dateien mit `requests.get` (Timeout 60 s, 3 Versuche). Fehler beim Ordner-Zeitstempel → Ordner zählt als ältester; HTTP-Fehler eines Parameter-Listings → `HTTPError` ungefangen.

**GitHub-Release-Assets** (`gh release view tile-videos --json assets`): `name`, `size`, `updatedAt` (ISO mit Zeitzone) entscheiden in `changed_videos`, ob ein Video hochgeladen wird; kein Hash-Vergleich.

**git / GitHub**: Remote `origin` = github.com/schletz/wetterkartenviewer, Branch `main`. Der Branch `legacy` enthält die alte App, dient nur als Archiv und hat für diese App keine Bedeutung (laut User). Der Workflow läuft bei Push auf `main` und manuell, `concurrency: pages` mit `cancel-in-progress`. Node 24 in CI.

Rendern, Kodieren, Manifest und App-Build sind offline. ffmpeg ist ein externer Prozess (`ffmpeg` im PATH), Fortschritt unterdrückt (`-loglevel error`); stderr wird erst nach dem letzten Frame gelesen.

## Details

- **Kartendateien** heißen nach Gültigkeitszeit (UTC), Tagesprodukte nach UTC-Datum; `orography.webp` liegt direkt im Fensterordner, kein Produktordner. `weather_summary`-Keys sind die `tp`-Steps > 0; Niederschlag = `tp(step) − tp(step − min(PRECIP_HOURS, step))`, bei 0 geklemmt, in mm (IFS ×1000 aus m, ICON direkt); ptype-Symbole nur, wo ptype passt und ≥ 0,2 mm fallen (ICON-ww-Symbole und Böen unabhängig davon). `dt850_24h`-Keys sind Steps mit vorhandenem `step − 24`. `tmax`/`tmin`-Keys liefert `extreme_days` (IFS: vollständige `mx2t`/`mn2t`-Abdeckung, ICON: Fenster ganz im Lauf).
- **Detailmodus** `ChartProducts.detail` (scripts/lib/chart_products.py:77) = `km_per_px(50)` kleiner als beim Europafenster (Mitteleuropa und `icon-d2`): dichtere Isobaren und gedruckte Werte (`print_values`, standardmäßig nur über Land).
- **Legendenzeile** „<MODEL> run DD.MM.YYYY HH UTC“ (`_run`, scripts/lib/chart_products.py:144).
- **Isothermen/Isobaren** werden vor dem Konturieren in km geglättet (`ContourStyle.smooth_km`); L/H-Zentren haben eigene 60-km-Glättung und Fenstergrößen.
- **Einzelkarten** verlustfreies WebP (`ChartCanvas.save`), Kontaktabzüge Qualität 90.
- **Windows:** Prozesspools nutzen spawn; Worker-Zustand entsteht in `init_worker` (Modulglobale `_products` in render_charts.py, `_grib`/`_surface` in derived_writer.py).
- UI-Texte der App sind deutsch, Kartentexte, Meldungen, Code und Kommentare englisch; data/charts.md ist deutsch.

## Fehlerbehandlung

| Situation | Verhalten |
| --- | --- |
| Manifest fehlt / HTTP-Fehler (App) | `MapViewer` zeigt die Fehlermeldung als Text, kein Retry |
| Layer ohne Eintrag im Manifest (kein Video) | Platzhalter „keine Karten in diesem Lauf“ |
| Slider vor erstem Step eines Produkts | Platzhalter „ab +N h“ |
| Slider nach `end` eines Produkts (ICON-D2 nach +48 h seines Laufs) | Platzhalter „bis +N h“ |
| Video nicht ladbar (HTTP-Fehler, Netz) | `loadVideo` resolved mit `null`; Platzhalter „<pfad> konnte nicht geladen werden“. Ergebnis bleibt pro URL gecacht, erst neuer Run (`?run=`) oder Reload lädt neu |
| Video geladen, aber nicht dekodierbar (z. B. Browser ohne AV1) | `onError` des `<video>` → Platzhalter „<pfad> konnte nicht geladen werden“ (src/components/ChartImage.tsx:63) |
| Meteogramm HTTP-Fehler / kein `result` nach 5 Versuchen | Fehlertext und Button „Erneut laden“ (erhöht `attempt`) |
| Ortswechsel während Meteogramm-Request | `AbortController`; veraltete Antworten über den `request`-Schlüssel verworfen |
| localStorage gesperrt oder kaputt | Default-Ort; Schreiben scheitert still |
| Ungültige Ortseingabe | Button deaktiviert (`isValidLocation`, leere Felder) |
| Lauf nicht publiziert (404) | `RuntimeError` → stderr, Exit 1; `.raw/` bleibt |
| Anderer Download-Fehler (Netz, Index) | 3 Versuche, dann propagiert die Originalausnahme aus `future.result()` → **Traceback** (nur `RuntimeError` wird gefangen) |
| Gruppe mit falscher Nachrichtenzahl | `RuntimeError`, Exit 1 |
| Abgebrochener Download | erneuter Aufruf: vollständige Rohgruppen werden übersprungen, andere neu geladen |
| gh500/gh1000 unvollständig, Fehler in `DerivedWriter` | ungefangen → Traceback; `<out>.part` und `.raw/` bleiben |
| `pending_notice` / Listing scheitert | still kein Hinweis |
| ECMWF-Download scheitert (in update_maps) | Meldung `<skript> failed with exit code N` auf stderr, dann `sys.exit("ECMWF download failed")`, vor jedem Löschen |
| ICON-Download scheitert (kein kompletter Lauf, `--icon-run` zu alt, Netz) | Warnung, `update_maps` läuft weiter: ICON-Fenster wird weder gerendert noch in `maps/` geleert, altes ICON-GRIB bleibt; das Manifest übernimmt das vorhandene Video mit neu berechneten Steps |
| ICON-Layer ohne Video und ohne Karten (erster ICON-Download gescheitert) | `encode_missing` warnt und überspringt ihn; Layer fehlt im Manifest → App „keine Karten in diesem Lauf“; nächster Aufruf rendert ICON (kein Lauf im Manifest) |
| ICON: Parameter-Listing HTTP-Fehler | `HTTPError` aus `IconRuns._files` → Traceback, Exit 1 (in update_maps: Warnung) |
| ICON: Datei nach 3 Versuchen nicht ladbar | Originalausnahme über `pool.map` → Traceback; fertige Rohdateien in `<out>.raw/` bleiben, Wiederholung lädt nur den Rest |
| ICON: Nachrichtenzahl ≠ Dateizahl nach `join` | stderr, Exit 1; `<out>.part` und `.raw/` bleiben |
| ICON: Ordner wird gerade geschrieben (zwei Läufe gemischt oder Step 48 fehlt) | Ordner gilt als unvollständig, `latest` nimmt den nächstälteren; `--run` → `RuntimeError` |
| Rendern eines Fensters scheitert | `sys.exit` mit stdout/stderr des Renderers; `maps/manifest.json` fehlt danach, bei neuem Lauf ist `maps/<fenster>/` des Modells schon geleert |
| Kachel-Pfad, dessen Produkt das Fenster nicht rendert (z. B. Nicht-Default-Produkt auf Mitteleuropa) | `stale_windows` rendert das Fenster bei jedem Aufruf neu (der Pfad hat nie Karten), danach beendet `encode_missing` mit `no charts in data for …; render them or remove them from the tiles`, bevor irgendein Video kodiert wird; Manifest fehlt. Für `ICON_WINDOWS` nur Warnung, Pfad fehlt im Manifest |
| Pfad einer Rückfallkette ohne Video im Manifest | `resolve` überspringt ihn (kein Frame); haben alle Pfade keins, Platzhalter des letzten Pfads |
| ICON-Tagesfenster nicht ganz im Lauf | Tag fehlt in `IconExtremes.days`, keine Karte; `field` liefert None |
| ffmpeg nicht im PATH | `FileNotFoundError` aus `Popen` im Encoder-Thread → Traceback; Manifest fehlt |
| ffmpeg mit Exit ≠ 0 (z. B. ohne libaom-av1) | `RuntimeError` mit ffmpeg-stderr, `.part` gelöscht → Traceback, sobald `pool.map` dieses Ergebnis erreicht; die übrigen Layer werden trotzdem fertig kodiert (der Pool wartet beim Verlassen), Manifest fehlt |
| Karte nicht lesbar während des Kodierens | Pillow-Ausnahme → Traceback; ffmpeg schließt das Video mit den bisherigen Frames ab, `<layer>.mp4.part` bleibt liegen (der nächste Aufruf zählt als neuer Lauf und leert `maps/<fenster>/`) |
| Fehlendes Feld in einem Produkt | `KeyError` aus `ForecastGrib.field`, via `pool.map` → Traceback |
| Klimatologie fehlt, Aufruf über `update_maps.py` | `check_climate` beendet mit Meldung und Exit 1, bevor etwas geladen oder gelöscht wird (Manifest bleibt) |
| Klimatologie fehlt, `render_charts.py` direkt mit CLIMATE-Produkt | `FileNotFoundError` in `ClimateArchive.__init__`, ungefangen |
| Gültigkeitsstunde ohne `HHz`-Datei | `ValueError` aus `term_kind`, ungefangen |
| `t850_anomaly` ohne Klimatologie | `ValueError` (render_charts verdrahtet sie für `CLIMATE`-Produkte immer) |
| Fenster ohne `DEFAULTS`-Eintrag der gewählten Klasse und ohne `--products` (z. B. IFS-Datei mit `--projection icon-d2`, ICON-Datei mit `opencharts_*`) | `KeyError` in `parse_args` |
| ICON-Datei mit `--products` außerhalb von `IconProducts.ALL` (z. B. `t850_mslp`) | argparse-Fehler, Exit 2 |
| `changed_videos`: `gh release view --json` scheitert | `sys.exit` mit gh-stderr, nichts hochgeladen |
| `publish_maps.py` ohne Manifest, ohne Videos darin oder mit fehlendem Video | Abbruch vor jedem Upload („run update_maps.py …“) |
| `gh` fehlt oder ist nicht angemeldet | `FileNotFoundError` (fehlt) bzw. `sys.exit` mit gh-stderr; nichts committet |
| Upload bricht mittendrin ab | `sys.exit`; einige Assets sind schon ersetzt, das Manifest ist nicht committet. Der nächste Aufruf lädt nur, was `changed_videos` als geändert erkennt (die schon ersetzten nicht) |
| Push abgelehnt (Remote weiter) | `sys.exit` mit git-stderr; der lokale Manifest-Commit bleibt, nach `git pull --rebase` pusht der nächste Aufruf ihn mit |
| `fetch_maps.py`: Asset fehlt (404) oder Netzfehler | `sys.exit` mit URL; Deploy scheitert, die alte Seite bleibt |

Kein Logging-Framework, keine Tests, keine Retries außer in `GroupDownloader`, `IconDownloader` und `fetchMeteogramUrl`.

## Erweiterungspunkte

**Layer zu einer Kachel hinzufügen oder neue Kachel** — `src/config/viewer.config.json` (`tiles[].layers`; ein Layer ist `"fenster/produkt"` oder eine Liste solcher Pfade als Rückfallkette, z. B. `["icon-d2/wind10m", "opencharts_central_europe/wind10m"]`: ICON, solange es einen Frame hat, sonst ECMWF). Jeder Pfad muss in `data/` gerendert werden: auf `opencharts_europe` jedes IFS-Produkt, auf `icon-d2` jedes ICON-Produkt, auf `opencharts_central_europe` nur die Defaults (sonst Abbruch in `encode_missing`, siehe Fehlerbehandlung, und vorher *Nicht-Default-Produkt auf Mitteleuropa*). Wirksam mit dem nächsten `download_data.cmd`, auch ohne neuen Lauf: Hat ein Pfad noch keine Karten in `data/`, rendert `stale_windows` sein Fenster neu; dann werden die Pfade ohne Video kodiert (ein Video ≈ 27 s, laut User), das Manifest neu geschrieben und per `publish_maps.py` veröffentlicht. In der Rückfallkette das Modell mit kürzerer Reichweite zuerst: `resolve` nimmt den ersten Pfad mit Frame. Code in App oder Pipeline muss nicht angefasst werden. `orography` (Datei, kein Ordner) und `sheets` taugen nicht als Layer.

**Layer entfernen** — Eintrag aus `tiles[].layers` streichen. Ab dem nächsten Aufruf fehlt er im Manifest, die App zeigt ihn also nicht; sein Video bleibt aber in `maps/` liegen und wird mitveröffentlicht, bis ein neuer Lauf oder `--force` `maps/<fenster>/` leert. Sofort weg nur durch Löschen der MP4 von Hand.

**Kodiereinstellungen ändern** — `CODEC`, `COLOUR`, `KEYFRAME_INTERVAL` (scripts/tile_videos.py:22-28), `FPS` (scripts/maps_manifest.py:31). Bestehende Videos werden bei gleichem Lauf nicht neu kodiert: entweder `--force` (rendert auch neu) oder die MP4-Dateien in `maps/<fenster>/` löschen und `download_data.cmd` aufrufen — dann werden nur sie kodiert. `FPS` geht über das Manifest an die App, dort ist nichts nachzuziehen. Ein größeres `KEYFRAME_INTERVAL` macht Videos kleiner und Seeks langsamer.

**Nicht-Default-Produkt auf Mitteleuropa** — `WINDOWS` (scripts/update_maps.py:52) für `opencharts_central_europe` auf eine kommagetrennte Produktliste oder `"all"` setzen (der String geht unverändert als `--products` an render_charts.py) oder `DEFAULTS` erweitern. Beides ändert, was der Skill in `data/` findet; data/charts.md (Tabelle der Fenster) nachziehen.

**Neues Kartenprodukt** — Methode mit dem Produktnamen in `ChartProducts` (scripts/lib/chart_products.py; `(self, step)` für Step-Produkte, `(self)` für statische), Name in `STEP` oder `STATIC` (`DAY` bildet einen Namen auf `"max"/"min"` ab). In `DEFAULTS` der Fenster, die es standardmäßig rendern, und in `CLIMATE`, falls es `self.climate` nutzt. Steht es als Layer in der Config, rendert `update_maps.py` das Fenster auch bei gleichem Lauf neu (`stale_windows`, scripts/update_maps.py:112), sofern das Fenster es rendert (`DEFAULTS` bzw. `WINDOWS`); ohne Config-Eintrag erst beim nächsten Lauf oder mit `--force`. Braucht es neue GRIB-Felder, die Gruppe in `RequestPlan` (scripts/lib/request_plan.py:24) erweitern: `expected_total` wächst mit, die vorhandene Datei gilt danach als unvollständig und wird neu geladen. Gibt es das Produkt nicht zu jedem `t`-Step, `keys()` (:83) wie bei `dt850_24h`/`weather_summary` erweitern. Skalen/Schwellen in chart_styles.py. Kontaktabzüge und `geometry.json`-Einträge kommen für `STEP`/`DAY` automatisch. Von Hand mitziehen: Produktliste im Docstring von scripts/render_charts.py:8-26 (= `--help`) und ein Abschnitt in data/charts.md (Vertrag mit dem Skill).

**Neues ICON-Produkt** — Ein vorhandenes `ChartProducts`-Produkt: nur den Namen in `IconProducts.STEP`/`DAY`/`STATIC` (scripts/lib/icon_products.py:30-32) eintragen, wenn die ICON-Datei alle Felder hat (Tabelle *ICON-D2*), sonst zuerst die Parameter laden (*Neuer ICON-Parameter*). Weicht nur die Datenquelle ab, einen Hook wie `profile`/`summit_cloud`/`extreme_days`/`daily_extreme_field`/`cloud_cover`/`precipitation`/`precipitation_type` in `ChartProducts` einführen und in `IconProducts` überschreiben (so sind `mountain_2000` und `tmax`/`tmin` angebunden). Ein reines ICON-Produkt als Methode in `IconProducts`. `ALL` und damit `DEFAULTS["icon-d2"]` folgen automatisch, `update_maps.py` rendert es ohne weitere Änderung. `keys` stammt aus `ChartProducts` (Step-Produkte: `t`-Steps, also T+0…48). Das Grau außerhalb des Gebiets setzt `IconProducts.draw` für jede Karte. Docstring von render_charts.py (ICON-Abschnitt :28-38) und data/charts.md nachziehen; als Layer `icon-d2/<produkt>` in die Config, meist als erster Pfad einer Rückfallkette mit dem ECMWF-Gegenstück.

**Neuer ICON-Parameter** — DWD-Ordnername in `FORECAST_PARAMS` bzw. `STATIC_PARAMS` (scripts/download_icon_d2.py:61-63), auf Druckflächen als `<ordner>@<hPa>` (neue Profilflächen über `PROFILE_LEVELS`, :60, nur Flächen, die ICON-D2 publiziert: kein 925 hPa); heißt sein shortName anders als der Name, den die Karten benutzen sollen, Alias in `ICON_NAMES` (scripts/lib/constants.py:18). Bedingungen: Dateien auf dem Ikosaedergitter mit dem Ebenentoken im Namen (`FILE`-Regex, scripts/lib/icon_runs.py:19), jeder Vorhersageparameter muss Step 48 erreichen (sonst findet `IconRuns` nie einen kompletten Lauf), und nach dem Filter auf volle Stunden genau eine Nachricht je Datei (sonst scheitert der Zählvergleich in download_icon_d2.py:88 und :101). Ein Ordner kostet ein Listing je Stundenordner, weitere Ebenen desselben Ordners nicht. Vorhandene ICON-Dateien gelten danach als unvollständig und werden neu geladen. `ForecastGrib` unterscheidet Ebenen nur über `level`: Mehrebenenparameter brauchen eindeutige Levels. Modul-Docstring von download_icon_d2.py und data/charts.md nachziehen.

**Neuer GRIB-Parameter** — Gruppe in `RequestPlan.__init__` (scripts/lib/request_plan.py:24) ergänzen oder erweitern; jede Gruppe muss ein vollständiges kartesisches Produkt dessen sein, was Open Data wirklich publiziert, sonst stimmt `expected()` nie und die Gruppe scheitert als unvollständig. Bestehende Vorhersagedateien gelten danach als unvollständig und werden neu gebaut (vollständige Rohgruppen werden wiederverwendet). Modul-Docstring von download_ecmwf_data.py und Tabelle in data/charts.md nachziehen.

**Neues abgeleitetes Feld** — in `step_messages` (scripts/lib/derived_writer.py:86) erzeugen und **`PER_STEP` (:35) von Hand passend halten** — die Formel spiegelt die Schleifen in `step_messages`, ist aber nicht daraus abgeleitet; eine Abweichung lässt `output_complete` nie wahr werden (jeder Lauf lädt neu). Ohne WMO/ECMWF-Parameter: nächste freie Nummer in `LOCAL_NAMES` (scripts/lib/local_params.py:12), bestehende Nummern nie umdeuten. Einmalige Felder wie `orog` zusätzlich im `+ 1` von `expected_total` (scripts/lib/request_plan.py:57) berücksichtigen. data/charts.md ergänzen.

**Neue Höhe in `MOUNTAIN_HEIGHTS`** — nur Werte, die nicht mit einem Druckflächen-Level übereinstimmen (500, 600, 700, 850, 925, 1000): der `ForecastGrib`-Index unterscheidet keine Ebenentypen, eine Höhe 1000 m würde t1000 hPa im Index überschreiben. `PER_STEP` folgt automatisch; charts.md nachziehen.

**Neue Druckfläche** — IFS: `PROFILE_LEVELS` (scripts/lib/constants.py:14) für t, r, gh und das Höhenprofil (nur von Open Data publizierte Flächen, kein 800 hPa); für Wind die Listen der Gruppen `uvw700`/`uv_low`. `HeightProfile` nimmt seine Flächen (`LEVELS`, scripts/lib/height_profile.py:9) aus derselben Liste; eine ICON-Fläche, die dort fehlt, ignoriert das Profil, also für ICON beide Listen (`constants.PROFILE_LEVELS` und `PROFILE_LEVELS` in download_icon_d2.py) pflegen.

**Neues Kartenfenster** — `Projection` in `PROJECTIONS` (scripts/lib/projection.py:128-139), für Lambert per `Projection.lambert(name, parallels, lon0, centre, km_per_px, graticule_step, borders=…, label_lon=…, label_lat=…)`; `label_lon`/`label_lat` müssen im Bild liegen, sonst fehlen die Gradnetzzahlen. IFS: Eintrag in `ChartProducts.DEFAULTS` (Pflicht) und `WINDOWS` (scripts/update_maps.py:52). ICON: Eintrag in `IconProducts.DEFAULTS` und `ICON_WINDOWS` (:53); das Fenster sollte ganz im ICON-D2-Gebiet liegen (sonst graue Flächen), und `parse_args` in render_charts.py nimmt ohne `--projection` immer `icon-d2`. In beiden Fällen `PROJECTIONS` in src/model/ChartProjection.ts:46 mit den Werten aus Python (`print(projection)`, cone und lon0 als 4./5. Argument). Die IFS-Zuschnittbox wächst automatisch (alle `PROJECTIONS`); alte Vorhersagedateien behalten die alte Box. `detail` greift für `km_per_px(50)` kleiner als Europa. Andere Bildgröße als 1200×690 betrifft `IMAGE_*` (beide Seiten), `WIDTH`/`HEIGHT` in scripts/tile_videos.py:21, `aspect-ratio` in ChartImage.module.css, die 1200 px in LargeView.module.css und `ContactSheet`.

**Klimatologie tauschen** — `PERIOD`/`DIRECTORY` (scripts/lib/climate_archive.py:26-28) bzw. `--climate`; `check_climate` in update_maps.py nutzt `DIRECTORY`. Kommt kein CLIMATE-Produkt mehr in `WINDOWS` vor, `check_climate` entfernen, sonst verlangt der Lauf die Dateien weiter. Anforderungen: GRIB2-Dateien `*.grb2`, Template 4.8 mit den Merkmalen, die `_key` liest, je Feld genau eine Nachricht, `HHz` für jede vorkommende Stunde (00…21 alle 3 h), T850 in K, reguläres Gitter Nord → Süd. Der Skill synop liest denselben Ordner mit einer eigenen Kopie von `ClimateArchive`. Neue Dateien nach `data/era5_means/` kopieren (alte, die es nicht mehr gibt, löschen) und den Download-Link in README.md anpassen.

**Grenzen neu bauen** (neue BEV-Daten, andere Länderauswahl) — `python scripts/build_borders.py <shp> [ziel]` mit pyshp, shapely ≥ 2.1, pyproj; Konstanten scripts/build_borders.py:39-48. Ein anderes Fenster mit eigenen Grenzen bekommt `borders=<Pfad>` in seiner `Projection`; `BaseMap` braucht nur GeoJSON in EPSG:4326 mit Polygon/MultiPolygon und optional `LEVEL: "state"`.

**Seltenes Wetter prüfen** — `python scripts/make_icon_test_grib.py data/icon-d2_<run>.grb2 <ordner>/icon-d2_<run>.grb2 --step N`, dann `render_charts.py <kopie> <ordner>`; nie nach `data/` schreiben (sonst rendert und veröffentlicht `update_maps.py` sie). Szene in `CELLS`/`FOG` (scripts/make_icon_test_grib.py:37-39).

**Weiteres Meteogramm** — Name in `meteograms`; Layout (drei pro Zeile) in Meteogram.module.css.

**Neue Seite** — `Route` und `currentRoute`/`navigate` in src/hooks/useHashRoute.ts, Verzweigung in src/App.tsx. Es gibt keinen Router.

**Andere Slider-Reichweite** — `MAX_STEP` (src/components/StepSlider.tsx:3); `currentStep` in ChartGrid klemmt mit demselben Wert.

**Neues Tastenkürzel** — `onKey` in src/components/ChartGrid.tsx:37. Eingaben in `<input>` werden für Pfeiltasten bewusst ignoriert.

**Ortswahl erweitern** (z. B. Name, Höhe) — `GeoLocation` und `isValidLocation`; gespeicherte alte Objekte laufen durch `isValidLocation` in `load()` (src/hooks/useStoredLocation.ts:6).

## Fallstricke

- **Destruktiv:** `update_maps.py` löscht GRIBs, `.raw/` und `.part` anderer Läufe desselben Modells in `data/` (`ecmwf_*` bzw. `icon-d2_*`), bei jedem Aufruf `maps/manifest.json`, bei jedem Rendern `data/<fenster>/` und bei neuem Lauf oder `--force` `maps/<fenster>/` der Fenster des Modells — vor dem Rendern, ein Fehlschlag hinterlässt also leere Fensterordner in `maps/` (die veröffentlichten Videos bleiben im Release). `download_ecmwf_data.py` und `download_icon_d2.py` ersetzen das Ziel (atomar über `<out>.part`) und löschen `<out>.raw/`. `publish_maps.py` ersetzt und löscht Release-Assets: Videos früherer Läufe gibt es nirgends mehr.
- **Render- und Kodierentscheidung nur über `maps/manifest.json` und die Kachel-Pfade:** Nennt es den geladenen Lauf (ECMWF oben, ICON an den `icon-d2`-Layern), wird ein Fenster nur gerendert, wenn sein Ordner in `data/` fehlt oder ein Kachel-Pfad dieses Fensters dort gar keine Karten hat — ein unvollständiger Produktordner und Nicht-Kachel-Produkte werden nicht geprüft —, und nur kodiert, was in `maps/` kein Video hat. Ein vorhandenes Video wird nie auf Aktualität oder Vollständigkeit geprüft.
- **ICON-Steps hängen am ECMWF-Run:** Alle Steps im Manifest zählen ab dem ECMWF-Lauf. Ist ICON älter (z. B. ICON-Download gescheitert, ECMWF neu), werden Karten vor dem ECMWF-Run auf Step 0 geklemmt. Wer Steps oder Slider auf den ICON-Lauf beziehen will, muss `chart_frames`, `ChartIndex` und `currentStep` gemeinsam ändern.
- **DWD hält nur ≈ 1 Tag Läufe:** `--icon-run` mit älterem Lauf scheitert; ein ICON-GRIB in `data/` lässt sich nicht nachladen. `download_icon_d2.py` fragt auch bei vorhandener Datei erst die Listings ab (kein Offline-Betrieb).
- **`changed_videos` vergleicht nur Größe und Zeit:** Ein Video, dessen Datei nach dem Upload neu geschrieben wurde, geht erneut hoch, auch mit gleichem Inhalt; ein anderer Inhalt mit gleicher Größe und älterer mtime als das Asset (z. B. von einem anderen Rechner hochgeladen) bleibt unerkannt.
- **Video und Steps können auseinanderlaufen:** Das Manifest liest die Steps bei jedem Aufruf aus `data/`, ein vorhandenes Video bleibt. Wer `data/<fenster>/<produkt>/` außerhalb von `update_maps.py` ändert (z. B. `render_charts.py --products` mit anderem GRIB), muss das zugehörige Video löschen, sonst passt `steps[i]` nicht zu Frame `i`.
- **Rückfallketten wechseln das Video:** In `[icon-d2/…, opencharts_central_europe/…]` zeigt die Kachel vor dem ersten und nach dem letzten ICON-Frame (`end`) das ECMWF-Video; beim Wechsel lädt `useLoadedVideo` das andere Video erst dann. Ein ICON-Tagesprodukt in einer Kette deckt nur seinen Tag bis 23 Uhr ab (`end` + 23). `resolve` prüft nur, ob ein Frame existiert, nicht, ob das Video ladbar ist.
- **Zwei Listen von Profilflächen:** `constants.PROFILE_LEVELS` (IFS-Download, `HeightProfile.LEVELS`) und `PROFILE_LEVELS` in download_icon_d2.py (ICON-Download). Das ICON-Profil nutzt nur Flächen, die in beiden stehen und für die Parameter und `z` vorhanden sind (`_stack`).
- **ICONs `max_2t`/`min_2t` sind keine Extreme ab T+0:** Sie starten alle 6 h neu, obwohl der GRIB-Kopf `stepRange 0-N` meldet; wer sie direkt liest, bekommt 6-h-Extreme. `IconExtremes` behandelt das; `ForecastGrib.daily_extreme` taugt für ICON nicht.
- **Veröffentlicht wird, was das Manifest nennt:** `publish_maps.py` lädt nur dessen Videos hoch und löscht alle anderen Assets. Videos entfernter Layer und `.part`-Dateien in `maps/` bleiben lokal liegen (ignoriert).
- **`publish_maps.py` pusht `HEAD`** ohne Rückfrage, also auch lokale Code-Commits. Gestagte andere Änderungen bleiben gestagt, der Commit enthält nur das Manifest.
- **`gh` ist Pflicht** auf jedem Rechner, der publiziert; das Release-Asset-Limit liegt bei 2 GB je Datei. `download_data.cmd` endet ohne `pause`.
- **Ausführbar-Bit der `.sh`-Dateien** steht nur im git-Index (Windows kennt es nicht). Eine neue `.sh`-Datei mit `git add --chmod=+x` aufnehmen, sonst fehlt es nach dem Klonen auf macOS/Linux.
- **Vertrag mit dem Skill:** Produktnamen, Ordnerlayout, `geometry.json`-Schlüssel, GRIB-Namen/Ebenen und lokale Parameternummern nicht ändern, ohne den Skill nachzuziehen. data/charts.md beschreibt das alles von Hand und muss mitgepflegt werden. `chart_geometry.py` des Skills kennt `cone`/`lon0` nicht: Ortsmarker des Skills auf `icon-d2`-Karten sind falsch, bis er nachgezogen ist.
- **Doppelte Werte, die synchron bleiben müssen:** Projektionsparameter (Python, TS — für `icon-d2` als von Python berechnete Literale); Bildgröße 1200×690 (chart_canvas.py, tile_videos.py, TS, CSS) — eine abweichende Kartengröße fällt beim Kodieren nicht auf, ffmpeg zerschneidet den Bytestrom dann falsch; `MOUNTAIN_HEIGHT_M` (Karte) vs. `MOUNTAIN_HEIGHTS` (GRIB); `PER_STEP` vs. `step_messages`; Produktnamen in `ChartProducts`/`IconProducts` vs. render_charts-Docstring und data/charts.md; Fensternamen in `PROJECTIONS`, `WINDOWS`/`ICON_WINDOWS`, `DEFAULTS` und TS-`PROJECTIONS`; `PREFIX` (download_icon_d2.py) vs. `ICON_PREFIX` (update_maps.py); Layer-Format (Pfad oder Liste) in `LayerConfig`/`layerPaths` (TS) vs. `tile_chart_paths` (Python).
- **Laufzeit/Netz:** Der Download braucht Internet und holt alle Gruppen als globale 0,1°-Rohdateien (2211 Nachrichten) vor dem Zuschneiden; stderr ist währenddessen stumm. Danach mehrere Minuten Rendern auf allen CPUs und ≈ 1:45 min Kodieren (laut User) mit `PARALLEL_ENCODES` ffmpeg-Prozessen. Jeder Aufruf fragt beide Server ab, auch ohne neuen Lauf (ICON: 8 + 20 Listings je geprüftem Stundenordner); ICON allein (gemessen): Download 43–138 s für ≈ 1100 Dateien (Netz schwankt), Rendern ≈ 148 s direkt nach dem Download bzw. ≈ 43 s mit warmem Dateicache, dazu das Kodieren von 4 Videos.
- **ffmpeg ist Pflicht:** Ohne `ffmpeg` mit `libaom-av1` im PATH bricht jeder `update_maps.py`-Lauf nach dem Rendern ab (Traceback), es gibt keine Vorabprüfung.
- **Browser-Speicher und AV1:** Jedes angezeigte Video liegt ganz als Blob im Speicher und wird bis zum Neuladen nie freigegeben (alle 14 Pfade ≈ 67 MB). Die App setzt einen Browser mit AV1-Decoder voraus; ohne ihn bleiben Kacheln leer.
- **Speicher:** Beim Zuschneiden dekodiert jeder der bis zu 8 `ForecastWriter`-Worker ein globales Feld (≈ 100 MB). Jeder Render-Worker baut eigenen `ForecastGrib` (bis ~250 MB Cache), `BaseMap` (8,7- bzw. 3,5-MB-GeoJSON) und ggf. Klimatologie bzw. die Delaunay-Triangulierung (`TriangleGrid`, auch im Hauptprozess); Default-Workerzahl = CPU-Zahl, bis zu drei Fenster laufen parallel. `DerivedWriter` hält alle abgeleiteten Nachrichten aller Steps im Hauptprozess, bevor er sie anhängt.
- **Read-only-Arrays:** Ergebnisse von `ForecastGrib.field` nie in-place ändern.
- **Schnelltests teilen den Namen:** `--max-step` mit Ordnerziel schreibt trotzdem `ecmwf_<run>.grb2`; ein späterer Vollaufruf sieht eine andere Nachrichtenzahl und lädt neu.
- **Ordner vs. Datei als Ziel:** `download_ecmwf_data.py` behandelt `out` nur als Ordner, wenn er existiert.
- **Modellfelder unter Grund:** Werte auf 1000/925/850 hPa unter der Modellorografie extrapoliert das Modell; Diagnostics maskiert pro Gitterpunkt, die Karten maskieren dagegen über feste Modellhöhen (`ABOVE_850HPA_M` usw.); `z500_t850`, `dt850_24h` färben T850 überall.
- **Der Dev-Server** liefert `maps/` aus dem Repo-Root aus; Vite beobachtet `data/` und `maps/` nicht (vite.config.ts:11), ein neues Manifest braucht einen Reload. `base: './'` ist für den Pages-Unterpfad nötig; alle Pfade gehen über `import.meta.env.BASE_URL`.
- **Zeitzonen:** Run, Steps und Dateinamen sind UTC; der Slider zeigt nur `+N h`, die Gültigkeitszeit steht in der Kartenlegende.
- **StrictMode** führt Effekte im Dev doppelt aus; Meteogramm-Requests werden dabei abgebrochen und neu gestellt. `Meteogram` fragt ECMWF bei jedem Ortswechsel neu ab, kein Cache außer dem Browser-Bildcache.
- **Es gibt keine Tests**, kein Logging, keine requirements-Datei, keine Validierung des Manifests (die App vertraut dem JSON-Typ) und kein Aufräumen von `<out>.part` bzw. `<layer>.mp4.part` nach einer Ausnahme. `lint` ist oxlint mit Hooks-Regeln.
