"""Values of fields on the Lambert grid of CHMI ALADIN at one location."""

import numpy as np

from .lambert_plane import LambertPlane
from .point_sampler import PointSampler


class LambertPointSampler(PointSampler):
    """Bilinear value at one location between the four grid points around it, in the plane of the projection."""

    def __init__(self, plane: LambertPlane, lat: float, lng: float):
        """Find the grid points around the location.

        Args:
            plane: the grid of the file; fields are flat, row by row from the south.
            lat, lng: the location in degrees.

        Raises:
            ValueError: if the location lies outside the grid of the file.
        """
        row, col = (float(index) for index in plane.indices(lat, lng))
        if not (0.0 <= row <= plane.ny - 1 and 0.0 <= col <= plane.nx - 1):
            raise ValueError(f"{lat} N {lng} E lies outside the CHMI ALADIN file")
        # The last row and column have no neighbour beyond them, so they take the cell before.
        low_row, low_col = min(int(row), plane.ny - 2), min(int(col), plane.nx - 2)
        north, east = row - low_row, col - low_col
        self._points = np.array([low_row * plane.nx + low_col, low_row * plane.nx + low_col + 1,
                                 (low_row + 1) * plane.nx + low_col, (low_row + 1) * plane.nx + low_col + 1])
        self._weights = np.array([(1 - north) * (1 - east), (1 - north) * east, north * (1 - east), north * east])
        self._nearest = round(row) * plane.nx + round(col)

    def __call__(self, values: np.ndarray) -> float:
        return float(np.asarray(values, dtype=float)[self._points] @ self._weights)

    def nearest(self, values: np.ndarray) -> float:
        """Value of the nearest grid point, for codes and fields that jump (precipitation type, visibility)."""
        return float(values[self._nearest])
