"""Write the temperature series of Austria that the start page of the viewer draws for its location.

Twelve JSON files in maps/austria/ (published like the videos, listed in the manifest under ``series``):

    t850.json      ECMWF T850 of every step on the 0.1 deg grid of the box, with the ERA5
                   climatology of T850 (mean, stdev) for the days of the run
    t2m.json       ECMWF and ICON-D2 T2m, with the ERA5 climatology of the daily mean T2m
                   (both ECMWF blocks and both climate blocks also hold the model
                   orography ``orog`` in m, ERA5 from lib/era5_orography.grib)
    td2m.json      ECMWF 2 m dew point (2d; no climatology)
    tw2m.json      ECMWF 2 m wet-bulb temperature (the derived field wbt; no climatology)
    heights.json   the ICON-D2 cells of Austria: centre and model orography (hsurf)
    thickness.json ECMWF 1000-500 hPa thickness in dam (no climatology)
    t500.json      ECMWF T500 (no climatology), for the vertical totals T850 - T500
    rh850.json     ECMWF relative humidity at 850 hPa in % (no climatology), for the parcel lifted from 850 hPa
    rh700.json     ECMWF relative humidity at 700 hPa in % (no climatology), drawn as a line
    thetae850.json ECMWF equivalent potential temperature at 850 hPa in K (the derived field papt;
                   no climatology), drawn as a line in the T850 panel
    gust10m.json   ECMWF 10 m gust in km/h (no climatology) with the hours it covers and the colour
                   bands of the wind10m chart, drawn as a colour bar in the T2m panel
    precip6h.json  ECMWF precipitation in mm over the 6 h before each step (3 h at T+3), as on the
                   weather_summary chart, with its bands, drawn as a colour bar in the T850 panel, and
                   the class of its type (snow, wet snow, freezing) from ptype, drawn as symbols above it

Every series is stored as whole tenths of a degree (of a dam for the
thickness; rh850 and rh700 as whole percent, gust10m as whole km/h,
precip6h as tenths of a mm), as deltas along time and
time-major (all points of the first time, then all of the second ...): the
first time holds absolute values, every further one the change since the
previous time. Neighbouring points change alike, which gzip packs to about a
fifth; GitHub Pages serves JSON compressed, so the files need no packing of
their own. A field of n points and t times is one flat list of n * t numbers.

The regular grids (ECMWF 0.1 deg, ERA5 0.25 deg) cover the box ``BOX``; their
``grid`` gives lat0 (northernmost row), lon0, dlat (step southwards), dlon,
nj, ni, rows north to south. The ERA5 window is wider by half a grid step, so
the grid point nearest to every location of the box is in it. ICON-D2 keeps
its cells, only those within ``BORDER_MARGIN`` of Austria, in file order; the
cell coordinates are in heights.json (deltas of 1e-4 deg along the cell
list), t2m.json only repeats their number.

The climatology covers every day from 00 UTC of the ECMWF run to its last
step, each file only with what the app draws: t850.json ``term``, each analysis
hour of each day (day-major, then hour); t2m.json ``daily``, the daily means and
the standard deviation of the daily means (the daily cycle of T2m makes the
term values a poor reference).

A file is written only if its ``version`` changed (the runs it comes from),
so publish_maps.py uploads it once per run. heights.json depends only on the
ICON grid and is written when it is missing or its cells differ.

Usage: python scripts/point_series.py data maps [--force]
"""

import argparse
import json
from collections.abc import Callable
from typing import Literal
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
from matplotlib.path import Path as Polygon
from scipy.spatial import cKDTree

from lib import chart_styles
from lib.chart_products import ChartProducts
from lib.climate_archive import DIRECTORY as CLIMATE_DIRECTORY, ClimateArchive
from lib.constants import ICON_NAMES, IFS_GUST_NAMES, KELVIN, KMH_PER_MS
from lib.era5_orography import era5_orography
from lib.forecast_grib import ForecastGrib
from lib.missing_field_error import MissingFieldError
from lib.projection import AUSTRIA_BORDERS
from maps_manifest import SERIES_FILES, read_version

