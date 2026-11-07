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
