"""Join the variable files of a CHMI ALADIN run into one forecast file, cut to the chart window."""

from collections.abc import Iterator
from functools import lru_cache
from pathlib import Path

import eccodes
import numpy as np

from .constants import ALADIN_GUST_PARAMETER, ALADIN_WIND_PARAMETERS
from .lambert_plane import LambertPlane
from .projection import Projection

# Grid lengths kept around the window, so that interpolation at its edge has neighbours on every side.
CROP_MARGIN = 4
# P1 and P2 of a GRIB 1 time range are one byte each.
LAST_STEP_IN_TIME_RANGE = 255


class AladinWriter:
    """Writes the messages of one run: copied and cut to the window, the wind and gust as the charts need them.

    The messages stay GRIB edition 1, as CHMI publishes them, on the original
    grid points. Instead of the four files of the wind the result holds:

    * 10u, 10v: components east and north, from speed and direction. The
      direction of the file refers to true north, unlike the components of
      the gust, which refer to the grid.
    * the gust: the speed of the components of the maximum gust of the last
      hour, with that hour as its time range; none at T+0.
    """

    # Files copied as they are; those accumulated from T+0 or valid for the last hour have no T+0.
    STATIC = ("SURFGEOPOTENTIEL", "SURFIND_TERREMER")
    FROM_ZERO = ("CLSTEMPERATURE", "MSLPRESSURE", "SURFNEBUL_TOTALE", "CLS_VISICLD")
    FROM_ONE = ("SURFPREC_TOTAL", "PRECIP_TYPE", "PRECIP_TYPESEV", "SURFDIAG_FLASH")
    WIND = ("CLSWIND_SPEED", "CLSWIND_DIREC")
    GUST = ("CLSU_RAF_MOD_XFU", "CLSV_RAF_MOD_XFU")
    VARIABLES = (*STATIC, *FROM_ZERO, *FROM_ONE, *WIND, *GUST)
    STEPS = 73

    def __init__(self, projection: Projection):
        self.projection = projection
        # Every message of a run has the same grid, and the coordinates of the whole grid are costly.
        self._window = lru_cache(maxsize=1)(self._find_window)

    @classmethod
    def expected_messages(cls, variable: str) -> int:
        """Messages a complete file of a variable holds."""
        return 1 if variable in cls.STATIC else cls.STEPS - 1 if variable in cls.FROM_ONE else cls.STEPS

    @classmethod
    def expected_total(cls) -> int:
        """Messages of the finished forecast file: every variable, the wind pair as two, the gust pair as one from T+1."""
        return sum(cls.expected_messages(v) for v in (*cls.STATIC, *cls.FROM_ZERO, *cls.FROM_ONE, *cls.WIND)) + cls.STEPS - 1

    def write(self, raw: dict[str, Path], target: Path) -> int:
        """Write the forecast file from the raw file of every variable; returns the number of messages."""
        with target.open("wb") as out:
            count = 0
            for variable in (*self.STATIC, *self.FROM_ZERO, *self.FROM_ONE):
                for gid in self._messages(raw[variable]):
                    count += self._write(out, gid, self._field(gid))
                    eccodes.codes_release(gid)
            for speed, direction in zip(self._messages(raw["CLSWIND_SPEED"]), self._messages(raw["CLSWIND_DIREC"])):
                count += self._write_wind(out, speed, direction)
                eccodes.codes_release(speed)
                eccodes.codes_release(direction)
            for u, v in zip(self._messages(raw["CLSU_RAF_MOD_XFU"]), self._messages(raw["CLSV_RAF_MOD_XFU"])):
                count += self._write_gust(out, u, v)
                eccodes.codes_release(u)
                eccodes.codes_release(v)
        return count

    @staticmethod
    def _messages(path: Path) -> Iterator[int]:
        """Open GRIB handles of a file in order; the caller releases each."""
        with path.open("rb") as fh:
            while (gid := eccodes.codes_grib_new_from_file(fh)) is not None:
                yield gid

    def _find_window(self, plane: LambertPlane) -> tuple[int, int, int, int, float, float]:
        """(first row, end row, first column, end column, latitude, longitude of the first kept point) of the model grid."""
        rows, cols = plane.indices(*self.projection.border_latlon())
        first_row, end_row = max(int(np.floor(rows.min())) - CROP_MARGIN, 0), min(int(np.ceil(rows.max())) + CROP_MARGIN + 1, plane.ny)
        first_col, end_col = max(int(np.floor(cols.min())) - CROP_MARGIN, 0), min(int(np.ceil(cols.max())) + CROP_MARGIN + 1, plane.nx)
        lat, lon = plane.latlon()
        corner = first_row * plane.nx + first_col
        return first_row, end_row, first_col, end_col, float(lat[corner]), float(lon[corner])

    def _field(self, gid: int) -> np.ndarray:
        """Values of a message cut to the window, (rows, columns)."""
        plane = LambertPlane.from_message(gid)
        first_row, end_row, first_col, end_col, _, _ = self._window(plane)
        return eccodes.codes_get_values(gid).reshape(plane.ny, plane.nx)[first_row:end_row, first_col:end_col]

    def _cropped(self, gid: int, values: np.ndarray) -> int:
        """A copy of a message with the grid and values of the cut window; the caller releases it."""
        *_, lat, lon = self._window(LambertPlane.from_message(gid))
        clone = eccodes.codes_clone(gid)
        eccodes.codes_set(clone, "Nx", values.shape[1])
        eccodes.codes_set(clone, "Ny", values.shape[0])
        eccodes.codes_set(clone, "latitudeOfFirstGridPointInDegrees", lat)
        eccodes.codes_set(clone, "longitudeOfFirstGridPointInDegrees", lon)
        eccodes.codes_set_values(clone, values.ravel())
        return clone

    def _write(self, out, gid: int, values: np.ndarray) -> int:
        """Write a message with the values of the window; returns 1 for the message count."""
        clone = self._cropped(gid, values)
        out.write(eccodes.codes_get_message(clone))
        eccodes.codes_release(clone)
        return 1

    def _write_wind(self, out, speed: int, direction: int) -> int:
        """Write 10u and 10v of one step, from wind speed and the direction the wind comes from."""
        strength = self._field(speed)
        angle = np.radians(self._field(direction))
        for parameter, values in zip(ALADIN_WIND_PARAMETERS, (-strength * np.sin(angle), -strength * np.cos(angle))):
            clone = self._cropped(speed, values)
            eccodes.codes_set(clone, "indicatorOfParameter", parameter)
            # Components east and north, no longer along the grid.
            eccodes.codes_set(clone, "uvRelativeToGrid", 0)
            out.write(eccodes.codes_get_message(clone))
            eccodes.codes_release(clone)
        return 2

    def _write_gust(self, out, u: int, v: int) -> int:
        """Write the gust of one step as a maximum over the last hour; nothing at T+0, which has no last hour."""
        step = eccodes.codes_get(u, "endStep")
        if step == 0:
            return 0
        if step > LAST_STEP_IN_TIME_RANGE:
            raise ValueError(f"step {step} does not fit the time range of GRIB 1")
        clone = self._cropped(u, np.hypot(self._field(u), self._field(v)))
        eccodes.codes_set(clone, "indicatorOfParameter", ALADIN_GUST_PARAMETER)
        eccodes.codes_set(clone, "timeRangeIndicator", 2)
        eccodes.codes_set(clone, "P1", step - 1)
        eccodes.codes_set(clone, "P2", step)
        out.write(eccodes.codes_get_message(clone))
        eccodes.codes_release(clone)
        return 1
