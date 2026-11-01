# synop `scripts/` — Agent reference

Reference for the six entry-point scripts and the package `lib/` of the synop skill, so that a later agent can extend, debug or refactor them without reading the whole source. Paths are relative to `scripts/` (the folder holding this file). How the analysing agent uses the outputs is in `../SKILL.md` (diagram and HTML report in `../references/html_report.md`); what the data directory holds and how each chart reads is in `charts.md` of the data directory.

## Purpose

- Read one ECMWF IFS run and one ICON-D2 run from a **data directory** that an external program, the viewer ("Wetterkartenviewer", laut User), writes. The scripts never derive or render; they only read the data directory and write to the paths given by `--out`/`--tsv`.
- The data directory is either a folder the user names or `../.cache`, which `fetch_data.py` mirrors from the public blob container the viewer pipeline fills (URL in `../download_url.txt`, not in the repo: the skill is public; `.cache/` and the URL file are git-ignored in `~/.claude/.gitignore`).
- Sample every field of either forecast GRIB at one location: Markdown tables on stdout plus a TSV of all values in GRIB units, one TSV per model.
- From the TSV plus the climatology `<data>/era5_means/`: SVG diagram of T850 and 1000–500 hPa thickness with the T850 anomaly; assemble the agent's Markdown, the SVG and the TSV into one self-contained HTML report.
- Copy the viewer's WebP charts and contact sheets with a point or lat/lon box drawn on.
- Helpers: calendar days with weekday and Austrian public holiday; `GribAnalyze` for ad-hoc climatology queries the agent writes itself (`../SKILL.md`, section "Klimavergleich").

## Module overview

### Entry points

Each script only parses arguments and wires `lib` classes. All insert their own directory into `sys.path` so that `python -I` works (e.g. location_table.py:54).

| File | Lines | Responsibility | lib classes used |
| --- | --- | --- | --- |
| location_table.py | 155 | sample every step at one point in a process pool, print Markdown, optional TSV; the file decides the model (`grib.grid is None` → ICON-D2) | ForecastGrib, GridPointSampler / CellPointSampler, StepSampler / IconStepSampler, LocationTables / IconLocationTables, ForecastTsv |
| generate_diagram.py | 93 | TSV + climatology → SVG diagram | ForecastTsv, ClimateArchive, T850Climate, DiagramRow, CoupledAxes, TimeAxis, AnomalyBands, ForecastDiagram |
| build_report.py | 115 | Markdown + SVG + TSV → one HTML file; holds the page CSS (`STYLE`, :23-46) | ForecastTsv, MarkdownHtml |
| mark_location.py | 93 | copy the charts of every window with a point or box drawn on | ChartGeometry, LocationMarker |
| calendar_days.py | 79 | days with weekday and Austrian holiday (Easter computus) | none |
| fetch_data.py | 153 | mirror the blob container into `../.cache`; standard library only (urllib, ElementTree) | none |

### Package `lib/` (20 classes, one per file; constants.py, diagram_layout.py, fonts.py and `__init__.py` hold none)

Every dependency is injected through the constructor ("Ctor deps"); no class creates its collaborators.

