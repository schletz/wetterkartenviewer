"""Download one ECMWF IFS HRES run (0.1 deg) from ECMWF open data into a single GRIB2 file.

The fields are cut to the lat/lon box around the chart windows of
lib/projection.py (the Europe window holds all others) and written to one file with
every parameter and step from T+0 to T+240, followed by the derived fields
of lib/derived_writer.py (values at 2000/2500/3000 m, freezing level, snow
line, inversion, boundary layer humidity, precipitation signal, free
atmosphere wind at 1000/925 hPa, orography in m, daily 2 m extremes):

    t, r, gh 500/600/700/850/925/1000        pressure levels; the profile gives heights such as
                                             2000 m and the freezing level
    u/v/w 700, u/v 850/925/1000              pressure levels (w: vertical velocity, Pa/s)
    thick                                    1000-500 hPa thickness (gpm), gh500 - gh1000
    msl, 2t                                  surface, every step
    mx2t3/mn2t3 (T+3..144), mx2t6/mn2t6      2 m max/min over the last 3 or 6 hours
    z, sdor, lsm (T+0 only)                  model orography (m2/s2), its sub-grid standard deviation (m),
                                             land-sea mask (0..1)
    tcc, tp, ptype                           total cloud cover, total precipitation since T+0 (m),
                                             precipitation type; only for the weather_summary chart

Apart from the 2 m temperature, the derived fields use no near-surface
parameters: the weather at the ground is derived from the pressure levels.
Cloud cover and precipitation feed only the weather_summary chart.
The 925 and 1000 hPa levels describe the boundary layer (inversion,
moist layer, mixing); where the ground lies above them, their values are
extrapolated by the model.

Steps run 3-hourly to T+144 and 6-hourly to T+240 (65 steps). Without
--base the newest 00z or 12z run that reaches T+240 is taken; 06z and 18z
end at T+144. A run appears at 0.1 deg about 2 h after 0.25 deg; if a
newer run is already out at 0.25 deg only, a notice on stderr gives its
expected arrival (time of the last 0p1/ folder + 12 h) and the older run
is downloaded.

If the target is an existing directory, the file is written into it as
ecmwf_<YYYYMMDDHH>.grb2 of the chosen run; the last line printed is the
absolute path of the file. A complete target file (RequestPlan.expected_total)
is not downloaded again. The file is assembled as <out>.part and renamed at
the end, so a target that exists is complete.

The raw global files land in <out>.raw/ and are removed after a
successful run (--keep-raw keeps them). A group whose raw file already
holds every expected message is not downloaded again, so an interrupted
call can simply be repeated.

Step files missing on the server and damaged messages do not stop the
download: those fields are written with every value missing (a warning
names them), and the charts of their steps say "No data available".
Only a run of which the server has no step at all fails.

Example::

    python download_ecmwf_data.py ecmwf_2026102912.grb2
    python download_ecmwf_data.py ecmwf_2026102900.grb2 --base 2026102900
    python download_ecmwf_data.py workdir
"""

import argparse
import contextlib
import os
import shutil
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path

from ecmwf.opendata import Client

# Keep imports working under "python -I", which drops the script directory.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib.derived_writer import DerivedWriter  # noqa: E402
from lib.forecast_writer import ForecastWriter  # noqa: E402
from lib.grib_cropper import GribCropper  # noqa: E402
from lib.group_downloader import GroupDownloader  # noqa: E402
from lib.open_data_runs import MAX_STEP, OpenDataRuns  # noqa: E402
from lib.projection import PROJECTIONS  # noqa: E402
from lib.request_plan import RequestPlan  # noqa: E402

STEPS = list(range(0, 144, 3)) + list(range(144, MAX_STEP + 1, 6))
PARALLEL_REQUESTS = 4


def parse_args(argv: list[str]) -> argparse.Namespace:
    """Command line options."""
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n", maxsplit=1)[0])
    parser.add_argument("out", type=Path,
                        help="target GRIB2 file, e.g. ecmwf_2026102912.grb2, or a directory for ecmwf_<run>.grb2")
    parser.add_argument("--base", help="run in YYYYMMDDHH (00 or 12 UTC); default: newest complete run")
    parser.add_argument("--max-step", type=int, default=MAX_STEP,
                        help=f"last step in hours (default {MAX_STEP}); smaller values for quick tests")
    parser.add_argument("--keep-raw", action="store_true", help="keep the global raw files in <out>.raw/")
    args = parser.parse_args(argv)
    if args.base:
        args.base = datetime.strptime(args.base, "%Y%m%d%H")
        if args.base.hour not in (0, 12):
            parser.error("only the 00z and 12z runs reach T+240")
    return args


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    started = time.monotonic()
    client = Client(source="ecmwf", resol="0p1")
    runs = OpenDataRuns(client, Client(source="ecmwf", resol="0p25"))
    run = args.base or runs.latest()
    print(f"run {run:%Y%m%d%H}", flush=True)
    if not args.base and (notice := runs.pending_notice(run)):
        print(notice, file=sys.stderr, flush=True)
    out = args.out / f"ecmwf_{run:%Y%m%d%H}.grb2" if args.out.is_dir() else args.out

    plan = RequestPlan([s for s in STEPS if s <= args.max_step], run)
    if plan.output_complete(out):
        print("already on disk")
        print(out.resolve())
        return 0
    raw_dir = out.with_name(out.name + ".raw")
    raw_dir.mkdir(parents=True, exist_ok=True)
    downloader = GroupDownloader(client, run, raw_dir)
    # The progress bars of ecmwf-opendata cannot be switched off and would flood
    # the log of an agent, so stderr is muted while downloading; errors are
    # re-raised by result() after the block.
    with open(os.devnull, "w", encoding="utf-8") as devnull, contextlib.redirect_stderr(devnull):
        # A few groups in parallel; each one already fetches its steps by byte ranges.
        with ThreadPoolExecutor(max_workers=PARALLEL_REQUESTS) as pool:
            futures = [pool.submit(downloader.retrieve, name, req) for name, req in plan.groups.items()]
    try:
        raw_files = [future.result() for future in futures]
    except RuntimeError as error:
        print(error, file=sys.stderr)
        return 1
    print(f"downloaded in {time.monotonic() - started:.0f}s", flush=True)

    cropper = GribCropper.for_windows(list(PROJECTIONS.values()))
    part = out.with_name(out.name + ".part")
    count = ForecastWriter(cropper).write(raw_files, part, plan.fields())
    print(f"{count} messages cropped to box {cropper.grid['Nj']}x{cropper.grid['Ni']} "
          f"({time.monotonic() - started:.0f}s)", flush=True)
    count += DerivedWriter().append(part)
    part.replace(out)
    print(f"{count} messages with derived fields, {out.stat().st_size / 1e6:.0f} MB "
          f"({time.monotonic() - started:.0f}s)")
    if not args.keep_raw:
        shutil.rmtree(raw_dir)
    print(out.resolve())
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
