"""Pixel geometry of the ECMWF open charts windows.

All open charts windows use the same polar stereographic projection with
a vertical zero meridian and a 1200x600 image; they differ only in scale
and offset. The forward model, in image coordinates with the origin at
the top left and the y axis pointing down, is

    rho = scale_k * tan(45 deg - lat / 2)
    x   = pole_x + rho * sin(lon)
    y   = pole_y + rho * cos(lon)

The parameters come from least squares fits to measured control points:
"opencharts_europe" RMS 0.45 px, "opencharts_central_europe" RMS 0.4 px
(three points; a free central meridian came out at 0.04 deg, i.e. none).
The central Europe window is the rectangle x 316-770, y 205-432 of the
Europe window enlarged 2.645 times. The north pole lies above both images.

Both directions accept scalars and numpy arrays, so whole pixel grids or
coastlines can be projected in one call.
"""

from dataclasses import dataclass

import numpy as np

IMAGE_WIDTH = 1200
IMAGE_HEIGHT = 600


@dataclass(frozen=True)
class Projection:
    """One open charts window.

    Attributes:
        name: open charts projection name.
        pole_x, pole_y: pixel position of the north pole.
        scale_k: projection scale in pixels.
        graticule_step: spacing of the drawn graticule in degrees.
    """

    name: str
    pole_x: float
    pole_y: float
    scale_k: float
    graticule_step: int
    width: int = IMAGE_WIDTH
    height: int = IMAGE_HEIGHT

    def latlon_to_pixel(self, lat, lon):
        """Project a geographic position (deg N, deg E) onto the image; returns (x, y)."""
        rho = self.scale_k * np.tan(np.radians(45.0 - np.asarray(lat) / 2.0))
        lon_rad = np.radians(lon)
        return self.pole_x + rho * np.sin(lon_rad), self.pole_y + rho * np.cos(lon_rad)

    def pixel_to_latlon(self, x, y):
        """Invert latlon_to_pixel; returns (lat, lon) in degrees, longitudes in -180..180."""
        dx = np.asarray(x, dtype=float) - self.pole_x
        dy = np.asarray(y, dtype=float) - self.pole_y
        lat = 90.0 - 2.0 * np.degrees(np.arctan(np.hypot(dx, dy) / self.scale_k))
        return lat, np.degrees(np.arctan2(dx, dy))

    def border_latlon(self):
        """(lat, lon) arrays of every pixel on the image border."""
        xs = np.r_[np.arange(self.width + 1), np.full(self.height + 1, self.width),
                   np.arange(self.width + 1), np.zeros(self.height + 1)]
        ys = np.r_[np.zeros(self.width + 1), np.arange(self.height + 1),
                   np.full(self.width + 1, self.height), np.arange(self.height + 1)]
        return self.pixel_to_latlon(xs, ys)


EUROPE = Projection("opencharts_europe", pole_x=481.0, pole_y=-180.8, scale_k=1320.8, graticule_step=10)
CENTRAL_EUROPE = Projection("opencharts_central_europe", pole_x=435.35, pole_y=-1021.0, scale_k=3493.4,
                            graticule_step=5)
PROJECTIONS = {p.name: p for p in (EUROPE, CENTRAL_EUROPE)}
