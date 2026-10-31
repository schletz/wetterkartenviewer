"""Write a copy of an ICON-D2 file with a synthetic summer scene, to check the charts of rare weather.

Thunderstorms, hail, fog and storm gusts are rare, and DWD keeps only the
last day of runs, so the symbols of weather_summary cannot be checked on
real data at will. This script copies a file of download_icon_d2.py and,
from --step on, places into it:

    a squall line west of Munich      ww 95 (thunderstorm), 8-25 mm/h, overcast
    a hail core at its eastern end    ww 96 (thunderstorm with hail), 45 mm/h
    fog in the Danube basin           ww 45 around Linz and in the Vienna basin, overcast
    storm gusts                       90-125 km/h along the squall line

The precipitation is added to tot_prec at --step and every later step, so
the accumulation stays monotonic and only the hour ending at --step gets it.
The output is a normal input of render_charts.py; it has nothing to do with
the forecast and must never be published.

Example::

    python make_icon_test_grib.py data/icon-d2_2026103109.grb2 test/icon-d2_2026103109.grb2 --step 12
"""

import argparse
import sys
from pathlib import Path

import eccodes
import numpy as np

# Keep imports working under "python -I", which drops the script directory.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib.constants import ICON_NAMES  # noqa: E402
from lib.forecast_grib import ForecastGrib  # noqa: E402

KM_PER_DEG = 111.2
# (lat, lon, radius km, ww, mm in the hour, gust m/s)
CELLS = ((48.0, 10.6, 25, 95, 8.0, 25.0), (48.15, 11.0, 22, 95, 15.0, 30.0), (48.3, 11.4, 18, 95, 25.0, 32.0),
         (48.35, 11.7, 9, 96, 45.0, 35.0))
FOG = ((48.25, 14.3, 35), (48.0, 16.4, 30))


def disc(lat: np.ndarray, lon: np.ndarray, centre_lat: float, centre_lon: float, radius_km: float) -> np.ndarray:
    """Cells within a radius around a centre (equirectangular distance, fine at this size)."""
    dy = (lat - centre_lat) * KM_PER_DEG
    dx = (lon - centre_lon) * KM_PER_DEG * np.cos(np.radians(centre_lat))
    return np.hypot(dx, dy) <= radius_km


def scene_values(name: str, step: int, first: int, values: np.ndarray, lat: np.ndarray, lon: np.ndarray):
    """Values of one message with the scene placed in it; None if the message stays as it is."""
    if step < first or name not in ("tcc", "tp", "ww", "gust"):
        return None
    values = values.copy()
    if name == "tp":
        # Accumulated since T+0: the rain of the hour ending at ``first`` stays in every later step.
        for centre_lat, centre_lon, radius, _, mm, _ in CELLS:
            values[disc(lat, lon, centre_lat, centre_lon, radius)] += mm
        return values
    if step != first:
        return None
    for centre_lat, centre_lon, radius, ww, _, gust in CELLS:
        inside = disc(lat, lon, centre_lat, centre_lon, radius)
        if name == "tcc":
            values[inside] = 100.0
        elif name == "ww":
            values[inside] = ww
        else:
            values[disc(lat, lon, centre_lat, centre_lon, radius * 1.5)] = gust
    for centre_lat, centre_lon, radius in FOG:
        inside = disc(lat, lon, centre_lat, centre_lon, radius)
        if name == "tcc":
            values[inside] = 100.0
        elif name == "ww":
            values[inside] = 45
    return values


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n", maxsplit=1)[0])
    parser.add_argument("source", type=Path, help="ICON file of download_icon_d2.py")
    parser.add_argument("target", type=Path, help="file to write; its name should keep icon-d2_<run>.grb2")
    parser.add_argument("--step", type=int, default=12, help="valid step of the scene (default 12)")
    args = parser.parse_args(argv)
    grib = ForecastGrib(args.source, ICON_NAMES)
    lat, lon = grib.field("clat", 0), grib.field("clon", 0)
    args.target.parent.mkdir(parents=True, exist_ok=True)
    changed = 0
    with args.source.open("rb") as src, args.target.open("wb") as out:
        while (gid := eccodes.codes_grib_new_from_file(src)) is not None:
            try:
                eccodes.codes_set(gid, "stepUnits", 1)
                name = ICON_NAMES.get(eccodes.codes_get(gid, "shortName"), eccodes.codes_get(gid, "shortName"))
                values = eccodes.codes_get_values(gid)
                new = scene_values(name, eccodes.codes_get(gid, "endStep"), args.step, values, lat, lon)
                if new is not None:
                    # Cells of the boundary zone keep their missing value.
                    new[values == eccodes.codes_get(gid, "missingValue")] = eccodes.codes_get(gid, "missingValue")
                    eccodes.codes_set_values(gid, new)
                    changed += 1
                out.write(eccodes.codes_get_message(gid))
            finally:
                eccodes.codes_release(gid)
    print(f"{changed} messages changed, scene at T+{args.step}: {args.target}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
