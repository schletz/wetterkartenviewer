"""Fixed colour scales and contour settings of the charts drawn by render_charts.py.

The T850, T700 and thickness scales are copied from the ECMWF open charts
legends (medium-z500-t850, medium-t-z, medium-thickness-mslp, medium-uv-rh), so the
self-rendered charts read like the originals. Every scale is a list of
bands (lower bound, upper bound, RGB); values outside the outermost
bands get the colour of the nearest band.
"""

from matplotlib.path import Path

from .colour_scale import ColourScale
from .contour_style import ContourStyle
from .symbol_style import SymbolStyle

# medium-z500-t850 legend, 850 hPa temperature in deg C.
T850 = ColourScale("850 hPa temperature (°C)", (
    (-80, -70, (255, 255, 255)), (-70, -60, (229, 229, 229)), (-60, -52, (204, 204, 204)),
    (-52, -48, (178, 178, 178)), (-48, -44, (173, 153, 173)), (-44, -40, (122, 102, 122)),
    (-40, -36, (71, 51, 71)), (-36, -32, (51, 0, 102)), (-32, -28, (89, 0, 127)),
    (-28, -24, (127, 0, 255)), (-24, -20, (0, 127, 255)), (-20, -16, (0, 204, 255)),
    (-16, -12, (0, 255, 255)), (-12, -8, (38, 229, 153)), (-8, -4, (102, 191, 38)),
    (-4, 0, (191, 229, 38)), (0, 4, (255, 255, 127)), (4, 8, (255, 255, 0)),
    (8, 12, (255, 217, 0)), (12, 16, (255, 176, 0)), (16, 20, (255, 114, 0)),
    (20, 24, (255, 0, 0)), (24, 28, (204, 0, 0)), (28, 32, (127, 0, 44)),
    (32, 36, (204, 61, 110)), (36, 40, (255, 0, 255)), (40, 44, (255, 127, 255)),
    (44, 48, (255, 191, 255)), (48, 52, (229, 204, 229)), (52, 56, (229, 229, 229)),
), legend_range=(-36, 36))

# medium-t-z legend at level 700, 700 hPa temperature in deg C.
T700 = ColourScale("700 hPa temperature (°C)", (
    (-72, -68, (0, 0, 25)), (-68, -64, (25, 0, 51)), (-64, -60, (51, 0, 102)),
    (-60, -56, (89, 0, 127)), (-56, -52, (107, 0, 153)), (-52, -48, (122, 17, 178)),
    (-48, -44, (127, 0, 216)), (-44, -40, (127, 0, 255)), (-40, -36, (107, 20, 255)),
    (-36, -32, (91, 40, 255)), (-32, -28, (63, 63, 255)), (-28, -24, (25, 102, 255)),
    (-24, -20, (0, 127, 255)), (-20, -16, (0, 153, 255)), (-16, -12, (0, 178, 255)),
    (-12, -8, (0, 204, 255)), (-8, -4, (0, 229, 255)), (-4, 0, (0, 255, 255)),
    (0, 4, (0, 255, 127)), (4, 8, (127, 255, 0)), (8, 12, (217, 255, 0)),
    (12, 16, (255, 255, 0)), (16, 20, (255, 245, 0)), (20, 24, (255, 217, 0)),
    (24, 28, (255, 176, 0)), (28, 32, (255, 127, 0)), (32, 36, (255, 78, 0)),
    (36, 40, (255, 37, 0)), (40, 44, (255, 9, 0)), (44, 48, (255, 0, 0)),
    (48, 52, (255, 0, 255)),
), legend_range=(-44, 28))

# T850 anomaly in standard deviations of the climatology of the same calendar
# day and time of day: from |z| = 1 a value stands out, from 2 it is unusual.
T850_ANOMALY = ColourScale("T850 anomaly (standard deviations σ)", (
    (-20, -3, (0, 40, 140)), (-3, -2, (40, 100, 220)), (-2, -1, (150, 190, 245)), (-1, 1, (255, 255, 255)),
    (1, 2, (255, 190, 170)), (2, 3, (235, 90, 60)), (3, 20, (160, 0, 0)),
), legend_range=(-4, 4))

# The same palette for 2 m temperatures, so one colour means one temperature on every chart.
T2M = ColourScale("2 m temperature (°C)", T850.bands, legend_range=(-36, 44))

