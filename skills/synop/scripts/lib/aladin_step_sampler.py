"""Every value of one CHMI ALADIN step at a location, as the ALADIN location table and its TSV need them.

This module reads the fields at the point, converts units and takes the
amounts of the last hour from the sums since T+0.
"""

from .constants import KELVIN
from .icon_step_sampler import GRAVITY, IconStepSampler

PERCENT = 100.0     # tcc and the relative humidity are fractions


class AladinStepSampler(IconStepSampler):
    """Samples the weather at the ground, the 850/700 hPa values and the GRIB values of one ALADIN step."""

    # A 2.3 km model resolves its weather, as ICON-D2 does, so nothing is left out of the TSV.
    HIDDEN = ()
    # Codes and the visibility, which jumps from a few km to fog, take the nearest grid point;
    # interpolated they would give values that no grid point has.
    NEAREST = ("ptype", "ptype_severe", "fog_visibility")

    def sample(self, step: int) -> dict:
        """Values of one step in deg C, hPa, %, mm, m and m/s, wind as (direction, speed).

        The key "grib" holds every parameter of the file in GRIB units (see grib_values).
        """
        grib = self.grib_values(step)
        return {
            "step": step,
            "t2m": grib["2t"] - KELVIN,
            # Components east and north: the download turned the wind of the model to true north.
            "wind10m": self.point.wind(self.grib.field("10u", step), self.grib.field("10v", step)),
            "gust": grib["gust"],
            "mslp": grib["msl"] / 100.0,
            "clouds": grib["tcc"] * PERCENT,
            "precip": self._last_hour("tp", step),
            "ptype": grib["ptype"],
            "ptype_severe": grib["ptype_severe"],
            "visibility": grib["fog_visibility"],
            "flashes": self._last_hour("flash", step),
            **self.upper_air(step, grib, grib["z"] / GRAVITY, PERCENT),
            "grib": grib,
        }

    def _last_hour(self, name: str, step: int) -> float | None:
        """Increase over the last hour of a sum that has no message at T+0; None at T+0."""
        if step == 0:
            return None
        total = self.point(self.grib.field(name, step))
        # Packing noise can make the difference slightly negative.
        return total if step == 1 else max(total - self.point(self.grib.field(name, step - 1)), 0.0)
