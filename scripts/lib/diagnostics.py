"""Diagnostics of one forecast step derived from the free atmosphere only.

The 2 m temperature and other near-surface fields of a global model are
weak exactly where an analysis needs them most: the model misses most
inversions, fog and low stratus in basins. These diagnostics therefore use
pressure level fields only, and a level counts only where it lies above
the model ground; below the ground the model extrapolates it from the
surface and would smuggle the near-surface error back in.
"""

import numpy as np
from scipy.ndimage import gaussian_filter

from . import chart_styles as styles
from .height_profile import HeightProfile
from .model_surface import ModelSurface

# Margin (gpm) by which a pressure level must lie above the model ground to count as free atmosphere.
ABOVE_GROUND_MARGIN = 20.0
# Smoothing of the vertical velocity in grid points (0.1 deg): it is noisy over mountains.
OMEGA_SIGMA = 4


class Diagnostics:
    """Free atmosphere diagnostics of one step on the model grid (arrays of ForecastGrib.grid)."""

    def __init__(self, profile: HeightProfile, surface: ModelSurface):
        self.profile = profile
        self.grib, self.step, self.ground = profile.grib, profile.step, surface.height

    def above_ground(self, level: int) -> np.ndarray:
        """Where a pressure level lies in the free atmosphere, i.e. above the model ground."""
        return self.grib.field("gh", self.step, level) > self.ground + ABOVE_GROUND_MARGIN

    def free(self, name: str, level: int) -> np.ndarray:
        """A pressure level field, NaN where the level lies below the model ground."""
        return np.where(self.above_ground(level), self.grib.field(name, self.step, level), np.nan)

    def inversion(self) -> np.ndarray:
        """Largest temperature increase (K) across 1000-925 or 925-850 hPa; > 0 is an inversion.

        Each layer is about 650 m deep; well mixed air gives about -6 K,
        the standard atmosphere -4 K. A layer counts only where its lower
        level lies above the model ground; NaN where none is left (high
        ground such as the inner Alps).
        """
        t1000, t925 = self.free("t", 1000), self.free("t", 925)
        t850 = self.grib.field("t", self.step, 850)
        return np.fmax(t925 - t1000, t850 - t925)

    def moist_boundary_layer(self) -> np.ndarray:
        """Highest relative humidity (%) at 925 or 1000 hPa where they lie above the ground, else NaN."""
        return np.fmax(self.free("r", 925), self.free("r", 1000))

    def precipitation_signal(self) -> np.ndarray:
        """True where the upper air points to precipitation: saturated air at 850 or 700 hPa that rises.

        This is a signal, not an amount: deep moisture plus ascent (omega < 0 at 700 hPa).
        """
        humid = np.maximum(self.grib.field("r", self.step, 850), self.grib.field("r", self.step, 700))
        omega = gaussian_filter(self.grib.field("w", self.step, 700), OMEGA_SIGMA, mode="nearest")
        return (humid >= styles.PRECIP_RH) & (omega < 0)

    def freezing_level(self) -> np.ndarray:
        """Freezing level in m (see HeightProfile.freezing_level)."""
        return self.profile.freezing_level(self.ground)

    def snow_line(self) -> np.ndarray:
        """Snow line in m: below the freezing level by the melting distance, at least the model ground."""
        return np.maximum(self.freezing_level() - styles.SNOW_LINE_BELOW_FREEZING_M, self.ground)
