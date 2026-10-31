"""Values of grid fields at one location."""

import numpy as np
from scipy.ndimage import map_coordinates

from .point_sampler import PointSampler


class GridPointSampler(PointSampler):
    """Bilinear values at one location of fields on a regular lat/lon grid (as described by ForecastGrib.grid)."""

    def __init__(self, grid: dict, lat: float, lng: float):
        """Locate the point on the grid.

        Raises:
            ValueError: if the location lies outside the grid.
        """
        row = (grid["lat0"] - lat) / grid["dlat"]
        col = ((lng - grid["lon0"]) % 360.0) / grid["dlon"]
        if not (0 <= row <= grid["nj"] - 1 and 0 <= col <= grid["ni"] - 1):
            raise ValueError(f"{lat} N {lng} E lies outside the forecast box")
        self._coords = np.array([[row], [col]])

    def __call__(self, values: np.ndarray) -> float:
        return float(map_coordinates(np.asarray(values, dtype=np.float32), self._coords, order=1)[0])
