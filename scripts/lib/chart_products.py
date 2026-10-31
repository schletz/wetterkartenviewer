"""The chart products of render_charts.py: which fields each chart combines and how."""

from dataclasses import replace
from datetime import date
from pathlib import Path

import numpy as np

from . import chart_styles as styles
from .base_map import BaseMap
from .chart_canvas import ChartCanvas
from .constants import KELVIN, KMH_PER_MS
from .contour_style import ContourStyle
from .diagnostics import Diagnostics
from .forecast_grib import ForecastGrib
from .height_profile import HeightProfile
from .model_surface import ModelSurface
from .pixel_grid import PixelGrid
from .projection import EUROPE
from .t850_climate import T850Climate

CHANGE_HOURS = 24
# weather_summary: factor from the GRIB cloud cover to %.
TCC_PERCENT = 100.0


class ChartProducts:
    """Draws the products of one forecast file for the chart window of ``base_map``.

    Products keyed by step (one chart per valid time) are listed in
    ``STEP``, daily ones in ``DAY`` and the static one in ``STATIC``.
    Every product can be drawn for every window; ``DEFAULTS`` is the
    selection per window. The central Europe window (23 W to 37 E) shows
    fronts about two days ahead and the boundary layer in detail; the
    Europe window adds the upstream patterns and the large scale flow.
    Locations outside central Europe (e.g. north of 57 N) take every
    product on the Europe window. Products in ``CLIMATE`` need the
    climatology.
    """

    STEP = ("z500_t850", "z700_t700", "z850_rh700", "thickness_mslp", "t850_mslp", "t850_anomaly", "rh700_wind700", "vt_rh700",
            "dt850_24h", "t2m_wind1000", "wind10m", "inversion", "mountain_2000", "freezing_level", "snow_line", "weather_summary")
    DAY = {"tmax": "max", "tmin": "min"}
    STATIC = ("orography",)
    ALL = (*STEP, *DAY, *STATIC)
    CLIMATE = ("t850_anomaly",)
    # Model name in the legend strip; weather_summary: precipitation interval in h;
    # valid hours (UTC) of the charts in a contact sheet: one per day over 10 days.
    MODEL = "ECMWF IFS"
    PRECIP_HOURS = 6
    SHEET_HOURS = (12,)
    DEFAULTS = {
        "opencharts_europe": ("z500_t850", "z700_t700", "z850_rh700", "thickness_mslp", "dt850_24h"),
        # T850 instead of the thickness under the isobars: the thickness is smooth at
        # this scale, while T850 shows the warm tongue of foehn in the lee of the Alps.
        "opencharts_central_europe": ("t850_mslp", "t850_anomaly", "rh700_wind700", "vt_rh700", "t2m_wind1000",
                                      "wind10m", "inversion", "mountain_2000", "freezing_level", "snow_line", "tmax", "tmin",
                                      "orography", "weather_summary"),
    }

    def __init__(self, grib: ForecastGrib, surface: ModelSurface, base_map: BaseMap, pixels: PixelGrid,
                 climate: T850Climate | None = None, climate_pixels: PixelGrid | None = None):
        """Wire the sources of one chart window.

        Args:
            grib: the forecast file.
            surface: its static surface fields.
            base_map: outlines of the chart window.
            pixels: mapping of the forecast grid onto the pixels of that window.
            climate: T850 climatology, needed only for t850_anomaly.
            climate_pixels: mapping of the climatology grid onto the same pixels.
        """
        self.grib, self.surface, self.base_map, self.pixels = grib, surface, base_map, pixels
        self.climate, self.climate_pixels = climate, climate_pixels
        self.projection = base_map.projection
        # Zoomed windows get denser isobars and printed values.
        self.detail = self.projection.km_per_px(50.0) < EUROPE.km_per_px(50.0)
        self.height = self.pixels.resample(surface.height)
        self.land = self.pixels.resample(surface.land) >= 0.5

    # Keys and files

    def keys(self, product: str) -> list:
        """Steps, days or [None] for which a product can be drawn."""
        if product in self.DAY:
            return self.extreme_days(self.DAY[product])
        if product in self.STATIC:
            return [None]
        if product == "weather_summary":
            # Precipitation needs an interval; files without the weather fields give no charts.
            return [s for s in self.grib.steps("tp") if s > 0]
        steps = self.grib.steps("t")
        if product == "dt850_24h":
            return [s for s in steps if s - CHANGE_HOURS in steps]
        return steps

    def path(self, out_dir: Path, product: str, key) -> Path:
        """File of one chart: valid time, day or the product name for static charts."""
        if product in self.DAY:
            return out_dir / product / f"{key:%Y%m%d}.webp"
        if product in self.STATIC:
            return out_dir / f"{product}.webp"
        return out_dir / product / f"{self.grib.valid_time(key):%Y%m%d%H}.webp"

    def draw(self, product: str, key) -> ChartCanvas:
        """Canvas of one chart with every layer."""
        if product in self.DAY:
            return self.daily_extreme(self.DAY[product], key)
        return getattr(self, product)() if product in self.STATIC else getattr(self, product)(key)

    # Helpers

    def field(self, name: str, step: int, level: int | None = None, *, smooth_km: float = 0.0,
              offset: float = 0.0, factor: float = 1.0) -> np.ndarray:
        """A field on the chart pixels, converted as (value + offset) * factor."""
        return self.pixels.resample((self.grib.field(name, step, level) + offset) * factor, smooth_km)

    def wind_arrows(self, step: int, level: int, hide: np.ndarray | None = None) -> tuple:
        """Pixel components (dx, dy) of the wind on a level; ``hide`` pixels get no arrow."""
        dx, dy = self.pixels.wind_vectors(self.field("u", step, level), self.field("v", step, level))
        if hide is not None:
            dx, dy = np.where(hide, np.nan, dx), np.where(hide, np.nan, dy)
        return dx, dy

    def profile(self, step: int) -> HeightProfile:
        """Pressure level profile of one step."""
        return HeightProfile(self.grib, step)

    def diagnostics(self, step: int) -> Diagnostics:
        """Free atmosphere diagnostics of one step."""
        return Diagnostics(self.profile(step), self.surface)

    def speed(self, step: int, level: int, smooth_km: float) -> np.ndarray:
        """Wind speed on a level, smoothed on the model grid."""
        speed = np.hypot(self.grib.field("u", step, level), self.grib.field("v", step, level))
        return self.pixels.resample(speed, smooth_km)

    def step_label(self, step: int) -> str:
        """Valid time, step and run for the legend strip."""
        valid = self.grib.valid_time(step)
        return f"Valid {valid:%a %d.%m.%Y %H} UTC   (T+{step:03d} h, {self._run})"

    @property
    def _run(self) -> str:
        return f"{self.MODEL} run {self.grib.base_time:%d.%m.%Y %H} UTC"

    def z500_lines(self, canvas: ChartCanvas, step: int) -> None:
        canvas.contours(self.field("gh", step, 500, smooth_km=styles.Z500.smooth_km, factor=0.1), styles.Z500,
                        "black lines: Z500 every 4 dam, bold 528/552/576")

    def print_values(self, canvas: ChartCanvas, values: np.ndarray, fmt: str, label: str,
                     where: np.ndarray | None = None) -> None:
        """Numbers (default: over land) on zoomed windows; on the Europe window they would hide the patterns."""
        if self.detail:
            canvas.values(values, styles.VALUE_SPACING_PX, self.land if where is None else where, fmt, label)

    def frost_line(self, canvas: ChartCanvas, celsius: np.ndarray) -> None:
        """Bold 0 deg C line of a 2 m temperature field on the model grid."""
        canvas.isolines(self.pixels.resample(celsius, smooth_km=styles.FROST_SMOOTH_KM), (styles.FROST_LINE,),
                        "#0000b0", "blue line: 0 °C")

    # Products keyed by step

    def z500_t850(self, step: int) -> ChartCanvas:
        canvas = ChartCanvas(self.base_map, "Z500 (dam, black lines) + T850 (°C, colours)", self.step_label(step))
        canvas.shade(self.field("t", step, 850, offset=-KELVIN), styles.T850)
        canvas.outlines()
        canvas.contours(self.field("t", step, 850, smooth_km=styles.ISOTHERM_850.smooth_km, offset=-KELVIN),
                        styles.ISOTHERM_850, "brown lines: isotherms 850 hPa every 4 K", boxed=False)
        self.z500_lines(canvas, step)
        canvas.extrema(self.field("gh", step, 500, smooth_km=60, factor=0.1), low_window_px=121,
                       high_window_px=181, min_depth=2)
        return canvas

    def z700_t700(self, step: int) -> ChartCanvas:
        canvas = ChartCanvas(self.base_map, "Z700 (dam, black lines) + T700 (°C, colours)", self.step_label(step))
        canvas.shade(self.field("t", step, 700, offset=-KELVIN), styles.T700)
        canvas.outlines()
        canvas.contours(self.field("t", step, 700, smooth_km=styles.ISOTHERM_850.smooth_km, offset=-KELVIN),
                        styles.ISOTHERM_850, "brown lines: isotherms 700 hPa every 4 K", boxed=False)
        canvas.contours(self.field("gh", step, 700, smooth_km=styles.Z700.smooth_km, factor=0.1), styles.Z700,
                        "black lines: Z700 every 5 dam, bold 270/290/310")
        canvas.extrema(self.field("gh", step, 700, smooth_km=60, factor=0.1), low_window_px=121,
                       high_window_px=181, min_depth=2)
        return canvas

    def z850_rh700(self, step: int) -> ChartCanvas:
        """Moisture at the level of the frontal clouds under the flow just above the boundary layer."""
        canvas = ChartCanvas(self.base_map, "Z850 (dam, black lines) + 700 hPa relative humidity (%, colours)",
                             self.step_label(step))
        canvas.background(styles.LAND_RGB, styles.SEA_RGB)
        canvas.shade(self.field("r", step, 700), styles.RH700)
        canvas.outlines()
        # Inside this line the 850 hPa level lies below the model ground and Z850 is extrapolated.
        canvas.isolines(self.pixels.resample(self.surface.height, smooth_km=10),
                        (styles.ABOVE_850HPA_M,), "#606060",
                        f"grey dashed: model ground {styles.ABOVE_850HPA_M:g} m (Z850 extrapolated inside)",
                        dashed=True, labelled=False)
        canvas.contours(self.field("gh", step, 850, smooth_km=styles.Z850.smooth_km, factor=0.1), styles.Z850,
                        "black lines: Z850 every 4 dam, bold every 12 dam (140/152/164)")
        canvas.extrema(self.field("gh", step, 850, smooth_km=60, factor=0.1), low_window_px=121,
                       high_window_px=181, min_depth=2)
        return canvas

    def thickness_mslp(self, step: int) -> ChartCanvas:
        canvas = ChartCanvas(self.base_map, "MSLP (hPa, black lines) + 1000-500 hPa thickness (dam, colours)",
                             self.step_label(step))
        canvas.shade(self.field("thick", step, factor=0.1), styles.THICKNESS)
        canvas.outlines()
        self.isobars(canvas, step)
        return canvas

    def t850_mslp(self, step: int) -> ChartCanvas:
        """T850 under the isobars: foehn shows as a pressure jump across the Alps and a warm tongue in the lee."""
        canvas = ChartCanvas(self.base_map, "MSLP (hPa, black lines) + T850 (°C, colours)", self.step_label(step))
        t850 = self.field("t", step, 850, offset=-KELVIN)
        canvas.shade(t850, styles.T850)
        canvas.outlines()
        # Inside this line the 850 hPa level lies below the model ground and T850 is extrapolated.
        canvas.isolines(self.pixels.resample(self.surface.height, smooth_km=10),
                        (styles.ABOVE_850HPA_M,), "#606060",
                        f"grey dashed: model ground {styles.ABOVE_850HPA_M:g} m (T850 extrapolated inside)",
                        dashed=True, labelled=False)
        self.isobars(canvas, step)
        self.print_values(canvas, t850, "{:.0f}", "numbers: T850 in °C", where=np.ones_like(self.land))
        return canvas

    def isobars(self, canvas: ChartCanvas, step: int, isobars: ContourStyle | None = None) -> None:
        """MSLP contours (default every 2 hPa on zoomed windows, else 5 hPa) with low and high centres."""
        isobars = isobars or (styles.MSLP_DETAIL if self.detail else styles.MSLP)
        bold = isobars.interval * isobars.bold_every
        canvas.contours(self.field("msl", step, smooth_km=isobars.smooth_km, factor=0.01), isobars,
                        f"black lines: isobars every {isobars.interval:g} hPa, bold every {bold:g} hPa")
        canvas.extrema(self.field("msl", step, smooth_km=60, factor=0.01), low_window_px=81, high_window_px=161,
                       min_depth=2)

    def t850_anomaly(self, step: int) -> ChartCanvas:
        """T850 against the climatology of the same calendar day and time of day, in standard deviations.

        Colours give how unusual the air mass is for the season, the printed
        numbers the anomaly in K; Z500 shows the flow that brings it.
        """
        if self.climate is None:
            raise ValueError("t850_anomaly needs a T850Climate")
        canvas = ChartCanvas(self.base_map, f"T850 anomaly (σ vs. {self.climate.period}, colours) + Z500 (dam)",
                             self.step_label(step))
        mean, std = self.climate.field(self.grib.valid_time(step))
        anomaly = self.field("t", step, 850, offset=-KELVIN) - self.climate_pixels.resample(mean)
        high = self.height > styles.ABOVE_850HPA_M
        canvas.shade(anomaly / self.climate_pixels.resample(std), styles.T850_ANOMALY, mask=high,
                     mask_colour=styles.MASK_RGB, mask_label=f"grey: model ground above {styles.ABOVE_850HPA_M:g} m")
        canvas.outlines()
        self.z500_lines(canvas, step)
        self.print_values(canvas, anomaly, "{:+.0f}", f"numbers: T850 − mean {self.climate.period} in K",
                          where=~high)
        return canvas

    def rh700_wind700(self, step: int) -> ChartCanvas:
        canvas = ChartCanvas(self.base_map, "700 hPa relative humidity (%, colours), wind (arrows), vertical motion",
                             self.step_label(step))
        canvas.background(styles.LAND_RGB, styles.SEA_RGB)
        canvas.shade(self.field("r", step, 700), styles.RH700)
        canvas.outlines()
        w = self.field("w", step, 700, smooth_km=styles.W700_SMOOTH_KM)
        canvas.isolines(w, styles.ASCENT_LINES, "#d00000", "red lines: ascent ω700 −0.2 / −0.6 Pa/s")
        canvas.isolines(w, styles.SUBSIDENCE_LINES, "#6000c0", "purple dashed: subsidence ω700 +0.2 Pa/s",
                        dashed=True)
        canvas.arrows(*self.wind_arrows(step, 700), spacing=30, px_per_ms=1.2, reference_ms=20,
                      label="700 hPa wind")
        return canvas

    def vt_rh700(self, step: int) -> ChartCanvas:
        canvas = ChartCanvas(self.base_map, "Vertical totals T850 − T500 (K, colours) + RH700 (%, green lines)",
                             self.step_label(step))
        totals = self.field("t", step, 850) - self.field("t", step, 500)
        canvas.shade(totals, styles.VERTICAL_TOTALS, mask=self.height > styles.ABOVE_850HPA_M,
                     mask_colour=styles.MASK_RGB, mask_label=f"grey: model ground above {styles.ABOVE_850HPA_M:g} m")
        canvas.outlines()
        canvas.isolines(self.field("r", step, 700, smooth_km=20), styles.RH700_LINES, "#008000",
                        "green lines: RH700 70 / 90 %")
        return canvas

    def dt850_24h(self, step: int) -> ChartCanvas:
        canvas = ChartCanvas(self.base_map, f"T850 change over {CHANGE_HOURS} h (K, colours) + Z500 (dam)",
                             self.step_label(step))
        change = self.field("t", step, 850) - self.field("t", step - CHANGE_HOURS, 850)
        canvas.shade(change, styles.DT850)
        canvas.outlines()
        self.z500_lines(canvas, step)
        return canvas

    def t2m_wind1000(self, step: int) -> ChartCanvas:
        canvas = ChartCanvas(self.base_map, "2 m temperature (°C, colours) + 1000 hPa wind (arrows)",
                             self.step_label(step))
        temperature = self.grib.field("2t", step) - KELVIN
        pixels = self.pixels.resample(temperature)
        canvas.shade(pixels, styles.T2M)
        canvas.outlines()
        self.frost_line(canvas, temperature)
        self.print_values(canvas, pixels, "{:.0f}", "numbers: T2m in °C at the model height")
        hide = self.height > styles.ABOVE_1000HPA_M
        canvas.arrows(*self.wind_arrows(step, 1000, hide), spacing=30, px_per_ms=2.5, reference_ms=10,
                      label=f"1000 hPa wind (none above {styles.ABOVE_1000HPA_M:g} m)")
        return canvas

    def wind10m(self, step: int) -> ChartCanvas:
        """The ground wind of the model, as a chart for people.

        Unlike the pressure levels, 10 m is the same height above every
        model ground, and the model's surface friction turns the wind across
        the isobars towards low pressure, which the streamlines show. Valleys
        narrower than the 9 km grid channel the real wind differently.
        """
        canvas = ChartCanvas(self.base_map, "10 m wind speed (km/h, colours), streamlines, MSLP (hPa)",
                             self.step_label(step))
        u, v = self.grib.field("10u", step), self.grib.field("10v", step)
        canvas.shade(self.pixels.resample(np.hypot(u, v) * KMH_PER_MS), styles.WIND10M)
        canvas.outlines()
        smooth = styles.STREAMLINE_SMOOTH_KM
        dx, dy = self.pixels.wind_vectors(self.pixels.resample(u, smooth), self.pixels.resample(v, smooth))
        canvas.streamlines(dx, dy, styles.STREAMLINE_DENSITY, "grey lines: streamlines of the 10 m wind")
        self.isobars(canvas, step, styles.MSLP_SUMMARY)
        return canvas

    def inversion(self, step: int) -> ChartCanvas:
        """Inversion and moist boundary layer from pressure levels only; T2m is not used (see diagnostics.py)."""
        canvas = ChartCanvas(self.base_map, "Inversion 1000–850 hPa (K, colours), moist layer (hatched), 925 hPa wind",
                             self.step_label(step))
        diagnostics = self.diagnostics(step)
        canvas.shade(self.pixels.resample(diagnostics.inversion()), styles.INVERSION,
                     mask=self.height > styles.HIGH_GROUND_M, mask_colour=styles.MASK_RGB,
                     mask_label=f"grey: model ground above {styles.HIGH_GROUND_M:g} m")
        canvas.outlines()
        canvas.hatch(self.pixels.resample(diagnostics.moist_boundary_layer(), smooth_km=10), styles.MOIST_LAYER_RH,
                     "#303030", f"hatched: RH 925/1000 hPa ≥ {styles.MOIST_LAYER_RH:g} % (fog, low stratus)")
        canvas.isolines(self.speed(step, 925, smooth_km=styles.WIND925_SMOOTH_KM), (styles.WIND925_CALM,),
                        "#0000b0", f"blue line: 925 hPa wind {styles.WIND925_CALM:g} m/s (weaker: little mixing)")
        return canvas

    def mountain_2000(self, step: int) -> ChartCanvas:
        """Mountain weather: temperature, wind and summits in cloud at a fixed height."""
        height = styles.MOUNTAIN_HEIGHT_M
        canvas = ChartCanvas(self.base_map, f"{height:g} m: temperature (°C), wind, in cloud (hatched)",
                             self.step_label(step))
        profile = self.profile(step)
        temperature = self.pixels.resample(profile.at_height("t", height) - KELVIN)
        below_ground = self.height > height
        canvas.shade(temperature, styles.MOUNTAIN_T, mask=below_ground, mask_colour=styles.MASK_RGB,
                     mask_label=f"grey: model ground above {height:g} m")
        canvas.outlines()
        cloud, label = self.summit_cloud(profile, step, height)
        canvas.hatch(self.pixels.resample(cloud, smooth_km=10), styles.SUMMIT_CLOUD_RH, "#303030", label)
        dx, dy = self.pixels.wind_vectors(self.pixels.resample(profile.at_height("u", height)),
                                          self.pixels.resample(profile.at_height("v", height)))
        canvas.arrows(np.where(below_ground, np.nan, dx), np.where(below_ground, np.nan, dy), spacing=30,
                      px_per_ms=1.5, reference_ms=20, label=f"wind at {height:g} m")
        self.print_values(canvas, temperature, "{:.0f}", f"numbers: temperature at {height:g} m in °C",
                          where=self.land & ~below_ground)
        return canvas

    def summit_cloud(self, profile: HeightProfile, step: int, height: float) -> tuple[np.ndarray, str]:
        """Relative humidity at a height on the model grid, hatched from SUMMIT_CLOUD_RH, and its legend note."""
        return profile.at_height("r", height), f"hatched: RH ≥ {styles.SUMMIT_CLOUD_RH:g} % (in cloud at {height:g} m)"

    def freezing_level(self, step: int) -> ChartCanvas:
        canvas = ChartCanvas(self.base_map, "Freezing level (m, colours)", self.step_label(step))
        level = self.pixels.resample(self.diagnostics(step).freezing_level())
        canvas.shade(level, styles.FREEZING_LEVEL)
        canvas.outlines()
        # Rounded to 100 m: the interpolation between pressure levels is not more precise.
        self.print_values(canvas, np.round(level, -2), "{:.0f}", "numbers: freezing level in m (frozen: ground)",
                          where=self.land & ~np.isnan(level))
        return canvas

    def snow_line(self, step: int) -> ChartCanvas:
        """Snow line where the upper air signals precipitation; elsewhere grey."""
        canvas = ChartCanvas(self.base_map, "Snow line (m, colours) where precipitation is likely",
                             self.step_label(step))
        diagnostics = self.diagnostics(step)
        line = self.pixels.resample(diagnostics.snow_line())
        dry = self.pixels.resample(diagnostics.precipitation_signal().astype(np.float32)) < 0.5
        canvas.shade(line, styles.SNOW_LINE, mask=dry, mask_colour=(235, 235, 235),
                     mask_label=f"grey: no precipitation signal (RH850/700 < {styles.PRECIP_RH:g} % or no ascent)")
        canvas.outlines()
        self.print_values(canvas, np.round(line, -2), "{:.0f}",
                          f"numbers: snow line in m (freezing level − {styles.SNOW_LINE_BELOW_FREEZING_M:g} m)",
                          where=self.land & ~dry & ~np.isnan(line))
        return canvas

    def weather_summary(self, step: int) -> ChartCanvas:
        """Clouds, precipitation and its type under the isobars, as a chart for people.

        It shows the near-surface weather of the model as it comes
        (WEATHER_PARAMS), which the analysis deliberately leaves out. The
        precipitation is summed over the last PRECIP_HOURS (6 h, 3 h at T+3);
        its type is the one at the valid time, so a shower that ended earlier
        shows colour but no symbol. The fields come from cloud_cover,
        precipitation and precipitation_type, which other models override.
        """
        hours = min(self.PRECIP_HOURS, step)
        canvas = ChartCanvas(self.base_map, "MSLP (hPa), total cloud cover, precipitation and its type",
                             self.step_label(step))
        canvas.background(styles.SUMMARY_LAND_RGB, styles.SUMMARY_SEA_RGB)
        canvas.shade(self.cloud_cover(step), styles.CLOUD_COVER, bar=styles.CLOUD_BAR)
        precip = self.precipitation(step, hours)
        canvas.shade(precip, replace(styles.PRECIPITATION, title=f"Precipitation over the last {hours} h (mm)"),
                     bar=styles.PRECIP_BAR)
        canvas.outlines()
        self.isobars(canvas, step, styles.MSLP_SUMMARY)
        # ptype is set even for traces; symbols outside the shaded precipitation would only confuse.
        wet = precip >= styles.PRECIPITATION.transparent_below
        ptype = self.precipitation_type(step)
        for codes, style in styles.PRECIP_TYPES:
            canvas.symbols(np.isin(ptype, codes) & wet, styles.PRECIP_TYPE_SPACING_PX, style,
                           "(type at the valid time; rain without symbol)")
        return canvas

    def cloud_cover(self, step: int) -> np.ndarray:
        """Total cloud cover in % on the chart pixels."""
        return self.field("tcc", step, factor=TCC_PERCENT)

    def precipitation(self, step: int, hours: int) -> np.ndarray:
        """Precipitation in mm over the ``hours`` before ``step`` on the chart pixels."""
        # tp accumulates from T+0 in m; packing noise can make the difference slightly negative.
        precip = np.maximum(self.grib.field("tp", step) - self.grib.field("tp", step - hours), 0) * 1000
        return self.pixels.resample(precip)

    def precipitation_type(self, step: int) -> np.ndarray:
        """ECMWF ptype code at the valid time on the chart pixels."""
        return self.pixels.nearest(self.grib.field("ptype", step))

    # Daily and static products

    def extreme_days(self, kind: str) -> list[date]:
        """Days with a complete daily maximum (``kind="max"``) or minimum ("min")."""
        return self.grib.extreme_days(kind)

    def daily_extreme_field(self, kind: str, day: date) -> np.ndarray:
        """Daily 2 m maximum or minimum in K on the model grid."""
        return self.grib.daily_extreme(kind, day)

    def daily_extreme(self, kind: str, day: date) -> ChartCanvas:
        window, name = ("06-18", "maximum") if kind == "max" else ("18-06", "minimum")
        canvas = ChartCanvas(self.base_map, f"Daily 2 m {name} temperature (°C, colours)",
                             f"{day:%a %d.%m.%Y}, {window} UTC   ({self._run})")
        values = self.daily_extreme_field(kind, day) - KELVIN
        pixels = self.pixels.resample(values)
        canvas.shade(pixels, styles.T2M)
        canvas.outlines()
        self.frost_line(canvas, values)
        self.print_values(canvas, pixels, "{:.0f}", f"numbers: T{kind} in °C at the model height")
        return canvas

    def orography(self) -> ChartCanvas:
        """Model orography: how fine the model resolves valleys and summits; rough terrain hatched if known."""
        rough = self.surface.sdor is not None
        canvas = ChartCanvas(self.base_map, "Model orography (m, colours)"
                             + (" + rough sub-grid terrain (hatched)" if rough else ""), f"Static field   ({self._run})")
        sea = self.pixels.resample(self.surface.land) < 0.5
        canvas.shade(self.height, styles.OROGRAPHY, mask=sea, mask_colour=styles.OROGRAPHY_SEA_RGB,
                     mask_label="light blue: sea (model land-sea mask)")
        canvas.outlines()
        if rough:
            canvas.hatch(self.pixels.resample(self.surface.sdor), styles.ROUGH_TERRAIN_SDOR, "black",
                         f"hatched: sub-grid std. dev. ≥ {styles.ROUGH_TERRAIN_SDOR:g} m (valleys/summits differ)")
        self.print_values(canvas, self.height, "{:.0f}", "numbers: model height in m")
        return canvas
