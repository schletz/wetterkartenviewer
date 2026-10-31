"""Every value of one forecast step at a location, as the location table and the TSV need them.

The derived quantities (values at fixed heights, freezing level, inversion,
precipitation signal, ...) are fields of the forecast file; this module only
reads them at the point and converts units.
"""

from .constants import KELVIN, WEATHER_PARAMS
from .forecast_grib import ForecastGrib
from .point_sampler import PointSampler

MOUNTAIN_HEIGHTS = (2000, 2500, 3000)


class StepSampler:
    """Samples the free atmosphere, mountain and GRIB values of one ECMWF step at one location."""

    # Parameters left out of the TSV.
    HIDDEN = WEATHER_PARAMS

    def __init__(self, grib: ForecastGrib, point: PointSampler):
        self.grib, self.point = grib, point

    def sample(self, step: int) -> dict:
        """Values of one step in deg C, dam, hPa, m, % and Pa/s, wind as (direction, speed).

        The key "grib" holds every parameter of the forecast file in GRIB
        units (see grib_values).
        """
        field, point = self.grib.field, self.point
        # Bilinear between grid points with and without signal; at least half of it counts.
        precip = point(field("psig", step)) >= 0.5
        row = {
            "step": step,
            "t850": point(field("t", step, 850)) - KELVIN,
            "thickness": point(field("thick", step)) / 10.0,
            "mslp": point(field("msl", step)) / 100.0,
            "wind1000": point.wind(field("uf", step, 1000), field("vf", step, 1000)),
            "wind925": point.wind(field("uf", step, 925), field("vf", step, 925)),
            "inversion": point(field("inv", step)),
            "rh_bl": point(field("rhbl", step)),
            "rh700": point(field("r", step, 700)),
            "omega700": point(field("w", step, 700)),
            "precip": precip,
            "t2m": point(field("2t", step)) - KELVIN,
            "freezing": point(field("deg0l", step)),
            "snow_line": point(field("snowl", step)) if precip else None,
            "rh2000": point(field("r", step, MOUNTAIN_HEIGHTS[0])),
            "grib": self.grib_values(step),
        }
        for height in MOUNTAIN_HEIGHTS:
            row[f"t{height}"] = point(field("t", step, height)) - KELVIN
            row[f"wind{height}"] = point.wind(field("u", step, height), field("v", step, height))
        return row

    def grib_values(self, step: int) -> dict[str, float | None]:
        """Every parameter of the forecast file at the location, in GRIB units, keyed by TSV column.

        Fields of T+0 only (orography, land-sea mask) count for every step;
        parameters missing at this step (e.g. mx2t3 after T+144, the daily
        extremes outside their end step) are None. HIDDEN is left out.
        """
        grib = self.grib
        values = {}
        # Pressure levels first, by parameter and from the ground upwards; the rest in file order.
        order = sorted((p for p in grib.parameters() if p[0] not in self.HIDDEN),
                       key=lambda p: (p[2] != "isobaricInhPa", p[0], -p[1])
                       if p[2] == "isobaricInhPa" else (True, "", 0))
        for name, level, level_type in order:
            if grib.has(name, step, level):
                source = step
            elif grib.steps(name) == [0]:
                source = 0
            else:
                source = None
            values[self.column_name(name, level, level_type)] = (self.value(name, grib.field(name, source, level))
                                                                 if source is not None else None)
        return values

    def value(self, name: str, values) -> float:
        """Value of a field at the location; subclasses may sample some parameters differently."""
        return self.point(values)

    @staticmethod
    def column_name(name: str, level: int, level_type: str) -> str:
        """TSV column of a parameter: the level appended on pressure levels (t850) and heights (t2000m)."""
        if level_type == "isobaricInhPa":
            return f"{name}{level}"
        if level_type == "heightAboveSea":
            return f"{name}{level}m"
        return name
