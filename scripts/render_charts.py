"""Render synoptic charts from a forecast file of download_ecmwf_data.py or download_icon_d2.py.

Every chart has the projection and the 1200x600 px map area of an ECMWF
open charts window (see lib/projection.py), plus a 90 px legend strip
below with valid time, title, run and colour bar. The products are
defined in lib/chart_products.py; one chart per step unless noted:

    z500_t850        T850 shading, isotherms every 4 K, Z500 contours, L/H centres
    z700_t700        T700 shading (ECMWF medium-t-z), isotherms every 4 K, Z700 contours every 5 dam, L/H centres
    z850_rh700       700 hPa relative humidity shading (> 65 %), Z850 contours every 4 dam, L/H centres
    thickness_mslp   1000-500 hPa thickness shading, isobars every 5 hPa, L/H centres
    t850_mslp        T850 shading under the isobars, values printed on zoomed windows
    t850_anomaly     T850 against the climatology of the same day and time of day (sigma), Z500 contours
    rh700_wind700    700 hPa relative humidity (> 65 %), wind arrows, ascent/subsidence lines
    vt_rh700         vertical totals T850 - T500 (convective instability), RH700 lines
    dt850_24h        24 h change of T850 (warm/cold advection), Z500 contours; from T+24
    t2m_wind10m      2 m temperature, 0 deg C line, 10 m wind arrows
    wind10m          10 m wind speed in km/h (Beaufort bands), streamlines, isobars every 4 hPa
    inversion        temperature increase 1000-850 hPa, moist boundary layer hatched, 925 hPa wind line
    mountain_2000    temperature, wind and summits in cloud at 2000 m
    freezing_level   freezing level
    snow_line        snow line where the upper air signals precipitation
    weather_summary  cloud cover, 6 h precipitation and its type, isobars every 4 hPa (near-surface
                     model weather); from T+3
    tmax, tmin      daily 2 m maximum (06-18 UTC) and minimum (18-06 UTC), one chart per day
    orography        model orography and rough sub-grid terrain, one static chart

An ICON-D2 file (unstructured grid, lib/icon_products.py) has its own products,
hourly from T+1 to T+48 on the window icon-d2 (Austria and surroundings, Lambert,
with the borders of the Austrian states):

    t2m_wind10m      as above
    wind10m          as above
    mountain_2000    as above, the profile from 850 and 700 hPa
    weather_summary  as above with 1 h precipitation, plus thunderstorm, hail, fog and storm gusts
    tmax, tmin       as above, from the 6-hourly extremes of the model (lib/icon_extremes.py)
    orography        model orography, one static chart: how finely ICON-D2 resolves valleys

--projection chooses the chart window (default: opencharts_europe, icon-d2 for
ICON files). Without --products each window gets its default selection
(ChartProducts.DEFAULTS, IconProducts.DEFAULTS): opencharts_europe
the large scale flow (z500_t850, z700_t700, z850_rh700, thickness_mslp, dt850_24h),
opencharts_central_europe (2.6 times enlarged, Ireland to Romania)
everything else, with isobars every 2 hPa and printed values.
update_maps.py renders every product (--products all) on opencharts_europe,
so locations outside central Europe have all of them.

Output in <outdir>/<projection>/:

    <product>/<YYYYMMDDHH>.webp    valid time in UTC (tmax/tmin: <YYYYMMDD>.webp)
    orography.webp                 static chart
    sheets/<product>.webp          contact sheet: the 12 UTC chart of every day (tmax/tmin: every day;
                                   ICON-D2: 03, 09, 15 and 21 UTC)
    geometry.json                  projection and run of the window and tile origins of every contact
                                   sheet, so readers of data/ can mark a location without this code

t850_anomaly reads the climatology from --climate (default: era5_means/ next to the GRIB file).

Example::

    python render_charts.py data/ecmwf_2026102912.grb2 data
    python render_charts.py data/ecmwf_2026102912.grb2 data --projection opencharts_central_europe --products t850_anomaly
"""

import argparse
import json
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

