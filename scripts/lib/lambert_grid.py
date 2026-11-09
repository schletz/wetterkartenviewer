"""Resampling of fields on a Lambert model grid onto the pixels of the chart image."""

import numpy as np
from scipy.ndimage import gaussian_filter, map_coordinates

from .lambert_plane import LambertPlane
from .projection import Projection


class LambertGrid:
    """Maps a LambertPlane onto the pixels of a chart window; the same interface as PixelGrid and TriangleGrid.

    Fields are flat arrays in the order of the file, as ForecastGrib returns
    them for a grid that is not regular in latitude and longitude.

    Attributes:
        covered: (height, width) bool, pixels inside the model grid.
    """

    def __init__(self, plane: LambertPlane, projection: Projection):
        self._shape = (plane.ny, plane.nx)
        self._km_per_cell = plane.dx_m / 1000.0
        px, py = np.meshgrid(np.arange(projection.width) + 0.5, np.arange(projection.height) + 0.5)
        rows, cols = plane.indices(*projection.pixel_to_latlon(px, py))
        self._coords = np.array([rows, cols])
        self.covered = (rows >= 0) & (rows <= plane.ny - 1) & (cols >= 0) & (cols <= plane.nx - 1)
        self._north, self._east = projection.north_east()

    def resample(self, values: np.ndarray, smooth_km: float = 0.0) -> np.ndarray:
        """Bilinearly interpolate a field to (height, width) pixels, optionally smoothed first."""
        field = values.reshape(self._shape)
        if smooth_km > 0:
            field = gaussian_filter(field, smooth_km / self._km_per_cell, mode="nearest")
        return map_coordinates(field, self._coords, order=1, mode="nearest").astype(np.float32)

    def nearest(self, values: np.ndarray) -> np.ndarray:
        """Value of the nearest grid point per pixel, for codes that must not be blended (e.g. the precipitation type)."""
        return map_coordinates(values.reshape(self._shape), self._coords, order=0, mode="nearest")

    def wind_vectors(self, u: np.ndarray, v: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        """Pixel components (dx right, dy down) of a wind given as resampled u (east) and v (north)."""
        return u * self._east[0] + v * self._north[0], u * self._east[1] + v * self._north[1]
