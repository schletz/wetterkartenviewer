"""Resampling of fields on an unstructured grid (ICON cell centres) onto the pixels of the chart image."""

import numpy as np
from scipy.ndimage import gaussian_filter
from scipy.spatial import Delaunay

from .projection import Projection

# Cells this far outside the image (px) still take part, so pixels at the border lie inside a triangle.
MARGIN_PX = 20


class TriangleGrid:
    """Maps the cells of an unstructured grid onto the pixels of a chart window; the same interface as PixelGrid.

    The cell centres are triangulated in pixel space (Delaunay); a pixel
    takes the values of the three corners of its triangle, weighted
    barycentrically. That interpolates the raw model cells once, straight
    onto the chart, without a regular grid in between. The weights are
    computed once per window.

    Attributes:
        covered: (height, width) bool, pixels with a value; outside the
            model domain and where a corner cell has no value it is False.
    """

    def __init__(self, lat: np.ndarray, lon: np.ndarray, projection: Projection, valid: np.ndarray):
        """Triangulate the cells of one window.

        Args:
            lat, lon: cell centres in degrees, one value per cell.
            projection: the chart window.
            valid: bool per cell, False where the model has no values (the boundary zone).
        """
        self.shape = (projection.height, projection.width)
        x, y = projection.latlon_to_pixel(lat, lon)
        cells = np.nonzero((x > -MARGIN_PX) & (x < projection.width + MARGIN_PX)
                           & (y > -MARGIN_PX) & (y < projection.height + MARGIN_PX))[0]
        triangulation = Delaunay(np.column_stack([x[cells], y[cells]]))
        px, py = np.meshgrid(np.arange(projection.width) + 0.5, np.arange(projection.height) + 0.5)
        points = np.column_stack([px.ravel(), py.ravel()])
        simplex = triangulation.find_simplex(points)
        affine = triangulation.transform[simplex]
        partial = np.einsum("nij,nj->ni", affine[:, :2], points - affine[:, 2])
        self._weights = np.column_stack([partial, 1.0 - partial.sum(axis=1)]).astype(np.float32)
        self._corners = cells[triangulation.simplices[simplex]]
        inside = simplex >= 0
        self.covered = (inside & valid[self._corners].all(axis=1)).reshape(self.shape)
        # Smoothing works on the pixels; their size varies by under 2 % across a window.
        centre_lat, _ = projection.pixel_to_latlon(projection.width / 2, projection.height / 2)
        self._km_per_px = projection.km_per_px(float(centre_lat))
        self._north, self._east = projection.north_east()

    def resample(self, values: np.ndarray, smooth_km: float = 0.0) -> np.ndarray:
        """Interpolate a field of one value per cell to (height, width) pixels, NaN where not covered.

        Smoothing is a Gaussian on the pixels that ignores uncovered ones, so
        the domain edge does not pull values towards zero.
        """
        result = (values[self._corners] * self._weights).sum(axis=1).reshape(self.shape)
        result[~self.covered] = np.nan
        if smooth_km > 0:
            sigma = smooth_km / self._km_per_px
            weight = gaussian_filter(self.covered.astype(np.float32), sigma, mode="nearest")
            result = gaussian_filter(np.where(self.covered, result, 0.0), sigma, mode="nearest") / np.maximum(weight, 1e-6)
            result[~self.covered] = np.nan
        return result.astype(np.float32)

    def nearest(self, values: np.ndarray) -> np.ndarray:
        """Value of the nearest corner cell per pixel, for codes that must not be blended (e.g. ww)."""
        nearest = self._corners[np.arange(len(self._weights)), self._weights.argmax(axis=1)]
        result = values[nearest].reshape(self.shape).astype(np.float32)
        result[~self.covered] = np.nan
        return result

    def wind_vectors(self, u: np.ndarray, v: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        """Pixel components (dx right, dy down) of a wind given as resampled u (east) and v (north)."""
        return u * self._east[0] + v * self._north[0], u * self._east[1] + v * self._north[1]
