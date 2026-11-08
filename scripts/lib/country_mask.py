"""Country outlines of the temperature series and the grid points of a regular grid that serve them.

Austria comes from the detailed border file, Hungary from the generalized world outlines.
"""

import json
from functools import cache

import numpy as np
from matplotlib.path import Path as Polygon
from scipy.spatial import cKDTree

from lib.projection import AUSTRIA_BORDERS, WORLD_COUNTRIES

# Spacing of the points along a border that stand in for it in the distance query, in degrees.
BORDER_POINT_SPACING = 0.01


def outer_rings(geometry: dict) -> list[np.ndarray]:
    """Outer rings of a GeoJSON Polygon or MultiPolygon as (lon, lat) arrays; no hole matters at grid resolution."""
    polygons = geometry["coordinates"] if geometry["type"] == "MultiPolygon" else [geometry["coordinates"]]
    return [np.array(polygon[0]) for polygon in polygons]


def austria_rings() -> list[np.ndarray]:
    """Outer rings of Austria from the detailed border file."""
    features = json.loads(AUSTRIA_BORDERS.read_text(encoding="utf-8"))["features"]
    country = next(f["geometry"] for f in features if f["properties"].get("ISO") == "AT"
                   and f["properties"].get("LEVEL") == "country")
    return outer_rings(country)


@cache
def region_rings() -> tuple[np.ndarray, ...]:
    """Outer rings of Austria and Hungary; cached, as the world outlines take a while to parse."""
    features = json.loads(WORLD_COUNTRIES.read_text(encoding="utf-8"))["features"]
    hungary = next(f["geometry"] for f in features if f["properties"].get("ISO") == "HU")
    return (*austria_rings(), *outer_rings(hungary))


def along_ring(ring: np.ndarray) -> np.ndarray:
    """Points along a closed ring at most ``BORDER_POINT_SPACING`` apart."""
    lengths = np.abs(np.diff(ring, axis=0)).max(axis=1)
    return np.concatenate([a + np.linspace(0, 1, max(1, int(np.ceil(length / BORDER_POINT_SPACING))),
                                           endpoint=False)[:, None] * (b - a)
                           for a, b, length in zip(ring[:-1], ring[1:], lengths)])


def nearest_point_mask(window: dict, margin: float = 0.0) -> np.ndarray:
    """Which points (nj x ni, rows north to south) of a regular grid are the nearest point of a place in the region.

    The app takes the nearest grid point and does not interpolate, so a point counts as soon as the rectangle of half
    a grid step around it touches the region, even with its centre beyond the border. ``margin`` (degrees) widens the
    rectangle on every side.
    """
    lats = window["lat0"] - window["dlat"] * np.arange(window["nj"])
    lons = window["lon0"] + window["dlon"] * np.arange(window["ni"])
    points = np.column_stack([a.ravel() for a in np.meshgrid(lons, lats)])
    rings = region_rings()
    inside = np.any([Polygon(ring).contains_points(points) for ring in rings], axis=0)
    # In units of the rectangle's half size the Chebyshev distance to the border decides: at most 1 means it touches.
    half = np.array([window["dlon"] / 2 + margin, window["dlat"] / 2 + margin])
    distance, _ = cKDTree(np.concatenate([along_ring(ring) for ring in rings]) / half).query(points / half, p=np.inf)
    return (inside | (distance <= 1.0)).reshape(window["nj"], window["ni"])


def mask_runs(mask: np.ndarray) -> list[list[int]]:
    """Kept columns of every row of a mask as [start, length, start, length, ...]; an empty list for an empty row."""
    runs = []
    for row in mask:
        # The difference of a row padded with zeros is non-zero exactly at the first and past the last column of a run.
        edges = np.flatnonzero(np.diff(row.astype(np.int8), prepend=0, append=0))
        runs.append(np.column_stack([edges[::2], edges[1::2] - edges[::2]]).ravel().tolist())
    return runs
