# wetterkartenviewer — Agent-Referenz

Referenz für die React-App und die Python-Datenpipeline (Download, abgeleitete Felder, Karten), damit Erweiterungen ohne vollständiges Lesen des Quellcodes möglich sind. Pfade relativ zum Repository-Root.

## Zweck

- Statische Single-Page-App (React 19, Vite, TypeScript), veröffentlicht auf GitHub Pages: https://schletz.github.io/wetterkartenviewer/
- **Startseite:** ECMWF-ENS-Meteogramme (Opencharts-API, live vom Browser abgefragt) für einen Ort, den der Nutzer einstellt.
- **Kartenseite (`#/maps`):** ein Raster aus Kacheln mit den Karten eines ECMWF-IFS-Laufs und ein Zeitslider von +0 bis +240 h. Jeder Kachel-Layer ist ein AV1-Video (ein Frame pro Termin), die App springt per `currentTime` zum Frame.
- **Datenpipeline** (`scripts/`): lädt einen IFS-HRES-Lauf (0,1°) von ECMWF Open Data, schneidet ihn auf Europa zu, hängt abgeleitete Felder an, rendert Karten (WebP) für zwei Kartenfenster nach `data/`, kodiert jeden Kachel-Layer mit ffmpeg als `maps/<fenster>/<produkt>.mp4`, schreibt `maps/manifest.json` und veröffentlicht per Amend + Force-Push.
- `data/` ist zugleich das Datenverzeichnis des Skills `synop` (`~/.claude/skills/synop`); siehe Abschnitt *Vertrag mit dem Skill synop*.

## Modulüberblick

### App

