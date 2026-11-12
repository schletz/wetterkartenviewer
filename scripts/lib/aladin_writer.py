"""Join the variable files of a CHMI ALADIN run into one forecast file on the whole model grid."""

from collections.abc import Iterator
from functools import lru_cache
from pathlib import Path

import eccodes
import numpy as np

from .constants import ALADIN_GUST_PARAMETER, ALADIN_WIND_PARAMETERS
from .lambert_plane import LambertPlane

# P1 and P2 of a GRIB 1 time range are one byte each.
LAST_STEP_IN_TIME_RANGE = 255
# Pressure levels in the file names of CHMI: 85000 Pa is 850 hPa, and 1000 hPa is written P00000.
LEVEL_850, LEVEL_700, LEVEL_1000 = "P85000", "P70000", "P00000"
# Levels of the wet-bulb profile of the snow line, bottom to top (aladin_products.WET_BULB_LEVELS in hPa): every
# level CHMI publishes from 1000 hPa up to 600 hPa (about 4200 m), so the snow line is found up to there.
WET_BULB_LEVELS = (LEVEL_1000, "P95000", "P92500", LEVEL_850, "P80000", LEVEL_700, "P60000")


class AladinWriter:
    """Writes the messages of one run: copied as published, what the charts need in another form converted.

    The messages stay GRIB edition 1, as CHMI publishes them, on the whole
    model grid: the server only offers whole files, so a smaller area would
    save no download. Converted are:

    * 10u, 10v: components east and north, from speed and direction. The
      direction of the file refers to true north, unlike the components of
      the gust and of the pressure levels, which refer to the grid.
    * the gust: the speed of the components of the maximum gust of the last
      hour, with that hour as its time range; none at T+0.
    * u, v on pressure levels: turned from the grid to east and north.
    * the 2 m extremes: the 12 h they cover written as their time range; CHMI
      gives them as instant fields valid at 06 and 18 UTC, so at T+12, 24 ... 72
      in the runs of 06 and 18 UTC and at T+6, 18 ... 66 in those of 00 and 12 UTC.
    """

    # Files copied as they are; those accumulated from T+0 or valid for the last hour have no T+0.
    STATIC = ("SURFGEOPOTENTIEL", "SURFIND_TERREMER")
    # SURFRESERV_NEIGE, THETA_P_W and the heights of the levels without temperature feed snow_line.
    FROM_ZERO = ("CLSTEMPERATURE", "MSLPRESSURE", "SURFNEBUL_TOTALE", "CLS_VISICLD", "CLSDEW_P_TEMPER", "CLSTPRIM_W",
                 *(f"{level}{name}" for level in (LEVEL_850, LEVEL_700)
                   for name in ("TEMPERATUR", "HUMI_RELAT", "GEOPOTENTI")),
                 "SURFRESERV_NEIGE", *(f"{level}THETA_P_W" for level in WET_BULB_LEVELS),
                 *(f"{level}GEOPOTENTI" for level in WET_BULB_LEVELS if level not in (LEVEL_850, LEVEL_700)))
    FROM_ONE = ("SURFPREC_TOTAL", "PRECIP_TYPE", "PRECIP_TYPESEV", "SURFDIAG_FLASH")
    WIND = ("CLSWIND_SPEED", "CLSWIND_DIREC")
    GUST = ("CLSU_RAF_MOD_XFU", "CLSV_RAF_MOD_XFU")
    # (u, v) of a pressure level, the two files of one wind.
    LEVEL_WINDS = tuple((f"{level}WIND_U_COM", f"{level}WIND_V_COM") for level in (LEVEL_1000, LEVEL_850, LEVEL_700))
    EXTREMES = ("CLSMAXI_TEMPERAT", "CLSMINI_TEMPERAT")
    EXTREME_HOURS = 12
    VARIABLES = (*STATIC, *FROM_ZERO, *FROM_ONE, *WIND, *GUST, *(file for pair in LEVEL_WINDS for file in pair), *EXTREMES)
    STEPS = 73

    @classmethod
    def expected_messages(cls, variable: str) -> int:
        """Messages a complete file of a variable holds."""
        if variable in cls.STATIC:
            return 1
        if variable in cls.EXTREMES:
            return (cls.STEPS - 1) // cls.EXTREME_HOURS
        return cls.STEPS - 1 if variable in cls.FROM_ONE else cls.STEPS

    @classmethod
    def expected_total(cls) -> int:
        """Messages of the finished forecast file: one per message of the files, the gust pair as one from T+1."""
        return sum(cls.expected_messages(v) for v in cls.VARIABLES if v not in cls.GUST) + cls.STEPS - 1

    def write(self, raw: dict[str, Path], target: Path) -> int:
        """Write the forecast file from the raw file of every variable; returns the number of messages."""
        with target.open("wb") as out:
            count = 0
            # STATIC first: a reader asking for z at T+0 without a level finds the model ground, not a pressure level.
            for variable in (*self.STATIC, *self.FROM_ZERO, *self.FROM_ONE):
                for gid in self._messages(raw[variable]):
                    eccodes.codes_write(gid, out)
                    eccodes.codes_release(gid)
                    count += 1
            for speed, direction in zip(self._messages(raw["CLSWIND_SPEED"]), self._messages(raw["CLSWIND_DIREC"])):
                count += self._write_wind(out, speed, direction)
                eccodes.codes_release(speed)
                eccodes.codes_release(direction)
            for u, v in zip(self._messages(raw["CLSU_RAF_MOD_XFU"]), self._messages(raw["CLSV_RAF_MOD_XFU"])):
                count += self._write_gust(out, u, v)
                eccodes.codes_release(u)
                eccodes.codes_release(v)
            for u_file, v_file in self.LEVEL_WINDS:
                for u, v in zip(self._messages(raw[u_file]), self._messages(raw[v_file])):
                    count += self._write_level_wind(out, u, v)
                    eccodes.codes_release(u)
                    eccodes.codes_release(v)
            for variable in self.EXTREMES:
                for gid in self._messages(raw[variable]):
                    count += self._write_extreme(out, gid)
                    eccodes.codes_release(gid)
        return count

    @staticmethod
    def _messages(path: Path) -> Iterator[int]:
        """Open GRIB handles of a file in order; the caller releases each."""
        with path.open("rb") as fh:
            while (gid := eccodes.codes_grib_new_from_file(fh)) is not None:
                yield gid

    @staticmethod
    def _with_values(gid: int, values: np.ndarray) -> int:
        """A copy of a message with other values; the caller releases it."""
        clone = eccodes.codes_clone(gid)
        eccodes.codes_set_values(clone, values)
        return clone

    @staticmethod
    def _set_time_range(gid: int, first: int, last: int) -> None:
        """Mark a message as valid for the hours first..last of the run."""
        if last > LAST_STEP_IN_TIME_RANGE:
            raise ValueError(f"step {last} does not fit the time range of GRIB 1")
        eccodes.codes_set(gid, "timeRangeIndicator", 2)
        eccodes.codes_set(gid, "P1", first)
        eccodes.codes_set(gid, "P2", last)

    @staticmethod
    @lru_cache(maxsize=1)
    def _grid_angle(plane: LambertPlane) -> np.ndarray:
        """Angle (radians) between the grid axes and east and north, per point; the whole grid is costly, so kept."""
        _, lon = plane.latlon()
        return np.sin(np.radians(plane.lat_d)) * np.radians((lon - plane.lon_v + 180.0) % 360.0 - 180.0)

    def _write_wind(self, out, speed: int, direction: int) -> int:
        """Write 10u and 10v of one step, from wind speed and the direction the wind comes from."""
        strength = eccodes.codes_get_values(speed)
        angle = np.radians(eccodes.codes_get_values(direction))
        for parameter, values in zip(ALADIN_WIND_PARAMETERS, (-strength * np.sin(angle), -strength * np.cos(angle))):
            clone = self._with_values(speed, values)
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
        clone = self._with_values(u, np.hypot(eccodes.codes_get_values(u), eccodes.codes_get_values(v)))
        eccodes.codes_set(clone, "indicatorOfParameter", ALADIN_GUST_PARAMETER)
        self._set_time_range(clone, step - 1, step)
        out.write(eccodes.codes_get_message(clone))
        eccodes.codes_release(clone)
        return 1

    def _write_level_wind(self, out, u: int, v: int) -> int:
        """Write u and v of one pressure level and step, turned from the grid to east and north."""
        angle = self._grid_angle(LambertPlane.from_message(u))
        along_x, along_y = eccodes.codes_get_values(u), eccodes.codes_get_values(v)
        east = along_x * np.cos(angle) + along_y * np.sin(angle)
        north = along_y * np.cos(angle) - along_x * np.sin(angle)
        for gid, values in ((u, east), (v, north)):
            clone = self._with_values(gid, values)
            eccodes.codes_set(clone, "uvRelativeToGrid", 0)
            out.write(eccodes.codes_get_message(clone))
            eccodes.codes_release(clone)
        return 2

    def _write_extreme(self, out, gid: int) -> int:
        """Write a 2 m extreme with the hours it covers as its time range; the first one of a run starts at T+0."""
        step = eccodes.codes_get(gid, "endStep")
        clone = eccodes.codes_clone(gid)
        self._set_time_range(clone, max(step - self.EXTREME_HOURS, 0), step)
        out.write(eccodes.codes_get_message(clone))
        eccodes.codes_release(clone)
        return 1
