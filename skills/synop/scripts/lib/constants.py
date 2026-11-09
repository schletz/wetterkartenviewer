"""Constants shared across the skill."""

KELVIN = 273.15     # 0 deg C in K

# Near-surface weather of the model (total cloud cover, total precipitation, precipitation type).
# The weather_summary chart shows them; the ECMWF TSV leaves them out, because a 9 km global model
# gets fog, low stratus and their precipitation wrong and the analysis rests on the free atmosphere.
WEATHER_PARAMS = ("tcc", "tp", "ptype")

# Maximum 10 m gust of the ECMWF file since the previous model output, under two names by step:
# 10fg over the last hour to T+90 and the last 6 h after T+144, 10fg3 over the last 3 h between;
# none at T+0. A copy of the viewer's constants.IFS_GUST_NAMES.
IFS_GUST_NAMES = ("10fg", "10fg3")

# ecCodes shortName -> name under which the viewer reads the fields of the ICON-D2 file
# (charts.md, "ICON-D2-Datei"); with them ICON and ECMWF share tcc, msl, ...
ICON_NAMES = {"tlat": "clat", "tlon": "clon", "HSURF": "hsurf", "CLCT": "tcc", "prmsl": "msl", "WW": "ww",
              "max_i10fg": "gust", "max_2t": "tmax_2m", "min_2t": "tmin_2m", "ceil": "ceiling",
              "TW_2M": "wbt"}

# GRIB 1 parameter number -> name of the fields of the CHMI ALADIN file for which ecCodes has no shortName
# (charts.md, "ALADIN-Datei"). A copy of the viewer's constants.ALADIN_NAMES.
ALADIN_NAMES = {61: "tp", 171: "tcc", 223: "fog_visibility", 229: "ptype_severe", 230: "ptype", 236: "flash",
                130: "gust"}

# ALADIN has no ww. Copies of the viewer's chart_styles, so that table and chart name the same weather: lightning
# density of one hour that counts as a thunderstorm (flashes per km2), lowest visibility due to cloud below which
# there is fog (m), codes of graupel and hail in ptype_severe.
ALADIN_STORM_FLASHES_KM2 = 0.02
ALADIN_FOG_VISIBILITY_M = 700.0
ALADIN_GRAUPEL, ALADIN_HAIL = 9, 10