| File | Lines | Class | Ctor deps | Responsibility |
| --- | --- | --- | --- | --- |
| constants.py | 13 | — | — | `KELVIN`, `WEATHER_PARAMS`, `ICON_NAMES` |
| forecast_grib.py | 135 | ForecastGrib | path | byte-offset index of either forecast GRIB, names for local and ICON parameters, cached read-only decoding |
| point_sampler.py | 21 | PointSampler (ABC) | — | interface of the point samplers: abstract `__call__(values)`, shared `wind(u, v)` |
| grid_point_sampler.py | 25 | GridPointSampler | grid dict, lat, lng | bilinear value at one point of the regular ECMWF grid |
| cell_point_sampler.py | 58 | CellPointSampler | clat, clon, valid mask, lat, lng | linear value inside the triangle of the three ICON cells around the point; `nearest(values)` |
| step_sampler.py | 91 | StepSampler | ForecastGrib, PointSampler | all values of one ECMWF step at the point (dict row) incl. every GRIB value for the TSV |
| icon_step_sampler.py | 59 | IconStepSampler(StepSampler) | ForecastGrib, CellPointSampler | all values of one ICON-D2 step; weather kept in the TSV, `ww`/`ceiling` from the nearest cell |
| location_tables.py | 117 | LocationTables | ForecastGrib, PointSampler | ECMWF Markdown header + three tables; module functions `number`, `wind`, `table` |
| icon_location_tables.py | 114 | IconLocationTables | ForecastGrib, PointSampler | ICON-D2 Markdown header + three tables (hourly ground weather, 3-hourly 850/700 hPa, daily extremes); module function `weather` |
| forecast_tsv.py | 48 | ForecastTsv | path | write the TSV; read back the air-mass series |
| climate_archive.py | 201 | ClimateArchive | directory (required), period | index every `*.grb2` of the directory from the header bytes, decode fields, grid, nearest point |
| t850_climate.py | 50 | T850Climate | ClimateArchive | T850 mean (°C) / std (K) per valid time, at a point (`at_point`) or as field (`field`, used by no script) |
| grib_analyze.py | 128 | GribAnalyze | ClimateArchive, bbox or None | pandas queries on the climatology; used by no script |
| chart_geometry.py | 55 | ChartGeometry | window folder | reads `geometry.json`: conic projection and contact-sheet tiles of one window |
| location_marker.py | 85 | LocationMarker | ChartGeometry, label, point or bbox | draw point/box on a chart or every tile of a sheet |
| fonts.py | 15 | — | — | `load_font(size, bold)`: Arial → DejaVu Sans → PIL default |
| diagram_row.py | 16 | DiagramRow (frozen dataclass) | valid, t850, thickness, rh700 (str), climate, climate_std | one valid time of the diagram |
| diagram_layout.py | 6 | — | — | SVG size 1000 × 440, margins L56 R64 T44 B52 → plot x 56–936, y 44–388 |
| coupled_axes.py | 149 | CoupledAxes | t_range, z_range; factory `fit(rows, limits…)` | coupled T850/thickness axes, gridlines; module function `label` |
| time_axis.py | 50 | TimeAxis | start, end | x mapping of valid times, day gridlines, 3-hourly ticks |
| anomaly_bands.py | 85 | AnomalyBands | sigma_steps | polygons between T850 and mean ± kσ (no SVG knowledge) |
| forecast_diagram.py | 199 | ForecastDiagram | rows, TimeAxis, CoupledAxes, AnomalyBands, climate_label | assemble the SVG (CSS in `STYLE`, :28-57) |
| markdown_html.py | 52 | MarkdownHtml | — | Markdown subset → HTML blocks + title |

About 2,470 lines of Python: scripts 688, lib 1,777.

External packages (no requirements file exists): `eccodes` (all GRIB I/O), `numpy`, `scipy` (`ndimage.map_coordinates` in grid_point_sampler.py, `spatial.Delaunay` in cell_point_sampler.py), `Pillow` (mark_location, location_marker, fonts), `pandas` (only grib_analyze.py). build_report.py and calendar_days.py need only the standard library plus `lib`.

## Interface

```
location_table.py <data>/(ecmwf|icon-d2)_<run>.grb2 --lat LAT --lng LNG [--elevation M] [--label NAME] [--tsv FILE] [--workers N]
mark_location.py --data <data> --out <dir> (--lat LAT --lng LNG | --bbox S N W E) [--label TXT] [--workers N]
generate_diagram.py <tsv> --climate <data>/era5_means --lat LAT --lng LNG [--min-850 --max-850 --min-thickness --max-thickness] [--out FILE]
build_report.py --markdown F --svg F [--tsv F] [--caption TXT] [--table-summary Data] [--lang de] --out F
calendar_days.py --start YYYY-MM-DD [--days 10]
fetch_data.py <container url> [--cache DIR]
```

| Script | Output | Exit 1 when | Notes |
| --- | --- | --- | --- |
| location_table | Markdown on stdout (UTF-8), optional TSV | point outside the forecast grid, the ICON-D2 domain or its boundary zone | default workers = CPU count; run and model come from the GRIB, not from the file name |
| mark_location | WebP copies (quality 90) at the same relative path below `--out` | no `<data>/*/geometry.json`; marker visible in no window (copies are written anyway) | argparse rejects both/neither of point and bbox, and S ≥ N or W ≥ E |
| generate_diagram | SVG to `--out` or stdout | TSV unreadable/<2 rows, climatology lookup fails, invalid axis limits | |
| build_report | HTML file; prints `Report written to <abs path>` | an input file unreadable | |
| calendar_days | `YYYY-MM-DD\tWeekday\tHoliday` per line (UTF-8) | invalid `--start` | weekday via `%A` without `setlocale`, i.e. English names; holiday names German |
| fetch_data | files below `--cache` (default `../.cache`); last stdout line = cache path | no `current_run.json` (upload running or failed; nothing downloaded); it names no ECMWF run or a GRIB the listing lacks; it is missing or changed after the download (cache may mix two runs); a download failed (rerun fetches the rest) | see *Blob cache* |

Argparse errors exit 2. Status lines go to stdout, errors to stderr; messages and table texts are English.

## Data flow

