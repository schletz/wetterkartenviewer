"""Markdown tables of the values of StepSampler at one location."""

import math

import numpy as np

from .constants import KELVIN
from .forecast_grib import ForecastGrib
from .point_sampler import PointSampler
from .step_sampler import MOUNTAIN_HEIGHTS

COMPASS = ("N", "NE", "E", "SE", "S", "SW", "W", "NW")
# Lapse rate of well mixed air for the height note (K per 100 m), not valid under inversions.
MIXED_LAPSE_K_PER_100M = 0.65
# Below this height of 850 hPa above the model ground (m), T850 carries the diurnal cycle of the ground.
NEAR_GROUND_M = 500
DASH = "–"


class LocationTables:
    """Header and tables of the location report; rows come from StepSampler.sample."""

    def __init__(self, grib: ForecastGrib, point: PointSampler):
        self.grib, self.point = grib, point

    def header(self, label: str | None, lat: float, lng: float, elevation: float | None, rows: list[dict]) -> str:
        """Location, model height and how far T2m and T850 can be trusted there."""
        height = self.point(self.grib.field("orog", 0))
        roughness = self.point(self.grib.field("sdor", 0))
        land = self.point(self.grib.field("lsm", 0))
        lines = [f"# {label or 'Location'} {lat:.2f} N {lng:.2f} E, "
                 f"ECMWF IFS run {self.grib.base_time:%d.%m.%Y %H} UTC", "",
                 f"- Model grid point: height {height:.0f} m, sub-grid std. dev. of the orography {roughness:.0f} m, "
                 f"land fraction {land:.2f}"]
        if elevation is not None:
            difference = height - elevation
            lines.append(f"- Real height {elevation:.0f} m: the model ground lies {abs(difference):.0f} m "
                         f"{'higher' if difference >= 0 else 'lower'}. In well mixed air that alone shifts T2m by "
                         f"{MIXED_LAPSE_K_PER_100M * difference / 100:+.1f} K for the real height; not under inversions.")
        # Close above the ground, daytime heating and nighttime cooling reach the level,
        # so a 12 h change shows the diurnal cycle rather than a change of air mass.
        clearance = np.mean([row["grib"]["gh850"] for row in rows]) - height
        if clearance < NEAR_GROUND_M:
            lines.append(f"- 850 hPa lies on average only {clearance:.0f} m above the model ground: T850, "
                         "ΔT850/12h and the mountain values just above the ground follow the diurnal cycle there. "
                         "For a change of air mass, compare equal times of day (12z with 12z).")
        lines += ["- T2m, Tmax and Tmin are model values at the model height; the model resolves neither "
                  "inversions in basins nor fog and low stratus well.",
                  "- Inv: largest temperature increase across 1000-925 or 925-850 hPa (> 0 inversion). "
                  "RH BL: humidity at 925/1000 hPa. Precip: saturated air at 850/700 hPa with ascent.",
                  "- Levels below the model ground are extrapolated by the model and shown as a dash "
                  "(wind and boundary layer values at 1000 and 925 hPa).",
                  "- Wind: direction it blows from and m/s."]
        return "\n".join(lines)

    def main_table(self, rows: list[dict]) -> str:
        """Free atmosphere and boundary layer per step."""
        t850 = {row["step"]: row["t850"] for row in rows}
        cells = []
        for row in rows:
            before = t850.get(row["step"] - 12)
            change = row["t850"] - before if before is not None else None
            cells.append([self._time(row), f"+{row['step']}", number(row["t850"], 1),
                          number(change, 1, signed=True), number(row["thickness"]), number(row["mslp"]),
                          wind(row["wind1000"]), wind(row["wind925"]), number(row["inversion"], 1, signed=True),
                          number(row["rh_bl"]), number(row["rh700"]), number(row["omega700"], 2, signed=True),
                          "x" if row["precip"] else "", number(row["t2m"], 1)])
        return table(["UTC", "T+", "T850 °C", "ΔT850/12h", "Z1000–500 dam", "MSLP hPa", "Wind 1000", "Wind 925",
                      "Inv K", "RH BL %", "RH700 %", "ω700 Pa/s", "Precip", "T2m °C"], cells)

    def mountain_table(self, rows: list[dict]) -> str:
        """Temperature, wind and humidity at fixed heights, freezing level and snow line per step."""
        cells = [[self._time(row), f"+{row['step']}",
                  *(number(row[f"t{h}"], 1) for h in MOUNTAIN_HEIGHTS),
                  *(wind(row[f"wind{h}"]) for h in (MOUNTAIN_HEIGHTS[0], MOUNTAIN_HEIGHTS[-1])),
                  number(row["rh2000"]), number(round(row["freezing"], -2)),
                  number(round(row["snow_line"], -2)) if row["snow_line"] is not None else ""]
                 for row in rows]
        return table(["UTC", "T+", *(f"T {h} m" for h in MOUNTAIN_HEIGHTS),
                      *(f"Wind {h} m" for h in (MOUNTAIN_HEIGHTS[0], MOUNTAIN_HEIGHTS[-1])),
                      f"RH {MOUNTAIN_HEIGHTS[0]} m %", "0 °C level m", "Snow line m"], cells)

    def extremes_table(self) -> str:
        """Daily maximum and minimum at 2 m; each daily field ends on its day (18 or 06 UTC)."""
        days: dict = {}
        for kind in ("mx2t", "mn2t"):
            for step in self.grib.steps(kind):
                day = self.grib.valid_time(step).date()
                days.setdefault(day, {})[kind] = self.point(self.grib.field(kind, step)) - KELVIN
        cells = [[f"{day:%a %d.%m.}", *(number(days[day].get(kind), 1) for kind in ("mx2t", "mn2t"))]
                 for day in sorted(days)]
        return table(["Day (UTC)", "Tmax 06–18 °C", "Tmin 18–06 °C"], cells)

    def _time(self, row: dict) -> str:
        return f"{self.grib.valid_time(row['step']):%d.%m. %H}"


def number(value: float | None, digits: int = 0, signed: bool = False) -> str:
    """Formatted number, a dash for missing values; rounding never shows "-0"."""
    if value is None or math.isnan(value):
        return DASH
    value = round(value, digits) + 0.0
    return f"{value:+.{digits}f}" if signed else f"{value:.{digits}f}"


def wind(value: tuple[float, float] | None) -> str:
    """Compass direction the wind blows from and speed in m/s, e.g. "SW 4"."""
    if value is None:
        return DASH
    direction, speed = value
    return f"{COMPASS[round(direction / 45.0) % 8]} {speed:.0f}"


def table(head: list[str], rows: list[list[str]]) -> str:
    """Markdown table."""
    lines = ["| " + " | ".join(head) + " |", "|" + "---|" * len(head)]
    return "\n".join(lines + ["| " + " | ".join(cells) + " |" for cells in rows])
