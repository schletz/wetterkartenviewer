"""Download the newest ECMWF and ICON-D2 runs into data/, render their charts there and encode the tiles as videos in maps/.

data/ (not committed except charts.md) holds exactly one run of each model plus what does not
depend on it; the synop skill reads it as its data directory:

    ecmwf_<run>.grb2                forecast file with derived fields (download_ecmwf_data.py)
    opencharts_europe/              every product (render_charts.py --products all)
    opencharts_central_europe/      the default products of the window
    icon-d2_<run>.grb2              ICON-D2 run on the raw model grid (download_icon_d2.py)
    icon-d2/                        the ICON-D2 products: Austria and surroundings, hourly to T+48
    era5_means/                     climatology for t850_anomaly and the skill, kept across runs;
                                    downloaded by hand (README.md)
    charts.md                       products and GRIB contents for the skill; copied into
                                    any other data directory

maps/ holds only what the web app loads: manifest.json (committed) and one
AV1 video <window>/<product>.mp4 per tile layer in src/config/viewer.config.json
(tile_videos.py, published as release assets by publish_maps.py).

Files of older runs in data/ are deleted. What else happens depends on the run, separately
for ECMWF (every 12 h) and ICON-D2 (every 3 h), so a new ICON run renders only its window:

    new run or --force    the model's windows in maps/ are emptied and rendered, their layers encoded
    same run              a window is rendered only if its folder in data/ is missing or a tile
                          layer of it has no charts there (a product just added to the config);
                          only layers without a video are encoded. Videos of removed layers stay until the next run; the manifest
                          lists only the layers of the config.

"Same run" means that maps/manifest.json names the run: the ECMWF run at its top,
the ICON-D2 run at the layers of its window. The manifest is deleted before anything
is rendered or emptied, so an interrupted call counts as a new run of both models.
If the ICON-D2 download fails, its window keeps what it had (a warning, no exit).

Usage: python scripts/update_maps.py data maps [--base YYYYMMDDHH] [--icon-run YYYYMMDDHH] [--force]
"""

import argparse
import shutil
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from lib.climate_archive import DIRECTORY as CLIMATE_DIRECTORY, ClimateArchive
from maps_manifest import (MANIFEST, chart_frames, read_run, read_window_runs, tile_chart_paths, video_file,
                           write_manifest)
from tile_videos import encode_video

SCRIPTS = Path(__file__).resolve().parent
CHARTS_DOC = SCRIPTS.parent / "data" / "charts.md"
# Products per window (None: the defaults); the Europe window gets all of them for locations outside central Europe.
WINDOWS = {"opencharts_europe": "all", "opencharts_central_europe": None}
ICON_WINDOWS = {"icon-d2": None}
ECMWF_PREFIX, ICON_PREFIX = "ecmwf_", "icon-d2_"
# ffmpeg processes at a time; libaom uses several threads each.
PARALLEL_ENCODES = 3


def check_climate(data: Path) -> None:
    """Exit if data/ has no climatology, before anything is downloaded or deleted.

    Both windows render t850_anomaly, which needs it. The climatology is not
    committed; it is downloaded once by hand (README.md), and without this
    check the renderer would fail only after the download of several minutes.
    """
    directory = data / CLIMATE_DIRECTORY
    try:
        ClimateArchive(directory)
    except FileNotFoundError:
        sys.exit(f"no climatology in {directory}: t850_anomaly needs era5_means.grb2; download it "
                 "as described in README.md (section Klimatologie) and run again")


def download(script: str, data: Path, options: list[str]) -> Path | None:
    """Run a downloader with its output shown live; returns the GRIB path (its last line), None if it failed."""
    command = [sys.executable, str(SCRIPTS / script), str(data), *options]
    last = ""
    with subprocess.Popen(command, stdout=subprocess.PIPE, text=True, encoding="utf-8") as process:
        for line in process.stdout:
            print(line, end="", flush=True)
            last = line.strip() or last
    if process.returncode:
        print(f"{script} failed with exit code {process.returncode}", file=sys.stderr)
        return None
    return Path(last)


def remove_old_runs(data: Path, grib: Path, prefix: str) -> None:
    """Delete GRIB files, unfinished parts and raw download folders of other runs of one model."""
    keep = (grib.name, grib.name + ".raw", grib.name + ".part")
    for old in data.glob(f"{prefix}*.grb2*"):
        if old.name not in keep:
            if old.is_dir():
                shutil.rmtree(old)
            else:
                old.unlink()
            print(f"removed {old}")


def render(grib: Path, data: Path, window: str) -> str:
    """Render the products of one window into data/; returns the output of the renderer."""
    command = [sys.executable, str(SCRIPTS / "render_charts.py"), str(grib), str(data), "--projection", window]
    products = {**WINDOWS, **ICON_WINDOWS}[window]
    if products:
        command += ["--products", products]
    result = subprocess.run(command, capture_output=True, text=True, encoding="utf-8")
    if result.returncode:
        sys.exit(f"rendering {window} failed:\n{result.stdout}{result.stderr}")
    return result.stdout


