"""Every value of one ICON-D2 step at a location, as the ICON location table and its TSV need them.

The ICON-D2 file holds raw model fields only; this module reads them at the
point, converts units and takes the precipitation of the last hour from the
accumulated sum.
"""

from .constants import KELVIN
from .step_sampler import StepSampler

GRAVITY = 9.80665           # m/s2, geopotential -> height
LEVELS = (850, 700)
# Height of 1000 hPa above sea level per hPa of MSLP above 1000 hPa (near the ground, about 8 m/hPa).
M_PER_HPA = 8.0
# ICON writes a cloud base of about 20 000 m where no layer has more than 50 % cover.
NO_CEILING_M = 15000


class IconStepSampler(StepSampler):
    """Samples the near-surface weather, the 850/700 hPa values and the GRIB values of one ICON-D2 step."""

    # Only the cell coordinates: ICON-D2 resolves fog, showers and thunderstorms, so its weather counts.
    HIDDEN = ("clat", "clon")
    # Codes and fields that jump (cloud base: 20 km next to 800 m) take the nearest cell; interpolated
    # they would give codes and heights that no cell has.
    NEAREST = ("ww", "ceiling")

    def sample(self, step: int) -> dict:
        """Values of one step in deg C, hPa, m, %, mm and m/s, wind as (direction, speed).

        The key "grib" holds every parameter of the file in GRIB units (see grib_values).
        """
        field, point = self.grib.field, self.point
        grib = self.grib_values(step)
        ceiling = grib["ceiling"]
        # ICON has no geopotential at 1000 hPa; below the model ground its wind is extrapolated, as for ECMWF a dash.
        above_ground = (grib["msl"] / 100.0 - 1000.0) * M_PER_HPA > grib["hsurf"]
        row = {
            "step": step,
            "t2m": grib["2t"] - KELVIN,
            "wind10m": point.wind(field("10u", step), field("10v", step)),
            "gust": grib["gust"],
            "mslp": grib["msl"] / 100.0,
            "clouds": grib["tcc"],
            "cloud_base": ceiling if ceiling is not None and ceiling < NO_CEILING_M else None,
            "precip": grib["tp"] - point(field("tp", step - 1)) if step > 0 else None,
            "ww": grib["ww"],
            "wind1000": point.wind(field("u", step, 1000), field("v", step, 1000)) if above_ground else None,
            "grib": grib,
        }
        for level in LEVELS:
            row[f"height{level}"] = grib[f"z{level}"] / GRAVITY
            row[f"t{level}"] = grib[f"t{level}"] - KELVIN
            row[f"rh{level}"] = grib[f"r{level}"]
            row[f"wind{level}"] = point.wind(field("u", step, level), field("v", step, level))
        return row

    def value(self, name: str, values) -> float:
        return self.point.nearest(values) if name in self.NEAREST else self.point(values)