# medium-thickness-mslp legend, 1000-500 hPa thickness in dam.
THICKNESS = ColourScale("1000-500 hPa thickness (dam)", (
    (488, 504, (2, 2, 114)), (504, 508, (12, 12, 140)), (508, 512, (38, 63, 191)),
    (512, 516, (51, 76, 229)), (516, 520, (94, 127, 255)), (520, 524, (127, 178, 255)),
    (524, 528, (127, 229, 255)), (528, 532, (76, 173, 102)), (532, 536, (109, 196, 51)),
    (536, 540, (153, 219, 25)), (540, 544, (191, 249, 0)), (544, 548, (255, 255, 0)),
    (548, 552, (255, 226, 0)), (552, 556, (255, 198, 0)), (556, 560, (255, 170, 0)),
    (560, 564, (255, 140, 0)), (564, 568, (255, 89, 0)), (568, 572, (255, 58, 0)),
    (572, 576, (255, 0, 51)), (576, 580, (255, 0, 135)), (580, 584, (255, 0, 214)),
    (584, 588, (255, 0, 242)), (588, 592, (234, 0, 255)), (592, 596, (211, 0, 255)),
    (596, 604, (191, 0, 255)),
))

# medium-uv-rh legend, relative humidity in %; drier air stays unshaded.
RH700 = ColourScale("700 hPa relative humidity (%)", (
    (65, 80, (37, 255, 0)), (80, 95, (0, 255, 236)), (95, 101, (0, 0, 255)),
), transparent_below=65)

# Largest temperature increase across 1000-925 or 925-850 hPa in K, free
# atmosphere only (see diagnostics.py). Each layer is about 650 m deep:
# well mixed air gives about -6 K, the standard atmosphere -4 K, values
# above 0 mean an inversion.
INVERSION = ColourScale("ΔT across 1000–925 or 925–850 hPa (K): > 0 inversion", (
    (-40, -6, (90, 140, 230)), (-6, -4, (170, 200, 245)), (-4, -2, (215, 228, 250)),
    (-2, 0, (245, 245, 245)), (0, 2, (255, 225, 130)), (2, 4, (255, 170, 60)),
    (4, 6, (240, 90, 30)), (6, 40, (170, 0, 60)),
), legend_range=(-8, 8))

# 24 h change of T850 in K: cold advection blue, warm advection red; the
# white band absorbs the noise of a few kelvin.
DT850 = ColourScale("T850 change over 24 h (K)", (
    (-40, -10, (0, 40, 160)), (-10, -6, (40, 110, 230)), (-6, -2, (160, 200, 250)),
    (-2, 2, (255, 255, 255)), (2, 6, (255, 190, 170)), (6, 10, (240, 90, 60)),
    (10, 40, (170, 0, 0)),
), legend_range=(-14, 14))

# Vertical totals T850 - T500 in K, the lapse rate between 1.5 and 5.5 km:
# from about 28 K showers and thunderstorms are possible if there is moisture.
VERTICAL_TOTALS = ColourScale("Vertical totals T850 − T500 (K): ≥ 28 showers/thunder possible", (
    (-20, 22, (255, 255, 255)), (22, 24, (230, 230, 230)), (24, 26, (200, 220, 240)),
    (26, 28, (255, 245, 160)), (28, 30, (255, 190, 80)), (30, 32, (250, 110, 40)),
    (32, 34, (210, 20, 20)), (34, 60, (140, 0, 110)),
), legend_range=(20, 36))

# Freezing level in m; 300 m steps where snow line and ski slopes are decided.
FREEZING_LEVEL = ColourScale("Freezing level (m)", (
    (-500, 300, (120, 60, 160)), (300, 600, (60, 80, 200)), (600, 900, (40, 130, 230)),
    (900, 1200, (80, 190, 240)), (1200, 1500, (130, 220, 200)), (1500, 1800, (170, 230, 120)),
    (1800, 2100, (230, 240, 110)), (2100, 2500, (255, 210, 80)), (2500, 3000, (255, 150, 50)),
    (3000, 3500, (240, 80, 40)), (3500, 4500, (200, 20, 40)), (4500, 9000, (130, 0, 60)),
), legend_range=(0, 5000))
SNOW_LINE = ColourScale("Snow line (m)", FREEZING_LEVEL.bands, legend_range=(0, 5000))

# Height of the model orography in m. Steps follow the thresholds of the
# analysis: lowland rules up to ~300 m, 925 hPa near 700 m, 850 hPa near 1300 m.
OROGRAPHY = ColourScale("Model orography (m)", (
    (-500, 1, (200, 225, 255)), (1, 200, (150, 200, 120)), (200, 300, (185, 215, 130)),
    (300, 500, (225, 225, 150)), (500, 700, (225, 200, 130)), (700, 1000, (205, 165, 105)),
    (1000, 1300, (180, 130, 85)), (1300, 1600, (150, 100, 70)), (1600, 2000, (130, 110, 110)),
    (2000, 2500, (170, 160, 160)), (2500, 6000, (225, 225, 225)),
), legend_range=(-500, 3000))
# Sub-grid standard deviation of the orography (m) from which the real
# height of a valley or summit differs from the model height by several 100 m.
ROUGH_TERRAIN_SDOR = 200.0
# Model heights (m) above which the values of a level are extrapolated or no lowland values:
# 2 m vs. 925/850 hPa on the inversion chart, 1000 hPa wind, 850 hPa on the vertical totals chart.
HIGH_GROUND_M = 700.0
ABOVE_1000HPA_M = 500.0
ABOVE_850HPA_M = 1300.0