```
location_table.main                               location_table.py:111
 ├─ ForecastGrib(grib)                            lib/forecast_grib.py:42
 ├─ locate: GridPointSampler or CellPointSampler(clat, clon, 2t at T+0 not NaN)  [outside → exit 1]   location_table.py:71
 ├─ ProcessPool(init_worker: own ForecastGrib + step_sampler per process)  location_table.py:87
 │    └─ StepSampler / IconStepSampler.sample(step) for step in grib.steps("t")   lib/step_sampler.py:24, lib/icon_step_sampler.py:28
 │         └─ grib_values(step) → row["grib"]                             lib/step_sampler.py:56
 ├─ print_ecmwf: LocationTables.header / main_table / mountain_table / extremes_table → stdout   location_table.py:134
 │  print_icon: IconLocationTables.header / surface_table / upper_table / extremes_table(rows)   location_table.py:144
 └─ [--tsv] ForecastTsv.write(valid times, steps, row["grib"])            lib/forecast_tsv.py:22

generate_diagram.main                             generate_diagram.py:51
 ├─ T850Climate(ClimateArchive(--climate))
 ├─ read_rows: ForecastTsv.air_mass → sort → T850Climate.at_point → DiagramRow   generate_diagram.py:37
 ├─ CoupledAxes.fit(rows, limits)                 lib/coupled_axes.py:52
 └─ ForecastDiagram(rows, TimeAxis(first, last), axes, AnomalyBands(SIGMA_STEPS), "Ø <period>").svg()

build_report.main                                 build_report.py:87
 ├─ [--tsv] data_table(ForecastTsv.air_mass)      build_report.py:49
 ├─ MarkdownHtml.blocks                           lib/markdown_html.py:17
 └─ build_html: figure inserted before the first <h2>   build_report.py:77

mark_location.main                                mark_location.py:71
 ├─ every <data>/<window>/geometry.json → ChartGeometry → one LocationMarker per window
 └─ ProcessPool × mark(): parent folder "sheets" → mark_sheet(stem) else mark_chart   mark_location.py:37
```

Order invariants:

1. **The viewer fills the data directory first.** location_table and mark_location read it; the ECMWF TSV of location_table is the only forecast input of generate_diagram and the data table of build_report (an ICON TSV has no `thick` and would give an empty thickness curve); build_report embeds the SVG of generate_diagram.
2. **All rows before the tables.** The header averages gh850 over all rows; ΔT850/12h looks up `step − 12` among the rows, so it is empty for steps below 12.
3. **TSV columns come from the first row** (`ForecastTsv.write`). Every row has the same keys because `grib_values` iterates over all parameters of the file at every step, with None where a field is absent.

## Core concepts

### Data directory contract

The scripts depend on what the viewer writes; nothing in the code checks it beyond the reads below.

| Item | Read by | Expectation |
| --- | --- | --- |
| `ecmwf_<run>.grb2` | ForecastGrib | path passed explicitly; regular lat/lon grid with rows north → south, one grid for all messages (taken from the first); run = `dataDate`/`dataTime` of the first message |
| `icon-d2_<run>.grb2` | ForecastGrib, CellPointSampler | path passed explicitly; `gridType` ≠ `regular_ll` (unstructured, 542 040 cells); raw DWD fields under the shortNames of `ICON_NAMES`; `clat`/`clon`/`hsurf`/`lsm` at T+0 only; boundary zone NaN; `ww` from T+1; `tmax_2m`/`tmin_2m` restart every 6 h from the run start |
| local parameters | `LOCAL_NAMES` (lib/forecast_grib.py:21) | discipline 0, category 192, parameterNumber 0–5 = `inv`, `rhbl`, `psig`, `snowl`, `uf`, `vf`; another number reads as `local<N>` |
| fields read by name (ICON) | IconStepSampler, IconLocationTables | `2t`, `10u`/`10v`, `gust`, `msl`, `tcc`, `ceiling`, `tp` (accumulated), `ww`, `u`/`v` 1000/850/700 hPa, `t`/`r`/`z` 850/700 hPa, `tmax_2m`/`tmin_2m`; T+0: `clat`, `clon`, `hsurf`, `lsm` |
| fields read by name (ECMWF) | StepSampler, LocationTables | `t` 850 hPa and 2000/2500/3000 m, `thick`, `msl`, `uf`/`vf` 1000/925 hPa, `inv`, `rhbl`, `r` 700 hPa and 2000 m, `w` 700 hPa, `psig`, `2t`, `deg0l`, `snowl`, `u`/`v` 2000/2500/3000 m, `gh` 850 hPa; T+0: `orog` (m), `sdor`, `lsm`; daily `mx2t`/`mn2t` at the end step of their window (18 / 06 UTC) |
| missing points | `ForecastGrib._read` (:102) | bitmap → NaN (points below the model ground for `uf`, `vf`, `inv`, `rhbl`) |
| `<window>/geometry.json` | ChartGeometry | keys `window`, `image.width/height` (map area without legend strip), `projection.pole_x/pole_y/scale_k/cone/lon0` (cone and lon0 default to 1 and 0, the old polar stereographic files), `sheets.scale`, `sheets.tiles` = {product: [[x, y], …]}; `model`, `run` and `projection.formula` are not read |
| `<window>/**/*.webp` | mark_location | single charts anywhere below the window; contact sheets in a folder named `sheets`, file stem = key of `sheets.tiles` |
| `era5_means/*.grb2` (era5_means.grb2) | ClimateArchive | see Climatology archive |

