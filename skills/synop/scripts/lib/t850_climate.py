"""Climate of T850 for the valid times of a forecast.

Mean and standard deviation come from the climatology of the time of day
of the valid time, so both belong to the same hour; the archive must hold
a climatology for every hour that occurs (the forecast runs in 3 h steps,
the climatology every 3 h).
"""

from datetime import datetime

import numpy as np

from .climate_archive import ClimateArchive
from .constants import KELVIN

LEVEL = 850


class T850Climate:
    """Mean (deg C) and standard deviation (K) of T850 per valid time, at a point or as a field."""

    def __init__(self, archive: ClimateArchive):
        self.archive = archive

    @property
    def period(self) -> str:
        """Reference period of the climatology, e.g. "1991–2020"."""
        return self.archive.period

    def at_point(self, valid_times: list[datetime], lat: float, lng: float) -> list[tuple[float, float]]:
        """(mean, std) for every valid time at the climatology grid point nearest to a location.

        Raises:
            ValueError: if the location lies outside the climatology grid or a
                valid time has no climatology file.
        """
        index = self.archive.nearest(lat, lng)
        return [tuple(float(values[index]) for values in self._values(valid)) for valid in valid_times]

    def field(self, valid: datetime) -> tuple[np.ndarray, np.ndarray]:
        """(mean, std) of one valid time as (nj, ni) arrays on the climatology grid (ClimateArchive.grid)."""
        shape = self.archive.grid["nj"], self.archive.grid["ni"]
        mean, std = self._values(valid)
        return mean.reshape(shape), std.reshape(shape)

    def _values(self, valid: datetime) -> tuple[np.ndarray, np.ndarray]:
        kind = self.archive.term_kind(valid.hour)
        mean = self.archive.field(kind, "mean", LEVEL, valid.month, valid.day) - KELVIN
        std = self.archive.field(kind, "std", LEVEL, valid.month, valid.day)
        return mean, std
