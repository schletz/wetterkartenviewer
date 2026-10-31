"""Download one ICON-D2 run of DWD open data (raw icosahedral grid, about 2.2 km) into a single GRIB2 file.

ICON-D2 starts every 3 hours and runs hourly to T+48. The fields stay on
the unstructured model grid; render_charts.py interpolates them straight
onto the chart pixels (lib/triangle_grid.py). Parameters, as named by DWD
(and as indexed by ForecastGrib with constants.ICON_NAMES):

    clat, clon, hsurf, fr_land     time invariant: cell centres (deg), model orography (m),
                                   land fraction (0..1); shortNames tlat, tlon, HSURF, lsm
    clct                           total cloud cover (%), T+0..48; CLCT -> tcc
    tot_prec                       total precipitation since T+0 (kg/m2 = mm); tp
    pmsl                           mean sea level pressure (Pa); prmsl -> msl
    ww                             significant weather (WMO 4677), T+1..48; WW -> ww
    vmax_10m                       maximum 10 m gust of the last hour (m/s); max_i10fg -> gust
    t_2m, tmax_2m, tmin_2m         2 m temperature and its extremes (K); 2t, max_2t -> tmax_2m,
                                   min_2t -> tmin_2m (they restart every 6 h, lib/icon_extremes.py)
    u_10m, v_10m                   10 m wind (m/s); 10u, 10v
    ceiling                        base of the lowest cloud layer above 50 % cover (m above sea level,
                                   about 20 km where there is none); ceil -> ceiling
    u, v @1000 hPa                 wind (m/s) for t2m_wind1000
    t, relhum, fi, u, v @850, 700  pressure levels for the values at 2000 m (mountain_2000): K, % (r),
                                   geopotential m2/s2 (z), m/s; ICON-D2 has no 925 hPa

Parameters on pressure levels are written "<folder>@<hPa>" (FORECAST_PARAMS). A run
is about 1130 files, 610 MB to download and 820 MB as GRIB.

Without --run the newest complete run is taken: the run folders (00/ ... 21/)
are ordered by the newest time stamp of their parameter folders, and the
first one whose parameters all reach T+48 wins (lib/icon_runs.py). Messages
between full hours (tot_prec at :15, :30, :45) are left out.

If the target is an existing directory, the file is written into it as
icon-d2_<YYYYMMDDHH>.grb2; the last line printed is the absolute path of the
file. A target that already holds one message per file of the run is not
downloaded again. The file is assembled as <out>.part and renamed at the end;
the raw files land in <out>.raw/ and are removed after success (--keep-raw
keeps them), so an interrupted call can simply be repeated.

A file missing on the server (also a gap in its listing) or delivered
damaged does not stop the download: it is written as a copy of the same
field at another step with every value missing (a warning names it), and
the charts of that step say "No data available".

Example::

    python download_icon_d2.py data
    python download_icon_d2.py data --run 2026103106
"""

import argparse
import shutil
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

# Keep imports working under "python -I", which drops the script directory.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib.forecast_writer import message_spans  # noqa: E402
from lib.icon_downloader import IconDownloader  # noqa: E402
from lib.icon_runs import IconRuns  # noqa: E402

# Pressure levels (hPa) of the height profile: they bracket 2000 m (mountain_2000) everywhere;
# ICON-D2 has no 925 hPa.
PROFILE_LEVELS = (850, 700)
FORECAST_PARAMS = ("clct", "tot_prec", "pmsl", "ww", "vmax_10m", "t_2m", "tmax_2m", "tmin_2m", "u_10m", "v_10m", "ceiling",
                   "u@1000", "v@1000", *(f"{p}@{level}" for level in PROFILE_LEVELS for p in ("t", "relhum", "fi", "u", "v")))
STATIC_PARAMS = ("clat", "clon", "hsurf", "fr_land")
PARALLEL_REQUESTS = 8
PREFIX = "icon-d2_"


def parse_args(argv: list[str]) -> argparse.Namespace:
    """Command line options."""
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n", maxsplit=1)[0])
    parser.add_argument("out", type=Path, help=f"target GRIB2 file or a directory for {PREFIX}<run>.grb2")
    parser.add_argument("--run", help="run in YYYYMMDDHH (00, 03, ... 21 UTC); default: newest complete run")
    parser.add_argument("--keep-raw", action="store_true", help="keep the raw files in <out>.raw/")
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    started = time.monotonic()
    runs = IconRuns(FORECAST_PARAMS, STATIC_PARAMS)
    try:
        run = runs.run(args.run) if args.run else runs.latest()
    except RuntimeError as error:
        print(error, file=sys.stderr)
        return 1
    print(f"run {run.run}: {len(run.urls)} files", flush=True)
    out = args.out / f"{PREFIX}{run.run}.grb2" if args.out.is_dir() else args.out
    if out.exists() and len(message_spans(out)) == len(run.urls):
        print("already on disk")
        print(out.resolve())
        return 0

    raw_dir = out.with_name(out.name + ".raw")
    raw_dir.mkdir(parents=True, exist_ok=True)
    downloader = IconDownloader(raw_dir)
    with ThreadPoolExecutor(max_workers=PARALLEL_REQUESTS) as pool:
        raw_files = list(pool.map(downloader.fetch, run.urls))
    print(f"downloaded in {time.monotonic() - started:.0f}s", flush=True)
    part = out.with_name(out.name + ".part")
    count = downloader.join(list(run.urls), raw_files, part)
    if count != len(run.urls):
        print(f"{count} messages instead of one per file ({len(run.urls)})", file=sys.stderr)
        return 1
    part.replace(out)
    print(f"{count} messages, {out.stat().st_size / 1e6:.0f} MB ({time.monotonic() - started:.0f}s)")
    if not args.keep_raw:
        shutil.rmtree(raw_dir)
    print(out.resolve())
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