# Austria with a margin of about 10 km on every side, in degrees.
BOX = {"north": 49.1, "south": 46.3, "west": 9.5, "east": 17.2}
# ICON cells farther from Austria than this (degrees of latitude) are left out.
BORDER_MARGIN = 0.15
# Values are stored as multiples of SCALE (0.1 K), coordinates of COORD_SCALE degrees.
SCALE, COORD_SCALE = 0.1, 1e-4
# Relative humidity in whole percent: 1 % is about 0.15 K of dew point at 80 %, and the file packs better.
RH_SCALE = 1.0
# Gusts in whole km/h: the band limits of the wind10m chart (Beaufort) are whole km/h.
WIND_SCALE = 1.0
# Precipitation in tenths of a mm: the lowest band of the weather_summary chart starts at 0.2 mm.
PRECIP_SCALE = 0.1
# Precipitation classes of precip6h.json (1-based index into chart_styles.PRECIP_TYPES: 1 snow, 2 wet snow or rain
# and snow, 3 freezing rain or drizzle, ice pellets), strongest first: freezing precipitation decides on black ice,
# and a window with snow and wet snow has snow.
PTYPE_PRECEDENCE = (3, 1, 2)
# 2 m humidity series, ECMWF only (ICON-D2 would multiply the file size), in deg C like T2m:
# file name -> GRIB shortName of the dew point and the wet-bulb temperature.
HUMIDITY_SERIES = {"td2m": "2d", "tw2m": "wbt"}


def time_major_deltas(fields: np.ndarray, scale: float = SCALE) -> list[int]:
    """Flat time-major deltas of (times, points...) values in multiples of ``scale``; the first time stays absolute."""
    whole = np.rint(np.asarray(fields, dtype=np.float64) / scale).astype(np.int64)
    return np.diff(whole, axis=0, prepend=0).ravel().tolist()


def box_window(grid: dict, margin: float = 0.0) -> tuple[slice, slice, dict]:
    """Rows, columns and grid of the part of a regular grid that lies in ``BOX`` widened by ``margin`` degrees."""
    lats = grid["lat0"] - grid["dlat"] * np.arange(grid["nj"])
    lons = grid["lon0"] + grid["dlon"] * np.arange(grid["ni"])
    tolerance = 1e-6  # grid coordinates come with rounding errors
    rows = np.flatnonzero((lats <= BOX["north"] + margin + tolerance) & (lats >= BOX["south"] - margin - tolerance))
    cols = np.flatnonzero((lons >= BOX["west"] - margin - tolerance) & (lons <= BOX["east"] + margin + tolerance))
    window = {"lat0": round(float(lats[rows[0]]), 4), "lon0": round(float(lons[cols[0]]), 4),
              "dlat": grid["dlat"], "dlon": grid["dlon"], "nj": len(rows), "ni": len(cols)}
    return slice(rows[0], rows[-1] + 1), slice(cols[0], cols[-1] + 1), window


def run_of(grib: ForecastGrib) -> str:
    return f"{grib.base_time:%Y%m%d%H}"


def ecmwf_block(grib: ForecastGrib, name: str, level: int | None, key: str, offset: float = -KELVIN,
                factor: float = 1.0, scale: float = SCALE) -> dict:
    """One ECMWF field over every step it has, as (value + offset) * factor under ``key`` in multiples of ``scale``.

    The defaults turn K into deg C. A step lost on the server is left out.
    """
    return derived_block(grib, grib.steps(name), key, lambda step: (grib.field(name, step, level) + offset) * factor,
                         scale)


def derived_block(grib: ForecastGrib, all_steps: list[int], key: str, field_of: Callable[[int], np.ndarray],
                  scale: float = SCALE) -> dict:
    """A field computed by ``field_of(step)`` at each of ``all_steps``, under ``key`` in multiples of ``scale``.

    A step at which ``field_of`` misses a field on the server is left out.
    """
    rows, cols, window = box_window(grib.grid)
    steps, fields = [], []
    for step in all_steps:
        try:
            fields.append(field_of(step)[rows, cols])
        except MissingFieldError:
            continue
        steps.append(step)
    # Model orography (m) of the grid points, for the height the series belongs to.
    orog = np.rint(grib.field("orog", 0)[rows, cols]).astype(np.int64).ravel().tolist()
    return {"run": run_of(grib), "steps": steps, "grid": window, "orog": orog, key: time_major_deltas(fields, scale)}


def gust_block(grib: ForecastGrib) -> dict:
    """IFS 10 m gusts in km/h at every step that has one, with ``hours``: the interval before each step it covers."""
    steps = sorted({step for name in IFS_GUST_NAMES for step in grib.steps(name)})
    block = derived_block(grib, steps, "gust10m",
                          lambda step: grib.field(grib.pick(IFS_GUST_NAMES, step), step) * KMH_PER_MS, WIND_SCALE)
    block["hours"] = [grib.window_hours(grib.pick(IFS_GUST_NAMES, step), step) for step in block["steps"]]
    return block


