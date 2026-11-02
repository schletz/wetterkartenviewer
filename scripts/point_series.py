"""Write the temperature series of Austria that the start page of the viewer draws for its location.

Four JSON files in maps/austria/ (published like the videos, listed in the manifest under ``series``):

    t850.json      ECMWF T850 of every step on the 0.1 deg grid of the box, with the ERA5
                   climatology of T850 (mean, stdev) for the days of the run
    t2m.json       ECMWF and ICON-D2 T2m, with the ERA5 climatology of T2m
                   (both ECMWF blocks also hold the model orography ``orog`` in m)
    heights.json   the ICON-D2 cells of Austria: centre and model orography (hsurf)
    thickness.json ECMWF 1000-500 hPa thickness in dam (no climatology)

Every series is stored as whole tenths of a degree (of a dam for the
thickness), as deltas along time and
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
step: ``term`` holds each analysis hour of each day (day-major, then hour),
``daily`` the daily means, ``monthly`` the months touched.

A file is written only if its ``version`` changed (the runs it comes from),
so publish_maps.py uploads it once per run. heights.json depends only on the
ICON grid and is written when it is missing or its cells differ.

Usage: python scripts/point_series.py data maps [--force]
"""

import argparse
import json
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
from matplotlib.path import Path as Polygon
from scipy.spatial import cKDTree

from lib.climate_archive import DIRECTORY as CLIMATE_DIRECTORY, ClimateArchive
from lib.constants import ICON_NAMES, KELVIN
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
                factor: float = 1.0) -> dict:
    """One ECMWF field over every step it has, as (value + offset) * factor under ``key``.

    The defaults turn K into deg C. A step lost on the server is left out.
    """
    rows, cols, window = box_window(grib.grid)
    steps, fields = [], []
    for step in grib.steps(name):
        try:
            fields.append((grib.field(name, step, level)[rows, cols] + offset) * factor)
        except MissingFieldError:
            continue
        steps.append(step)
    # Model orography (m) of the grid points, for the height the series belongs to.
    orog = np.rint(grib.field("orog", 0)[rows, cols]).astype(np.int64).ravel().tolist()
    return {"run": run_of(grib), "steps": steps, "grid": window, "orog": orog, key: time_major_deltas(fields)}


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


def climate_block(archive: ClimateArchive, level: int, run: datetime, last_step: int) -> dict:
    """ERA5 mean (deg C) and stdev (K) of one level for every day of the run: per analysis hour, daily, monthly."""
    first_day = run.replace(hour=0)
    days = [first_day + timedelta(days=i) for i in range((run + timedelta(hours=last_step) - first_day).days + 1)]
    months = sorted({day.month for day in days})
    rows, cols, window = box_window(archive.grid, max(archive.grid["dlat"], archive.grid["dlon"]) / 2)
    shape = archive.grid["nj"], archive.grid["ni"]

    def fields(kind_dates: list[tuple[str, int, int | None]], statistic: str) -> list[int]:
        values = [archive.field(kind, statistic, level, month, day).reshape(shape)[rows, cols]
                  for kind, month, day in kind_dates]
        return time_major_deltas(np.array(values) - (KELVIN if statistic == "mean" else 0))

    hours = archive.term_hours
    term = [(archive.term_kind(hour), day.month, day.day) for day in days for hour in hours]
    daily = [("daily", day.month, day.day) for day in days]
    monthly = [("monthly", month, None) for month in months]
    return {"period": archive.period, "grid": window, "first_day": f"{first_day:%Y-%m-%d}", "days": len(days),
            "hours": list(hours), "months": months,
            **{kind: {statistic: fields(dates, statistic) for statistic in ("mean", "std")}
               for kind, dates in (("term", term), ("daily", daily), ("monthly", monthly))}}


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
    versions = {"t850": ecmwf_run, "t2m": f"{ecmwf_run}-{icon_run}", "thickness": ecmwf_run}
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
                                         "climate": climate_block(archive, 850, ecmwf.base_time, last_step)})
    if "thickness" in stale:
        # gpm to dam
        write_document(targets["thickness"], {"version": versions["thickness"], **common,
                                              "ecmwf": ecmwf_block(ecmwf, "thick", None, "thickness", 0.0, 0.1)})
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
                    "climate": climate_block(archive, 2, ecmwf.base_time, last_step)}
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
