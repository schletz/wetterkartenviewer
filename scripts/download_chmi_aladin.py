"""Download one CHMI ALADIN run (Lambert grid, 2.3 km, to T+72) into a single GRIB file.

CHMI publishes four runs a day (00, 06, 12, 18 UTC), one bz2 file per variable
with all 73 steps, about 3 to 4.5 hours after the start of the run, and keeps them for about three days:
https://opendata.chmi.cz/meteorology/weather/nwp_aladin/Lambert_2.3km/

The file stays GRIB edition 1 on the whole model grid: the server only offers
whole files, so nothing that was downloaded is thrown away. Fields (names as
indexed by ForecastGrib with constants.ALADIN_NAMES):

    SURFGEOPOTENTIEL, SURFIND_TERREMER   z (m2/s2), lsm (0..1), T+0 only
    CLSTEMPERATURE, MSLPRESSURE          2t (K), msl (Pa)
    SURFNEBUL_TOTALE                     tcc (0..1)
    CLS_VISICLD                          fog_visibility: lowest visibility due to cloud in the last hour (m)
    SURFPREC_TOTAL                       tp: accumulated from the start of the run (kg/m2 = mm), from T+1
    SURFDIAG_FLASH                       flash: lightning density accumulated from the start (per km2), from T+1
    PRECIP_TYPE, PRECIP_TYPESEV          ptype, ptype_severe: most frequent and most dangerous type of
                                         the last hour (codes as ECMWF ptype), from T+1
    CLSWIND_SPEED, CLSWIND_DIREC         written as 10u and 10v (m/s, east and north)
    CLSU_RAF_MOD_XFU, CLSV_RAF_MOD_XFU   written as gust: speed of the maximum gust of the last hour (m/s), from T+1
    CLSDEW_P_TEMPER, CLSTPRIM_W          2d, wbt: 2 m dew point and wet-bulb temperature (K)
    CLSMAXI_TEMPERAT, CLSMINI_TEMPERAT   tmax_2m, tmin_2m: 2 m extremes of the last 12 h (K), at T+12, 24 ... 72
    P85000..., P70000...                 t (K), r (0..1), z (m2/s2), u, v (m/s, turned to east and north)
    P00000WIND_U_COM, P00000WIND_V_COM   u, v at 1000 hPa (m/s, turned to east and north)

If the target is an existing directory, the file is written into it as
chmi-aladin_<YYYYMMDDHH>.grb; the last line printed is the absolute path of the
file. A target that already holds every message of the run is not downloaded
again. The file is assembled as <out>.part and renamed at the end; the raw files
land in <out>.raw/ and are removed after success, so an interrupted call can
simply be repeated. A run CHMI is still uploading has too few messages in a file:
the call then fails, and the next one tries again.

Example::

    python download_chmi_aladin.py data
    python download_chmi_aladin.py data --run 2026110900
"""

import argparse
import bz2
import shutil
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from pathlib import Path

import eccodes
import requests

# Keep imports working under "python -I", which drops the script directory.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib.aladin_runs import AladinRuns  # noqa: E402
from lib.aladin_writer import AladinWriter  # noqa: E402
from lib.progress import Progress  # noqa: E402
from lib.run_schedule import RunSchedule  # noqa: E402

PREFIX = "chmi-aladin_"
SUFFIX = ".grb"
# The last file of a run was written 3:14 to 3:36 h (00, 12 UTC) or 4:26 to 4:34 h (06, 18 UTC)
# after its start, in the 11 runs read on 2026-11-09; the earliest value counts for every cycle.
SCHEDULE = RunSchedule(PREFIX, SUFFIX, timedelta(hours=6), timedelta(hours=3))
PARALLEL_REQUESTS = 4
RETRIES = 3
RETRY_DELAY = 10
TIMEOUT_S = 300
CHUNK = 1 << 20


def count_messages(path: Path) -> int:
    """Number of GRIB messages of a file; a truncated last message does not count."""
    with path.open("rb") as fh:
        return eccodes.codes_count_in_file(fh)


