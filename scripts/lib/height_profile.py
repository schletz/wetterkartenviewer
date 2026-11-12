"""Pressure level profile of one forecast step, interpolated to heights above sea level."""

import numpy as np

from . import moist_air
from .constants import KELVIN, PROFILE_LEVELS
from .forecast_grib import ForecastGrib

# Profile levels from the ground upwards; parameters missing on a level are skipped.
LEVELS = tuple(sorted(PROFILE_LEVELS, reverse=True))
PA_PER_HPA = 100.0


class HeightProfile:
    """Vertical profile of one step on the model grid.

    Heights are geopotential heights (gpm), which differ from metres above
    sea level by well under 1 % in the troposphere. Interpolation is linear
    in height between neighbouring pressure levels.
    """

    def __init__(self, grib: ForecastGrib, step: int, height: str = "gh", height_factor: float = 1.0,
                 levels: tuple[int, ...] = LEVELS):
        """Profile of one step.

        Args:
            grib: the forecast file.
            step: its step.
            height: field of the level heights, e.g. "gh" (gpm) or "z" (geopotential, m2/s2).
            height_factor: factor from that field to gpm, e.g. 1 / GRAVITY for "z".
            levels: pressure levels (hPa) of the profile, bottom to top; a level the file lacks is skipped.
        """
        self.grib, self.step = grib, step
        self.height, self.height_factor = height, height_factor
        self.levels = levels

    def _levels(self, *names: str) -> list[int]:
        """Profile levels, bottom to top, that hold every one of the parameters and the height field."""
        return [level for level in self.levels
                if all(self.grib.has(name, self.step, level) for name in (*names, self.height))]

    def _heights(self, levels: list[int]) -> np.ndarray:
        """Heights (gpm) of the levels, stacked bottom to top."""
        return np.stack([self.grib.field(self.height, self.step, level) * self.height_factor for level in levels])

    def _stack(self, name: str) -> tuple[np.ndarray, np.ndarray]:
        """(heights, values) of a parameter on every profile level that holds it and its height, bottom to top."""
        levels = self._levels(name)
        values = np.stack([self.grib.field(name, self.step, level) for level in levels])
        return self._heights(levels), values

    def _wet_bulb_stack(self) -> tuple[np.ndarray, np.ndarray]:
        """(heights, wet-bulb temperatures in K) on the profile levels, bottom to top.

        A file with the model's wet-bulb potential temperature thetaw (ALADIN)
        gives the wet bulb of its levels along the pseudo-adiabat. Otherwise it
        comes from every level that holds t and r: the dew point from the IFS
        relative humidity as in moist_air.py, the wet bulb the isobaric one at
        the pressure of the level.
        """
        if levels := self._levels("thetaw"):
            tw = [moist_air.wet_bulb_from_theta_w(self.grib.field("thetaw", self.step, level), level)
                  for level in levels]
            return self._heights(levels), np.stack(tw)
        levels = self._levels("t", "r")
        tw = []
        for level in levels:
            t = self.grib.field("t", self.step, level)
            td = moist_air.dew_point(moist_air.vapour_pressure(t, self.grib.field("r", self.step, level)))
            tw.append(moist_air.wet_bulb_temperature(t, td, level * PA_PER_HPA).astype(np.float32))
        return self._heights(levels), np.stack(tw)

    def at_height(self, name: str, height: float) -> np.ndarray:
        """A parameter at a fixed height; NaN where the height lies outside its levels."""
        heights, values = self._stack(name)
        result = np.full(heights.shape[1:], np.nan, dtype=np.float32)
        for lo in range(len(heights) - 1):
            inside = (heights[lo] <= height) & (height < heights[lo + 1])
            weight = (height - heights[lo]) / (heights[lo + 1] - heights[lo])
            result = np.where(inside, values[lo] + weight * (values[lo + 1] - values[lo]), result)
        return result

    def freezing_level(self, ground: np.ndarray) -> np.ndarray:
        """Height of the 0 deg C level in m (see zero_crossing)."""
        return self.zero_crossing(*self._stack("t"), ground)

    def wet_bulb_zero(self, ground: np.ndarray) -> np.ndarray:
        """Height of the 0 deg C wet-bulb level in m (see zero_crossing).

        Falling snow is cooled by evaporation to about the wet-bulb
        temperature and starts melting only where that exceeds 0 deg C. In
        saturated air the level equals the freezing level, in dry air it lies
        lower.
        """
        return self.zero_crossing(*self._wet_bulb_stack(), ground)

    def wet_bulb_level(self, ground: np.ndarray, celsius: float) -> np.ndarray:
        """Height in m where the wet-bulb temperature falls to ``celsius`` deg C (see zero_crossing).

        ICON-D2 diagnoses its snow line (snowlmt) this way with +1.3 deg C.
        """
        heights, tw = self._wet_bulb_stack()
        return self.zero_crossing(heights, tw - celsius, ground)

    @staticmethod
    def zero_crossing(heights: np.ndarray, temperatures: np.ndarray, ground: np.ndarray) -> np.ndarray:
        """Height of the 0 deg C crossing of a temperature profile (K, bottom to top), searched from the top down.

        Searching from the top finds the upper end of a warm layer above a
        cold pool, which is the level that matters for snow and skiers. Where
        the whole column up to the top level is frozen, or the crossing lies
        below the model ground, the result is the ground height; where the
        top level is still above 0 deg C it is NaN.
        """
        result = np.full(heights.shape[1:], np.nan, dtype=np.float32)
        for lo in reversed(range(len(heights) - 1)):
            t_lo, t_hi = temperatures[lo], temperatures[lo + 1]
            crossing = np.isnan(result) & (t_lo > KELVIN) & (t_hi <= KELVIN)
            # Equal temperatures divide by zero, but only where there is no crossing.
            with np.errstate(divide="ignore", invalid="ignore"):
                level = heights[lo] + (KELVIN - t_lo) / (t_hi - t_lo) * (heights[lo + 1] - heights[lo])
            result = np.where(crossing, level, result)
        frozen = np.isnan(result) & (temperatures[0] <= KELVIN)
        result = np.where(frozen, ground, result)
        return np.maximum(result, ground)
