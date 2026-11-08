"""Constants shared across the data scripts."""

KELVIN = 273.15     # 0 deg C in K
KMH_PER_MS = 3.6    # m/s to km/h
GRAVITY = 9.80665   # m/s2, geopotential to geopotential height

# Near-surface weather of the model (total cloud cover, total precipitation, precipitation type).
# They feed only the weather_summary chart and the colour bar of the start page diagram that repeats it; the derived
# fields leave them out, because a 9 km global model gets fog, low stratus and their precipitation wrong.
WEATHER_PARAMS = ("tcc", "tp", "ptype")

# Maximum 10 m gust of IFS Open Data, over the time since the previous model output: 10fg over the
# last hour to T+90 (hourly output) and over the last 6 h after T+144; 10fg3 over the last 3 h between.
# Never at T+0. ForecastGrib.pick finds the one a step has.
IFS_GUST_NAMES = ("10fg", "10fg3")
IFS_HOURLY_LAST_STEP = 90

# Pressure levels of the temperature, humidity and height profile, ground to about 5.5 km.
# 600 hPa (about 4.2 km) halves the gap above 700 hPa for 3000 m values and the freezing level.
PROFILE_LEVELS = [500, 600, 700, 850, 925, 1000]
# GRIB shortNames of ICON-D2 -> the names its charts use: those of the ECMWF file where one
# exists (ForecastGrib aliases). tcc is in % and tp in kg/m2 (mm) there, not 0..1 and m.
# The 2 m extremes keep the DWD names: they restart every 6 h (icon_extremes.py), unlike any ECMWF field.
# TW_2M is the DWD name of the derived wet-bulb temperature (GRIB2 0/0/27 on a DWD template, icon_derived_writer.py).
ICON_NAMES = {"tlat": "clat", "tlon": "clon", "HSURF": "hsurf", "CLCT": "tcc", "prmsl": "msl", "WW": "ww",
              "max_i10fg": "gust", "max_2t": "tmax_2m", "min_2t": "tmin_2m", "ceil": "ceiling",
              "TW_2M": "wbt"}
