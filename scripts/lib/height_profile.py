"""Pressure level profile of one forecast step, interpolated to heights above sea level."""

import numpy as np

from .constants import KELVIN, PROFILE_LEVELS
from .forecast_grib import ForecastGrib

# Profile levels from the ground upwards; parameters missing on a level are skipped.
LEVELS = tuple(sorted(PROFILE_LEVELS, reverse=True))


class HeightProfile:
    """Vertical profile of one step on the model grid.

    Heights are geopotential heights (gpm), which differ from metres above
    sea level by well under 1 % in the troposphere. Interpolation is linear
    in height between neighbouring pressure levels.
    """

    def __init__(self, grib: ForecastGrib, step: int, height: str = "gh", height_factor: float = 1.0):
        """Profile of one step.

        Args:
            grib: the forecast file.
            step: its step.
            height: field of the level heights, e.g. "gh" (gpm) or "z" (geopotential, m2/s2).
            height_factor: factor from that field to gpm, e.g. 1 / GRAVITY for "z".
        """
        self.grib, self.step = grib, step
        self.height, self.height_factor = height, height_factor

    def _stack(self, name: str) -> tuple[np.ndarray, np.ndarray]:
        """(heights, values) of a parameter on every profile level that holds it and its height, bottom to top."""
        levels = [level for level in LEVELS
                  if self.grib.has(name, self.step, level) and self.grib.has(self.height, self.step, level)]
        heights = np.stack([self.grib.field(self.height, self.step, level) * self.height_factor for level in levels])
        values = np.stack([self.grib.field(name, self.step, level) for level in levels])
        return heights, values

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
        """Height of the 0 deg C level in m, searched from the top downwards.

        Searching from the top finds the upper end of a warm layer above a
        cold pool, which is the freezing level that matters for snow and
        skiers. Where the whole column up to 500 hPa is frozen, or the
        crossing lies below the model ground, the result is the ground
        height; where 500 hPa is still above 0 deg C it is NaN.
        """
        heights, temperatures = self._stack("t")
        result = np.full(heights.shape[1:], np.nan, dtype=np.float32)
        for lo in reversed(range(len(heights) - 1)):
            t_lo, t_hi = temperatures[lo], temperatures[lo + 1]
            crossing = np.isnan(result) & (t_lo > KELVIN) & (t_hi <= KELVIN)
            level = heights[lo] + (KELVIN - t_lo) / (t_hi - t_lo) * (heights[lo + 1] - heights[lo])
            result = np.where(crossing, level, result)
        frozen = np.isnan(result) & (temperatures[0] <= KELVIN)
        result = np.where(frozen, ground, result)
        return np.maximum(result, ground)