# Keep imports working under "python -I", which drops the script directory.
sys.path.insert(0, str(Path(__file__).resolve().parent))
import eccodes  # noqa: E402

from lib.base_map import BaseMap  # noqa: E402
from lib.chart_products import ChartProducts  # noqa: E402
from lib.climate_archive import DIRECTORY as CLIMATE_DIRECTORY, ClimateArchive  # noqa: E402
from lib.constants import ICON_NAMES  # noqa: E402
from lib.contact_sheet import ContactSheet  # noqa: E402
from lib.forecast_grib import ForecastGrib  # noqa: E402
from lib.icon_products import IconProducts  # noqa: E402
from lib.icon_surface import IconSurface  # noqa: E402
from lib.model_surface import ModelSurface  # noqa: E402
from lib.pixel_grid import PixelGrid  # noqa: E402
from lib.projection import EUROPE, ICON_D2, PROJECTIONS, Projection  # noqa: E402
from lib.t850_climate import T850Climate  # noqa: E402
from lib.triangle_grid import TriangleGrid  # noqa: E402

# State of a worker process, set once by init_worker.
_products: ChartProducts | None = None


def is_icon(grib_path: Path) -> bool:
    """Whether a forecast file holds ICON fields on the unstructured grid (download_icon_d2.py)."""
    with Path(grib_path).open("rb") as fh:
        gid = eccodes.codes_grib_new_from_file(fh, headers_only=True)
        try:
            return eccodes.codes_get(gid, "gridType") == "unstructured_grid"
        finally:
            eccodes.codes_release(gid)


def build_products(grib_path: Path, projection: Projection, climate_dir: Path | None) -> ChartProducts:
    """Wire the chart products of one window; the climatology is loaded only when a product needs it."""
    if is_icon(grib_path):
        grib = ForecastGrib(grib_path, ICON_NAMES)
        surface = IconSurface(grib)
        return IconProducts(grib, surface, BaseMap(projection),
                            TriangleGrid(surface.lat, surface.lon, projection, surface.valid))
    grib = ForecastGrib(grib_path)
    climate = climate_pixels = None
    if climate_dir is not None:
        archive = ClimateArchive(climate_dir)
        climate, climate_pixels = T850Climate(archive), PixelGrid(archive.grid, projection)
    return ChartProducts(grib, ModelSurface(grib), BaseMap(projection), PixelGrid(grib.grid, projection),
                         climate, climate_pixels)


def init_worker(grib_path: Path, projection: str, climate_dir: Path | None) -> None:
    """Load the forecast index, pixel mappings and base map once per process."""
    global _products  # pylint: disable=global-statement
    _products = build_products(grib_path, PROJECTIONS[projection], climate_dir)


def render(task: tuple) -> Path:
    """Worker: render one (product, key) and return the file written."""
    product, key, out_dir = task
    canvas = _products.draw(product, key)
    path = _products.path(out_dir, product, key)
    canvas.save(path)
    return path


def write_sheets(products: ChartProducts, names: list[str], out_dir: Path, sheet: ContactSheet) -> dict:
    """One contact sheet per product (charts at products.SHEET_HOURS UTC, or every day of tmax/tmin).

    Returns the tile origins (x, y) of every sheet written, keyed by product.
    """
    grib = products.grib
    run = f"run {grib.base_time:%d.%m.%Y %H} UTC"
    written = {}
    for name in names:
        if name in products.STEP:
            steps = [s for s in products.keys(name) if grib.valid_time(s).hour in products.SHEET_HOURS]
            tiles = [(products.path(out_dir, name, s), f"{grib.valid_time(s):%a %d.%m. %H} UTC") for s in steps]
            title = f"{name}: {'/'.join(f'{h:02d}' for h in products.SHEET_HOURS)} UTC of every day, {run}"
        elif name in products.DAY:
            tiles = [(products.path(out_dir, name, d), f"{d:%a %d.%m.}") for d in products.keys(name)]
            title = f"{name}: every day, {run}"
        else:
            continue
        if tiles:
            sheet.build(tiles, title, out_dir / "sheets" / f"{name}.webp")
            written[name] = sheet.origins(len(tiles))
    return written