def fetch(raw_dir: Path, run: str, variable: str) -> Path:
    """Unpacked file of one variable; one that exists was complete, since it is written through .part.

    Raises:
        RuntimeError: if the file on the server holds too few messages, as during an upload.
        requests.RequestException, EOFError, OSError: if it stays out of reach after the last attempt.
    """
    target = raw_dir / f"{variable}{SUFFIX}"
    if target.exists():
        return target
    part = target.with_name(target.name + ".part")
    for attempt in range(1, RETRIES + 1):
        try:
            with requests.get(AladinRuns.url(run, variable), stream=True, timeout=TIMEOUT_S) as response:
                response.raise_for_status()
                unpack = bz2.BZ2Decompressor()
                with part.open("wb") as out:
                    for chunk in response.iter_content(CHUNK):
                        out.write(unpack.decompress(chunk))
            found = count_messages(part)
            if found != AladinWriter.expected_messages(variable):
                part.unlink()
                raise RuntimeError(f"{variable} of run {run} has {found} messages, upload still running?")
            part.replace(target)
            return target
        except (requests.RequestException, EOFError, OSError):
            part.unlink(missing_ok=True)
            if attempt == RETRIES:
                raise
            time.sleep(RETRY_DELAY)
    raise AssertionError("unreachable")


def parse_args(argv: list[str]) -> argparse.Namespace:
    """Command line options."""
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n", maxsplit=1)[0])
    parser.add_argument("out", type=Path, help=f"target GRIB file or a directory for {PREFIX}<run>{SUFFIX}")
    parser.add_argument("--run", help="run in YYYYMMDDHH (00, 06, 12 or 18 UTC); default: newest complete run")
    parser.add_argument("--keep-raw", action="store_true", help="keep the raw files in <out>.raw/")
    parser.add_argument("--force", action="store_true", help="ask the server even if no new run can be complete yet")
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    if not (args.run or args.force) and (waiting := SCHEDULE.file_until_next_run(args.out)):
        print(waiting)
        return 0
    started = time.monotonic()
    runs = AladinRuns(AladinWriter.VARIABLES)
    try:
        run = args.run or runs.latest()
        if args.run and not runs.has(args.run):
            raise RuntimeError(f"run {args.run} is not complete on the server")
    except (RuntimeError, requests.RequestException) as error:
        print(error, file=sys.stderr)
        return 1
    out = args.out / f"{PREFIX}{run}{SUFFIX}" if args.out.is_dir() else args.out
    print(f"run {run}: {len(AladinWriter.VARIABLES)} files", flush=True)
    if out.exists() and count_messages(out) == AladinWriter.expected_total():
        print("already on disk")
        print(out.resolve())
        return 0

    raw_dir = out.with_name(out.name + ".raw")
    raw_dir.mkdir(parents=True, exist_ok=True)
    progress = Progress("CHMI ALADIN download", len(AladinWriter.VARIABLES), "files", every=0)

    def get(variable: str) -> tuple[str, Path]:
        raw = fetch(raw_dir, run, variable)
        progress.advance(variable)
        return variable, raw

    try:
        with ThreadPoolExecutor(max_workers=PARALLEL_REQUESTS) as pool:
            raw_files = dict(pool.map(get, AladinWriter.VARIABLES))
    except (RuntimeError, requests.RequestException, EOFError, OSError) as error:
        print(error, file=sys.stderr)
        return 1
    print(f"downloaded in {time.monotonic() - started:.0f}s, joining the files", flush=True)
    part = out.with_name(out.name + ".part")
    count = AladinWriter().write(raw_files, part)
    if count != AladinWriter.expected_total():
        print(f"{count} messages instead of {AladinWriter.expected_total()}", file=sys.stderr)
        return 1
    part.replace(out)
    print(f"{count} messages, {out.stat().st_size / 1e6:.0f} MB ({time.monotonic() - started:.0f}s)")
    if not args.keep_raw:
        shutil.rmtree(raw_dir)
    print(out.resolve())
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
