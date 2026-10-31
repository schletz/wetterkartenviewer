"""Country (and state) outlines and graticule projected onto the chart image."""

import json
from pathlib import Path

import numpy as np

from .projection import Projection

# Rings are kept if any point lies within this many px of the image.
MARGIN_PX = 50


class BaseMap:
    """Projected geometry shared by every chart, loaded once per process.

    The outlines come from ``projection.borders``, a GeoJSON whose features
    are countries unless their property LEVEL is "state" (build_borders.py).

    Attributes:
        rings: country polygon rings as (n, 2) pixel arrays; their outlines
            are the coastlines and borders, their areas the land.
        state_rings: rings of states inside a country, drawn as thinner lines only.
        parallels: {lat: (n, 2) array} of the graticule.
        meridians: {lon: (n, 2) array} of the graticule.
    """

    def __init__(self, projection: Projection, borders: Path | None = None):
        self.projection = projection
        features = json.loads(Path(borders or projection.borders).read_text(encoding="utf-8"))["features"]
        self.rings = self._visible_rings(f for f in features if f["properties"].get("LEVEL") != "state")
        self.state_rings = self._visible_rings(f for f in features if f["properties"].get("LEVEL") == "state")
        step = projection.graticule_step
        # Parallels are sampled every 0.5 deg from -180, meridians every 0.5 deg from 0 deg N.
        self.parallels = {lat: self._line(np.full(721, lat), np.linspace(-180, 180, 721))
                          for lat in range(10, 90, step)}
        self.meridians = {lon: self._line(np.linspace(0, 80, 161), np.full(161, lon))
                          for lon in range(-180, 180, step)}

    def _visible_rings(self, features) -> list[np.ndarray]:
        return [ring for ring in self._rings(features) if self._visible(ring)]

    def _rings(self, features):
        """Every polygon ring of GeoJSON features in pixel coordinates (lon/lat order, EPSG:4326)."""
        for feature in features:
            geometry = feature["geometry"]
            polygons = geometry["coordinates"] if geometry["type"] == "MultiPolygon" else [geometry["coordinates"]]
            for polygon in polygons:
                for ring in polygon:
                    coords = np.asarray(ring, dtype=float)
                    # The southern hemisphere lies far outside the window and
                    # the projection diverges towards the south pole.
                    if coords[:, 1].max() < 0:
                        continue
                    yield self._line(coords[:, 1], coords[:, 0])

    def _line(self, lat: np.ndarray, lon: np.ndarray) -> np.ndarray:
        x, y = self.projection.latlon_to_pixel(lat, lon)
        return np.column_stack([x, y])

    def _visible(self, ring: np.ndarray) -> bool:
        x, y = ring[:, 0], ring[:, 1]
        return bool(np.any((x > -MARGIN_PX) & (x < self.projection.width + MARGIN_PX)
                           & (y > -MARGIN_PX) & (y < self.projection.height + MARGIN_PX)))