def precipitation_block(grib: ForecastGrib) -> dict:
    """Precipitation in mm over the PRECIP_HOURS before every step after T+0, as on the weather_summary chart.

    The window is that of ``ChartProducts.weather_summary``: 6 h, 3 h at T+3. Up to T+144 the steps are 3 h apart,
    so neighbouring windows overlap by 3 h; ``hours`` holds the window of each kept step.
    """
    def field_of(step: int) -> np.ndarray:
        # tp accumulates from T+0 in m; packing noise can make the difference slightly negative.
        start = step - min(ChartProducts.PRECIP_HOURS, step)
        return np.maximum(grib.field("tp", step) - grib.field("tp", start), 0) * 1000

    block = derived_block(grib, [step for step in grib.steps("tp") if step > 0], "precip6h", field_of, PRECIP_SCALE)
    block["hours"] = [min(ChartProducts.PRECIP_HOURS, step) for step in block["steps"]]
    block["ptype"] = derived_block(grib, block["steps"], "ptype", lambda step: precipitation_class(grib, step),
                                   1.0)["ptype"]
    return block


def precipitation_class(grib: ForecastGrib, step: int) -> np.ndarray:
    """Precipitation class of the window before ``step``: 0 none, k the k-th group of ``PRECIP_TYPES``.

    ptype is the type at an output step, not over the window, so every output step inside the window counts (two up
    to T+144, one after); of several classes the first in ``PTYPE_PRECEDENCE`` wins. Windows below the threshold of
    the shading get 0: the chart draws no symbol outside its shaded precipitation either.
    """
    start = step - min(ChartProducts.PRECIP_HOURS, step)
    found = []
    for sample in (t for t in grib.steps("ptype") if start < t <= step):
        try:
            ptype = np.rint(grib.field("ptype", sample))
        except MissingFieldError:
            continue
        found.append([np.isin(ptype, codes) for codes, _ in chart_styles.PRECIP_TYPES])
    classes = np.zeros(grib.field("tp", step).shape, np.int64)
    for k in reversed(PTYPE_PRECEDENCE):
        # Later assignments win, so the loop runs from the weakest to the strongest class.
        classes[np.any([sample[k - 1] for sample in found], axis=0)] = k
    precip = (grib.field("tp", step) - grib.field("tp", start)) * 1000
    classes[precip < chart_styles.PRECIPITATION.transparent_below] = 0
    return classes


def colour_bands(scale) -> list[list]:
    """Bands of a chart colour scale as [lower, upper, "#rrggbb"], so the app colours a series like the chart."""
    return [[lower, upper, "#{:02x}{:02x}{:02x}".format(*rgb)] for lower, upper, rgb in scale.bands]


def austria_cells(lat: np.ndarray, lon: np.ndarray) -> np.ndarray:
    """Indices of the ICON cells within ``BORDER_MARGIN`` of Austria, in file order."""
    features = json.loads(AUSTRIA_BORDERS.read_text(encoding="utf-8"))["features"]
    country = next(f["geometry"] for f in features if f["properties"].get("ISO") == "AT"
                   and f["properties"].get("LEVEL") == "country")
    polygons = country["coordinates"] if country["type"] == "MultiPolygon" else [country["coordinates"]]
    in_box = np.flatnonzero((lat <= BOX["north"]) & (lat >= BOX["south"]) & (lon >= BOX["west"]) & (lon <= BOX["east"]))
    # Distances in degrees of latitude: longitudes shrink with the cosine of the latitude.
    shrink = np.cos(np.radians((BOX["north"] + BOX["south"]) / 2))
    points = np.column_stack([lat[in_box], lon[in_box] * shrink])
    inside = np.zeros(len(in_box), bool)
    for polygon in polygons:
        # Only the outer ring: Austria has no holes that matter at 2 km.
        inside |= Polygon(np.array(polygon[0])[:, ::-1] * [1, shrink]).contains_points(points)
    distance, _ = cKDTree(points[inside]).query(points, distance_upper_bound=BORDER_MARGIN)
    return in_box[np.isfinite(distance)]


def icon_cells(grib: ForecastGrib) -> np.ndarray:
    """Indices of the ICON cells of the series; cells without values in any field (boundary zone) are dropped."""
    cells = austria_cells(grib.field("clat", 0), grib.field("clon", 0))
    return cells[np.isfinite(grib.field("hsurf", 0)[cells])]


