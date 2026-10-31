"""Bring the data cache of the skill up to date with the blob container the viewer pipeline fills.

The container holds one data directory (ECMWF and ICON-D2 GRIB, charts, climatology,
charts.md) and is readable without credentials. The cache <skill-dir>/.cache mirrors it:
only blobs that are new or changed are downloaded (size and Last-Modified, kept as the
modification time of the local file), files the container no longer holds are deleted, so
the cache keeps exactly one run of each model and the climatology is fetched only once.

The pipeline replaces the container while it uploads a new run. It deletes current_run.json
({"ecmwf": "<run>", "icon-d2": "<run>", "updated": ...}) before and writes it after an
upload, so the container is consistent only while the file exists. Without it the script
stops before downloading. It reads the file again afterwards: if it is gone or changed, an
upload began meanwhile and the cache may mix two runs; the script says so and exits 1, and
a call a few minutes later fetches only what changed.

The last line of the output is the cache path, the <data> of the other scripts.

Example::

    python fetch_data.py https://<account>.blob.core.windows.net/<container>
"""

import argparse
import json
import os
import shutil
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ElementTree
from concurrent.futures import ThreadPoolExecutor
from email.utils import parsedate_to_datetime
from pathlib import Path

CACHE = Path(__file__).resolve().parent.parent / ".cache"
RUN_FILE = "current_run.json"
PARALLEL_DOWNLOADS = 8
TIMEOUT_S = 60
CHUNK = 1024 * 1024
MB = 1024 * 1024


def list_blobs(url: str) -> dict[str, tuple[int, int]]:
    """Blob name → (size in bytes, Last-Modified as Unix seconds), all pages of the listing."""
    blobs, marker = {}, ""
    while True:
        query = urllib.parse.urlencode({"restype": "container", "comp": "list", "marker": marker})
        with urllib.request.urlopen(f"{url}?{query}", timeout=TIMEOUT_S) as response:
            root = ElementTree.fromstring(response.read())
        for blob in root.iter("Blob"):
            properties = blob.find("Properties")
            modified = parsedate_to_datetime(properties.findtext("Last-Modified"))
            blobs[blob.findtext("Name")] = (int(properties.findtext("Content-Length")), int(modified.timestamp()))
        marker = root.findtext("NextMarker") or ""
        if not marker:
            return blobs


def read_runs(url: str) -> dict | None:
    """Content of RUN_FILE in the container; None while it is missing (upload running or failed)."""
    request = urllib.request.Request(f"{url}/{RUN_FILE}", headers={"Cache-Control": "no-cache"})
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT_S) as response:
            return json.load(response)
    except urllib.error.HTTPError as error:
        if error.code == 404:
            return None
        raise


def grib_files(runs: dict) -> list[str]:
    """GRIB file names of the runs in RUN_FILE (model key = file prefix)."""
    return [f"{model}_{run}.grb2" for model, run in runs.items() if model != "updated"]


def up_to_date(path: Path, size: int, modified: int) -> bool:
    """The cached file has the size and Last-Modified time of its blob."""
    if not path.is_file():
        return False
    stat = path.stat()
    return stat.st_size == size and int(stat.st_mtime) == modified


def download(url: str, name: str, target: Path, modified: int) -> None:
    """Download one blob via a .part file and give it the Last-Modified time of the blob."""
    target.parent.mkdir(parents=True, exist_ok=True)
    part = target.with_name(target.name + ".part")
    with urllib.request.urlopen(f"{url}/{urllib.parse.quote(name)}", timeout=TIMEOUT_S) as response, \
            part.open("wb") as file:
        shutil.copyfileobj(response, file, CHUNK)
    part.replace(target)
    # The modification time marks the cached version; the next call compares it with Last-Modified.
    os.utime(target, (modified, modified))


def remove_obsolete(cache: Path, blobs: dict) -> int:
    """Delete files the container no longer holds (older runs, unfinished .part files) and empty folders."""
    removed = 0
    for path in sorted(cache.rglob("*"), reverse=True):
        if path.is_file() and path.relative_to(cache).as_posix() not in blobs:
            path.unlink()
            removed += 1
        elif path.is_dir() and not any(path.iterdir()):
            path.rmdir()
    return removed


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("url", help="URL of the blob container (download_url.txt in the skill directory)")
    parser.add_argument("--cache", type=Path, default=CACHE, help=f"cache directory (default {CACHE})")
    args = parser.parse_args()
    url = args.url.strip().rstrip("/")

    runs = read_runs(url)
    if runs is None:
        sys.exit(f"{url} has no {RUN_FILE}: the pipeline is uploading a new run or its last upload "
                 "failed; run this script again in a few minutes")
    blobs = list_blobs(url)
    missing = [name for name in grib_files(runs) if name not in blobs]
    if "ecmwf" not in runs or missing:
        sys.exit(f"{RUN_FILE} {runs} does not match the container (missing {missing}); run again in a few minutes")

    started = time.monotonic()
    stale = [name for name, (size, modified) in blobs.items()
             if not up_to_date(args.cache / name, size, modified)]
    failed = []

    def fetch(name: str) -> None:
        try:
            download(url, name, args.cache / name, blobs[name][1])
        except OSError as error:
            failed.append(f"{name}: {error}")

    with ThreadPoolExecutor(PARALLEL_DOWNLOADS) as pool:
        list(pool.map(fetch, stale))
    if read_runs(url) != runs:
        sys.exit("the pipeline began uploading a new run during the download, so the cache may mix two "
                 "runs; run this script again in a few minutes, it fetches only what changed")
    removed = remove_obsolete(args.cache, blobs)
    size = sum(blobs[name][0] for name in stale) / MB
    print(f"runs {', '.join(grib_files(runs))} (uploaded {runs.get('updated')})")
    print(f"downloaded {len(stale) - len(failed)} of {len(blobs)} files ({size:.0f} MB), "
          f"removed {removed} in {time.monotonic() - started:.0f} s")
    if failed:
        sys.exit("download failed, run again to fetch the rest:\n" + "\n".join(failed))
    print(args.cache)


if __name__ == "__main__":
    main()
