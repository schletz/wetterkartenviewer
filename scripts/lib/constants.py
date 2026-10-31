"""Constants shared across the data scripts."""

KELVIN = 273.15     # 0 deg C in K
KMH_PER_MS = 3.6    # m/s to km/h
GRAVITY = 9.80665   # m/s2, geopotential to geopotential height

# Near-surface weather of the model (total cloud cover, total precipitation, precipitation type).
# They feed only the weather_summary chart; the derived fields leave them out, because a 9 km
# global model gets fog, low stratus and their precipitation wrong.
WEATHER_PARAMS = ("tcc", "tp", "ptype")

# Pressure levels of the temperature, humidity and height profile, ground to about 5.5 km.
# 600 hPa (about 4.2 km) halves the gap above 700 hPa for 3000 m values and the freezing level.
PROFILE_LEVELS = [500, 600, 700, 850, 925, 1000]
# GRIB shortNames of ICON-D2 -> the names its charts use: those of the ECMWF file where one
# exists (ForecastGrib aliases). tcc is in % and tp in kg/m2 (mm) there, not 0..1 and m.
# The 2 m extremes keep the DWD names: they restart every 6 h (icon_extremes.py), unlike any ECMWF field.
ICON_NAMES = {"tlat": "clat", "tlon": "clon", "HSURF": "hsurf", "CLCT": "tcc", "prmsl": "msl", "WW": "ww",
              "max_i10fg": "gust", "max_2t": "tmax_2m", "min_2t": "tmin_2m", "ceil": "ceiling"}