# Sea on the orography chart; the spectral model orography oscillates around 0 m off the coasts.
OROGRAPHY_SEA_RGB = (200, 225, 255)

# Background colours of the RH chart, as in medium-uv-rh.
LAND_RGB = (250, 220, 170)
SEA_RGB = (255, 255, 255)
# Ground above a level, where values of that level are extrapolated by the model.
MASK_RGB = (190, 190, 190)

# weather_summary, the chart for people: legends after the ogimet surface charts
# (precipitation in mm over 6 h, cloud amount in %), which many readers know.
PRECIPITATION = ColourScale("Precipitation over the last 6 h (mm)", (
    (0.2, 1, (190, 255, 140)), (1, 2, (120, 225, 70)), (2, 5, (50, 175, 40)), (5, 10, (30, 175, 175)),
    (10, 20, (70, 150, 235)), (20, 30, (40, 80, 215)), (30, 50, (125, 90, 235)), (50, 70, (180, 80, 230)),
    (70, 100, (245, 90, 235)), (100, 1000, (230, 30, 60)),
), transparent_below=0.2)
CLOUD_COVER = ColourScale("Total cloud cover (%)", (
    (40, 50, (232, 232, 232)), (50, 60, (215, 215, 215)), (60, 70, (198, 198, 198)),
    (70, 80, (180, 180, 180)), (80, 90, (162, 162, 162)), (90, 101, (140, 140, 140)),
), transparent_below=40)
# Clear sky shows land and sea; the colours stay apart from the greys of the clouds.
SUMMARY_LAND_RGB = (245, 205, 180)
SUMMARY_SEA_RGB = (170, 200, 235)
# Precipitation type at the valid time by ECMWF ptype code; rain (1) gets no symbol.
ASTERISK = (6, 2, 0)
PRECIP_TYPES = (
    ((5,), SymbolStyle("snow", ASTERISK, 7, "white", width=1.6, halo="#1a1a60")),
    ((6, 7), SymbolStyle("wet snow, rain and snow", ASTERISK, 7, "#ff9a00", width=1.6, halo="#402000")),
    ((3, 8, 12), SymbolStyle("freezing rain or drizzle, ice pellets", "D", 4.5, "white", fill="#e00000",
                             width=0.8)),
)
PRECIP_TYPE_SPACING_PX = 14
# Two colour bars side by side in the legend strip, (left, width) in px.
PRECIP_BAR = (8, 470)
CLOUD_BAR = (500, 270)

# Pixels outside the domain of a limited area model.
OUTSIDE_RGB = (190, 190, 190)

# Weather of ICON-D2 at the valid time from ww (WMO code table 4677). Snow, mixed and freezing
# precipitation are given the ECMWF ptype codes above, so both models share symbols and legend;
# rain and drizzle (50-67 otherwise, 80-82) get none.
WW_PTYPE = {5: (70, 71, 72, 73, 74, 75, 77, 85, 86), 7: (68, 69, 83, 84), 3: (56, 57, 66, 67), 8: (79,)}
# Weather that ECMWF has no field for; ICON-D2 resolves convection and fog explicitly.
LIGHTNING = ((0.15, 1.0), (-0.45, -0.05), (-0.05, -0.05), (-0.3, -1.0), (0.5, 0.2), (0.1, 0.2), (0.45, 1.0))
# Fog as in station plots: three horizontal lines.
FOG_LINES = Path([(-1, 0.7), (1, 0.7), (-1, 0), (1, 0), (-1, -0.7), (1, -0.7)], [Path.MOVETO, Path.LINETO] * 3)
WW_SYMBOLS = (
    ((95,), SymbolStyle("thunderstorm", LIGHTNING, 11, "#600000", fill="#ffd000", width=0.6)),
    ((96,), SymbolStyle("thunderstorm with hail", "^", 7, "#600000", fill="white", width=1.2)),
    ((45, 48), SymbolStyle("fog", FOG_LINES, 8, "#fff060", width=1.4, halo="#404040")),
)
WW_SYMBOL_SPACING_PX = 20
# Gusts from Beaufort 9 (75 km/h, the "Sturmböen" of the DWD warnings) are printed in km/h.
STORM_GUST_KMH = 75.0
GUST_SPACING_PX = 60

