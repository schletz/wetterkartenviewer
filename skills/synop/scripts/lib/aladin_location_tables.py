"""Markdown tables of the values of AladinStepSampler at one location."""

from datetime import datetime, timedelta

from .constants import ALADIN_FOG_VISIBILITY_M, ALADIN_GRAUPEL, ALADIN_HAIL, ALADIN_STORM_FLASHES_KM2
from .forecast_grib import ForecastGrib
from .icon_location_tables import WINDOWS
from .icon_step_sampler import GRAVITY
from .location_tables import height_note, number, table, wind
from .point_sampler import PointSampler

# Precipitation types of CHMI ALADIN: the ECMWF ptype codes, 2xx for intermittent precipitation, and 193.
PRECIP_TYPES = {1: "rain", 3: "freezing rain", 5: "snow", 6: "wet snow", 7: "rain and snow", 8: "ice pellets",
                9: "graupel", 10: "hail", 11: "drizzle", 12: "freezing drizzle", 193: "wet snow and rain",
                201: "intermittent rain", 205: "intermittent snow", 206: "intermittent wet snow",
                207: "intermittent rain and snow", 213: "intermittent wet snow and rain"}


class AladinLocationTables:
    """Header and tables of the ALADIN location report; rows come from AladinStepSampler.sample."""

    def __init__(self, grib: ForecastGrib, point: PointSampler):
        self.grib, self.point = grib, point

    def header(self, label: str | None, lat: float, lng: float, elevation: float | None) -> str:
        """Location, model height and how to read the values."""
        height = self.point(self.grib.field("z", 0)) / GRAVITY
        land = self.point(self.grib.field("lsm", 0))
        lines = [f"# {label or 'Location'} {lat:.2f} N {lng:.2f} E, CHMI ALADIN run {self.grib.base_time:%d.%m.%Y %H} UTC",
                 "", f"- Model ground: height {height:.0f} m (grid points 2.3 km apart), land fraction {land:.2f}"]
        if elevation is not None:
            lines.append(height_note(height, elevation))
        lines += ["- The file holds near-surface fields only; the free atmosphere comes from ECMWF.",
                  "- Single showers and thunderstorms are possibilities in the area, not a point forecast.",
                  "- Precip: mm in the hour before the time. Type: most frequent type of that hour at the nearest "
                  "grid point.",
                  f"- Signal, as on the weather_summary chart: thunderstorm from {ALADIN_STORM_FLASHES_KM2} flashes per "
                  f"km2 in the hour (a threshold not checked against observed storms), hail from the most dangerous "
                  f"type of the hour, fog where the lowest visibility due to cloud of the hour is below "
                  f"{ALADIN_FOG_VISIBILITY_M:.0f} m.",
                  "- Wind: direction it blows from and m/s; gust: strongest gust in the hour before, m/s."]
        return "\n".join(lines)

    def surface_table(self, rows: list[dict]) -> str:
        """Weather at the ground per hour."""
        cells = [[self._time(row), f"+{row['step']}", number(row["t2m"], 1), wind(row["wind10m"]),
                  number(row["gust"]), number(row["mslp"]), number(row["clouds"]), number(row["precip"], 1),
                  precip_type(row["ptype"]), signal(row)]
                 for row in rows]
        return table(["UTC", "T+", "T2m °C", "Wind 10 m", "Gust", "MSLP hPa", "Clouds %", "Precip mm", "Type", "Signal"],
                     cells)

    def extremes_table(self, rows: list[dict]) -> str:
        """Highest (06-18 UTC) and lowest (18-06 UTC) hourly T2m for the windows inside the run.

        The file has no extremes of the model, so a peak between full hours is missing.
        """
        temperature = {row["step"]: row["t2m"] for row in rows}
        days: dict = {}
        for day in sorted({self.grib.valid_time(step).date() for step in temperature}):
            for kind, (start_time, end_time, days_before) in WINDOWS.items():
                first = self._step(datetime.combine(day - timedelta(days=days_before), start_time))
                end = self._step(datetime.combine(day, end_time))
                if first >= 0 and end <= max(temperature):
                    hourly = [temperature[step] for step in range(first, end + 1)]
                    days.setdefault(day, {})[kind] = max(hourly) if kind == "max" else min(hourly)
        cells = [[f"{day:%a %d.%m.}", *(number(days[day].get(kind), 1) for kind in WINDOWS)] for day in sorted(days)]
        return table(["Day (UTC)", "Tmax 06–18 °C", "Tmin 18–06 °C"], cells)

    def _step(self, valid: datetime) -> int:
        return round((valid - self.grib.base_time).total_seconds() / 3600)

    def _time(self, row: dict) -> str:
        return f"{self.grib.valid_time(row['step']):%d.%m. %H}"


def precip_type(code: float | None) -> str:
    """Text of a precipitation type; empty without precipitation and at T+0."""
    if code is None or round(code) == 0:
        return ""
    return PRECIP_TYPES.get(round(code), str(round(code)))


def signal(row: dict) -> str:
    """Thunderstorm, hail or fog of the hour by the rules of the weather_summary chart (ww 96, 95, 45)."""
    storm = row["flashes"] is not None and row["flashes"] >= ALADIN_STORM_FLASHES_KM2
    severe = round(row["ptype_severe"]) if row["ptype_severe"] is not None else None
    if severe == ALADIN_HAIL or (storm and severe == ALADIN_GRAUPEL):
        return "thunderstorm with hail"
    if storm:
        return "thunderstorm"
    return "fog" if row["visibility"] < ALADIN_FOG_VISIBILITY_M else ""