def write_geometry(projection: Projection, products: ChartProducts, sheet: ContactSheet, sheets: dict,
                   out_dir: Path) -> None:
    """geometry.json of a window: what a reader needs to draw a location onto charts and contact sheets.

    ``model`` and ``run`` (YYYYMMDDHH) name the forecast the charts come from;
    maps_manifest.py takes the run of a window from here.

    Sheet entries of other products are kept, so rendering single products adds to the file.
    """
    path = out_dir / "geometry.json"
    known = json.loads(path.read_text(encoding="utf-8"))["sheets"]["tiles"] if path.exists() else {}
    geometry = {
        "window": projection.name,
        "model": products.MODEL,
        "run": f"{products.grib.base_time:%Y%m%d%H}",
        "image": {"width": projection.width, "height": projection.height},
        "projection": {"pole_x": projection.pole_x, "pole_y": projection.pole_y, "scale_k": projection.scale_k,
                       "cone": projection.cone, "lon0": projection.lon0,
                       "formula": "rho = scale_k * tan(45 - lat/2) ** cone; x = pole_x + rho * sin(cone * (lon - lon0)); "
                                  "y = pole_y + rho * cos(cone * (lon - lon0)); degrees, origin top left, y down"},
        "sheets": {"scale": sheet.scale, "tiles": {**known, **sheets}},
    }
    path.write_text(json.dumps(geometry, indent=1), encoding="utf-8")


def parse_args(argv: list[str]) -> argparse.Namespace:
    """Command line options."""
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n", maxsplit=1)[0])
    parser.add_argument("grib", type=Path, help="forecast file of download_ecmwf_data.py or download_icon_d2.py")
    parser.add_argument("outdir", type=Path, help="target directory")
    parser.add_argument("--climate", type=Path, help="directory of the climatology (default: era5_means next to grib)")
    parser.add_argument("--projection", choices=sorted(PROJECTIONS),
                        help=f"chart window (default: {EUROPE.name}, {ICON_D2.name} for ICON files)")
    parser.add_argument("--products", help="comma separated products or 'all' (default: selection of the window)")
    parser.add_argument("--workers", type=int, default=os.cpu_count(), help="render processes (default: CPUs)")
    args = parser.parse_args(argv)
    icon = is_icon(args.grib)
    products = IconProducts if icon else ChartProducts
    args.projection = args.projection or (ICON_D2 if icon else EUROPE).name
    if args.climate is None:
        args.climate = args.grib.parent / CLIMATE_DIRECTORY
    if not args.products:
        args.products = list(products.DEFAULTS[args.projection])
    elif args.products == "all":
        args.products = list(products.ALL)
    else:
        args.products = [p.strip() for p in args.products.split(",") if p.strip()]
    unknown = set(args.products) - set(products.ALL)
    if unknown:
        parser.error(f"unknown products: {', '.join(sorted(unknown))}")
    return args


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    started = time.monotonic()
    projection = PROJECTIONS[args.projection]
    out_dir = args.outdir / projection.name
    climate_dir = args.climate if any(name in ChartProducts.CLIMATE for name in args.products) else None
    products = build_products(args.grib, projection, climate_dir)
    tasks = [(name, key, out_dir) for name in args.products for key in products.keys(name)]
    print(f"run {products.grib.base_time:%Y%m%d%H}, {projection.name}: {len(tasks)} charts", flush=True)
    with ProcessPoolExecutor(max_workers=args.workers, initializer=init_worker,
                             initargs=(args.grib, projection.name, climate_dir)) as pool:
        written = list(pool.map(render, tasks, chunksize=2))
    sheet = ContactSheet()
    sheets = write_sheets(products, args.products, out_dir, sheet)
    write_geometry(projection, products, sheet, sheets, out_dir)
    print(f"{len(written)} charts and {len(sheets)} contact sheets in {out_dir} "
          f"({time.monotonic() - started:.0f}s)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
