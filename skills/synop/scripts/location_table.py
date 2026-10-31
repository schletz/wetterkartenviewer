"""Forecast values at one location, read directly from a forecast file in the data directory.

The file decides the model. For ecmwf_<run>.grb2 it prints Markdown with
three tables for every step from T+0 to T+240:

    free atmosphere and boundary layer   T850, its 12 h change, thickness, MSLP, wind at 1000 and
                                         925 hPa, inversion, moisture of the boundary layer and at
                                         700 hPa, vertical motion, precipitation signal, T2m
    mountain weather                     temperature and wind at 2000/2500/3000 m, humidity at
                                         2000 m, freezing level, snow line where precipitation is likely
    daily extremes                       Tmax 06-18 UTC and Tmin 18-06 UTC at 2 m

A header gives the model height of the location, its sub-grid roughness
and, with --elevation, the difference to the real height: T2m holds for
the model height. Where 850 hPa lies close above the model ground, it
warns that T850 follows the diurnal cycle there. Values are bilinear
between the four surrounding grid points (0.1 deg). Every derived value
(heights, freezing level, inversion, ...) is a field of the forecast file;
the script computes nothing but units and the 12 h change of T850.

For icon-d2_<run>.grb2 (T+0 to T+48, hourly) the tables are

    weather at the ground   per hour: T2m, 10 m wind, gust, MSLP, cloud cover and base,
                            precipitation of the last hour, weather code (WMO 4677)
    free atmosphere         every 3 h: wind at 1000 hPa; height, T, RH and wind at 850 and 700 hPa
    daily extremes          Tmax 06-18 UTC and Tmin 18-06 UTC at 2 m

Values are linear inside the triangle of the three cell centres around the
location; the weather code and the cloud base come from the nearest cell.

With --tsv every parameter of the forecast file is written per step, in
GRIB units: columns valid_utc and step_h, then the GRIB shortName, local or
ICON name, with the level appended on pressure levels (t850, gh500, uf1000)
and heights (t2000m), else bare (msl, 2t, thick, deg0l, inv, mx2t, orog,
ceiling, ...). Fields of T+0 only (orog, z, sdor, lsm, hsurf) repeat in
every row, parameters missing at a step stay empty. The ECMWF TSV leaves
out cloud cover and precipitation (lib/constants.py), the ICON TSV keeps
them. generate_diagram.py and build_report.py read the ECMWF TSV (see
lib/forecast_tsv.py).

Example::

    python location_table.py <data>/ecmwf_2026102900.grb2 --lat 47.27 --lng 11.39 --elevation 574 --tsv data_innsbruck_ecmwf.tsv
    python location_table.py <data>/icon-d2_2026102909.grb2 --lat 47.27 --lng 11.39 --elevation 574 --tsv data_innsbruck_icon.tsv
"""

import argparse
import os
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

# Keep imports working under "python -I", which drops the script directory.
sys.path.insert(0, str(Path(__file__).resolve().parent))
import numpy as np  # noqa: E402

from lib.cell_point_sampler import CellPointSampler  # noqa: E402
from lib.forecast_grib import ForecastGrib  # noqa: E402
from lib.forecast_tsv import ForecastTsv  # noqa: E402
from lib.grid_point_sampler import GridPointSampler  # noqa: E402
from lib.icon_location_tables import IconLocationTables  # noqa: E402
from lib.icon_step_sampler import IconStepSampler  # noqa: E402
from lib.location_tables import LocationTables  # noqa: E402
from lib.point_sampler import PointSampler  # noqa: E402
from lib.step_sampler import StepSampler  # noqa: E402

# State of a worker process, set once by init_worker.
_sampler: StepSampler | None = None


def locate(grib: ForecastGrib, lat: float, lng: float) -> PointSampler:
    """The location on the grid of the file: bilinear on the ECMWF grid, in the triangle of ICON cells.

    Raises:
        ValueError: if the location lies outside the forecast area.
    """
    if grib.grid is not None:
        return GridPointSampler(grib.grid, lat, lng)
    return CellPointSampler(grib.field("clat", 0), grib.field("clon", 0), ~np.isnan(grib.field("2t", 0)), lat, lng)


def step_sampler(grib: ForecastGrib, point: PointSampler) -> StepSampler:
    """The sampler of the model of the file."""
    return (StepSampler if grib.grid is not None else IconStepSampler)(grib, point)


def init_worker(grib_path: Path, lat: float, lng: float) -> None:
    """Index the forecast file and locate the point once per process."""
    global _sampler  # pylint: disable=global-statement
    grib = ForecastGrib(grib_path)
    _sampler = step_sampler(grib, locate(grib, lat, lng))


def sample_step(step: int) -> dict:
    """Worker: every value of one step at the location."""
    return _sampler.sample(step)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n", maxsplit=1)[0])
    parser.add_argument("grib", type=Path, help="forecast file ecmwf_<run>.grb2 or icon-d2_<run>.grb2")
    parser.add_argument("--lat", type=float, required=True, help="latitude in degrees north")
    parser.add_argument("--lng", type=float, required=True, help="longitude in degrees east")
    parser.add_argument("--elevation", type=float, help="real height of the location in m")
    parser.add_argument("--label", help="name of the location for the header")
    parser.add_argument("--tsv", type=Path, help="also write every GRIB parameter to this TSV file")
    parser.add_argument("--workers", type=int, default=os.cpu_count(), help="processes (default: CPUs)")
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    # Windows consoles default to cp1252, which lacks "–" and "Δ".
    sys.stdout.reconfigure(encoding="utf-8")
    args = parse_args(argv)
    grib = ForecastGrib(args.grib)
    try:
        point = locate(grib, args.lat, args.lng)
    except ValueError as error:
        print(error, file=sys.stderr)
        return 1
    with ProcessPoolExecutor(max_workers=args.workers, initializer=init_worker,
                             initargs=(args.grib, args.lat, args.lng)) as pool:
        rows = list(pool.map(sample_step, grib.steps("t")))
    if grib.grid is not None:
        print_ecmwf(LocationTables(grib, point), args, rows)
    else:
        print_icon(IconLocationTables(grib, point), args, rows)
    if args.tsv:
        ForecastTsv(args.tsv).write([grib.valid_time(row["step"]) for row in rows], [row["step"] for row in rows],
                                    [row["grib"] for row in rows])
    return 0


def print_ecmwf(tables: LocationTables, args: argparse.Namespace, rows: list[dict]) -> None:
    print(tables.header(args.label, args.lat, args.lng, args.elevation, rows))
    print("\n## Free atmosphere and boundary layer\n")
    print(tables.main_table(rows))
    print("\n## Mountain weather\n")
    print(tables.mountain_table(rows))
    print("\n## Daily extremes at 2 m (model height)\n")
    print(tables.extremes_table())


def print_icon(tables: IconLocationTables, args: argparse.Namespace, rows: list[dict]) -> None:
    print(tables.header(args.label, args.lat, args.lng, args.elevation, rows))
    print("\n## Weather at the ground\n")
    print(tables.surface_table(rows))
    print("\n## Free atmosphere\n")
    print(tables.upper_table(rows))
    print("\n## Daily extremes at 2 m (model height)\n")
    print(tables.extremes_table(rows))


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