`charts.md` is not read by any script.

### Forecast GRIB index

`ForecastGrib` reads only headers at construction: key `(name, level, endStep)` → byte offset, plus `(name, level)` → `typeOfLevel` in file order (`parameters()`). `stepUnits` is set to hours before reading `endStep`, because ICON gives its time-invariant fields in minutes ("0m"). Names: local category 192 → `LOCAL_NAMES`, else the shortName mapped through `ICON_NAMES` (no ECMWF shortName is a key there). `grid` is None for an unstructured file; its fields are 1-D. Fields are decoded on demand into an `lru_cache` of `CACHED_FIELDS` = 64 (≈ 250 MB per the code comment), per instance, i.e. per process. Arrays are float32 `(nj, ni)` and **read-only** because the cache shares them. `field(name, step, level=None)` with no level returns the first key with that name and step — safe only for single-level parameters. `level` is a pressure in hPa or a height in m (heightAboveSea); **the key does not include `typeOfLevel`**, so the same name at the same level number on two level types would collide (last offset wins).

### Grid dicts and coordinate mapping

`ForecastGrib.grid` and `ClimateArchive.grid` share the keys `lat0, lon0 (-180…180), dlat, dlon, ni, nj` (the archive adds flat point arrays `lat`, `lon`). `GridPointSampler` computes `row = (lat0 − lat)/dlat`, `col = ((lng − lon0) % 360)/dlon` and interpolates bilinearly (`map_coordinates`, order 1); a NaN neighbour makes the value NaN. Wind = `(atan2(−u, −v)` in degrees, i.e. direction it blows from, `hypot(u, v))`, None if a component is NaN.

`CellPointSampler` (lib/cell_point_sampler.py:24): takes the `NEIGHBOURS` = 12 nearest cell centres in a local km plane, triangulates them (Delaunay) and keeps the triangle containing the point with its barycentric weights; outside if there is none, the nearest centre is more than `MAX_DISTANCE_KM` = 5 km away or a corner is NaN in the `valid` mask (boundary zone). `__call__` = weighted sum (NaN propagates), `nearest` = value of the nearest cell. The viewer draws the ICON charts with the same linear interpolation.

`ChartGeometry.latlon_to_pixel` (lib/chart_geometry.py:50): Lambert conformal conic with the north pole at the apex, `rho = scale_k·tan(45° − lat/2)^cone`, `θ = cone·(lon − lon0)` with lon − lon0 wrapped to ±180°, `x = pole_x + rho·sin θ`, `y = pole_y + rho·cos θ`, origin top-left, y down; parameters from geometry.json. cone = 1, lon0 = 0 are the ECMWF windows (polar stereographic). Checked against the viewer's `Projection.latlon_to_pixel`: identical for all three windows.

### Location sampling

`StepSampler.sample(step)` returns one dict: T in °C, thickness in dam (`thick`/10), MSLP in hPa, inversion in K, RH in %, ω700 in Pa/s, freezing level and snow line in m, winds as `(from-direction °, m/s)` or None. `precip` = bilinear `psig` ≥ 0.5 (lib/step_sampler.py:32); `snow_line` only where `precip`. Mountain values for `MOUNTAIN_HEIGHTS` = 2000/2500/3000 m; RH only at the first height. `"grib"` holds `grib_values(step)`: every parameter except the class attribute `HIDDEN` (`WEATHER_PARAMS`) in GRIB units keyed by TSV column, each read through the hook `value(name, field)` (default: the point sampler); fields that exist only at T+0 repeat, other absent fields are None.

`IconStepSampler.sample(step)` (lib/icon_step_sampler.py:28) builds on `grib_values`: T2m and T850/T700 in °C, MSLP in hPa, gust in m/s, `tcc` in %, cloud base = `ceiling` (m above sea level) or None from `NO_CEILING_M` (15 000; ICON writes about 20 000 without a layer), precipitation of the last hour = `tp(step) − tp(step − 1)` (None at T+0), `ww` as float, height of 850/700 hPa = `z`/`GRAVITY`, winds at 10 m, 1000, 850, 700 hPa. Wind 1000 is None where (MSLP − 1000 hPa)·`M_PER_HPA` (8 m/hPa) is below `hsurf`: ICON has no `z1000` and extrapolates below the ground. `HIDDEN` = `clat`, `clon` only (ICON-D2 resolves its weather); `NEAREST` = `ww`, `ceiling` take `CellPointSampler.nearest`, because interpolated codes and cloud bases between 800 m and 20 km exist in no cell.

