"""Copy the charts of the data directory with the analysed location or region marked.

The charts carry no marker, so the same charts serve Vienna, Rome or the
whole of Austria; this script draws a point or a lat/lon box onto copies.
The charts carry borders but no place names, and without a marker it is
easy to misjudge whether a trough or a humidity band reaches the location.

Every WebP below <data>/<window> (every folder with a geometry.json, i.e.
opencharts_europe, opencharts_central_europe and icon-d2) is copied to the same
relative path below --out; geometry.json gives the projection and the
tiles of the contact sheets in sheets/, each of which gets the marker.
Charts on which the location does not lie are copied unmarked.

Example::

    python mark_location.py --data <data> --out work/marked_wien --lat 48.21 --lng 16.37 --label Wien
    python mark_location.py --data <data> --out work/marked_austria --bbox 46.4 49.0 9.5 17.2 --label Österreich
"""

import argparse
import os
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

from PIL import Image

# Keep imports working under "python -I", which drops the script directory.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib.chart_geometry import FILE_NAME, ChartGeometry  # noqa: E402
from lib.location_marker import LocationMarker  # noqa: E402

# Quality of the copies; the charts in the data directory are lossy WebP already.
WEBP_QUALITY = 90


def mark(task: tuple) -> bool:
    """Worker: copy one chart with the marker; returns whether a marker was drawn."""
    source, target, marker = task
    with Image.open(source) as chart:
        image = chart.convert("RGB")
    if marker.visible:
        if source.parent.name == "sheets":
            marker.mark_sheet(image, source.stem)
        else:
            marker.mark_chart(image)
    target.parent.mkdir(parents=True, exist_ok=True)
    image.save(target, quality=WEBP_QUALITY)
    return marker.visible


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n", maxsplit=1)[0])
    parser.add_argument("--data", type=Path, required=True, help="data directory with the chart window folders")
    parser.add_argument("--out", type=Path, required=True, help="target directory of the marked copies")
    parser.add_argument("--lat", type=float, help="latitude of the location (deg N)")
    parser.add_argument("--lng", type=float, help="longitude of the location (deg E)")
    parser.add_argument("--bbox", type=float, nargs=4, metavar=("SOUTH", "NORTH", "WEST", "EAST"),
                        help="region instead of a point: latitudes and longitudes in degrees")
    parser.add_argument("--label", default="", help="text next to the marker, e.g. the place name")
    parser.add_argument("--workers", type=int, default=os.cpu_count(), help="processes (default: CPUs)")
    args = parser.parse_args(argv)
    point = args.lat is not None and args.lng is not None
    if point == (args.bbox is not None) or (args.lat is None) != (args.lng is None):
        parser.error("give either --lat and --lng or --bbox")
    if args.bbox and not (args.bbox[0] < args.bbox[1] and args.bbox[2] < args.bbox[3]):
        parser.error("--bbox expects SOUTH < NORTH and WEST < EAST")
    return args


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    point = None if args.bbox else (args.lat, args.lng)
    windows = [path.parent for path in sorted(args.data.glob(f"*/{FILE_NAME}"))]
    markers = {window: LocationMarker(ChartGeometry(window), args.label, point=point, bbox=args.bbox)
               for window in windows}
    tasks = [(path, args.out / path.relative_to(args.data), marker)
             for window, marker in markers.items()
             for path in sorted(window.rglob("*.webp"))]
    if not tasks:
        print(f"no chart window with {FILE_NAME} below {args.data}", file=sys.stderr)
        return 1
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        drawn = sum(pool.map(mark, tasks, chunksize=8))
    print(f"{len(tasks)} charts copied to {args.out}, {drawn} with marker")
    if not drawn:
        print("The location lies on none of the charts.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
