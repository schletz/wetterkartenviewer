"""Values of fields on an unstructured grid (ICON-D2: one value per cell) at one location."""

import math

import numpy as np
from scipy.spatial import Delaunay

from .point_sampler import PointSampler

KM_PER_DEGREE = 111.2
# Nearest cell centres among which the triangle around the location is sought.
NEIGHBOURS = 12
# Farther from the nearest cell centre (km), a location lies off the grid; ICON-D2 cells are about 2.2 km apart.
MAX_DISTANCE_KM = 5.0


class CellPointSampler(PointSampler):
    """Linear values at one location inside the triangle of the three cell centres around it.

    This is the counterpart of bilinear interpolation on a regular grid and
    the interpolation the viewer draws the ICON-D2 charts with.
    """

    def __init__(self, lat: np.ndarray, lon: np.ndarray, valid: np.ndarray, point_lat: float, point_lng: float):
        """Find the triangle of cell centres around the location.

        Args:
            lat, lon: centre of every cell in degrees.
            valid: True for cells with forecast values (ICON leaves its boundary zone empty).
            point_lat, point_lng: the location in degrees.

        Raises:
            ValueError: if the location lies outside the cells with values.
        """
        # Distances in a local plane in km are exact enough over a few cells.
        x = (np.asarray(lon, dtype=float) - point_lng) * KM_PER_DEGREE * math.cos(math.radians(point_lat))
        y = (np.asarray(lat, dtype=float) - point_lat) * KM_PER_DEGREE
        distance = np.hypot(x, y)
        near = np.argpartition(distance, NEIGHBOURS)[:NEIGHBOURS]
        triangles = Delaunay(np.column_stack([x[near], y[near]]))
        simplex = int(triangles.find_simplex(np.zeros((1, 2)))[0])
        self._nearest = int(near[np.argmin(distance[near])])
        if simplex < 0 or distance[self._nearest] > MAX_DISTANCE_KM:
            raise ValueError(f"{point_lat} N {point_lng} E lies outside the ICON-D2 domain")
        self._cells = near[triangles.simplices[simplex]]
        if not np.all(np.asarray(valid)[self._cells]):
            raise ValueError(f"{point_lat} N {point_lng} E lies in the boundary zone of the ICON-D2 domain")
        # Barycentric coordinates of the location (the origin of the local plane).
        transform = triangles.transform[simplex]
        weights = transform[:2] @ (np.zeros(2) - transform[2])
        self._weights = np.r_[weights, 1.0 - weights.sum()]

    def __call__(self, values: np.ndarray) -> float:
        return float(np.asarray(values, dtype=float)[self._cells] @ self._weights)

    def nearest(self, values: np.ndarray) -> float:
        """Value of the nearest cell, for codes and fields that jump (weather code, cloud base)."""
        return float(values[self._nearest])