def icon_block(grib: ForecastGrib, cells: np.ndarray) -> dict:
    """ICON T2m of the cells over every step."""
    steps = grib.steps("2t")
    fields = [grib.field("2t", step)[cells] - KELVIN for step in steps]
    return {"run": run_of(grib), "steps": steps, "cells": len(cells), "t2m": time_major_deltas(fields)}


def heights_document(grib: ForecastGrib, cells: np.ndarray) -> dict:
    """Centre and model orography of the ICON cells; coordinates as deltas along the cell list."""
    coordinate = lambda name: np.diff(np.rint(grib.field(name, 0)[cells] / COORD_SCALE).astype(np.int64),  # noqa: E731
                                      prepend=0).tolist()
    return {"version": f"{run_of(grib)}-{len(cells)}", "box": BOX, "coord_scale": COORD_SCALE, "cells": len(cells),
            "lat": coordinate("clat"), "lon": coordinate("clon"),
            "hsurf": np.rint(grib.field("hsurf", 0)[cells]).astype(np.int64).tolist()}


def climate_block(archive: ClimateArchive, level: int, run: datetime, last_step: int,
                  kind: Literal["term", "daily"]) -> dict:
    """ERA5 mean (deg C) and stdev (K) of one level for every day of the run, of one kind.

    ``kind`` "term" holds every analysis hour of every day (day-major) with their ``hours``, "daily" the daily
    means. ``orog`` is the ERA5 orography of every point in whole m, the ground the T2m climate refers to.
    """
    first_day = run.replace(hour=0)
    days = [first_day + timedelta(days=i) for i in range((run + timedelta(hours=last_step) - first_day).days + 1)]
    rows, cols, window = box_window(archive.grid, max(archive.grid["dlat"], archive.grid["dlon"]) / 2)
    shape = archive.grid["nj"], archive.grid["ni"]

    def fields(kind_dates: list[tuple[str, int, int]], statistic: str) -> list[int]:
        values = [archive.field(field_kind, statistic, level, month, day).reshape(shape)[rows, cols]
                  for field_kind, month, day in kind_dates]
        return time_major_deltas(np.array(values) - (KELVIN if statistic == "mean" else 0))

    if kind == "term":
        hours = archive.term_hours
        dates = [(archive.term_kind(hour), day.month, day.day) for day in days for hour in hours]
        extra = {"hours": list(hours)}
    elif kind == "daily":
        dates = [("daily", day.month, day.day) for day in days]
        extra = {}
    else:
        raise ValueError(f"unknown climate kind {kind}")
    orography = era5_orography(archive.grid)[rows, cols]
    return {"period": archive.period, "grid": window, "first_day": f"{first_day:%Y-%m-%d}", "days": len(days),
            **extra, "orog": np.rint(orography).astype(np.int64).ravel().tolist(),
            kind: {statistic: fields(dates, statistic) for statistic in ("mean", "std")}}


