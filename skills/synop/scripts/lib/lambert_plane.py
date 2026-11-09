"""The Lambert conformal grid of a limited area model: from positions to grid indices and back."""

from dataclasses import dataclass

import eccodes
import numpy as np

# Earth radius of GRIB edition 1, on which the coordinates of the file are defined (m).
EARTH_RADIUS_M = 6367470.0


@dataclass(frozen=True)
class LambertPlane:
    """A regular grid in the plane of a tangent Lambert projection, the grid of CHMI ALADIN.

    The grid points are ``dx_m`` apart in the plane and stored row by row from
    the southern edge, so the fields read as (ny, nx) have row 0 in the south.

    Attributes:
        lat_d, lon_v: tangent latitude and central meridian in degrees.
        dx_m: grid length in m.
        lat0, lon0: position of the first grid point (south-western corner) in degrees.
        nx, ny: columns and rows.
    """

    lat_d: float
    lon_v: float
    dx_m: float
    lat0: float
    lon0: float
    nx: int
    ny: int

    @classmethod
    def from_message(cls, gid: int) -> "LambertPlane":
        """The grid of an open GRIB message."""
        get = lambda key: eccodes.codes_get(gid, key)  # noqa: E731
        return cls(get("LaDInDegrees"), get("LoVInDegrees"), float(get("DxInMetres")),
                   get("latitudeOfFirstGridPointInDegrees"), get("longitudeOfFirstGridPointInDegrees"), get("Nx"), get("Ny"))

    @property
    def _cone(self) -> float:
        return float(np.sin(np.radians(self.lat_d)))

    @property
    def _scale(self) -> float:
        """R F of the projection: rho = R F / tan(45 deg + lat / 2) ** n."""
        lat = np.radians(self.lat_d)
        return float(EARTH_RADIUS_M * np.cos(lat) * np.tan(np.pi / 4 + lat / 2) ** self._cone / self._cone)

    def _rho(self, lat) -> np.ndarray:
        return self._scale / np.tan(np.pi / 4 + np.radians(np.asarray(lat, dtype=float)) / 2) ** self._cone

    def _plane(self, lat, lon) -> tuple[np.ndarray, np.ndarray]:
        """Position in the plane in m; y grows northwards and is 0 on the apex."""
        rho = self._rho(lat)
        theta = self._cone * np.radians((np.asarray(lon, dtype=float) - self.lon_v + 180.0) % 360.0 - 180.0)
        return rho * np.sin(theta), -rho * np.cos(theta)

    def indices(self, lat, lon) -> tuple[np.ndarray, np.ndarray]:
        """Fractional (row, column) of positions in degrees."""
        x, y = self._plane(lat, lon)
        x0, y0 = self._plane(self.lat0, self.lon0)
        return (y - y0) / self.dx_m, (x - x0) / self.dx_m

    def latlon(self) -> tuple[np.ndarray, np.ndarray]:
        """(lat, lon) of every grid point in degrees as flat arrays, in the order of a field's values."""
        x0, y0 = self._plane(self.lat0, self.lon0)
        rows, cols = np.mgrid[0:self.ny, 0:self.nx]
        x, y = x0 + cols.ravel() * self.dx_m, y0 + rows.ravel() * self.dx_m
        lat = 2.0 * np.arctan((self._scale / np.hypot(x, y)) ** (1.0 / self._cone)) - np.pi / 2
        lon = np.degrees(np.arctan2(x, -y)) / self._cone + self.lon_v
        return np.degrees(lat), (lon + 180.0) % 360.0 - 180.0
