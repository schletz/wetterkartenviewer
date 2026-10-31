"""Pixel geometry of the charts of one window, read from the geometry.json the viewer writes next to them.

The charts are conformal conic (Lambert) with the north pole at the apex;
the file gives the parameters of

    rho = scale_k * tan(45 deg - lat / 2) ** cone
    x   = pole_x + rho * sin(cone * (lon - lon0))
    y   = pole_y + rho * cos(cone * (lon - lon0))

in image coordinates (origin top left, y down), and the tile origins and
scale of every contact sheet. cone = 1 and lon0 = 0 is the polar
stereographic projection of the ECMWF windows; an older geometry.json
without these keys means exactly that.
"""

import json
from pathlib import Path

import numpy as np

FILE_NAME = "geometry.json"


class ChartGeometry:
    """Projection and contact sheet layout of one chart window.

    Attributes:
        window: name of the window, e.g. "opencharts_central_europe" or "icon-d2".
        width, height: map area of a single chart in px (the legend strip lies below).
        sheet_scale: size of a sheet tile relative to a single chart.
        sheet_tiles: {product: [(x, y), ...]} top left corners of the tiles of each sheet.
    """

    def __init__(self, window_dir: Path):
        """Read geometry.json of a window folder.

        Raises:
            FileNotFoundError: if the folder has no geometry.json.
        """
        data = json.loads((Path(window_dir) / FILE_NAME).read_text(encoding="utf-8"))
        self.window = data["window"]
        self.width, self.height = data["image"]["width"], data["image"]["height"]
        projection = data["projection"]
        self._pole_x, self._pole_y, self._scale_k = projection["pole_x"], projection["pole_y"], projection["scale_k"]
        self._cone, self._lon0 = projection.get("cone", 1.0), projection.get("lon0", 0.0)
        self.sheet_scale = data["sheets"]["scale"]
        self.sheet_tiles = {name: [tuple(origin) for origin in origins]
                            for name, origins in data["sheets"]["tiles"].items()}

    def latlon_to_pixel(self, lat, lon):
        """Project a geographic position (deg N, deg E) onto the image; scalars or arrays, returns (x, y)."""
        rho = self._scale_k * np.tan(np.radians(45.0 - np.asarray(lat) / 2.0)) ** self._cone
        # Longitude relative to the central meridian in -180..180, so the cut lies opposite to it.
        theta = self._cone * np.radians((np.asarray(lon) - self._lon0 + 180.0) % 360.0 - 180.0)
        return self._pole_x + rho * np.sin(theta), self._pole_y + rho * np.cos(theta)
