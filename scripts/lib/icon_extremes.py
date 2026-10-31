"""Daily 2 m extremes of an ICON-D2 file (download_icon_d2.py)."""

from datetime import date, timedelta

import numpy as np

from .extreme_windows import ExtremeWindows
from .forecast_grib import ForecastGrib

# tmax_2m/tmin_2m restart every 6 h from the run start. The GRIB header claims "since T+0"
# (stepRange 0-N); the values drop after every 6th step and match the extreme of the hourly
# 2 m temperature since the last restart.
RESTART_HOURS = 6
FIELDS = {"max": "tmax_2m", "min": "tmin_2m"}


class IconExtremes:
    """Daily maximum (06-18 UTC) and minimum (18-06 UTC) of the 2 m temperature, as for ECMWF (EXTREME_WINDOWS).

    Where whole restart periods lie inside the window, their extreme is
    exact. The hours before the first restart in the window (runs at 03,
    09, 15 and 21 UTC, whose periods start 3 h off the window) take the
    hourly 2 m temperature instead, which misses peaks between full hours;
    those hours are the morning of the maximum and the evening of the
    minimum, when the extreme rarely occurs.
    """

    def __init__(self, grib: ForecastGrib):
        self.grib = grib
        self.windows = ExtremeWindows([], grib.base_time)
        self.last_step = max(grib.steps("2t"))

    def days(self, kind: str) -> list[date]:
        """Calendar days (UTC) whose window lies within the run."""
        first = self.grib.base_time.date()
        last = self.grib.valid_time(self.last_step).date()
        candidates = [first + timedelta(days=n) for n in range((last - first).days + 1)]
        return [day for day in candidates if self._inside(*self.windows.window(kind, day))]

    def field(self, kind: str, day: date) -> np.ndarray | None:
        """Daily maximum (``kind="max"``) or minimum ("min") in K, one value per cell; None outside the run."""
        start, end = self.windows.window(kind, day)
        if not self._inside(start, end):
            return None
        hourly = [self.grib.field(FIELDS[kind], step) if self._restart(step) >= start else self.grib.field("2t", step)
                  for step in range(start + 1, end + 1)]
        return (np.fmax if kind == "max" else np.fmin).reduce(hourly)

    def _inside(self, start: int, end: int) -> bool:
        return start >= 0 and end <= self.last_step

    @staticmethod
    def _restart(step: int) -> int:
        """Step of the last restart before a step: the extreme at ``step`` covers (restart, step]."""
        return (step - 1) // RESTART_HOURS * RESTART_HOURS
