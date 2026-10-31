"""GRIB codes of the derived fields that have no WMO or ECMWF parameter.

They use discipline 0 and the category 192 reserved for local use, which
ecCodes reads as shortName "unknown"; ForecastGrib names them by
parameterNumber instead. The synop skill reads the same numbers from
data/, so a number must never change its meaning (data/charts.md,
section "GRIB-Datei", documents them for the skill).
"""

LOCAL_CATEGORY = 192
# parameterNumber -> name used by ForecastGrib and as TSV column of the skill.
LOCAL_NAMES = {
    0: "inv",    # largest temperature increase across 1000-925 or 925-850 hPa in K, free atmosphere
    1: "rhbl",   # highest relative humidity at 925 or 1000 hPa in %, free atmosphere
    2: "psig",   # precipitation signal 0/1: saturated air at 850 or 700 hPa with ascent
    3: "snowl",  # snow line in m
    4: "uf",     # u wind (m/s) on a pressure level, missing where the level lies below the model ground
    5: "vf",     # v wind (m/s) on a pressure level, missing where the level lies below the model ground
}
LOCAL_NUMBERS = {name: number for number, name in LOCAL_NAMES.items()}