def write_document(path: Path, document: dict) -> None:
    """Write compact JSON through a temporary file, so a reader never sees half a file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    part = path.with_suffix(path.suffix + ".part")
    part.write_text(json.dumps(document, separators=(",", ":"), ensure_ascii=False), encoding="utf-8")
    part.replace(path)
    print(f"{path}: {path.stat().st_size / 1e6:.1f} MB")


def write_series(data: Path, maps: Path, ecmwf_grib: Path, icon_grib: Path | None, force: bool = False) -> None:
    """Write the series files whose runs changed; without an ICON file t2m.json has no ICON part."""
    ecmwf_run = ecmwf_grib.stem.split("_")[-1]
    icon_run = icon_grib.stem.split("_")[-1] if icon_grib else "none"
    targets = {name: maps / file for name, file in SERIES_FILES.items()}
    versions = {"t850": ecmwf_run, "t2m": f"{ecmwf_run}-{icon_run}", "thickness": ecmwf_run, "t500": ecmwf_run,
                "rh850": ecmwf_run, "rh700": ecmwf_run, "thetae850": ecmwf_run, "gust10m": ecmwf_run,
                "precip6h": ecmwf_run, "td2m": ecmwf_run, "tw2m": ecmwf_run}
    stale = [name for name, version in versions.items() if force or read_version(targets[name]) != version]
    heights_missing = icon_grib is not None and (force or read_version(targets["heights"]) is None)
    if not stale and not heights_missing:
        print(f"series of runs {versions['t2m']} are up to date")
        return

    archive = ClimateArchive(data / CLIMATE_DIRECTORY)
    ecmwf = ForecastGrib(ecmwf_grib)
    last_step = max(ecmwf.steps("2t"))
    common = {"box": BOX, "scale": SCALE}
    if "t850" in stale:
        write_document(targets["t850"], {"version": versions["t850"], **common,
                                         "ecmwf": ecmwf_block(ecmwf, "t", 850, "t850"),
                                         "climate": climate_block(archive, 850, ecmwf.base_time, last_step, "term")})
    if "thickness" in stale:
        # gpm to dam
        write_document(targets["thickness"], {"version": versions["thickness"], **common,
                                              "ecmwf": ecmwf_block(ecmwf, "thick", None, "thickness", 0.0, 0.1)})
    if "t500" in stale:
        write_document(targets["t500"], {"version": versions["t500"], **common,
                                         "ecmwf": ecmwf_block(ecmwf, "t", 500, "t500")})
    # Relative humidity in %, as the IFS gives it (mixed phase between −23 °C and 0 °C); whole percent suffice.
    # Stored raw, without clipping (the IFS has values slightly above 100 %); the app clamps. Not **common:
    # the document's scale must be the encoding scale.
    for name, level in (("rh850", 850), ("rh700", 700)):
        if name in stale:
            write_document(targets[name], {"version": versions[name], "box": BOX, "scale": RH_SCALE,
                                           "ecmwf": ecmwf_block(ecmwf, "r", level, name, 0.0, scale=RH_SCALE)})
    if "thetae850" in stale:
        # Forecast files of older pipelines lack the derived field; the app then draws no theta-e line.
        if ecmwf.has("papt", 0, 850):
            write_document(targets["thetae850"], {"version": versions["thetae850"], **common,
                                                  "ecmwf": ecmwf_block(ecmwf, "papt", 850, "thetae850", 0.0)})
        else:
            print(f"{ecmwf_grib.name} has no papt at 850 hPa, {SERIES_FILES['thetae850']} not written")
    for name, short_name in HUMIDITY_SERIES.items():
        if name in stale:
            # Forecast files of older pipelines lack the field; the app then draws no line of it.
            if ecmwf.has(short_name, 0):
                write_document(targets[name], {"version": versions[name], **common,
                                               "ecmwf": ecmwf_block(ecmwf, short_name, None, name)})
            else:
                print(f"{ecmwf_grib.name} has no {short_name}, {SERIES_FILES[name]} not written")
    if "gust10m" in stale:
        write_document(targets["gust10m"], {"version": versions["gust10m"], "box": BOX, "scale": WIND_SCALE,
                                            "colours": colour_bands(chart_styles.GUST10M),
                                            "ecmwf": gust_block(ecmwf)})
    if "precip6h" in stale:
        # transparent_below: drier windows stay uncoloured, as on the chart.
        write_document(targets["precip6h"], {"version": versions["precip6h"], "box": BOX, "scale": PRECIP_SCALE,
                                             "colours": colour_bands(chart_styles.PRECIPITATION),
                                             "transparent_below": chart_styles.PRECIPITATION.transparent_below,
                                             "ecmwf": precipitation_block(ecmwf)})
    icon = cells = None
    if icon_grib is not None and ("t2m" in stale or heights_missing):
        icon = ForecastGrib(icon_grib, ICON_NAMES)
        cells = icon_cells(icon)
        # heights.json changes only with the ICON grid or the cell selection, not with every run.
        current = read_version(targets["heights"])
        if heights_missing or current.split("-")[-1] != str(len(cells)):
            write_document(targets["heights"], heights_document(icon, cells))
    if "t2m" in stale:
        document = {"version": versions["t2m"], **common, "ecmwf": ecmwf_block(ecmwf, "2t", None, "t2m"),
                    "climate": climate_block(archive, 2, ecmwf.base_time, last_step, "daily")}
        if icon is not None:
            document["icon"] = icon_block(icon, cells)
        write_document(targets["t2m"], document)


def newest(data: Path, prefix: str) -> Path | None:
    """Newest finished GRIB of a model in data/; unfinished downloads end in .part and do not match."""
    files = sorted(data.glob(f"{prefix}*.grb2"))
    return files[-1] if files else None


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("data", type=Path, help="data directory with the GRIB files and era5_means/")
    parser.add_argument("maps", type=Path, help="directory of the web app files")
    parser.add_argument("--force", action="store_true", help="write every file even if its version is current")
    args = parser.parse_args()
    ecmwf_grib = newest(args.data, "ecmwf_")
    if ecmwf_grib is None:
        raise SystemExit(f"no ecmwf_*.grb2 in {args.data}")
    write_series(args.data, args.maps, ecmwf_grib, newest(args.data, "icon-d2_"), args.force)


if __name__ == "__main__":
    main()
