"""The chart products of CHMI ALADIN: the near-surface products of ICON-D2, from the fields of the Czech model."""

import numpy as np

from . import chart_styles as styles
from .icon_products import IconProducts
from .missing_field_error import MissingFieldError


class AladinProducts(IconProducts):
    """Draws the products of a CHMI ALADIN file (download_chmi_aladin.py) for a chart window.

    The drawing is that of ICON-D2, with a run to T+72. What differs are the
    sources: the cloud cover is a fraction, the precipitation and the lightning
    accumulate from T+1, the type of the precipitation is the most frequent one
    of the last hour, and thunderstorms, hail and fog have no common field
    (ICON-D2 has ww); they are put together from lightning density, the most
    dangerous precipitation type and visibility in the codes of ww.

    It is wired like ChartProducts, with an AladinSurface as surface and a
    LambertGrid as pixel mapping.
    """

    STEP = ("t2m_wind10m", "wind10m", "weather_summary")
    DAY: dict = {}
    STATIC = ()
    ALL = STEP
    MODEL = "CHMI ALADIN"
    DEFAULTS = {"chmi-aladin": ALL}

    def last_hour(self, name: str, step: int) -> np.ndarray:
        """Increase over the last hour of a field accumulated from T+0, which has no message at T+0."""
        if step == 1:
            return self.grib.field(name, step)
        # Packing noise can make the difference slightly negative.
        return np.maximum(self.grib.field(name, step) - self.grib.field(name, step - 1), 0)

    def cloud_cover(self, step: int) -> np.ndarray:
        return self.field("tcc", step, factor=styles.ALADIN_CLOUD_PERCENT)

    def precipitation(self, step: int, hours: int) -> np.ndarray:
        if hours != 1:
            raise MissingFieldError(f"precipitation over {hours} h")
        return self.pixels.resample(self.last_hour("tp", step))

    def precipitation_type(self, step: int) -> np.ndarray:
        """The most frequent type of the last hour in the ECMWF ptype codes of the legend; 0 for everything else."""
        kinds = np.rint(self.pixels.nearest(self.grib.field("ptype", step)))
        ptype = np.zeros_like(kinds)
        for code, aladin_codes in styles.ALADIN_PTYPE.items():
            ptype[np.isin(kinds, aladin_codes)] = code
        return ptype

    def significant_weather(self, step: int) -> np.ndarray:
        """Thunderstorm, hail and fog of the last hour in the codes of ww, which ALADIN does not publish.

        Fog: the lowest visibility due to cloud in the last hour. Hail: the
        most dangerous precipitation type, graupel only with lightning, since
        graupel falls from ordinary showers too.
        """
        storm = self.pixels.resample(self.last_hour("flash", step)) >= styles.ALADIN_STORM_FLASHES_KM2
        severe = np.rint(self.pixels.nearest(self.grib.field("ptype_severe", step)))
        codes = np.zeros(storm.shape, np.float32)
        codes[self.pixels.resample(self.grib.field("fog_visibility", step)) < styles.ALADIN_FOG_VISIBILITY_M] = 45
        codes[storm] = 95
        codes[(severe == styles.ALADIN_HAIL) | (storm & (severe == styles.ALADIN_GRAUPEL))] = 96
        return codes