`IconLocationTables` (lib/icon_location_tables.py): header with `hsurf`, `lsm`, the same height note and 850 hPa warning as ECMWF (constants imported from location_tables.py), surface table every hour, upper table every `UPPER_HOURS` = 3 h, extremes from the rows (no extra reads): window (start, end] as for ECMWF, skipped unless it lies inside the run; per hour `tmax_2m`/`tmin_2m` where its 6 h period (restart = (step − 1) // 6·6) begins at or after the window start, else the hourly `2t`. `weather(code)` prints the code with its text from `WEATHER` (WMO 4677).

`LocationTables.header` gives model height (`orog`), `sdor`, `lsm`; with `--elevation` the T2m shift `MIXED_LAPSE_K_PER_100M` (0.65) × (model − real height)/100; a warning when mean gh850 − model height < `NEAR_GROUND_M` (500 m). Head lists and cell lists of `main_table`/`mountain_table` are written side by side by hand and must stay aligned (lib/location_tables.py:56-81). Mountain winds only at the first and last height; freezing level and snow line rounded to 100 m. `extremes_table` groups `mx2t`/`mn2t` by the UTC date of their end step.

### TSV

`ForecastTsv`: header `valid_utc` (YYYYMMDDHH), `step_h`, then the columns of the first row. `StepSampler.column_name` (lib/step_sampler.py:85): `isobaricInhPa` → name + level (`t850`), `heightAboveSea` → name + level + `m` (`t2000m`), else the bare name. Order: pressure-level parameters sorted by name and from 1000 hPa upwards, then all others in file order. Values up to 3 decimals without trailing zeros, empty when None/NaN, never `-0`. ICON columns: `r850 r700 t850 t700 u1000 u850 u700 v1000 v850 v700 z850 z700 hsurf lsm tcc tp msl gust 2t tmax_2m tmin_2m 10u 10v ceiling ww` (49 rows, T+0 to T+48). `air_mass()` reads back `(valid, step, t850 °C, thick dam, r700 %)` per row in file order, None for empty or absent columns; that 5-tuple is unpacked positionally in generate_diagram.py:47-48 and build_report.py:59.

### Climatology archive

`ClimateArchive(directory, period=PERIOD)` (lib/climate_archive.py:45) reads every `*.grb2` in the directory, however the fields are spread over files; `PERIOD` = `"1991–2020"` (label only, feeds the diagram legend). Key `(kind, statistic, level, month, day)`: kind `HHz` (one time of day per calendar day, every 3 h; `term_hours` come from the messages present), `daily`, `monthly`; statistic `mean`/`std`; level 850 (T850) or 2 (T2m); day None for `monthly`; values in K. `field(kind, statistic, level, month, day)` returns one field, `keys(kind)` the `(statistic, level, month, day)` of a kind. The index is built on first use without ecCodes from the bytes of each message header (`_headers`, `_key`, lib/climate_archive.py:164-201): section 1 month/day/hour of the reference time (year ignored), template 4.8 first fixed surface (type 100 Pa → hPa, type 103 m), number of time ranges (1 = time of day, 2 = `daily`, 3 = `monthly`) and the statistical process of the **outermost** range (0 = mean, 6 = std). ecCodes needs ≈ 4.8 s for the 13 224 headers, the bytes ≈ 0.09 s. Never identify fields by `shortName`: ecCodes calls the `daily`/`monthly` standard deviations `avg_t`/`avg_2t` as well. Another template than 4.8 or a header beyond `HEADER_BYTES` (512) raises ValueError. Fields are read from the file and decoded on demand (≈ 7 ms each, JPEG2000), cached without bound. `grid` comes from the first indexed message. `nearest` uses distance in degrees and rejects points more than one grid spacing away.

`T850Climate._values(valid)` picks the kind of `valid.hour`; **every hour among the valid times must have one**, else `term_kind` raises ValueError. `GribAnalyze` maps `avg_*` to statistic `mean` and `std_*` to `std` and returns DataFrames `month, day, lat, lon, <param>` (avg in °C, std in K, rounded to 0.01; `day` Int64 with <NA> for monthly); point queries return the nearest grid point, other queries all points or those inside the constructor's `bbox` (south, north, west, east, inclusive).

### Coupled diagram axes

`CoupledAxes` (lib/coupled_axes.py:37): thickness = 544 dam + 1.6 dam/K · T850, both constants determined empirically (laut User); with that, both curves overlap for typical central European air masses (module docstring). Auto T850 range = multiples of 4 K covering T850, the climate mean and the thickness converted to T850; a missing thickness limit follows through the coupling; each given limit replaces only its own fitted value. Gridlines follow the T850 axis (first step of 2/4/8/16 K that divides the span evenly into ≤ 12 intervals, else 10); thickness ticks are independent multiples of the first of 4/8/16/32 dam giving ≤ 12 intervals.

Anomaly shading: for every k in `SIGMA_STEPS` (0, 1, 2, 3; generate_diagram.py:34) `AnomalyBands.polygons` yields polygons where T850 > mean + kσ (warm) or < mean − kσ (cold), split exactly at crossings; `ForecastDiagram` stacks them with `fill-opacity` `LAYER_OPACITY` 0.2 each. A None value breaks lines and areas. Hover dots appear only for values inside the axis range.

## Constants reference

| Constant | Where | Value / meaning |
| --- | --- | --- |
| `KELVIN` | lib/constants.py:3 | 273.15 |
| `WEATHER_PARAMS` | lib/constants.py:8 | `tcc`, `tp`, `ptype`; left out of the ECMWF TSV because a 9 km global model gets fog, low stratus and their precipitation wrong (comment :5-7) |
| `ICON_NAMES` | lib/constants.py:12 | ecCodes shortName → viewer name of the ICON fields (`tlat`→`clat`, `CLCT`→`tcc`, `prmsl`→`msl`, `WW`→`ww`, `max_i10fg`→`gust`, `ceil`→`ceiling`, …); a copy of the viewer's `constants.ICON_NAMES` |
| `LOCAL_CATEGORY`, `LOCAL_NAMES` | lib/forecast_grib.py:25-27 | 192; parameterNumber → name, fixed by the viewer |
| `CACHED_FIELDS` | lib/forecast_grib.py:29 | 64 decoded fields per instance |
| `NEIGHBOURS`, `MAX_DISTANCE_KM` | lib/cell_point_sampler.py:12-14 | 12 cells triangulated around the point; 5 km to the nearest cell centre at most |
| `GRAVITY`, `LEVELS`, `M_PER_HPA`, `NO_CEILING_M` | lib/icon_step_sampler.py:11-16 | 9.80665; 850/700 hPa; 8 m per hPa for the height of 1000 hPa; cloud base ≥ 15 000 m means none |
| `RESTART_HOURS`, `WINDOWS`, `UPPER_HOURS`, `WEATHER` | lib/icon_location_tables.py:13-19 | 6 h restart of `tmax_2m`/`tmin_2m`; Tmax 06–18, Tmin 18–06 UTC; upper table every 3 h; WMO 4677 texts |
| `MOUNTAIN_HEIGHTS` | lib/step_sampler.py:12 | 2000, 2500, 3000 m; must exist as heightAboveSea levels of `t`/`u`/`v`, and of `r` for the first one |
| `MIXED_LAPSE_K_PER_100M` | lib/location_tables.py:14 | 0.65 K/100 m for the height note; not valid under inversions |
| `NEAR_GROUND_M` | lib/location_tables.py:16 | 500 m clearance of 850 hPa below which T850 carries the diurnal cycle |
| `PERIOD`, `DIRECTORY` | lib/climate_archive.py:27-29 | `"1991–2020"`, `"era5_means"` (DIRECTORY used by no skill script) |
| `LEVEL` | lib/t850_climate.py:16 | 850 |
| `PARAMS` | lib/grib_analyze.py:30 | valid level/param pairs: 850 → avg_t/std_t, 2 → avg_2t/std_2t |
| `FILE_NAME` | lib/chart_geometry.py:21 | `geometry.json`; mark_location finds windows by it |
| `MARKER_RADIUS`, `LABEL_SIZE` | lib/location_marker.py:9-10 | 5 px, 16 pt on single charts; on sheet tiles × √scale (min 3 px / 10 pt) |
| `EDGE_POINTS` | lib/location_marker.py:12 | 50 points per box edge (edges are curved in the projection) |
| `WEBP_QUALITY` | mark_location.py:34 | 90 for the copies (the source charts are lossy WebP already) |
| `SIGMA_STEPS` | generate_diagram.py:34 | anomaly layers k = 0, 1, 2, 3 |
| `THICKNESS_AT_ZERO`, `THICKNESS_PER_KELVIN` | lib/coupled_axes.py:23-24 | 544 dam, 1.6 dam/K; empirically determined (laut User) |
| `AXIS_ROUNDING`, `GRID_STEPS`, `THICKNESS_STEPS`, `MAX_GRID_INTERVALS`, `FALLBACK_GRID_INTERVALS` | lib/coupled_axes.py:25-33 | see Coupled diagram axes |
| `LAYER_OPACITY` | lib/forecast_diagram.py:23 | 0.2 per anomaly layer |
| `TICK_HOURS`, `MIN_DAY_LABEL_WIDTH` | lib/time_axis.py:7-8 | ticks every 3 h (00 UTC 10 px, 12 UTC 7 px, else 4 px); day labels only on segments ≥ 36 px |
| `FIXED_HOLIDAYS`, `EASTER_HOLIDAYS` | calendar_days.py:14-32 | Austrian holidays; Easter ones as days after Easter Sunday |

## Details

- **HTML report**: the figure (SVG + optional caption + collapsible TSV table) goes before the first `<h2>`; the first `#` heading becomes `<title>` (default "Synoptic analysis"); the CSS styles `h1 + p` as the plain-language summary box. Markdown subset: `#`–`###` (`####` is plain text), paragraphs, `- ` lists, a non-blank line after a list item is appended to that item, `**bold**`, `*italic*`; everything else is escaped text.
- **SVG**: 1000 × 440 user units, no script; hover via `<title>` tooltips and CSS `:hover` crosshair columns that reach halfway to the neighbours; light/dark via `prefers-color-scheme` in embedded CSS. The page CSS (build_report.py) and the diagram CSS (forecast_diagram.py) define the same palette separately.
- **Markers**: single charts get the label, sheet tiles do not; drawing happens on a crop of the map area (tile size = image size × `sheets.scale`) so boxes never spill onto the legend or neighbour tiles. `LocationMarker.visible` is decided once per window from the map area, so all charts of a window are either marked or copied plain.
- **Windows**: scripts that print non-ASCII reconfigure stdout to UTF-8; process pools use spawn, so worker state is set in `init_worker` (module global `_sampler`, location_table.py:68).

- **Blob cache**: listing `?restype=container&comp=list` with `NextMarker` paging (anonymous, container-level public access). A cached file is current if size and `int(st_mtime)` equal `Content-Length` and `Last-Modified` of the blob; after a download `os.utime` sets the mtime to `Last-Modified`, so no index file is needed. Downloads go via `<file>.part`, 8 in parallel, timeout 60 s, no retries. Afterwards every file not listed (old runs, `.part`) and empty folders are deleted, so the cache holds exactly one run per model; the climatology (≈ 400 MB) is fetched once. Consistency: the pipeline (wetterkartenviewer `scripts/blob_mirror.py`) deletes `current_run.json` (`{"ecmwf": run, "icon-d2": run, "updated": …}`, model key = GRIB prefix without `_`) before an upload and writes it last; `read_runs` fetches it with `Cache-Control: no-cache` before the listing and again after the downloads, and only an unchanged file counts. It is cached like any other blob.

## Error handling

| Situation | Behaviour |
| --- | --- |
| Forecast file missing / without messages | `FileNotFoundError` / `ValueError` in `ForecastGrib.__init__`, **uncaught** traceback |
| Location outside the forecast grid / ICON-D2 domain / its boundary zone | `ValueError` from `GridPointSampler` / `CellPointSampler` → stderr, exit 1 |
| Field absent (e.g. the viewer did not write it) | `KeyError` from `ForecastGrib.field`, re-raised by `pool.map` → traceback; `gh850` absent from a row's `grib` → KeyError/TypeError in `header` |
| Climatology directory missing or without `*.grb2` | `FileNotFoundError` in `ClimateArchive.__init__`, uncaught in generate_diagram |
| Valid hour without climatology file / point outside climatology grid | `ValueError`; generate_diagram reports it as "Cannot read <tsv>: …", exit 1 |
| TSV with < 2 rows or malformed values | `ValueError`/`KeyError`, exit 1 |
| No T850/thickness values or invalid axis limits | `ValueError` from `CoupledAxes`, exit 1 |
| geometry.json malformed or missing keys | `JSONDecodeError`/`KeyError` in mark_location main, uncaught |
| `LocationMarker` with both or neither of point/bbox | `ValueError` (CLI validates first) |
| `GribAnalyze`: unknown level/param, no matching day, only one of lat/lng, missing kind/hour | `ValueError` with the valid options |
| Write errors (`--out`, `--tsv`) | uncaught |

No logging framework, no tests, no retries; only fetch_data.py uses the network.

## Extension points

**New location-table column** — add the value to the dict in `StepSampler.sample` (lib/step_sampler.py:24) and extend both the head list and the cell list in `LocationTables.main_table` or `mountain_table` at the same position; for ICON-D2 `IconStepSampler.sample` (lib/icon_step_sampler.py:28) and `IconLocationTables.surface_table`/`upper_table`. The TSV needs nothing. Formatting helpers: `number(value, digits, signed)` and `wind(value)` (lib/location_tables.py:98-111).

**New derived field from the viewer** — appears in the TSV automatically. If it is a local parameter of category 192, add its number to `LOCAL_NAMES` (lib/forecast_grib.py:27) with the viewer's numbering (charts.md, "GRIB-Datei"), else its column is `local<N>`. A new `typeOfLevel` that needs a level suffix goes into `StepSampler.column_name` (:85). Parameters to hide from the ECMWF TSV go into `WEATHER_PARAMS`.

**New ICON-D2 parameter from the viewer** — appears in the ICON TSV automatically under its shortName; if the viewer reads it under another name, add the pair to `ICON_NAMES` (same as the viewer's `constants.ICON_NAMES`). A code or a field with jumps goes into `IconStepSampler.NEAREST`.

**Another model** — a regular lat/lon file works with `GridPointSampler`; location_table.py picks samplers and tables only by `grib.grid is None`, so a second unstructured or regular model needs its own test there (e.g. on `base_time` of a name prefix) plus a StepSampler subclass and a tables class.

**Other mountain heights** — `MOUNTAIN_HEIGHTS` (lib/step_sampler.py:12); the viewer must write `t`/`u`/`v` (and `r` for the first height) at those heightAboveSea levels. Table heads follow automatically; `rh2000` keeps its key name in the row dict.

**Switch the climatology** — pass `period` to `ClimateArchive` or change `PERIOD` (lib/climate_archive.py:27). Requirements on the files: GRIB2 `*.grb2` with template 4.8 identified as in `_key`, exactly one message per key; an `HHz` kind for every hour that occurs among valid times (T850Climate); `daily`/`monthly` only for GribAnalyze; levels 850 and 2, in K; regular grid with rows north → south. lib/climate_archive.py and lib/t850_climate.py are identical copies of the files in the wetterkartenviewer repository (scripts/lib/). `period` feeds the diagram legend ("Ø <period>"); text in `../SKILL.md` naming the period is separate.

**Diagram look** — `SIGMA_STEPS` (generate_diagram.py:34), `LAYER_OPACITY` and CSS variables in `STYLE` (lib/forecast_diagram.py:23-57), coupling `THICKNESS_AT_ZERO`/`THICKNESS_PER_KELVIN` (lib/coupled_axes.py:23-24; the module docstring and `../references/html_report.md` repeat the formula), size/margins in lib/diagram_layout.py. An additional series needs a TSV column in `ForecastTsv.air_mass` (and both positional unpackings, see TSV), a `DiagramRow` field, a `_series_path` call, a `_legend` entry and a `_tooltip` part.

**Report Markdown features** — `MarkdownHtml.inline`/`blocks` (lib/markdown_html.py:11-52); unsupported syntax renders as escaped text, not dropped. The list of supported elements is repeated in `../references/html_report.md`.

**New chart window** — nothing to change: mark_location takes every folder of the data directory that holds a `geometry.json`.

**Holidays / other country** — `FIXED_HOLIDAYS`, `EASTER_HOLIDAYS` (calendar_days.py:14-32).

## Pitfalls

- **Destructive:** mark_location, location_table `--tsv`, generate_diagram `--out` and build_report `--out` overwrite their targets without asking; mark_location never deletes stale copies in `--out`.
- **External contract in two constants:** `LOCAL_NAMES` and `MOUNTAIN_HEIGHTS` must match what the viewer writes; a mismatch shows up as `KeyError` or as `local<N>` columns, not as a clear message.
- **Memory:** each location worker builds its own `ForecastGrib` with up to 64 cached fields (ICON: 542 040 cells, about 2 MB per field); default worker count is the CPU count.
- **ICON 1000 hPa:** u/v at 1000 hPa exist everywhere, extrapolated below the ground; the table hides them there by an estimate from MSLP (8 m/hPa), the TSV keeps them.
- **ICON names:** `ICON_NAMES` and `NO_CEILING_M` mirror the viewer (scripts/lib/constants.py, charts.md "ICON-D2-Datei"); a renamed or rescaled field there shows up here as `KeyError` or a wrong unit.
- **Read-only arrays:** never modify a `ForecastGrib.field` result in place; derive a new array.
- **Below the model ground:** `uf`, `vf`, `inv`, `rhbl` are NaN there (dash in the table, empty in the TSV); plain pressure-level fields (`t1000`, `u925`, …) are model extrapolations and come through as numbers.
- **Wind at 3000 m** and other mountain values are whatever the viewer wrote at those heights; the scripts do no vertical interpolation.
- **Climatology hours:** every hour among the valid times needs an `HHz` file.
- **Sheets:** a sheet whose stem has no entry in `sheets.tiles` gets no marker but still counts as "with marker" in the summary line.
- **Missing:** no tests, no logging, no requirements file, no configuration file (all settings are module constants).
