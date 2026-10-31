"""Write maps/manifest.json, the index of the tile videos the viewer shows.

Every tile layer ("window/product" in src/config/viewer.config.json) is one
AV1 video maps/<window>/<product>.mp4 (tile_videos.py) whose frames are the
charts of data/<window>/<product>/ in the order of their forecast step. The
viewer needs the step of every frame, because products start at different
steps (weather_summary at T+3, dt850_24h at T+24) and the steps thin out
from 3 h to 6 h after T+144. Only layers of the current config with a video
are listed.

Usage: python scripts/maps_manifest.py data maps --run 2026103000
"""

import argparse
import json
from datetime import datetime, timedelta
from pathlib import Path

CONFIG = Path(__file__).resolve().parent.parent / "src" / "config" / "viewer.config.json"
MANIFEST = "manifest.json"
# Frame rate of the tile videos (tile_videos.py); the viewer seeks by it.
FPS = 10


def tile_chart_paths(config: Path = CONFIG) -> list[str]:
    """Chart paths ("window/product") of all tile layers, without duplicates, in config order."""
    tiles = json.loads(config.read_text(encoding="utf-8"))["tiles"]
    return list(dict.fromkeys(path for tile in tiles for path in tile["layers"]))


def file_step(stem: str, base: datetime) -> int | None:
    """Forecast step of a chart file named by valid time.

    YYYYMMDDHH is the valid time; daily charts (tmax/tmin) are named YYYYMMDD
    and count from 00 UTC of that day. Other names are no charts.
    """
    for pattern in ("%Y%m%d%H", "%Y%m%d"):
        if len(stem) == len(datetime(2000, 1, 1).strftime(pattern)) and stem.isdigit():
            hours = (datetime.strptime(stem, pattern) - base) / timedelta(hours=1)
            return max(int(hours), 0)
    return None


def chart_frames(data: Path, path: str, run: str) -> list[tuple[int, Path]]:
    """(step, chart file) of a layer in data/, sorted by step: the frames of its video."""
    base = datetime.strptime(run, "%Y%m%d%H")
    frames = [(file_step(f.stem, base), f) for f in (data / path).glob("*.webp")]
    return sorted(frame for frame in frames if frame[0] is not None)


def video_file(path: str) -> str:
    """Video of a layer relative to maps/."""
    return f"{path}.mp4"


def build_manifest(data: Path, maps: Path, run: str, paths: list[str]) -> dict:
    """Manifest of one run: per layer its video and the step of every frame."""
    charts = {}
    for path in paths:
        if (maps / video_file(path)).exists():
            charts[path] = {"file": video_file(path), "steps": [step for step, _ in chart_frames(data, path, run)]}
        else:
            print(f"warning: no video for {path}")
    return {"run": run, "fps": FPS, "charts": charts}


def read_run(maps: Path) -> str | None:
    """Run of the manifest in ``maps``, or None if there is no readable manifest."""
    try:
        return json.loads((maps / MANIFEST).read_text(encoding="utf-8"))["run"]
    except (OSError, ValueError, KeyError):
        return None


def video_files(maps: Path) -> list[str]:
    """Videos the manifest in ``maps`` lists, relative to ``maps``; empty if there is no readable manifest."""
    try:
        charts = json.loads((maps / MANIFEST).read_text(encoding="utf-8"))["charts"]
    except (OSError, ValueError, KeyError):
        return []
    return [chart["file"] for chart in charts.values()]


def write_manifest(data: Path, maps: Path, run: str) -> Path:
    """Write the manifest of the tile videos into ``maps``; returns its path."""
    target = maps / MANIFEST
    manifest = build_manifest(data, maps, run, tile_chart_paths())
    target.write_text(json.dumps(manifest, indent=1), encoding="utf-8")
    return target


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("data", type=Path, help="data directory with the rendered charts")
    parser.add_argument("maps", type=Path, help="video directory of the viewer")
    parser.add_argument("--run", required=True, help="base time of the run, YYYYMMDDHH")
    args = parser.parse_args()
    print(write_manifest(args.data, args.maps, args.run))


if __name__ == "__main__":
    main()
