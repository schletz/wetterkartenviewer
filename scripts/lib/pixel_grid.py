"""Resampling of regular lat/lon fields onto the pixels of the chart image."""

import numpy as np
from scipy.ndimage import gaussian_filter, map_coordinates

from .projection import Projection

KM_PER_DEG = 111.2
# Latitude at which the zonal smoothing width is exact; elsewhere it is off by cos(lat) / cos(50).
SMOOTH_REF_LAT = 50.0


class PixelGrid:
    """Maps a lat/lon grid (ForecastGrib.grid, ClimateArchive.grid) onto the pixels of a chart window."""

    def __init__(self, grid: dict, projection: Projection):
        self.grid = grid
        px, py = np.meshgrid(np.arange(projection.width) + 0.5, np.arange(projection.height) + 0.5)
        lat, lon = projection.pixel_to_latlon(px, py)
        rows = (grid["lat0"] - lat) / grid["dlat"]
        cols = ((lon - grid["lon0"]) % 360.0) / grid["dlon"]
        self._coords = np.array([rows, cols])
        # Unit vectors of north and east in image coordinates (y down): north points to the pole.
        north = np.array([projection.pole_x - px, projection.pole_y - py])
        north /= np.hypot(*north)
        self._north = north
        self._east = np.array([-north[1], north[0]])

    def resample(self, values: np.ndarray, smooth_km: float = 0.0) -> np.ndarray:
        """Bilinearly interpolate a (nj, ni) field to (height, width) pixels, optionally smoothed first."""
        if smooth_km > 0:
            sigma_y = smooth_km / (KM_PER_DEG * self.grid["dlat"])
            sigma_x = smooth_km / (KM_PER_DEG * self.grid["dlon"] * np.cos(np.radians(SMOOTH_REF_LAT)))
            values = gaussian_filter(values, (sigma_y, sigma_x), mode="nearest")
        return map_coordinates(values, self._coords, order=1, mode="nearest").astype(np.float32)

    def nearest(self, values: np.ndarray) -> np.ndarray:
        """Value of the nearest grid point per pixel, for codes that must not be blended (e.g. ptype)."""
        return map_coordinates(values, self._coords, order=0, mode="nearest")

    def wind_vectors(self, u: np.ndarray, v: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        """Pixel components (dx right, dy down) of a wind given as resampled u (east) and v (north)."""
        return u * self._east[0] + v * self._north[0], u * self._east[1] + v * self._north[1]
