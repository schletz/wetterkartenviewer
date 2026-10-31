"""The chart products of ICON-D2: products of ChartProducts, drawn from the raw model cells."""

import numpy as np

from . import chart_styles as styles
from .chart_canvas import ChartCanvas
from .chart_products import ChartProducts
from .constants import GRAVITY, KMH_PER_MS
from .height_profile import HeightProfile
from .icon_extremes import IconExtremes


class IconProducts(ChartProducts):
    """Draws the products of an ICON-D2 file (download_icon_d2.py) for a chart window.

    The fields carry the names of the ECMWF file (constants.ICON_NAMES), so
    the drawing of ChartProducts applies; overridden is only what differs:
    the cloud cover is in % already, the precipitation in kg/m2 (= mm) and
    summed over 1 h (the model writes every hour), its type comes from ww,
    the profile heights from the geopotential z of 850 and 700 hPa, the
    daily extremes from hourly ones. weather_summary adds what ECMWF has no
    field for: thunderstorms, hail, fog and storm gusts. orography shows how
    finely the model resolves valleys and summits (no hatching: ICON has no
    sdor). Every chart greys what lies outside the model domain.

    It is wired like ChartProducts, with an IconSurface as surface and a
    TriangleGrid as pixel mapping.
    """

    STEP = ("t2m_wind1000", "wind10m", "mountain_2000", "weather_summary")
    DAY = {"tmax": "max", "tmin": "min"}
    STATIC = ("orography",)
    ALL = (*STEP, *DAY, *STATIC)
    CLIMATE = ()
    MODEL = "ICON-D2"
    PRECIP_HOURS = 1
    # Every 6 h, so the sheet keeps 8 readable tiles over 48 h, at hours that catch the daily cycle:
    # 15 UTC the afternoon thunderstorms, 03 and 09 UTC fog forming and clearing, 21 UTC the evening.
    SHEET_HOURS = (3, 9, 15, 21)
    DEFAULTS = {"icon-d2": ALL}

    def draw(self, product: str, key) -> ChartCanvas:
        canvas = super().draw(product, key)
        canvas.uncovered(self.pixels.covered, styles.OUTSIDE_RGB, "grey: outside the ICON-D2 domain")
        return canvas

    def profile(self, step: int) -> HeightProfile:
        return HeightProfile(self.grib, step, "z", 1.0 / GRAVITY)

    def summit_cloud(self, profile: HeightProfile, step: int, height: float) -> tuple[np.ndarray, float, str]:
        """Cells in cloud at the height (100) or not (0), hatched where at least half the area around is in cloud.

        A cell is in cloud where the model's cloud base (lowest layer above
        50 % cover, m above sea level) lies at or below the height, and the
        humidity there, interpolated over the 1500 m between 850 and 700 hPa,
        still reaches ICON_SUMMIT_CLOUD_RH, i.e. the height lies below the top
        of the moist layer. ICON's layer covers (clcl/clcm) do not tell: their
        border at 800 hPa lies near 2000 m. The cloud of the 2 km model is
        patchy; smoothed as a 0/1 field it gives the share of the area in
        cloud, whereas RH set to 0 outside and smoothed would need almost all
        cells in cloud to reach a humidity threshold.
        """
        inside = ((self.grib.field("ceiling", step) <= height)
                  & (profile.at_height("r", height) >= styles.ICON_SUMMIT_CLOUD_RH))
        return (np.where(inside, 100.0, 0.0), styles.SUMMIT_CLOUD_AREA,
                f"hatched: ≥ {styles.SUMMIT_CLOUD_AREA:g} % in cloud at {height:g} m "
                f"(base below, RH ≥ {styles.ICON_SUMMIT_CLOUD_RH:g} %)")

    def extreme_days(self, kind: str) -> list:
        return IconExtremes(self.grib).days(kind)

    def daily_extreme_field(self, kind: str, day) -> np.ndarray:
        return IconExtremes(self.grib).field(kind, day)

    def weather_summary(self, step: int) -> ChartCanvas:
        """The weather summary of ECMWF plus thunderstorms, hail, fog and storm gusts."""
        canvas = super().weather_summary(step)
        ww = self.pixels.nearest(self.grib.field("ww", step))
        for codes, style in styles.WW_SYMBOLS:
            canvas.symbols(np.isin(ww, codes), styles.WW_SYMBOL_SPACING_PX, style)
        gust = self.field("gust", step, factor=KMH_PER_MS)
        canvas.values(gust, styles.GUST_SPACING_PX, gust >= styles.STORM_GUST_KMH, "{:.0f}",
                      f"numbers: gusts ≥ {styles.STORM_GUST_KMH:g} km/h in the last hour (km/h)")
        return canvas

    def cloud_cover(self, step: int) -> np.ndarray:
        # Outside the domain nothing is shaded; draw paints it grey on top.
        return np.nan_to_num(self.field("tcc", step))

    def precipitation(self, step: int, hours: int) -> np.ndarray:
        # tp accumulates from T+0 in kg/m2 = mm; packing noise can make the difference slightly negative.
        precip = np.maximum(self.grib.field("tp", step) - self.grib.field("tp", step - hours), 0)
        return np.nan_to_num(self.pixels.resample(precip))

    def precipitation_type(self, step: int) -> np.ndarray:
        """ww at the valid time translated to the ECMWF ptype codes of the legend; 0 for everything else."""
        ww = self.pixels.nearest(self.grib.field("ww", step))
        ptype = np.zeros_like(ww)
        for code, ww_codes in styles.WW_PTYPE.items():
            ptype[np.isin(ww, ww_codes)] = code
        return ptype
