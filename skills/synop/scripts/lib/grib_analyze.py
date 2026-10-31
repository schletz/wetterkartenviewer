"""OLAP-style queries on the climatology of a ClimateArchive, by parameter, calendar day and point.

Every query returns a DataFrame with the same columns,

    month, day, lat, lon, <param>

so results can be merged and compared directly. ``avg_*`` values are in deg C,
``std_*`` values in K. ``day`` is empty (<NA>) for monthly values. A query
for a point (lat, lng) returns the nearest grid point; without a point every
grid point comes back, or those inside the bbox given to the constructor.

Requires the packages eccodes, numpy and pandas.

Example:
    from lib.climate_archive import ClimateArchive
    clim = GribAnalyze(ClimateArchive(r"<data>/era5_means"), bbox=(46.4, 49.0, 9.5, 17.2))
    mean = clim.get_12z_means(850, "avg_t", month=1, day=15)
    stdev = clim.get_12z_means(850, "std_t", month=1, day=15)
    z = mean.merge(stdev, on=["month", "day", "lat", "lon"])

    year = clim.get_12z_means(850, "avg_t", lat=48.21, lng=16.37)  # annual cycle at Vienna
"""

import numpy as np
import pandas as pd

from .climate_archive import ClimateArchive
from .constants import KELVIN

PARAMS = {850: ("avg_t", "std_t"), 2: ("avg_2t", "std_2t")}


class GribAnalyze:
    """Slice the climatology by parameter, time and point."""

    def __init__(self, archive: ClimateArchive, bbox: tuple[float, float, float, float] | None = None):
        """Set up the points of the results.

        Args:
            archive: the climatology files.
            bbox: (south, north, west, east) in degrees; queries without a
                point return only grid points inside it. None: all points.
        """
        self._archive = archive
        grid = archive.grid
        self._points = pd.DataFrame({"lat": grid["lat"], "lon": grid["lon"]})
        inside = np.ones(len(self._points), dtype=bool)
        if bbox is not None:
            south, north, west, east = bbox
            inside = (grid["lat"] >= south) & (grid["lat"] <= north) & (grid["lon"] >= west) & (grid["lon"] <= east)
        self._selected = np.flatnonzero(inside)  # indices of the points returned without a point query

    def get_daily_means(self, level=850, param="avg_t", lat=None, lng=None, month=None, day=None):
        """Climatology per calendar day based on daily means.

        Args:
            level: 850 for 850 hPa or 2 for 2 m above ground.
            param: avg_t / std_t at 850 hPa, avg_2t / std_2t at 2 m.
            lat, lng: a single location in degrees; both or neither.
            month, day: restrict the calendar days; each may be given alone.

        Returns:
            DataFrame with the columns month, day, lat, lon, <param>,
            sorted by month, day and point.
        """
        return self._query("daily", level, param, lat, lng, month, day)

    def get_00z_means(self, level=850, param="avg_t", lat=None, lng=None, month=None, day=None):
        """Climatology per calendar day of the 00 UTC values; arguments as in get_daily_means."""
        return self.get_term_means(0, level, param, lat, lng, month, day)

    def get_06z_means(self, level=850, param="avg_t", lat=None, lng=None, month=None, day=None):
        """Climatology per calendar day of the 06 UTC values; arguments as in get_daily_means."""
        return self.get_term_means(6, level, param, lat, lng, month, day)

    def get_12z_means(self, level=850, param="avg_t", lat=None, lng=None, month=None, day=None):
        """Climatology per calendar day of the 12 UTC values; arguments as in get_daily_means."""
        return self.get_term_means(12, level, param, lat, lng, month, day)

    def get_18z_means(self, level=850, param="avg_t", lat=None, lng=None, month=None, day=None):
        """Climatology per calendar day of the 18 UTC values; arguments as in get_daily_means."""
        return self.get_term_means(18, level, param, lat, lng, month, day)

    def get_term_means(self, hour, level=850, param="avg_t", lat=None, lng=None, month=None, day=None):
        """Climatology per calendar day of one time of day (ClimateArchive.term_hours); arguments as in get_daily_means."""
        return self._query(self._archive.term_kind(hour), level, param, lat, lng, month, day)

    def get_monthly_means(self, level=850, param="avg_t", lat=None, lng=None, month=None):
        """Climatology per calendar month based on daily means; arguments as in get_daily_means.

        The column day is <NA>.
        """
        return self._query("monthly", level, param, lat, lng, month, None)

    def _query(self, kind, level, param, lat, lng, month, day):
        if param not in PARAMS.get(level, ()):
            options = ", ".join(f"level={lv}: {' / '.join(ps)}" for lv, ps in PARAMS.items())
            raise ValueError(f"unknown combination level={level}, param={param!r}; use {options}")
        statistic = "mean" if param.startswith("avg") else "std"
        keys = sorted(k for k in self._archive.keys(kind) if k[:2] == (statistic, level)
                      and (month is None or k[2] == month) and (day is None or k[3] == day))
        if not keys:
            raise ValueError(f"no {kind} values for month={month}, day={day}")
        index = self._point_index(lat, lng)

        # float64, so that rounding to 0.01 yields clean decimal values.
        fields = np.stack([self._archive.field(kind, *key)[index] for key in keys]).astype(np.float64)
        if param.startswith("avg"):
            fields = fields - KELVIN
        points = self._points.iloc[index]
        n_points = len(index)
        # Monthly keys carry day None, which the nullable integer type turns into <NA>.
        days = np.repeat(np.array([k[3] for k in keys], dtype=object), n_points)
        return pd.DataFrame({
            "month": np.repeat([k[2] for k in keys], n_points),
            "day": pd.array(days, dtype="Int64"),
            "lat": np.tile(points["lat"].to_numpy(), len(keys)),
            "lon": np.tile(points["lon"].to_numpy(), len(keys)),
            param: np.round(fields.ravel(), 2),
        })

    def _point_index(self, lat, lng):
        """Indices of the points to return: all selected ones, or the one nearest to (lat, lng)."""
        if (lat is None) != (lng is None):
            raise ValueError("give both lat and lng, or neither")
        if lat is None:
            return self._selected
        return np.array([self._archive.nearest(lat=lat, lng=lng)])
