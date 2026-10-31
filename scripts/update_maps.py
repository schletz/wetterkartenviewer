"""Download the newest ECMWF run into data/, render its charts there and encode the tiles as videos in maps/.

data/ (not committed except charts.md) holds exactly one run plus what does not depend on it;
the synop skill reads it as its data directory:

    ecmwf_<run>.grb2                forecast file with derived fields (download_ecmwf_data.py)
    opencharts_europe/              every product (render_charts.py --products all)
    opencharts_central_europe/      the default products of the window
    era5_means/                     climatology for t850_anomaly and the skill, kept across runs;
                                    downloaded by hand (README.md)
    charts.md                       products and GRIB contents for the skill; copied into
                                    any other data directory

maps/ holds only what the web app loads: manifest.json (committed) and one
AV1 video <window>/<product>.mp4 per tile layer in src/config/viewer.config.json
(tile_videos.py, published as release assets by publish_maps.py).

Files of older runs in data/ are deleted. What else happens depends on the run:

    new run or --force    maps/ is emptied, both windows are rendered, every layer is encoded
    same run              nothing is rendered (unless a window folder in data/ is missing);
                          only layers without a video are encoded, e.g. ones just added to the
                          config. Videos of removed layers stay until the next run; the manifest
                          lists only the layers of the config.

"Same run" means that maps/manifest.json names the run. It is deleted before
anything is rendered or emptied, so an interrupted call counts as a new run.

Usage: python scripts/update_maps.py data maps [--base YYYYMMDDHH] [--force]
"""

import argparse
import shutil
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from lib.climate_archive import DIRECTORY as CLIMATE_DIRECTORY, ClimateArchive
from maps_manifest import MANIFEST, chart_frames, read_run, tile_chart_paths, video_file, write_manifest
from tile_videos import encode_video

SCRIPTS = Path(__file__).resolve().parent
CHARTS_DOC = SCRIPTS.parent / "data" / "charts.md"
# Products per window; the Europe window gets all of them for locations outside central Europe.
WINDOWS = {"opencharts_europe": "all", "opencharts_central_europe": None}
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


def download(data: Path, base: str | None) -> Path:
    """Run the downloader with its output shown live; returns the GRIB path (its last line)."""
    command = [sys.executable, str(SCRIPTS / "download_ecmwf_data.py"), str(data)]
    if base:
        command += ["--base", base]
    last = ""
    with subprocess.Popen(command, stdout=subprocess.PIPE, text=True, encoding="utf-8") as process:
        for line in process.stdout:
            print(line, end="", flush=True)
            last = line.strip() or last
    if process.returncode:
        sys.exit(f"download failed with exit code {process.returncode}")
    return Path(last)


def remove_old_runs(data: Path, grib: Path) -> None:
    """Delete GRIB files, unfinished parts and raw download folders of other runs."""
    keep = (grib.name, grib.name + ".raw", grib.name + ".part")
    for old in data.glob("ecmwf_*.grb2*"):
        if old.name not in keep:
            if old.is_dir():
                shutil.rmtree(old)
            else:
                old.unlink()
            print(f"removed {old}")


def render(grib: Path, data: Path, window: str) -> str:
    """Render the products of one window into data/; returns the output of the renderer."""
    command = [sys.executable, str(SCRIPTS / "render_charts.py"), str(grib), str(data), "--projection", window]
    if WINDOWS[window]:
        command += ["--products", WINDOWS[window]]
    result = subprocess.run(command, capture_output=True, text=True, encoding="utf-8")
    if result.returncode:
        sys.exit(f"rendering {window} failed:\n{result.stdout}{result.stderr}")
    return result.stdout


def encode_missing(data: Path, maps: Path, run: str) -> None:
    """Encode every tile layer that has no video in maps/ yet."""
    paths = [path for path in tile_chart_paths() if not (maps / video_file(path)).exists()]
    missing = [path for path in paths if not chart_frames(data, path, run)]
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
    parser.add_argument("data", type=Path, help="data directory (forecast, all charts, climatology)")
    parser.add_argument("maps", type=Path, help="video directory of the web app")
    parser.add_argument("--base", help="run YYYYMMDDHH instead of the newest one")
    parser.add_argument("--force", action="store_true", help="render and encode even if the manifest has this run")
    args = parser.parse_args()
    args.data.mkdir(parents=True, exist_ok=True)
    args.maps.mkdir(parents=True, exist_ok=True)

    check_climate(args.data)
    grib = download(args.data, args.base)
    run = grib.stem.removeprefix("ecmwf_")
    remove_old_runs(args.data, grib)
    if (args.data / CHARTS_DOC.name).resolve() != CHARTS_DOC.resolve():
        shutil.copyfile(CHARTS_DOC, args.data / CHARTS_DOC.name)
    same_run = read_run(args.maps) == run and not args.force
    rendered = all((args.data / window).is_dir() for window in WINDOWS)
    # The manifest goes first, so an interrupted call is never taken for a finished one.
    (args.maps / MANIFEST).unlink(missing_ok=True)
    if not same_run:
        for window in WINDOWS:
            shutil.rmtree(args.maps / window, ignore_errors=True)
    if same_run and rendered:
        print(f"charts of run {run} are already rendered")
    else:
        for window in WINDOWS:
            shutil.rmtree(args.data / window, ignore_errors=True)
        # The renderer spreads over all CPUs; both windows in parallel still finish sooner than one after the other.
        with ThreadPoolExecutor(len(WINDOWS)) as pool:
            for output in pool.map(lambda window: render(grib, args.data, window), WINDOWS):
                print(output, end="")
    encode_missing(args.data, args.maps, run)
    print(write_manifest(args.data, args.maps, run))


if __name__ == "__main__":
    main()