def stale_windows(data: Path, maps: Path, windows: dict, same_run: bool, run: str) -> list[str]:
    """Windows of one model to render; empties their videos in maps/ unless the run is the same.

    With the same run a window is rendered again only if its folder is missing or
    a tile layer of it has no charts yet, e.g. a product just added to the config.
    """
    if not same_run:
        for window in windows:
            shutil.rmtree(maps / window, ignore_errors=True)
        return list(windows)
    layers = tile_chart_paths()
    return [window for window in windows if not (data / window).is_dir() or any(
        not chart_frames(data, path, run) for path in layers if path.split("/")[0] == window)]


def encode_missing(data: Path, maps: Path, run: str) -> None:
    """Encode every tile layer that has no video in maps/ yet.

    A layer of an ICON-D2 window without charts (its first download failed)
    is skipped with a warning, so ECMWF still updates.
    """
    paths = [path for path in tile_chart_paths() if not (maps / video_file(path)).exists()]
    missing = [path for path in paths if not chart_frames(data, path, run)]
    for path in [path for path in missing if path.split("/")[0] in ICON_WINDOWS]:
        print(f"warning: no charts in {data} for {path}", file=sys.stderr)
        missing.remove(path)
        paths.remove(path)
    if missing:
        sys.exit(f"no charts in {data} for {', '.join(missing)}; render them or remove them from the tiles")

    def encode(path: str) -> str:
        encode_video([chart for _, chart in chart_frames(data, path, run)], maps / video_file(path))
        return path

    with ThreadPoolExecutor(PARALLEL_ENCODES) as pool:
        for path in pool.map(encode, paths):
            print(f"encoded {video_file(path)}", flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("data", type=Path, help="data directory (forecasts, all charts, climatology)")
    parser.add_argument("maps", type=Path, help="video directory of the web app")
    parser.add_argument("--base", help="ECMWF run YYYYMMDDHH instead of the newest one")
    parser.add_argument("--icon-run", help="ICON-D2 run YYYYMMDDHH instead of the newest one")
    parser.add_argument("--force", action="store_true", help="render and encode even if the manifest has the runs")
    args = parser.parse_args()
    args.data.mkdir(parents=True, exist_ok=True)
    args.maps.mkdir(parents=True, exist_ok=True)

    check_climate(args.data)
    grib = download("download_ecmwf_data.py", args.data, ["--base", args.base] if args.base else [])
    if grib is None:
        sys.exit("ECMWF download failed")
    run = grib.stem.removeprefix(ECMWF_PREFIX)
    remove_old_runs(args.data, grib, ECMWF_PREFIX)
    icon_grib = download("download_icon_d2.py", args.data, ["--run", args.icon_run] if args.icon_run else [])
    if icon_grib is None:
        print("warning: ICON-D2 download failed; its window keeps the charts it has", file=sys.stderr)
    else:
        remove_old_runs(args.data, icon_grib, ICON_PREFIX)
    if (args.data / CHARTS_DOC.name).resolve() != CHARTS_DOC.resolve():
        shutil.copyfile(CHARTS_DOC, args.data / CHARTS_DOC.name)

    published = read_window_runs(args.maps)
    same_run = read_run(args.maps) == run and not args.force
    icon_run = icon_grib.stem.removeprefix(ICON_PREFIX) if icon_grib else None
    # Without a new download the ICON window stays as it is.
    icon_same = icon_grib is None or (all(published.get(w) == icon_run for w in ICON_WINDOWS) and not args.force)
    # The manifest goes first, so an interrupted call is never taken for a finished one.
    (args.maps / MANIFEST).unlink(missing_ok=True)
    renders = {window: grib for window in stale_windows(args.data, args.maps, WINDOWS, same_run, run)}
    if icon_grib is not None:
        renders |= {window: icon_grib for window in stale_windows(args.data, args.maps, ICON_WINDOWS, icon_same, run)}
    if not renders:
        print(f"charts of runs {run} (ECMWF) and {icon_run or 'unchanged'} (ICON-D2) are already rendered")
    for window in renders:
        shutil.rmtree(args.data / window, ignore_errors=True)
    # The renderer spreads over all CPUs; the windows in parallel still finish sooner than one after the other.
    with ThreadPoolExecutor(max(len(renders), 1)) as pool:
        for output in pool.map(lambda window: render(renders[window], args.data, window), renders):
            print(output, end="")
    encode_missing(args.data, args.maps, run)
    print(write_manifest(args.data, args.maps, run))


if __name__ == "__main__":
    main()
