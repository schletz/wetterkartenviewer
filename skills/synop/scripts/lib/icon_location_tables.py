"""Markdown tables of the values of IconStepSampler at one location."""

from datetime import datetime, time, timedelta

import numpy as np

from .constants import KELVIN
from .forecast_grib import ForecastGrib
from .location_tables import MIXED_LAPSE_K_PER_100M, NEAR_GROUND_M, number, table, wind
from .point_sampler import PointSampler

# tmax_2m/tmin_2m restart every 6 h from the run start, although the GRIB header claims "since T+0".
RESTART_HOURS = 6
# Daily windows as for ECMWF: Tmax 06-18 UTC of the day, Tmin 18 UTC of the day before to 06 UTC.
WINDOWS = {"max": (time(6), time(18), 0), "min": (time(18), time(6), 1)}
# Free atmosphere every 3 h: it changes slowly, the hourly rows are for the weather at the ground.
UPPER_HOURS = 3
# WMO code table 4677 as far as ICON-D2 uses it.
WEATHER = {0: "clear", 1: "mainly clear", 2: "partly cloudy", 3: "overcast", 45: "fog", 48: "rime fog",
           51: "light drizzle", 53: "drizzle", 55: "heavy drizzle", 56: "freezing drizzle",
           57: "heavy freezing drizzle", 61: "light rain", 63: "rain", 65: "heavy rain", 66: "freezing rain",
           67: "heavy freezing rain", 71: "light snow", 73: "snow", 75: "heavy snow", 77: "snow grains",
           80: "light showers", 81: "showers", 82: "heavy showers", 85: "snow showers", 86: "heavy snow showers",
           95: "thunderstorm", 96: "thunderstorm with hail"}


class IconLocationTables:
    """Header and tables of the ICON-D2 location report; rows come from IconStepSampler.sample."""

    def __init__(self, grib: ForecastGrib, point: PointSampler):
        self.grib, self.point = grib, point

    def header(self, label: str | None, lat: float, lng: float, elevation: float | None, rows: list[dict]) -> str:
        """Location, model height and how to read the values."""
        height = self.point(self.grib.field("hsurf", 0))
        land = self.point(self.grib.field("lsm", 0))
        lines = [f"# {label or 'Location'} {lat:.2f} N {lng:.2f} E, ICON-D2 run {self.grib.base_time:%d.%m.%Y %H} UTC",
                 "", f"- Model ground: height {height:.0f} m (cells about 2.2 km apart), land fraction {land:.2f}"]
        if elevation is not None:
            difference = height - elevation
            lines.append(f"- Real height {elevation:.0f} m: the model ground lies {abs(difference):.0f} m "
                         f"{'higher' if difference >= 0 else 'lower'}. In well mixed air that alone shifts T2m by "
                         f"{MIXED_LAPSE_K_PER_100M * difference / 100:+.1f} K for the real height; not under inversions.")
        clearance = np.mean([row["height850"] for row in rows]) - height
        if clearance < NEAR_GROUND_M:
            lines.append(f"- 850 hPa lies on average only {clearance:.0f} m above the model ground: T850 follows "
                         "the diurnal cycle of the ground there.")
        lines += ["- The weather at the ground (clouds, precipitation, weather code, gusts) comes from a model that "
                  "resolves showers, thunderstorms and fog; single cells are possibilities in the area, not a point "
                  "forecast.",
                  "- Precip: mm in the hour before the time. Cloud base: lowest layer above 50 % cover, m above sea "
                  "level, dash where there is none. Weather: WMO code 4677 of the nearest cell.",
                  "- Wind: direction it blows from and m/s; gust: strongest gust in the hour before, m/s. "
                  "Z: height of the pressure level in m. Wind 1000 is a dash where 1000 hPa lies below the "
                  "model ground (the model extrapolates it there; the TSV keeps those values)."]
        return "\n".join(lines)

    def surface_table(self, rows: list[dict]) -> str:
        """Weather at the ground per hour."""
        cells = [[self._time(row), f"+{row['step']}", number(row["t2m"], 1), wind(row["wind10m"]),
                  number(row["gust"]), number(row["mslp"]), number(row["clouds"]),
                  number(round(row["cloud_base"], -1)) if row["cloud_base"] is not None else "–",
                  number(row["precip"], 1), weather(row["ww"])]
                 for row in rows]
        return table(["UTC", "T+", "T2m °C", "Wind 10 m", "Gust", "MSLP hPa", "Clouds %", "Cloud base m",
                      "Precip mm", "Weather"], cells)

    def upper_table(self, rows: list[dict]) -> str:
        """Wind at 1000 hPa and height, temperature, humidity and wind at 850 and 700 hPa every 3 h."""
        cells = [[self._time(row), f"+{row['step']}", wind(row["wind1000"]),
                  *(cell for level in (850, 700) for cell in (
                      number(row[f"height{level}"]), number(row[f"t{level}"], 1), number(row[f"rh{level}"]),
                      wind(row[f"wind{level}"])))]
                 for row in rows if row["step"] % UPPER_HOURS == 0]
        return table(["UTC", "T+", "Wind 1000", *(head for level in (850, 700) for head in (
            f"Z{level} m", f"T{level} °C", f"RH{level} %", f"Wind {level}"))], cells)

    def extremes_table(self, rows: list[dict]) -> str:
        """Daily maximum (06-18 UTC) and minimum (18-06 UTC) at 2 m for the windows inside the run.

        Where the 6 h period of the model extreme lies inside the window, its
        value counts; the hours before the first restart in the window (runs
        at 03, 09, 15, 21 UTC) take the hourly T2m, which may miss a peak
        between full hours.
        """
        by_step = {row["step"]: row["grib"] for row in rows}
        last = max(by_step)
        days: dict = {}
        for day in sorted({self.grib.valid_time(step).date() for step in by_step}):
            for kind, (start_time, end_time, days_before) in WINDOWS.items():
                start = datetime.combine(day - timedelta(days=days_before), start_time)
                first, end = self._step(start), self._step(datetime.combine(day, end_time))
                if first < 0 or end > last:
                    continue
                name = "tmax_2m" if kind == "max" else "tmin_2m"
                hourly = [by_step[step][name] if (step - 1) // RESTART_HOURS * RESTART_HOURS >= first
                          else by_step[step]["2t"] for step in range(first + 1, end + 1)]
                days.setdefault(day, {})[kind] = (max(hourly) if kind == "max" else min(hourly)) - KELVIN
        cells = [[f"{day:%a %d.%m.}", *(number(days[day].get(kind), 1) for kind in WINDOWS)] for day in sorted(days)]
        return table(["Day (UTC)", "Tmax 06–18 °C", "Tmin 18–06 °C"], cells)

    def _step(self, valid: datetime) -> int:
        return round((valid - self.grib.base_time).total_seconds() / 3600)

    def _time(self, row: dict) -> str:
        return f"{self.grib.valid_time(row['step']):%d.%m. %H}"


def weather(code: float | None) -> str:
    """WMO weather code with its meaning, e.g. "61 light rain"; empty where there is none (T+0)."""
    if code is None or np.isnan(code):
        return ""
    code = round(code)
    return f"{code} {WEATHER.get(code, '')}".strip()
