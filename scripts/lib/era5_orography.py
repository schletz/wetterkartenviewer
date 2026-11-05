"""Model orography of ERA5 on the 0.25 deg grid of the climatology (data/era5_means/).

era5_orography.grib next to this module is the invariant ERA5 surface
geopotential (``reanalysis-era5-single-levels``, variable ``geopotential``,
any date, the area of era5_means.grb2: 75.25 N, -70.25 E to 11.75 N,
76.75 E). It is the ground height the T2m climatology refers to; ERA5 smooths
the Alps, so it differs from the ECMWF 0.1 deg orography by hundreds of
metres in many valleys.

Requires the packages eccodes and numpy.
"""

from pathlib import Path

import eccodes
import numpy as np

from .constants import GRAVITY

FILE = Path(__file__).with_name("era5_orography.grib")
# Keys a grid must agree in; coordinates are compared with a tolerance, sizes exactly.
GRID_KEYS = ("lat0", "lon0", "dlat", "dlon")
TOLERANCE = 1e-6


def era5_orography(grid: dict, path: Path = FILE) -> np.ndarray:
    """Orography in m, shape (nj, ni), rows north to south, for the climatology grid ``grid`` (ClimateArchive.grid).

    Raises:
        ValueError: if the file has another grid than ``grid``.
    """
    with path.open("rb") as fh:
        gid = eccodes.codes_grib_new_from_file(fh)
    try:
        get = lambda key: eccodes.codes_get(gid, key)  # noqa: E731
        own = {"lat0": get("latitudeOfFirstGridPointInDegrees"),
               "lon0": (get("longitudeOfFirstGridPointInDegrees") + 180.0) % 360.0 - 180.0,
               "dlat": get("jDirectionIncrementInDegrees"), "dlon": get("iDirectionIncrementInDegrees"),
               "ni": get("Ni"), "nj": get("Nj")}
        if (own["ni"], own["nj"]) != (grid["ni"], grid["nj"]) or get("jScansPositively") != 0 \
                or any(abs(own[key] - grid[key]) > TOLERANCE for key in GRID_KEYS):
            raise ValueError(f"{path}: grid {own} differs from the climatology grid")
        return eccodes.codes_get_values(gid).reshape(own["nj"], own["ni"]) / GRAVITY
    finally:
        eccodes.codes_release(gid)