| Datei | Zeilen | Verantwortung |
| --- | --- | --- |
| src/main.tsx | 10 | React-Root in StrictMode mounten |
| src/App.tsx | 13 | Route (Hash) und gespeicherten Ort halten, Start- oder Kartenseite zeigen |
| src/config/viewer.config.json | 44 | Kacheln mit Layern und Meteogrammnamen, von Hand gepflegt |
| src/config/viewerConfig.ts | 21 | JSON typisieren (`ViewerConfig`, `TileConfig`, `ChartPath`) |
| src/model/ChartIndex.ts | 85 | Manifest abfragen: Frame zu einem Step, Steps aller Layer, Video-URL, Seek-Zeit |
| src/model/ChartProjection.ts | 46 | Lat/Lon in Bildpixel der beiden Kartenfenster umrechnen |
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
| src/components/ChartGrid.tsx | 68 | Step-, Layer- und Großansicht-State, Tastatur, Raster |
| src/components/ChartTile.tsx | 33 | Kachel: Linksklick nächster Layer, Rechtsklick Großansicht |
| src/components/ChartImage.tsx | 71 | Stummes `<video>` auf den Frame des Steps setzen bzw. Platzhalter, Ortsmarker |
| src/components/LargeView.tsx | 69 | Verschiebbares Fenster mit der Karte in 1:1-Größe |
| src/components/StepSlider.tsx | 23 | Range-Input 0–240 h mit Tagesmarken |
| src/components/*.module.css | je 4–41 | CSS-Module pro Komponente |
| src/index.css | 28 | Globale CSS-Variablen (`--bg`, `--accent`, `--gap` …) |
| .github/workflows/deploy.yml | 39 | Bei Push auf `main`: bauen, Manifest und Videos aus dem Release nach `dist/maps` (`fetch_maps.py`), Pages deployen |
| vite.config.ts | 13 | `base: './'`, `data/` und `maps/` vom Watcher ausnehmen |

### Skripte und Steuerdateien

Jedes Pipeline-Skript parst nur Argumente und verdrahtet Klassen aus `scripts/lib/`. `download_ecmwf_data.py` und `render_charts.py` setzen ihr eigenes Verzeichnis in `sys.path`, damit `python -I` funktioniert. `update_maps.py`, `maps_manifest.py`, `publish_maps.py` und `fetch_maps.py` importieren ihre Nachbarmodule (`maps_manifest`, `maps_release`, `tile_videos`) über das Skriptverzeichnis in `sys.path`, also ohne `-I`.

| Datei | Zeilen | Verantwortung |
| --- | --- | --- |
| scripts/update_maps.py | 157 | Orchestrierung: Klimatologie prüfen, Download, alte Läufe löschen, beide Fenster nach `data/` rendern, fehlende Kachel-Videos kodieren, Manifest |
| scripts/maps_manifest.py | 102 | Layer-Pfade aus der Config, Frame-Reihenfolge eines Layers (`chart_frames`), Manifest erzeugen, Run und Videoliste lesen |
| scripts/tile_videos.py | 55 | `encode_video`: WebP-Karten als rohes RGB an ffmpeg, AV1-MP4 schreiben (Modul ohne CLI) |
| scripts/publish_maps.py | 99 | Manifest prüfen, Videos ins Release laden, überzählige Assets löschen, Manifest committen, pushen (`gh`, `git`) |
| scripts/fetch_maps.py | 48 | Im Deploy: Manifest und dessen Videos aus dem Release nach `dist/maps` (nur Standardbibliothek, ohne Token) |
| scripts/maps_release.py | 20 | `TAG` des Releases, Asset-Name und Download-URL eines Videos |
| scripts/download_ecmwf_data.py | 145 | Lauf wählen, Gruppen parallel laden, zuschneiden, abgeleitete Felder anhängen |
| scripts/render_charts.py | 191 | Produkte eines Fensters im Prozesspool rendern, Kontaktabzüge, `geometry.json` |
| data/charts.md | 345 | Deutsche Beschreibung von Ordner, GRIB-Feldern und Produkten **für den Skill**; einzige committete Datei in `data/`, wird nur in einen anderen Datenordner kopiert |
| download_data.cmd | 5 | `update_maps.py data maps %*` und bei Erfolg `publish_maps.py maps` |
| download_data.sh | 5 | dasselbe für macOS/Linux mit `python3`; im Index ausführbar (100755) |

### Paket `scripts/lib/` (22 Klassen, eine öffentliche Klasse pro Datei)

Alle Abhängigkeiten werden über den Konstruktor injiziert. Ohne Klasse: `__init__.py`, constants.py, local_params.py, chart_styles.py, fonts.py.

| Datei | Zeilen | Klasse | Verantwortung |
| --- | --- | --- | --- |
| constants.py | 14 | — | `KELVIN`, `KMH_PER_MS`, `GRAVITY`, `WEATHER_PARAMS`, `PROFILE_LEVELS` |
| local_params.py | 20 | — | Nummern der lokalen GRIB-Parameter (Kategorie 192) ↔ Namen |
| projection.py | 74 | Projection (frozen dataclass) | Polarstereografische Pixelgeometrie eines Opencharts-Fensters; `EUROPE`, `CENTRAL_EUROPE`, `PROJECTIONS` |
| open_data_runs.py | 52 | OpenDataRuns | Neuester kompletter Lauf; Hinweis, wenn ein neuerer erst mit 0,25° da ist |
| request_plan.py | 69 | RequestPlan | Request-Gruppen eines Laufs, erwartete Nachrichtenzahlen; Funktion `count_messages` |
| group_downloader.py | 52 | GroupDownloader | Eine Gruppe mit Retries laden, Anzahl prüfen |
| grib_cropper.py | 88 | GribCropper | Globale Nachrichten auf die Box schneiden und neu kodieren |
| forecast_writer.py | 141 | ForecastWriter | Rohdateien im Prozesspool zuschneiden, in Rohdatei-Reihenfolge in eine Datei schreiben, `thick` je Step |
| derived_writer.py | 147 | DerivedWriter | Abgeleitete Felder an die Vorhersagedatei anhängen (Prozesspool) |
| extreme_windows.py | 45 | ExtremeWindows | Welche 3-/6-h-Extreme ein Tagesfenster lückenlos abdecken |
| forecast_grib.py | 161 | ForecastGrib | Byte-Offset-Index der Vorhersagedatei, gecachtes Dekodieren, Tagesextreme |
| model_surface.py | 21 | ModelSurface | Statische T+0-Felder: `height` (m), `sdor`, `land` |
| height_profile.py | 58 | HeightProfile | Druckflächenprofil → Wert in fester Höhe, Nullgradgrenze |
| diagnostics.py | 70 | Diagnostics | Diagnosen der freien Atmosphäre (Inversion, feuchte Grenzschicht, Niederschlagssignal, Schneefallgrenze) |
| climate_archive.py | 201 | ClimateArchive | Klimatologie-GRIBs über die Bytes der Kopfteile indizieren, Felder dekodieren, Gitter, nächster Punkt |
| t850_climate.py | 50 | T850Climate | T850-Mittel (°C) / Std (K) je Gültigkeitszeit, als Feld oder Punkt |
| pixel_grid.py | 43 | PixelGrid | Lat/Lon-Gitter auf 1200×600 Pixel resamplen; Wind in Pixelvektoren |
| base_map.py | 57 | BaseMap | Projizierte Länderringe (world_countries.geojson) und Gradnetz |
| colour_scale.py / contour_style.py / symbol_style.py | 27 / 27 / 26 | ColourScale / ContourStyle / SymbolStyle | Frozen dataclasses für Farbbänder, Konturlinien, Punktsymbole |
| chart_styles.py | 217 | — | Alle Farbskalen, Konturstile, Schwellen (auch von Diagnostics benutzt) |
| fonts.py | 18 | — | `load_font`: Arial (Dateinamen von Windows und macOS) → DejaVu Sans → PIL-Default in Größe `size` |
| chart_canvas.py | 304 | ChartCanvas | Eine matplotlib-Figur: Kartenlayer + Legendenstreifen, verlustfrei als WebP speichern |
| chart_products.py | 431 | ChartProducts | Produktregister (`STEP`, `DAY`, `STATIC`, `ALL`, `CLIMATE`, `DEFAULTS`), eine Methode pro Produkt |
| contact_sheet.py | 67 | ContactSheet | Kontaktabzüge bauen, Kachelursprünge liefern |
| world_countries.geojson | 8,7 MB, eine Zeile | — | Ländergrenzen, Esri „World Countries (Generalized)“ (https://hub.arcgis.com/datasets/esri::world-countries-generalized), lokal gelesen |

Python gesamt 2.959 Zeilen (Skripte 671, lib 2.288).

Externe Abhängigkeiten: npm (`package.json`), Laufzeit nur `react`/`react-dom`, Entwicklung `vite`, `@vitejs/plugin-react`, `typescript ~7.0`, `oxlint`. Kein Router, kein State-Management, keine UI-Bibliothek. npm-Skripte: `dev`, `build` (`tsc -b && vite build`), `lint` (oxlint, .oxlintrc.json), `preview`.
Python-Pakete (keine requirements-Datei): `ecmwf-opendata`, `eccodes`, `numpy`, `scipy` (`ndimage`), `matplotlib` (Agg, erzwungen in scripts/lib/chart_canvas.py:14), `Pillow`, `requests`. `update_maps.py` ruft die beiden Pipeline-Skripte als Subprozess mit `sys.executable` auf. `tile_videos.py` braucht Pillow und **ffmpeg mit dem Encoder `libaom-av1` im PATH**.
Die App kennt die Pipeline nicht, sie liest nur `maps/manifest.json` und die MP4-Videos.

## Verzeichnisse

| Ordner | Git | Inhalt |
| --- | --- | --- |
| `data/` | ignoriert (`/data/*`) bis auf `charts.md` | genau ein Lauf: `ecmwf_<run>.grb2`, `opencharts_europe/` (**alle** Produkte), `opencharts_central_europe/` (Default-Produkte), je Fenster `sheets/`, `orography.webp`, `geometry.json`; dazu `era5_means/` und `charts.md` (committet, von Hand gepflegt) |
| `data/era5_means/` | ignoriert | `era5_means.grb2` (422 MB, 13 224 Felder, ERA5 1991–2020). Kein Skript erzeugt oder lädt sie: einmal von Hand von Google Drive laden (Link in README.md, Abschnitt Klimatologie; laut User). `update_maps.py` prüft vor dem Download, dass ein `*.grb2` da ist, und lässt es stehen |
| `maps/` | nur `manifest.json` committet (`/maps/*`, `!/maps/manifest.json`) | `manifest.json` und je Kachel-Layer ein Video `<fenster>/<produkt>.mp4`, kodiert aus `data/<fenster>/<produkt>/`; dazu Videos von Layern, die seit dem letzten neuen Lauf aus der Config entfernt wurden (siehe Fallstricke). Die Videos des Manifests liegen als Assets im Release `tile-videos` |

Größen beim Lauf 2026103000: GRIB 1,54 GB, `data/opencharts_europe` 266 MB, `data/opencharts_central_europe` 125 MB, `maps/` ≈ 52 MB (10 Videos, 2,5–7,3 MB je Video).

### Vertrag mit dem Skill synop

Der Skill liest `data/` als Datenverzeichnis (Docstrings scripts/update_maps.py:3-12, scripts/lib/local_params.py:1-8). Laut User bilden diese Punkte die Schnittstelle; Änderungen daran brechen den Skill, der im Skill-Ordner nachgezogen werden muss:

| Element | Erzeuger | Was der Skill erwartet |
| --- | --- | --- |
| `data/charts.md` | von Hand gepflegt, committet; in einen anderen Datenordner kopiert (scripts/update_maps.py:134-135) | Beschreibung der Dateien, GRIB-Felder (inkl. Einheiten, lokale Nummern) und aller Produkte; von Hand gepflegt |
| `data/<fenster>/geometry.json` | `write_geometry` (scripts/render_charts.py:128) | Schlüssel `window`, `image.width/height` (= Kartenfläche 1200×600, ohne Legende), `projection.pole_x/pole_y/scale_k/formula`, `sheets.scale`, `sheets.tiles.<produkt>` = Liste `[x, y]` der Kachel-Ecken oben links |
| GRIB-Layout | download_ecmwf_data.py + `DerivedWriter` | shortNames, Ebenen, Einheiten, `stepRange` der Tagesextreme und vor allem die lokalen `parameterNumber` 0–5 in Kategorie 192 (`LOCAL_NAMES`, scripts/lib/local_params.py:12) — der Skill benennt sie selbst nach Nummer |
| Ordner-/Dateinamen | `ChartProducts.path` (scripts/lib/chart_products.py:93), `ClimateArchive` | `<fenster>/<produkt>/<YYYYMMDDHH>.webp`, Tagesprodukte `<YYYYMMDD>.webp`, `sheets/<produkt>.webp`, `orography.webp`, `era5_means/*.grb2`, ein Lauf `ecmwf_<run>.grb2` |

## Schnittstelle (CLI)

```
update_maps.py <data> <maps> [--base YYYYMMDDHH] [--force]
maps_manifest.py <data> <maps> --run YYYYMMDDHH
publish_maps.py <maps>                     (gh und git laufen im Repo-Root)
fetch_maps.py <maps> <target> --repository owner/name
download_ecmwf_data.py <out file|existing dir> [--base YYYYMMDDHH] [--max-step N] [--keep-raw]
render_charts.py <grib> <outdir> [--climate DIR] [--projection opencharts_europe|opencharts_central_europe]
                 [--products a,b|all] [--workers N]
```

| Skript | Ausgabe | Exit ≠ 0 bei | Hinweise |
| --- | --- | --- | --- |
| update_maps | `data/…`, `maps/<fenster>/<produkt>.mp4`, `maps/manifest.json` | Download-, Render-Fehler, Layer ohne Karten in `data/` (`sys.exit` mit Meldung); ffmpeg-Fehler (Traceback) | `--force` erzwingt Rendern und Neukodieren aller Layer, nicht den Download |
| maps_manifest | `maps/manifest.json`, Pfad auf stdout | — | rendert/kodiert nichts; Steps aus den Kartennamen in `data/`, listet nur Layer mit vorhandenem Video (sonst `warning: no video for …`) |
| publish_maps | Release-Assets, Commit „Data update <run>z“, Push | kein Manifest oder keine Videos darin, Video des Manifests fehlt, jeder gh-/git-Fehler (`sys.exit` mit stderr) | legt das Release beim ersten Aufruf an (`--latest=false`); committet nur das Manifest und nur, wenn es sich geändert hat; pusht immer (auch lokale Code-Commits) |
| fetch_maps | `<target>/manifest.json`, `<target>/<fenster>/<produkt>.mp4` | kein Manifest oder keine Videos darin, Download-Fehler (`sys.exit` mit URL) | lädt anonym über `https://github.com/<repo>/releases/download/tile-videos/<asset>`; das Repo muss öffentlich sein |
| download | `<dir>/ecmwf_<YYYYMMDDHH>.grb2` (bei existierendem Ordner) oder die genannte Datei; letzte stdout-Zeile = absoluter Pfad | Lauf nicht publiziert (404), Gruppe unvollständig | `--base` nur 00/12 UTC (argparse-Fehler, Exit 2); vollständiges Ziel → „already on disk“, Exit 0 |
| render_charts | `<outdir>/<fenster>/…` (siehe Verzeichnisse) | unbekanntes Produkt (argparse, Exit 2) | ohne `--products`: `ChartProducts.DEFAULTS[fenster]`; `--climate` Default `<grib-Ordner>/era5_means` (`DIRECTORY` in climate_archive.py); Workers Default = CPU-Zahl |

Status auf stdout, Fehler auf stderr; Meldungen englisch.

## Datenfluss

### Karten erzeugen und veröffentlichen (lokal)

```
download_data.cmd | download_data.sh [--base YYYYMMDDHH] [--force]
 ├─ update_maps.py data maps                    scripts/update_maps.py:120
 │    ├─ check_climate(data)                    :51   ohne data/era5_means/*.grb2 sys.exit, vor Download und Löschen
 │    ├─ download(data, base)                   :66   Subprozess, Ausgabe live; letzte nichtleere Zeile = GRIB-Pfad
 │    ├─ remove_old_runs(data, grib)            :81   löscht data/ecmwf_*.grb2* (Datei, .raw/, .part) anderer Läufe
 │    ├─ [anderer Datenordner] data/charts.md -> <data>/charts.md
 │    ├─ same_run = read_run(maps) == run und kein --force
 │    ├─ maps/manifest.json löschen             (immer)
 │    ├─ [nicht same_run] maps/<fenster>/ löschen (alle Videos)
 │    ├─ [nicht same_run oder ein data/<fenster>/ fehlt]
 │    │    data/<fenster>/ löschen, render(grib, data, fenster) × 2 parallel (Threads)   :93
 │    │      WINDOWS: opencharts_europe -> --products all, opencharts_central_europe -> Defaults
 │    ├─ encode_missing(data, maps, run)        :104
 │    │    ├─ Layer der Config ohne maps/<layer>.mp4
 │    │    ├─ [einer davon ohne Karten in data/] sys.exit, vor dem ersten Kodieren
 │    │    └─ ThreadPool(PARALLEL_ENCODES) × encode_video(chart_frames(data, layer, run), maps/<layer>.mp4)
 │    │         scripts/tile_videos.py:31   Karten als rohes RGB über stdin an ffmpeg -> <layer>.mp4.part -> rename
 │    └─ write_manifest(data, maps, run)        scripts/maps_manifest.py:84
 └─ publish_maps.py maps                        scripts/publish_maps.py:79
      ├─ [kein Manifest, keine Videos darin oder ein Video fehlt] Abbruch
      ├─ ensure_release()                       :39   gh release view, sonst create tile-videos --latest=false
      ├─ upload_videos(maps, files)             :47   Kopie unter Asset-Namen in ein Temp-Verzeichnis, gh release upload --clobber
      ├─ prune_assets(files)                    :59   gh release delete-asset für Assets, die das Manifest nicht nennt
      ├─ commit_manifest(maps, run)             :68   git add + git commit -- maps/manifest.json, nur bei Änderung
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
 │    ├─ ProcessPool(min(CPU, 8), init_worker) × step_messages(step)   :87   21 Nachrichten je Step
 │    └─ anhängen: alle Steps, dann orog, dann mx2t je Tag, mn2t je Tag
 ├─ <out>.part -> <out>  (rename)
 └─ rmtree(<out>.raw) [ohne --keep-raw]
```

### Rendern

```
render_charts.main                               scripts/render_charts.py:171
 ├─ build_products(...) im Hauptprozess          :78   (für keys(), Kontaktabzüge)
 │    └─ ForecastGrib, ModelSurface, BaseMap, PixelGrid(grib.grid)
 │       [+ ClimateArchive, T850Climate, PixelGrid(archive.grid) nur wenn ein CLIMATE-Produkt verlangt ist]
 ├─ tasks = (produkt, key, out_dir) für key in ChartProducts.keys(produkt)
 ├─ ProcessPool(workers, init_worker -> build_products je Prozess), chunksize 2
 │    └─ render: ChartProducts.draw -> ChartCanvas.save                :95
 ├─ write_sheets -> ContactSheet.build (liest die geschriebenen WebPs)  :104
 └─ write_geometry -> geometry.json                                     :128
```

Invarianten der Reihenfolge:

1. **Manifest wird vor allem anderen gelöscht** (scripts/update_maps.py:139) und erst nach dem Kodieren geschrieben. „Gleicher Lauf“ heißt: das Manifest nennt den Lauf; ein abgebrochener Aufruf hinterlässt kein Manifest und zählt beim nächsten Mal als neuer Lauf. Neuer Lauf oder `--force` → `maps/<fenster>/` leeren, rendern, alle Layer kodieren. Gleicher Lauf → nur rendern, wenn ein Fensterordner in `data/` fehlt, und nur Layer ohne Video kodieren. `encode_missing` und das Manifest laufen bei jedem Aufruf, ein in viewer.config.json ergänzter Layer greift also ohne `--force`.
2. **Frame-Reihenfolge und Manifest-Steps kommen aus derselben Quelle:** `chart_frames` (scripts/maps_manifest.py:44) sortiert die Karten eines Layers in `data/` nach Step; `encode_video` schreibt sie in dieser Reihenfolge, `build_manifest` (:56) übernimmt deren Steps. Das Manifest liest die Steps bei jedem Aufruf neu aus `data/`, das Video kann aus einem vorigen Aufruf stammen — `len(steps)` muss der Frame-Zahl des Videos entsprechen, sonst zeigt die App stillschweigend falsche Termine. Beides gehört zum selben Lauf, solange `data/` nur durch `update_maps.py` geändert wird.
3. **`DerivedWriter` läuft auf der fertigen `.part`-Datei**: Er indiziert sie neu und braucht alle Modellfelder. Die Reihenfolge der angehängten Nachrichten ist Teil von `expected_total` (scripts/lib/request_plan.py:48).
4. **`ForecastWriter` schreibt `thick` direkt nach dem zweiten von gh500/gh1000 eines Steps**; die Reihenfolge 500/1000 innerhalb eines Steps wird nicht vorausgesetzt. Nur der Hauptprozess schreibt, und `pool.map` liefert in Eingabereihenfolge — die Datei ist deshalb byte-gleich mit einem Lauf ohne Pool. Wer auf `as_completed`/`imap_unordered` umstellt, bricht diese Reihenfolge.
5. **`GribCropper` berechnet Zeilen/Spalten aus der ersten Nachricht** (`fit`) und nutzt sie für alle weiteren; `cropper.grid` existiert erst nach dem ersten `fit`/`crop`. `ForecastWriter.write` ruft `fit` vor dem Pool auf, damit die Worker einen fertigen Cropper bekommen und `download_ecmwf_data` danach `cropper.grid` lesen kann.
6. **Einzelkarten vor Kontaktabzügen.** `write_sheets` öffnet die von den Workern geschriebenen WebPs; die Farbskala des Abzugs stammt aus dem Legendenstreifen der ersten Karte.
7. **ChartCanvas-Layer** werden in Aufrufreihenfolge innerhalb ihres zorder-Bands gezeichnet; `save` muss zuletzt kommen, weil dort Notizspalte und Symbolzeile entstehen (scripts/lib/chart_canvas.py:295).
8. **Erst hochladen, dann Manifest pushen:** `publish_maps.py` ersetzt die Assets, bevor der Manifest-Commit gepusht wird, und löscht überzählige Assets vor dem Push. Der Deploy des neuen Manifests findet so alle Videos. Die Asset-Namen enthalten keinen Lauf: Ein Deploy eines älteren Manifests, der während eines Uploads läuft, kann Videos des neuen Laufs holen; der Push danach startet einen neuen Deploy, `concurrency` (`cancel-in-progress`) bricht den alten ab. Die Historie wächst nur um das Manifest (≈ 20 KB je Lauf).

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
                  ├─ ChartTile × tiles -> ChartImage                src/components/ChartImage.tsx:29
                  │    ├─ index.frame(path, step)   -> ChartFrame {index, step} oder null
                  │    ├─ index.videoUrl(path)      -> <BASE_URL>maps/<file>?run=<run> oder null
                  │    ├─ useLoadedVideo(url)       src/hooks/useLoadedVideo.ts:21
                  │    │    │   -> { shown: {url, objectUrl} des zuletzt geladenen Videos, failed }
                  │    │    └─ loadVideo(url)       src/services/videoLoader.ts:13  fetch ganz -> Blob -> Object-URL
                  │    ├─ time = index.frameTime(frame), nur wenn shown.url === url
                  │    ├─ placeholderText(...)      src/components/ChartImage.tsx:18
                  │    ├─ <video muted playsInline preload="auto">; currentTime = time
                  │    │    (Effect ab readyState HAVE_METADATA, sonst onLoadedMetadata)
                  │    └─ projectionOf(path).toPixel(location) -> Marker
                  └─ [enlarged] LargeView -> ChartImage (1200 px breit; dieselbe URL, also dasselbe gecachte Video)
```

Während ein neuer Layer lädt, bleibt das Video des vorigen Layers mit seinem letzten Frame stehen (`time` ist `null`, der Slider bewegt es nicht). Erst wenn das neue Video da ist, wechselt `src`, und `onLoadedMetadata` setzt den Frame. Videos werden nur für angezeigte Layer geladen, es gibt kein Vorausladen anderer Layer.

## Kernkonzept: Manifest, Frames und Step-Auflösung

`maps/manifest.json` (Typ `Manifest`, src/model/ChartIndex.ts:18) ist die einzige Schnittstelle zwischen Pipeline und App:

```json
{ "run": "2026103000", "fps": 10,
  "charts": { "opencharts_europe/thickness_mslp":
                { "file": "opencharts_europe/thickness_mslp.mp4", "steps": [0, 3, 6, ..., 240] } } }
```

- **Schlüssel** sind die Layer-Pfade aus `viewer.config.json` (`fenster/produkt`), dedupliziert in Config-Reihenfolge (`tile_chart_paths`, scripts/maps_manifest.py:25). Dieselbe Liste bestimmt, welche Videos `encode_missing` kodiert. Ein Layer der Config ohne Video in `maps/` fehlt im Manifest (Warnung auf stdout); die App zeigt dann „keine Karten in diesem Lauf“. Videos in `maps/`, deren Layer nicht in der Config steht, fehlen ebenfalls.
- **`file`** ist relativ zu `maps/` (`video_file`, scripts/maps_manifest.py:51: `<pfad>.mp4`).
- **`steps[i]`** ist der Step von Frame `i`. Die Steps stammen aus den Kartennamen in `data/<pfad>/` (Gültigkeitszeiten): `file_step` (scripts/maps_manifest.py:31) rechnet `YYYYMMDDHH` in Stunden ab Run um, `YYYYMMDD` (Tagesprodukte `tmax`/`tmin`) ab 00 UTC des Tages, negative Werte auf 0 geklemmt; andere Namen werden ignoriert. Sortiert nach Step = Frame-Reihenfolge (`chart_frames`, :44).
- **Steps sind unregelmäßig:** bis +144 h alle 3 h, danach alle 6 h (65 Frames); Produkte beginnen unterschiedlich (`weather_summary` ab +3 mit 64 Frames, `dt850_24h` ab +24).
- **`fps`** stammt aus `FPS` (scripts/maps_manifest.py:22), den auch `encode_video` verwendet, und gilt für alle Videos; die App rechnet nur mit dem Manifestwert.
- **Der Slider läuft in 1-h-Schritten** (0…`MAX_STEP`). `ChartIndex.frame` (src/model/ChartIndex.ts:50) liefert den letzten Frame mit `step <= slider` (lineare Suche); liegt der Slider vor dem ersten Frame, zeigt `ChartImage` einen Platzhalter „ab +N h“.
- **Seek:** `frameTime` (src/model/ChartIndex.ts:78) = `(index + 0.5) / fps`, die Mitte des Frames, damit Rundung im Browser nie auf dem Nachbarframe landet. Mit einem Keyframe alle 8 Frames dekodiert ein Seek höchstens 7 Frames nach.
- **Ganzes Video statt Streaming:** `loadVideo` (src/services/videoLoader.ts:13) lädt die Datei per `fetch` komplett und spielt sie als Object-URL ab, damit jeder Slider-Seek lokal dekodiert statt auf Range-Requests zu warten. Das Promise bleibt pro URL für die Lebensdauer der Seite gecacht (auch ein Fehlschlag), Object-URLs werden nie freigegeben.
- **Pfeiltasten** springen zum nächsten/vorigen Step, den irgendeine *sichtbare* Layer-Karte hat (`index.steps(visible)`, src/components/ChartGrid.tsx:34-48); auf dem fokussierten Slider (Event-Target `HTMLInputElement`) bleibt die native 1-h-Bewegung. Escape schließt die Großansicht.
- **Start-Step** ist die aktuelle Stunde seit Run, abgerundet und auf 0…240 geklemmt (`currentStep`, src/components/ChartGrid.tsx:17).
- **Cache:** Video-URLs tragen `?run=<run>` (`videoUrl`, src/model/ChartIndex.ts:72), weil jeder Lauf dieselben Dateinamen wiederverwendet. Das Manifest selbst wird mit `cache: 'no-cache'` geladen.

### Tile-Videos (scripts/tile_videos.py)

`encode_video(frames, target)` (scripts/tile_videos.py:31) öffnet jede Karte mit Pillow, konvertiert sie nach RGB und schreibt die Bytes als `rawvideo rgb24` 1200×690 über stdin an ffmpeg. Ausgabe zuerst nach `<target>.part`, bei Erfolg per `replace` nach `target`.

| Einstellung | Wert | Zweck / Herkunft |
| --- | --- | --- |
| Codec | `libaom-av1`, `-crf 20 -b:v 0` (konstante Qualität), `-cpu-used 6` | Aus einem Encodervergleich auf `z500_t850` gegen die verlustfreien Karten: libaom CRF 20 mit Screen-Tuning ≈ 7 MB bei gleicher PSNR wie WebP q90 mit 17 MB (laut User) |
| `tune-content=screen` | über `-aom-params` | schaltet Palettenmodus und Intra Block Copy ein, passend für flache Farben und Linien (Modul-Docstring) |
| `KEYFRAME_INTERVAL` (`-g`) | 8 | hält jeden Seek kurz |
| Pixelformat, Farbe | 4:2:0 (`yuv420p`), BT.709 Matrix/Primaries/Transfer, TV-Range | Die Karten sind sRGB; die BT.709-Tags lassen den Browser die Farben so zurückrechnen, wie sie kodiert wurden (Kommentar :25) |
| `FPS` | 10 | nur Zeitbasis für die Frame-Adressierung, das Video wird nie abgespielt |
| Container | MP4, `+faststart`, ohne Ton (`-an`) | |

Gemessen (laut User): Kodieren aller 10 Kachel-Videos ≈ 1:45 min mit 3 parallel, ein Video ≈ 27 s.

## Projektion und Ortsmarker

`Projection` (scripts/lib/projection.py:31) und `ChartProjection` (src/model/ChartProjection.ts:17) bilden dasselbe Modell: polarstereografisch, Nullmeridian senkrecht, Ursprung oben links, y nach unten, Kartenfläche 1200×600.

```
rho = scale_k * tan(45° - lat/2);  x = pole_x + rho*sin(lon);  y = pole_y + rho*cos(lon)
```

| Fenster | pole_x | pole_y | scale_k | Gradnetz |
| --- | --- | --- | --- | --- |
| opencharts_europe | 481.0 | −180.8 | 1320.8 | 10° |
| opencharts_central_europe | 435.35 | −1021.0 | 3493.4 | 5° |

Die Werte stehen doppelt: scripts/lib/projection.py:71-73 und `PROJECTIONS` (src/model/ChartProjection.ts:38), außerdem in jeder `geometry.json`. Laut Modul-Docstring Least-Squares-Fits an gemessene Passpunkte der ECMWF-Opencharts-Fenster (RMS 0,45 bzw. 0,4 px); Mitteleuropa = Rechteck x 316–770, y 205–432 des Europafensters, 2,645-fach vergrößert. Sie sind für die Europafenster statisch und werden sich nicht ändern (laut User). Der Nordpol liegt über beiden Bildern; `GribCropper.for_windows` verlässt sich darauf (Extreme liegen auf dem Bildrand). Python hat `pixel_to_latlon`, die App keine Rückwärtstransformation.

App: `toPixel` liefert `null` außerhalb der Kartenfläche 1200×600; die Legende (90 px) zählt nicht dazu. Der Marker wird in Prozent von 1200×690 positioniert (src/components/ChartImage.tsx:65-68) und hat feste Bildschirmgröße (10 px), damit er auf verkleinerten Kacheln sichtbar bleibt. Unbekanntes Fenster → kein Marker.

## GRIB-Vorhersagedatei

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

**Lokale Parameter** (`LOCAL_NAMES`, scripts/lib/local_params.py:12): Disziplin 0, Kategorie 192, `parameterNumber` 0 `inv`, 1 `rhbl`, 2 `psig`, 3 `snowl`, 4 `uf`, 5 `vf`. ecCodes liest sie als shortName `unknown`; `ForecastGrib._name` (scripts/lib/forecast_grib.py:49) ersetzt das durch den Namen (unbekannte Nummer → `local<n>`). Die Nummern sind Vertrag mit dem Skill.

**Fehlende Werte:** `encode` (scripts/lib/derived_writer.py:48) schreibt NaN als Bitmap-Missing; `ForecastGrib._read` macht daraus wieder NaN. NaN entsteht bei `inv`/`rhbl`/`uf`/`vf` unter dem Modellboden, bei Höhenwerten außerhalb der Profil-Ebenen (Wind auf 3000 m überall dort, wo gh700 < 3000 m, weil u/v nur bis 700 hPa reichen) und bei `deg0l`/`snowl`, wo 500 hPa noch > 0 °C hat. `snowl` ist überall gesetzt, nicht nur bei `psig` (die Karte `snow_line` maskiert selbst).

`WEATHER_PARAMS` (`tcc`, `tp`, `ptype`; scripts/lib/constants.py:10) speisen nur `weather_summary`; die abgeleiteten Felder lassen sie aus, weil ein 9-km-Globalmodell Nebel, Hochnebel und deren Niederschlag falsch trifft (Kommentar dort). `tp` akkumuliert ab T+0 in m.

**Index** von `ForecastGrib` (scripts/lib/forecast_grib.py:19): Schlüssel `(shortName, level, endStep)` → `(startStep, Byte-Offset)`, **ohne typeOfLevel**. `t` auf 850 hPa und `t` auf 2000 m unterscheiden sich nur über `level`. `field()`/`message()` mit `level=None` liefern den ersten Treffer in Dateireihenfolge (nur für Einzelebenen-Parameter sicher). Arrays sind float32 und **read-only** (über `lru_cache` geteilt, `CACHED_FIELDS` = 64 pro Instanz ≈ 250 MB, pro Prozess).

### Gitter und Koordinaten

`ForecastGrib.grid` und `ClimateArchive.grid` teilen die Schlüssel `lat0, lon0 (−180…180), dlat, dlon, ni, nj` (Archiv zusätzlich flache Arrays `lat`, `lon`). `PixelGrid` rechnet `row = (lat0 − lat)/dlat`, `col = ((lon − lon0) % 360)/dlon`, setzt also reguläre Gitter mit Zeilen Nord → Süd voraus. Resampling bilinear (`map_coordinates` order 1, `mode="nearest"`: außerhalb des Quellgitters Randwert), optional Gauß-Glättung in km (zonal exakt bei `SMOOTH_REF_LAT` 50°); `nearest()` (order 0) für Codes (`ptype`); `wind_vectors` dreht u/v über die Richtung zum Pol je Pixel.

### Freie Atmosphäre (Diagnostics)

Alle Diagnosen nutzen nur Druckflächen; eine Fläche zählt nur, wo ihr Geopotential mehr als `ABOVE_GROUND_MARGIN` = 20 gpm über dem Modellboden liegt (`above_ground`, scripts/lib/diagnostics.py:31), sonst NaN (`free`). Dieselben Klassen rechnen die abgeleiteten GRIB-Felder **und** die Karten (ChartProducts liest die abgeleiteten Felder nicht aus der Datei, sondern rechnet neu).

| Diagnose | Definition | Ort |
| --- | --- | --- |
| inversion (`inv`) | `fmax(t925 − t1000, t850 − t925)`, t1000/t925 per `free` maskiert; > 0 = Inversion | diagnostics.py:39 |
| moist_boundary_layer (`rhbl`) | `fmax(r925, r1000)`, beide maskiert | :51 |
| precipitation_signal (`psig`) | `max(r850, r700) ≥ PRECIP_RH` (90) und Gauß-geglättetes (σ 4 Gitterpunkte) `w700 < 0`; unmaskiert | :55 |
| freezing_level (`deg0l`) | `HeightProfile.freezing_level`: 0-°C-Durchgang von oben gesucht (Obergrenze einer Warmschicht über Kaltluftsee); ganz gefroren oder Durchgang unter Grund → Bodenhöhe; 500 hPa > 0 °C → NaN | height_profile.py:40 |
| snow_line (`snowl`) | `max(freezing_level − 350 m, ground)` | diagnostics.py:68 |

`HeightProfile.at_height` (scripts/lib/height_profile.py:30) interpoliert linear in gpm zwischen den Nachbarflächen, die den Parameter haben; NaN außerhalb. `PRECIP_RH` und `SNOW_LINE_BELOW_FREEZING_M` stehen in chart_styles.py und wirken auf Karten und GRIB gleichzeitig.

### Tagesextreme

`EXTREME_WINDOWS` (scripts/lib/extreme_windows.py:8): Max 06–18 UTC des Tages, Min 18 UTC Vortag – 06 UTC. `ExtremeWindows.parts` sammelt alle `mx2t3/mx2t6` (bzw. `mn…`)-Intervalle innerhalb des Fensters und akzeptiert sie nur, wenn ihre Längen exakt die Fensterlänge ergeben; sonst fehlt der Tag. Dieselbe Klasse dient `ForecastGrib` (vorhandene Datei) und `RequestPlan` (Zählung vor dem Download). Tage sind UTC-Kalendertage; der `endStep` der `mx2t`/`mn2t`-Nachricht liegt auf dem Tag selbst.

### Klimatologie

`ClimateArchive` (scripts/lib/climate_archive.py:45) indiziert **jedes** `<dir>/*.grb2`, egal wie die Felder auf Dateien verteilt sind; `PERIOD` = `1991–2020` (nur Beschriftung). Schlüssel `(kind, statistic, level, month, day)`, abgefragt mit `field(kind, statistic, level, month, day)`, `keys(kind)` liefert `(statistic, level, month, day)` einer Art (für `GribAnalyze` im Skill): kind `HHz` (Terminstunden aus den vorhandenen Nachrichten), `daily`, `monthly`; statistic `mean`/`std`; level 850 (T850) oder 2 (T2m); day None bei `monthly`; Werte in K. Der Index entsteht beim ersten Zugriff ohne ecCodes aus den Bytes jeder Nachricht (`_headers`, `_key`, scripts/lib/climate_archive.py:164-201): Sektion 1 Monat/Tag/Stunde der Referenzzeit (Jahr ignoriert), Template 4.8 erste Fläche (Typ 100 Pa → hPa, Typ 103 m), Anzahl Zeitbereiche (1 = Termin, 2 = `daily`, 3 = `monthly`) und statistischer Prozess des **äußersten** Bereichs (0 = Mittel, 6 = Streuung). Grund: ecCodes braucht für die 13 224 Kopfteile ≈ 4,8 s, die Bytes ≈ 0,09 s, und jeder Render-Worker baut sein eigenes Archiv (`init_worker`). Nicht über `shortName` unterscheiden: ecCodes nennt bei `daily`/`monthly` auch die Streuung `avg_t`/`avg_2t`. Der Byte-Index ist gegen den ecCodes-Index geprüft (gleiche Schlüssel und Offsets). Ein anderes Template als 4.8 oder ein Kopfteil über `HEADER_BYTES` (512) bricht mit `ValueError` ab. Felder werden bei Bedarf aus der Datei gelesen und dekodiert (Cache unbegrenzt). `T850Climate` braucht für **jede** Stunde der Gültigkeitszeiten ein `HHz`-Kind, sonst `ValueError` aus `term_kind`. Im Repo nutzt nur `t850_anomaly` die Klimatologie (`period` steht im Kartentitel).

### Kontaktabzüge und geometry.json

`ContactSheet` (scripts/lib/contact_sheet.py:26): 2 Spalten × 580 px (Skalierung 0,4833), Kachelhöhe 290, Kopf 26 px, darunter die Legende der ersten Karte ohne ihre ersten 26 px, 62 px hoch. Höhe = 26 + Zeilen × 290 + 62: 10 Kacheln (00z-Lauf) → 1538 px, 11 Kacheln (12z-Lauf, T+0…T+240) → 1828 px. `STEP`-Produkte: Karten mit Gültigkeit `SHEET_HOUR` = 12 UTC; `DAY`-Produkte: jeder Tag; `orography` keinen Abzug. `origins(n)` liefert die Kachel-Ecken, die `write_geometry` unter `sheets.tiles.<produkt>` ablegt. `write_geometry` übernimmt Einträge anderer Produkte aus einer vorhandenen Datei, damit Einzelprodukt-Läufe ergänzen statt überschreiben.

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
| `WINDOWS` | scripts/update_maps.py:46 | `opencharts_europe` → `"all"`, `opencharts_central_europe` → None (Defaults) |
| `CHARTS_DOC` | scripts/update_maps.py:44 | data/charts.md im Repo |
| `PARALLEL_ENCODES` | scripts/update_maps.py:48 | 3 ffmpeg-Prozesse gleichzeitig; libaom nutzt je mehrere Threads |
| `CONFIG`, `MANIFEST` | scripts/maps_manifest.py:19-20 | Pfad der Viewer-Config, `manifest.json` |
| `FPS` | scripts/maps_manifest.py:22 | 10; Bildrate beim Kodieren und `fps` im Manifest |
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
| `CACHED_FIELDS` | scripts/lib/forecast_grib.py:16 | 64 Felder ≈ 250 MB pro `ForecastGrib`, pro Prozess |

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
| `ABOVE_GROUND_MARGIN`, `OMEGA_SIGMA` | scripts/lib/diagnostics.py:19-21 | 20 gpm; 4 Gitterpunkte Glättung von w700 (verrauscht über Gebirge) |

### Karten

| Konstante | Ort | Wert / Bedeutung |
| --- | --- | --- |
| `STEP`, `DAY`, `STATIC`, `ALL`, `CLIMATE` | scripts/lib/chart_products.py:42-47 | Produktregister; `ALL` = alle drei Gruppen |
| `DEFAULTS` | scripts/lib/chart_products.py:48-55 | Europa: `z500_t850`, `z700_t700`, `z850_rh700`, `thickness_mslp`, `dt850_24h`; Mitteleuropa: `t850_mslp`, `t850_anomaly`, `rh700_wind700`, `vt_rh700`, `t2m_wind1000`, `wind10m`, `inversion`, `mountain_2000`, `freezing_level`, `snow_line`, `tmax`, `tmin`, `orography`, `weather_summary` |
| `CHANGE_HOURS`, `PRECIP_HOURS`, `TCC_PERCENT` | scripts/lib/chart_products.py:22-25 | 24 h für `dt850_24h`; 6-h-Niederschlag (3 h bei T+3); tcc 0–1 → % |
| `SHEET_HOUR` | scripts/render_charts.py:72 | 12 UTC-Karten im Kontaktabzug |
| `LEGEND_HEIGHT` | scripts/lib/chart_canvas.py:31 | 90 px unter 1200×600 → Bilder 1200×690 |
| `BAR`, `NOTES_X` | scripts/lib/chart_canvas.py:33-34 | Farbskala (8, 760); Notizspalte ab x 800, eine Notiz pro 13-px-Zeile |
| `WEBP_QUALITY` | scripts/lib/chart_canvas.py:37 | 90, nur für Kontaktabzüge; Einzelkarten verlustfrei |
| `EXTREMA_BORDER_PX` | scripts/lib/chart_canvas.py:43 | kein L/H näher als 20 px am Rand |
| `STREAMLINE_GRID_PX` | scripts/lib/chart_canvas.py:45 | `streamlines` integriert auf jedem 4. Pixel (300 × 150 Punkte) |
| `WIND10M` | scripts/lib/chart_styles.py:161 | km/h, Bandgrenzen = Beaufortgrenzen 6/12/20/29/39/50/62/75/89/103/118 km/h |
| `STREAMLINE_SMOOTH_KM`, `STREAMLINE_DENSITY` | scripts/lib/chart_styles.py:167-169 | 15 km Glättung von u/v nur für die Stromlinien (die Farben bleiben ungeglättet); `density` 3 von `streamplot`. Beides nach Augenmaß gewählt |
| `COLUMNS`, `TILE_WIDTH` | scripts/lib/contact_sheet.py:19-20 | 2 × 580 px, damit 10 Kacheln unter 1568 px Höhe bleiben (darüber verkleinern Modelle Bilder) |
| `LEGEND_SKIP` | scripts/lib/contact_sheet.py:23 | erste 26 px der Legende (Gültigkeitszeit) nicht übernommen |
| `MARGIN_PX` | scripts/lib/base_map.py:12 | Ringe bleiben, wenn ein Punkt ≤ 50 px vom Bild entfernt liegt |

Literale in den Produktmethoden, alle empirisch bestimmt (laut User): Z500- und Z700-Zentren (scripts/lib/chart_products.py:163, :175) L-Fenster 121 px, H-Fenster 181 px, `min_depth` 2 dam, 60 km Vorglättung; MSLP-Zentren (`isobars`, :226) 81/161 px, 2 hPa, 60 km; Pfeile `rh700_wind700` (:260) Raster 30 px, 1,2 px pro m/s, Referenz 20 m/s; `t2m_wind1000` (:294) 30 px, 2,5 px pro m/s, 10 m/s; `mountain_2000` (:328-329) 30 px, 1,5 px pro m/s, 20 m/s. Die Z850-Zentren von `z850_rh700` (:193) verwenden dieselben Literale wie Z500.

### chart_styles.py (Schwellen; Begründungen aus den Code-Kommentaren)

| Konstante | Zeile | Wert / Bedeutung |
| --- | --- | --- |
| `T850`, `T700`, `THICKNESS`, `RH700` | 15, 29, 54, 67 | aus den ECMWF-Opencharts-Legenden kopiert (medium-z500-t850, medium-t-z 700, medium-thickness-mslp, medium-uv-rh) |
| `T2M`, `MOUNTAIN_T` | 51, 203 | Bänder von T850: eine Farbe = eine Temperatur auf allen Karten |
| `T850_ANOMALY` | 45 | σ-Bänder; ≥ 1 auffällig, ≥ 2 ungewöhnlich |
| `ROUGH_TERRAIN_SDOR` | 116 | 200 m sdor: echte Tal-/Gipfelhöhen weichen um mehrere 100 m ab |
| `HIGH_GROUND_M`, `ABOVE_1000HPA_M`, `ABOVE_850HPA_M` | 119-121 | 700 / 500 / 1300 m Modellhöhe: Inversionskarte grau, keine 1000-hPa-Pfeile, T850-basierte Flächen maskiert bzw. gestrichelte Linie in `t850_mslp`/`z850_rh700` |
| `PRECIPITATION`, `CLOUD_COVER` | 134, 139 | nach den ogimet-Bodenkarten; ungefärbt unter 0,2 mm / 40 % |
| `PRECIP_TYPES` | 148 | ptype 5 Schnee; 6/7 nasser Schnee, Schneeregen; 3/8/12 gefrierender Regen/Niesel, Eiskörner; Regen (1) ohne Symbol |
| `PRECIP_BAR`, `CLOUD_BAR` | 156-157 | zwei Farbskalen nebeneinander (links, Breite px) |
| `Z500`, `Z700`, `Z850`, `MSLP`, `MSLP_DETAIL`, `MSLP_SUMMARY` | 160-169 | 4 dam (fett 528/552/576); 5 dam (fett 270/290/310); 4 dam (fett 140/152/164); 5 hPa Europa; 2 hPa Mitteleuropa (schwache Gradienten entscheiden Inversion/Föhn); 4 hPa `weather_summary` |
| `ISOTHERM_850` | 171 | 4-K-Isothermen an den Bandgrenzen, für `z500_t850` und `z700_t700` |
| `MOIST_LAYER_RH`, `WIND925_CALM` | 179, 181 | 90 % Nebel-/Hochnebelschicht; 5 m/s, darunter wird eine Inversion kaum ausgeräumt |
| `ASCENT_LINES`, `SUBSIDENCE_LINES` | 186-187 | ω700 −0,6/−0,2 und +0,2 Pa/s |
| `PRECIP_RH` | 193 | 90 %, Niederschlagssignal (auch Diagnostics/`psig`) |
| `SNOW_LINE_BELOW_FREEZING_M` | 196 | 350 m Schmelzstrecke (300–400 m) (auch `snowl`) |
| `MOUNTAIN_HEIGHT_M`, `SUMMIT_CLOUD_RH` | 200-201 | 2000 m Kartenhöhe (getrennt von `MOUNTAIN_HEIGHTS` definiert), 95 % = in Wolken |
| `VALUE_SPACING_PX` | 205 | 80 px (~250 km) Raster gedruckter Werte, nur Detailfenster |

## Externe Systeme

**ECMWF Opencharts epsgrams** (`fetchMeteogramUrl`, src/services/ecmwfMeteogram.ts:28): `POST` ohne Auth, `mode: 'cors'`, Body `{"location":{"type":"latlon","lat":…,"lon":…,"station_name":""},"axis":{},"epsgrams":"<name>"}`. Antwort `result.url` ist die Bild-URL; das Bild existiert erst nach diesem Request. Fehlt `result`, wird nach 3 s bis zu 5-mal wiederholt. Gültige Namen in `viewer.config.json`: `classical_10d`, `classical_15d_with_climate`, `classical_plume`.

**ECMWF Open Data** über `ecmwf.opendata.Client(source="ecmwf", resol="0p1" | "0p25")`: `latest(type="fc", stream="oper", step=240, param="t", levelist=850)` findet den Lauf; `retrieve(date, time, type="fc", stream="oper", target, **gruppe)` lädt eine Gruppe (Byte-Ranges). Ohne Auth. HTTP 404 → „not (or no longer) published“. Die Fortschrittsbalken der Bibliothek lassen sich nicht abschalten, daher die stderr-Umleitung.

**data.ecmwf.int Verzeichnislisting** (`requests.get`, Timeout 30 s) nur für den Ankunftshinweis; jeder Fehler → kein Hinweis.

**git / GitHub**: Remote `origin` = github.com/schletz/wetterkartenviewer, Branch `main`. Der Branch `legacy` enthält die alte App, dient nur als Archiv und hat für diese App keine Bedeutung (laut User). Der Workflow läuft bei Push auf `main` und manuell, `concurrency: pages` mit `cancel-in-progress`. Node 24 in CI.

Rendern, Kodieren, Manifest und App-Build sind offline. ffmpeg ist ein externer Prozess (`ffmpeg` im PATH), Fortschritt unterdrückt (`-loglevel error`); stderr wird erst nach dem letzten Frame gelesen.

## Details

- **Kartendateien** heißen nach Gültigkeitszeit (UTC), Tagesprodukte nach UTC-Datum; `orography.webp` liegt direkt im Fensterordner, kein Produktordner. `weather_summary`-Keys sind die `tp`-Steps > 0; Niederschlag = `tp(step) − tp(step − min(6, step))`, bei 0 geklemmt, in mm; Symbole nur, wo ptype passt und ≥ 0,2 mm fallen. `dt850_24h`-Keys sind Steps mit vorhandenem `step − 24`.
- **Detailmodus** `ChartProducts.detail` = `scale_k` größer als Europa: dichtere Isobaren und gedruckte Werte (`print_values`, standardmäßig nur über Land).
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
| Download scheitert (in update_maps) | `sys.exit` mit Exit-Code-Meldung |
| Rendern eines Fensters scheitert | `sys.exit` mit stdout/stderr des Renderers; `maps/manifest.json` fehlt danach, bei neuem Lauf ist `maps/<fenster>/` schon geleert |
| Layer ohne Video, dessen Karten nicht in `data/` liegen (z. B. Nicht-Default-Produkt auf Mitteleuropa) | `encode_missing` beendet mit `no charts in data for …; render them or remove them from the tiles`, bevor irgendein Video kodiert wird; Manifest fehlt |
| ffmpeg nicht im PATH | `FileNotFoundError` aus `Popen` im Encoder-Thread → Traceback; Manifest fehlt |
| ffmpeg mit Exit ≠ 0 (z. B. ohne libaom-av1) | `RuntimeError` mit ffmpeg-stderr, `.part` gelöscht → Traceback, sobald `pool.map` dieses Ergebnis erreicht; die übrigen Layer werden trotzdem fertig kodiert (der Pool wartet beim Verlassen), Manifest fehlt |
| Karte nicht lesbar während des Kodierens | Pillow-Ausnahme → Traceback; ffmpeg schließt das Video mit den bisherigen Frames ab, `<layer>.mp4.part` bleibt liegen (der nächste Aufruf zählt als neuer Lauf und leert `maps/<fenster>/`) |
| Fehlendes Feld in einem Produkt | `KeyError` aus `ForecastGrib.field`, via `pool.map` → Traceback |
| Klimatologie fehlt, Aufruf über `update_maps.py` | `check_climate` beendet mit Meldung und Exit 1, bevor etwas geladen oder gelöscht wird (Manifest bleibt) |
| Klimatologie fehlt, `render_charts.py` direkt mit CLIMATE-Produkt | `FileNotFoundError` in `ClimateArchive.__init__`, ungefangen |
| Gültigkeitsstunde ohne `HHz`-Datei | `ValueError` aus `term_kind`, ungefangen |
| `t850_anomaly` ohne Klimatologie | `ValueError` (render_charts verdrahtet sie für `CLIMATE`-Produkte immer) |
| Fenster ohne `DEFAULTS`-Eintrag und ohne `--products` | `KeyError` in `parse_args` |
| `publish_maps.py` ohne Manifest, ohne Videos darin oder mit fehlendem Video | Abbruch vor jedem Upload („run update_maps.py …“) |
| `gh` fehlt oder ist nicht angemeldet | `FileNotFoundError` (fehlt) bzw. `sys.exit` mit gh-stderr; nichts committet |
| Upload bricht mittendrin ab | `sys.exit`; einige Assets sind schon ersetzt, das Manifest ist nicht committet. Der nächste Aufruf lädt alle Videos erneut |
| Push abgelehnt (Remote weiter) | `sys.exit` mit git-stderr; der lokale Manifest-Commit bleibt, nach `git pull --rebase` pusht der nächste Aufruf ihn mit |
| `fetch_maps.py`: Asset fehlt (404) oder Netzfehler | `sys.exit` mit URL; Deploy scheitert, die alte Seite bleibt |

Kein Logging-Framework, keine Tests, keine Retries außer in `GroupDownloader` und `fetchMeteogramUrl`.

## Erweiterungspunkte

**Layer zu einer Kachel hinzufügen oder neue Kachel** — `src/config/viewer.config.json` (`tiles[].layers`, Format `fenster/produkt`). Das Produkt muss in `data/` gerendert werden: auf `opencharts_europe` jedes Produkt, auf `opencharts_central_europe` nur die Defaults (sonst Abbruch in `encode_missing`, siehe Fehlerbehandlung, und vorher *Nicht-Default-Produkt auf Mitteleuropa*). Wirksam mit dem nächsten `download_data.cmd`, auch ohne neuen Lauf: Bei gleichem Lauf wird nichts gerendert, nur der neue Layer kodiert (ein Video ≈ 27 s, laut User), das Manifest neu geschrieben und per `publish_maps.py` veröffentlicht. Code in App oder Pipeline muss nicht angefasst werden. `orography` (Datei, kein Ordner) und `sheets` taugen nicht als Layer.

**Layer entfernen** — Eintrag aus `tiles[].layers` streichen. Ab dem nächsten Aufruf fehlt er im Manifest, die App zeigt ihn also nicht; sein Video bleibt aber in `maps/` liegen und wird mitveröffentlicht, bis ein neuer Lauf oder `--force` `maps/<fenster>/` leert. Sofort weg nur durch Löschen der MP4 von Hand.

**Kodiereinstellungen ändern** — `CODEC`, `COLOUR`, `KEYFRAME_INTERVAL` (scripts/tile_videos.py:22-28), `FPS` (scripts/maps_manifest.py:22). Bestehende Videos werden bei gleichem Lauf nicht neu kodiert: entweder `--force` (rendert auch neu) oder die MP4-Dateien in `maps/<fenster>/` löschen und `download_data.cmd` aufrufen — dann werden nur sie kodiert. `FPS` geht über das Manifest an die App, dort ist nichts nachzuziehen. Ein größeres `KEYFRAME_INTERVAL` macht Videos kleiner und Seeks langsamer.

**Nicht-Default-Produkt auf Mitteleuropa** — `WINDOWS` (scripts/update_maps.py:46) für `opencharts_central_europe` auf eine kommagetrennte Produktliste oder `"all"` setzen (der String geht unverändert als `--products` an render_charts.py) oder `DEFAULTS` erweitern. Beides ändert, was der Skill in `data/` findet; data/charts.md (Tabelle der Fenster) nachziehen.

**Neues Kartenprodukt** — Methode mit dem Produktnamen in `ChartProducts` (scripts/lib/chart_products.py; `(self, step)` für Step-Produkte, `(self)` für statische), Name in `STEP` oder `STATIC` (`DAY` bildet einen Namen auf `"max"/"min"` ab). In `DEFAULTS` der Fenster, die es standardmäßig rendern, und in `CLIMATE`, falls es `self.climate` nutzt. Bei gleichem Lauf rendert `update_maps.py` nichts neu: ein neues Produkt erst mit `--force` (oder neuem Lauf), sonst bricht `encode_missing` ab, wenn es als Layer in der Config steht. Braucht es neue GRIB-Felder, die Gruppe in `RequestPlan` (scripts/lib/request_plan.py:24) erweitern: `expected_total` wächst mit, die vorhandene Datei gilt danach als unvollständig und wird neu geladen. Gibt es das Produkt nicht zu jedem `t`-Step, `keys()` (:79) wie bei `dt850_24h`/`weather_summary` erweitern. Skalen/Schwellen in chart_styles.py. Kontaktabzüge und `geometry.json`-Einträge kommen für `STEP`/`DAY` automatisch. Von Hand mitziehen: Produktliste im Docstring von scripts/render_charts.py:8-26 (= `--help`) und ein Abschnitt in data/charts.md (Vertrag mit dem Skill).

**Neuer GRIB-Parameter** — Gruppe in `RequestPlan.__init__` (scripts/lib/request_plan.py:24) ergänzen oder erweitern; jede Gruppe muss ein vollständiges kartesisches Produkt dessen sein, was Open Data wirklich publiziert, sonst stimmt `expected()` nie und die Gruppe scheitert als unvollständig. Bestehende Vorhersagedateien gelten danach als unvollständig und werden neu gebaut (vollständige Rohgruppen werden wiederverwendet). Modul-Docstring von download_ecmwf_data.py und Tabelle in data/charts.md nachziehen.

**Neues abgeleitetes Feld** — in `step_messages` (scripts/lib/derived_writer.py:86) erzeugen und **`PER_STEP` (:35) von Hand passend halten** — die Formel spiegelt die Schleifen in `step_messages`, ist aber nicht daraus abgeleitet; eine Abweichung lässt `output_complete` nie wahr werden (jeder Lauf lädt neu). Ohne WMO/ECMWF-Parameter: nächste freie Nummer in `LOCAL_NAMES` (scripts/lib/local_params.py:12), bestehende Nummern nie umdeuten. Einmalige Felder wie `orog` zusätzlich im `+ 1` von `expected_total` (scripts/lib/request_plan.py:57) berücksichtigen. data/charts.md ergänzen.

**Neue Höhe in `MOUNTAIN_HEIGHTS`** — nur Werte, die nicht mit einem Druckflächen-Level übereinstimmen (500, 600, 700, 850, 925, 1000): der `ForecastGrib`-Index unterscheidet keine Ebenentypen, eine Höhe 1000 m würde t1000 hPa im Index überschreiben. `PER_STEP` folgt automatisch; charts.md nachziehen.

**Neue Druckfläche** — `PROFILE_LEVELS` (scripts/lib/constants.py:14) für t, r, gh und das Höhenprofil (nur von Open Data publizierte Flächen, kein 800 hPa); für Wind die Listen der Gruppen `uvw700`/`uv_low`.

**Neues Kartenfenster** — `Projection` in `PROJECTIONS` (scripts/lib/projection.py:71-74), Eintrag in `ChartProducts.DEFAULTS` (Pflicht), `WINDOWS` (scripts/update_maps.py:46) und `PROJECTIONS` (src/model/ChartProjection.ts:38). Die Zuschnittbox wächst automatisch; alte Vorhersagedateien behalten die alte Box. `detail` greift für `scale_k` > Europa. Andere Bildgröße als 1200×690 betrifft `IMAGE_*` (beide Seiten), `WIDTH`/`HEIGHT` in scripts/tile_videos.py:21, `aspect-ratio` in ChartImage.module.css, die 1200 px in LargeView.module.css und `ContactSheet`.

**Klimatologie tauschen** — `PERIOD`/`DIRECTORY` (scripts/lib/climate_archive.py:27-29) bzw. `--climate`; `check_climate` in update_maps.py nutzt `DIRECTORY`. Kommt kein CLIMATE-Produkt mehr in `WINDOWS` vor, `check_climate` entfernen, sonst verlangt der Lauf die Dateien weiter. Anforderungen: GRIB2-Dateien `*.grb2`, Template 4.8 mit den Merkmalen, die `_key` liest, je Feld genau eine Nachricht, `HHz` für jede vorkommende Stunde (00…21 alle 3 h), T850 in K, reguläres Gitter Nord → Süd. Der Skill synop liest denselben Ordner mit einer eigenen Kopie von `ClimateArchive`. Neue Dateien nach `data/era5_means/` kopieren (alte, die es nicht mehr gibt, löschen) und den Download-Link in README.md anpassen.

**Weiteres Meteogramm** — Name in `meteograms`; Layout (drei pro Zeile) in Meteogram.module.css.

**Neue Seite** — `Route` und `currentRoute`/`navigate` in src/hooks/useHashRoute.ts, Verzweigung in src/App.tsx. Es gibt keinen Router.

**Andere Slider-Reichweite** — `MAX_STEP` (src/components/StepSlider.tsx:3); `currentStep` in ChartGrid klemmt mit demselben Wert.

**Neues Tastenkürzel** — `onKey` in src/components/ChartGrid.tsx:37. Eingaben in `<input>` werden für Pfeiltasten bewusst ignoriert.

**Ortswahl erweitern** (z. B. Name, Höhe) — `GeoLocation` und `isValidLocation`; gespeicherte alte Objekte laufen durch `isValidLocation` in `load()` (src/hooks/useStoredLocation.ts:6).

## Fallstricke

- **Destruktiv:** `update_maps.py` löscht GRIBs, `.raw/` und `.part` anderer Läufe in `data/`, bei jedem Aufruf `maps/manifest.json`, bei jedem Rendern `data/<fenster>/` und bei neuem Lauf oder `--force` `maps/<fenster>/` komplett — vor dem Rendern, ein Fehlschlag hinterlässt also ein leeres `maps/` (die veröffentlichten Videos bleiben im Release). `download_ecmwf_data.py` ersetzt das Ziel (atomar über `<out>.part`) und löscht `<out>.raw/`. `publish_maps.py` ersetzt und löscht Release-Assets: Videos früherer Läufe gibt es nirgends mehr.
- **Render- und Kodierentscheidung nur über `maps/manifest.json`:** Nennt es den geladenen Lauf, wird nur gerendert, wenn ein Fensterordner in `data/` ganz fehlt — ein unvollständiger Ordner wird nicht erkannt —, und nur kodiert, was in `maps/` kein Video hat. Ein vorhandenes Video wird nie auf Aktualität oder Vollständigkeit geprüft.
- **Video und Steps können auseinanderlaufen:** Das Manifest liest die Steps bei jedem Aufruf aus `data/`, ein vorhandenes Video bleibt. Wer `data/<fenster>/<produkt>/` außerhalb von `update_maps.py` ändert (z. B. `render_charts.py --products` mit anderem GRIB), muss das zugehörige Video löschen, sonst passt `steps[i]` nicht zu Frame `i`.
- **Veröffentlicht wird, was das Manifest nennt:** `publish_maps.py` lädt nur dessen Videos hoch und löscht alle anderen Assets. Videos entfernter Layer und `.part`-Dateien in `maps/` bleiben lokal liegen (ignoriert).
- **`publish_maps.py` pusht `HEAD`** ohne Rückfrage, also auch lokale Code-Commits. Gestagte andere Änderungen bleiben gestagt, der Commit enthält nur das Manifest.
- **`gh` ist Pflicht** auf jedem Rechner, der publiziert; das Release-Asset-Limit liegt bei 2 GB je Datei. `download_data.cmd` endet ohne `pause`.
- **Ausführbar-Bit der `.sh`-Dateien** steht nur im git-Index (Windows kennt es nicht). Eine neue `.sh`-Datei mit `git add --chmod=+x` aufnehmen, sonst fehlt es nach dem Klonen auf macOS/Linux.
- **Vertrag mit dem Skill:** Produktnamen, Ordnerlayout, `geometry.json`-Schlüssel, GRIB-Namen/Ebenen und lokale Parameternummern nicht ändern, ohne den Skill nachzuziehen. data/charts.md beschreibt das alles von Hand und muss mitgepflegt werden.
- **Doppelte Werte, die synchron bleiben müssen:** Projektionsparameter (Python, TS); Bildgröße 1200×690 (chart_canvas.py, tile_videos.py, TS, CSS) — eine abweichende Kartengröße fällt beim Kodieren nicht auf, ffmpeg zerschneidet den Bytestrom dann falsch; `MOUNTAIN_HEIGHT_M` (Karte) vs. `MOUNTAIN_HEIGHTS` (GRIB); `PER_STEP` vs. `step_messages`; Produktnamen in `ChartProducts` vs. render_charts-Docstring und data/charts.md.
- **Laufzeit/Netz:** Der Download braucht Internet und holt alle Gruppen als globale 0,1°-Rohdateien (2211 Nachrichten) vor dem Zuschneiden; stderr ist währenddessen stumm. Danach mehrere Minuten Rendern auf allen CPUs und ≈ 1:45 min Kodieren (laut User) mit `PARALLEL_ENCODES` ffmpeg-Prozessen.
- **ffmpeg ist Pflicht:** Ohne `ffmpeg` mit `libaom-av1` im PATH bricht jeder `update_maps.py`-Lauf nach dem Rendern ab (Traceback), es gibt keine Vorabprüfung.
- **Browser-Speicher und AV1:** Jedes angezeigte Video liegt ganz als Blob im Speicher und wird bis zum Neuladen nie freigegeben (alle 10 Layer ≈ 52 MB). Die App setzt einen Browser mit AV1-Decoder voraus; ohne ihn bleiben Kacheln leer.
- **Speicher:** Beim Zuschneiden dekodiert jeder der bis zu 8 `ForecastWriter`-Worker ein globales Feld (≈ 100 MB). Jeder Render-Worker baut eigenen `ForecastGrib` (bis ~250 MB Cache), `BaseMap` (8,7-MB-GeoJSON) und ggf. Klimatologie; Default-Workerzahl = CPU-Zahl, zwei Fenster laufen parallel. `DerivedWriter` hält alle abgeleiteten Nachrichten aller Steps im Hauptprozess, bevor er sie anhängt.
- **Read-only-Arrays:** Ergebnisse von `ForecastGrib.field` nie in-place ändern.
- **Schnelltests teilen den Namen:** `--max-step` mit Ordnerziel schreibt trotzdem `ecmwf_<run>.grb2`; ein späterer Vollaufruf sieht eine andere Nachrichtenzahl und lädt neu.
- **Ordner vs. Datei als Ziel:** `download_ecmwf_data.py` behandelt `out` nur als Ordner, wenn er existiert.
- **Modellfelder unter Grund:** Werte auf 1000/925/850 hPa unter der Modellorografie extrapoliert das Modell; Diagnostics maskiert pro Gitterpunkt, die Karten maskieren dagegen über feste Modellhöhen (`ABOVE_850HPA_M` usw.); `z500_t850`, `dt850_24h` färben T850 überall.
- **Der Dev-Server** liefert `maps/` aus dem Repo-Root aus; Vite beobachtet `data/` und `maps/` nicht (vite.config.ts:11), ein neues Manifest braucht einen Reload. `base: './'` ist für den Pages-Unterpfad nötig; alle Pfade gehen über `import.meta.env.BASE_URL`.
- **Zeitzonen:** Run, Steps und Dateinamen sind UTC; der Slider zeigt nur `+N h`, die Gültigkeitszeit steht in der Kartenlegende.
- **StrictMode** führt Effekte im Dev doppelt aus; Meteogramm-Requests werden dabei abgebrochen und neu gestellt. `Meteogram` fragt ECMWF bei jedem Ortswechsel neu ab, kein Cache außer dem Browser-Bildcache.
- **Es gibt keine Tests**, kein Logging, keine requirements-Datei, keine Validierung des Manifests (die App vertraut dem JSON-Typ) und kein Aufräumen von `<out>.part` bzw. `<layer>.mp4.part` nach einer Ausnahme. `lint` ist oxlint mit Hooks-Regeln.