# wind10m, a chart for people: km/h with the band limits of the Beaufort scale (force 0-1 to 12),
# so a band reads as a force; blue (calm) over green and yellow to red and purple (hurricane).
WIND10M = ColourScale("10 m wind speed (km/h), bands = Beaufort 0–1 … 12", (
    (0, 6, (215, 230, 255)), (6, 12, (160, 195, 255)), (12, 20, (95, 150, 245)), (20, 29, (60, 200, 225)),
    (29, 39, (80, 200, 120)), (39, 50, (175, 225, 60)), (50, 62, (255, 230, 0)), (62, 75, (255, 170, 0)),
    (75, 89, (255, 95, 0)), (89, 103, (215, 0, 0)), (103, 118, (200, 0, 150)), (118, 300, (120, 0, 170)),
), legend_range=(0, 140))
# The 10 m wind follows every model valley and coast; smoothing keeps the streamlines readable.
STREAMLINE_SMOOTH_KM = 15
# Streamlines per chart width (matplotlib streamplot density).
STREAMLINE_DENSITY = 3.0

# Line contours.
Z500 = ContourStyle(interval=4, bold_every=6, bold_base=552, label_every=2, smooth_km=25)
# medium-t-z: Z700 every 5 dam, bold 270/290/310.
Z700 = ContourStyle(interval=5, bold_every=4, bold_base=310, label_every=2, smooth_km=25)
# Z850 every 4 dam (about 5 hPa at the ground, as the isobars of the Europe window), bold 140/152/164.
Z850 = ContourStyle(interval=4, bold_every=3, bold_base=152, label_every=2, smooth_km=25)
MSLP = ContourStyle(interval=5, bold_every=4, bold_base=1000, label_every=2, smooth_km=40)
# Central Europe: weak gradients decide on inversions and foehn, so isobars every 2 hPa.
MSLP_DETAIL = ContourStyle(interval=2, bold_every=5, bold_base=1000, label_every=2, smooth_km=40)
# weather_summary: 4 hPa as on common surface charts; under clouds and precipitation 2 hPa would clutter.
MSLP_SUMMARY = ContourStyle(interval=4, bold_every=5, bold_base=1000, label_every=1, smooth_km=40)
# Isotherms at the band boundaries of the T850 and T700 shading, so values can be read from the labels.
ISOTHERM_850 = ContourStyle(interval=4, bold_every=0, bold_base=0, label_every=1, smooth_km=30,
                            colour="#5a3c28", width=0.5)
# 2 m temperatures follow the model orography, so isotherms fray over every
# mountain range; only the 0 deg C line (frost, snow) is drawn.
FROST_LINE = 0.0
FROST_SMOOTH_KM = 20
# Relative humidity (%) at 925 or 1000 hPa from which the boundary layer
# counts as moist: under an inversion this is the layer of fog and low stratus.
MOIST_LAYER_RH = 90.0
# 925 hPa wind speed in m/s below which an inversion is hardly mixed away.
WIND925_CALM = 5.0
WIND925_SMOOTH_KM = 50
# 700 hPa vertical velocity in Pa/s: negative is ascent (clouds, precipitation),
# positive is subsidence (drying, inversions strengthen). The field is noisy
# over mountains, hence the smoothing.
ASCENT_LINES = (-0.6, -0.2)
SUBSIDENCE_LINES = (0.2,)
W700_SMOOTH_KM = 60
# RH700 lines on the vertical totals chart: moisture available for convection.
RH700_LINES = (70.0, 90.0)
# Precipitation signal from the upper air: relative humidity (%) at 850 or
# 700 hPa from which the air counts as saturated, together with ascent.
PRECIP_RH = 90.0
# Snow line below the freezing level in m: the melting distance of falling
# snow (300-400 m; less in heavy precipitation, which cools the layer).
SNOW_LINE_BELOW_FREEZING_M = 350.0

# Mountain weather: height in m (2000 m: ski areas and huts of the Alps) and the
# relative humidity from which the summits are in cloud.
MOUNTAIN_HEIGHT_M = 2000.0
SUMMIT_CLOUD_RH = 95.0
# ICON-D2: a cell is in cloud at the height where the model's cloud base lies below it and RH (over
# water) reaches this; ice-saturated air has only about 95 % at -5 deg C and 91 % at -10 deg C. Hatched
# where at least SUMMIT_CLOUD_AREA % of the cells around (10 km smoothing) are in cloud.
ICON_SUMMIT_CLOUD_RH = 90.0
SUMMIT_CLOUD_AREA = 50.0
# The T850 palette at the mountain height, so one colour means one temperature on every chart.
MOUNTAIN_T = ColourScale(f"Temperature at {MOUNTAIN_HEIGHT_M:g} m (°C)", T850.bands, legend_range=T850.legend_range)
# Central Europe: values printed on a lattice of this spacing (about 250 km), over land only.
VALUE_SPACING_PX = 80
