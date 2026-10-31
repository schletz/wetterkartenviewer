# Wetterkartenviewer

Zeigt selbst gerenderte Karten des ECMWF IFS mit einem Zeitslider und auf der
Startseite drei ECMWF-ENS-Meteogramme. Die Seite: https://schletz.github.io/wetterkartenviewer/

## Karten aktualisieren

```
download_data.cmd      (Windows)
./download_data.sh     (macOS, Linux)
```

1. `scripts/update_maps.py` lädt den neuesten Lauf nach `data/` (GRIB mit abgeleiteten Feldern)
   und rendert dort beide Kartenfenster. Ältere Läufe werden gelöscht. Jeden Layer der Kacheln
   kodiert es als AV1-Video `maps/<fenster>/<produkt>.mp4` (ein Frame pro Termin),
   `maps/manifest.json` listet Videos und Termine. Kodieren braucht ffmpeg mit libaom-av1.
2. `scripts/publish_maps.py` lädt die Videos als Assets in das Release `tile-videos` (ersetzt die
   des vorigen Laufs), committet nur `maps/manifest.json` als „Data update <lauf>z“ und pusht.
   Dafür braucht es ein angemeldetes `gh`.
3. Der Push startet `.github/workflows/deploy.yml`. Es baut die App, holt die Videos, die das
   Manifest nennt, aus dem Release (`scripts/fetch_maps.py`) und veröffentlicht alles auf GitHub Pages.

`data/` ist in `.gitignore`, bis auf `data/charts.md`. `data/` dient auch dem Skill `synop` als
Datenordner, `data/charts.md` beschreibt ihm den Inhalt. Von `maps/` ist nur `manifest.json`
committet. Welche Videos nach `maps/` kommen, bestimmt allein
`src/config/viewer.config.json`. Nach einer Änderung dort genügt `download_data`: Gibt es
keinen neuen Lauf, kodiert es nur die Layer ohne Video nach. Videos entfernter Layer bleiben bis
zum nächsten Lauf liegen. Ein neuer Lauf oder `--force` leert `maps/` und baut alles neu.

Codeänderungen kommen als normale Commits ins Repo; `publish_maps.py` pusht sie beim nächsten
Lauf mit. Die Historie enthält so nur Code und pro Lauf einen kleinen Manifest-Commit, die Videos
liegen nur im Release.

## Klimatologie

`t850_anomaly` und der Skill `synop` brauchen die ERA5-Klimatologie 1991–2020 (422 MB). Sie ist
nicht im Repo. Nach dem Klonen einmal von
[Google Drive](https://drive.google.com/open?id=1kwR15ysJSWGjBXqyzyteZSQCXaQPgVXa) laden und als
`data/era5_means/era5_means.grb2` ablegen. Ohne sie bricht `download_data` vor dem Download ab.

## Kacheln

`src/config/viewer.config.json`:

- `tiles`: pro Kachel die Layer als `fenster/produkt` (Ordner unter `maps/`). Linksklick schaltet
  zum nächsten Layer, Rechtsklick öffnet die Karte 1:1 in einem verschiebbaren Fenster.
- `meteograms`: Namen der ECMWF-Meteogramme der Startseite.

Den Ort für Meteogramme und Kartenmarker stellst du auf der Startseite ein (localStorage).

## Entwicklung

```
npm install
npm run dev
```

Der Dev-Server liefert `maps/` direkt aus. Die App lädt jedes Video ganz und springt per
`currentTime` zum Frame des Termins. Pfeiltasten springen zum vorigen/nächsten Termin, Esc schließt
die große Ansicht.
