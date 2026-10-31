"""Derived fields appended to a forecast file, so that readers of data/ need no meteorology of their own.

The synop skill reads its time series straight from the GRIB file; every
quantity that needs the vertical profile, the model ground or a threshold
is computed here once, with the same code that draws the charts:

    t, r, u, v at 2000/2500/3000 m   standard parameters on heightAboveSea levels, per step
    deg0l                            freezing level in m (ECMWF 228024), per step
    inv, rhbl, psig, snowl           local parameters (local_params.py) on the surface, per step
    uf, vf at 1000/925 hPa           local parameters: wind, missing where the level lies below the ground
    orog                             model orography in m (ECMWF 228002), T+0 only
    mx2t, mn2t                       daily 2 m maximum 06-18 UTC and minimum 18-06 UTC, per complete day

Values below the model ground are missing (GRIB bitmap) and read back as NaN.
"""

import os
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import eccodes
import numpy as np

from .diagnostics import Diagnostics
from .forecast_grib import ForecastGrib
from .height_profile import HeightProfile
from .local_params import LOCAL_CATEGORY, LOCAL_NUMBERS
from .model_surface import ModelSurface

MOUNTAIN_HEIGHTS = (2000, 2500, 3000)
PROFILE_PARAMS = ("t", "r", "u", "v")
FREE_LEVELS = (1000, 925)
SURFACE_FIELDS = ("inv", "rhbl", "psig", "snowl")
# Messages per step: profile values at every height, the freezing level, the surface fields, free winds.
PER_STEP = len(PROFILE_PARAMS) * len(MOUNTAIN_HEIGHTS) + 1 + len(SURFACE_FIELDS) + 2 * len(FREE_LEVELS)
# ECMWF parameter ids where one exists.
PARAM_IDS = {"deg0l": 228024, "orog": 228002, "max": 201, "min": 202}
# Ground surface as level of a single level field (code table 4.5: 1).
SURFACE = {"typeOfFirstFixedSurface": 1, "scaleFactorOfFirstFixedSurface": None, "scaledValueOfFirstFixedSurface": None}
# Each worker caches up to 64 decoded fields (~250 MB), so the pool stays small.
MAX_WORKERS = 8

# State of a worker process, set once by init_worker.
_grib: ForecastGrib | None = None
_surface: ModelSurface | None = None


def encode(template: bytes, values: np.ndarray, keys: dict) -> bytes:
    """A copy of ``template`` with new keys and values; NaN becomes missing in a bitmap."""
    gid = eccodes.codes_new_from_message(template)
    try:
        for key, value in keys.items():
            if value is None:
                eccodes.codes_set_missing(gid, key)
            else:
                eccodes.codes_set(gid, key, value)
        values = np.asarray(values, dtype=np.float64).ravel()
        missing = np.isnan(values)
        if missing.any():
            eccodes.codes_set(gid, "bitmapPresent", 1)
            values = np.where(missing, eccodes.codes_get(gid, "missingValue"), values)
        eccodes.codes_set_values(gid, values)
        return eccodes.codes_get_message(gid)
    finally:
        eccodes.codes_release(gid)


def height_keys(height: int) -> dict:
    """Level keys of a height above mean sea level in m."""
    return {"typeOfFirstFixedSurface": 102, "scaleFactorOfFirstFixedSurface": 0,
            "scaledValueOfFirstFixedSurface": height}


def local_keys(name: str) -> dict:
    """Parameter keys of a field of local_params.py."""
    return {"discipline": 0, "parameterCategory": LOCAL_CATEGORY, "parameterNumber": LOCAL_NUMBERS[name]}


def init_worker(path: Path) -> None:
    """Index the forecast file once per process."""
    global _grib, _surface  # pylint: disable=global-statement
    _grib = ForecastGrib(path)
    _surface = ModelSurface(_grib)


def step_messages(step: int) -> list[bytes]:
    """Worker: the derived messages of one step."""
    grib = _grib
    profile = HeightProfile(grib, step)
    diagnostics = Diagnostics(profile, _surface)
    t850 = grib.message("t", step, 850)
    messages = []
    for name in PROFILE_PARAMS:
        template = grib.message(name, step, 850)
        messages += [encode(template, profile.at_height(name, height), height_keys(height))
                     for height in MOUNTAIN_HEIGHTS]
    messages.append(encode(t850, diagnostics.freezing_level(), {"paramId": PARAM_IDS["deg0l"]}))
    surface_values = {"inv": diagnostics.inversion(), "rhbl": diagnostics.moist_boundary_layer(),
                      "psig": diagnostics.precipitation_signal().astype(np.float32),
                      "snowl": diagnostics.snow_line()}
    messages += [encode(t850, surface_values[name], {**local_keys(name), **SURFACE}) for name in SURFACE_FIELDS]
    for level in FREE_LEVELS:
        for component, name in (("u", "uf"), ("v", "vf")):
            messages.append(encode(grib.message(component, step, level), diagnostics.free(component, level),
                                   local_keys(name)))
    return messages


class DerivedWriter:
    """Appends the derived fields to a forecast file written by ForecastWriter."""

    def __init__(self, workers: int = min(os.cpu_count() or 1, MAX_WORKERS)):
        self.workers = workers

    def append(self, path: Path) -> int:
        """Compute the derived fields of every step in parallel and append them; returns the message count."""
        grib = ForecastGrib(path)
        steps = grib.steps("t")
        count = 0
        with ProcessPoolExecutor(max_workers=self.workers, initializer=init_worker, initargs=(path,)) as pool:
            batches = list(pool.map(step_messages, steps))
        with path.open("ab") as fh:
            def write(message: bytes) -> None:
                nonlocal count
                fh.write(message)
                count += 1

            for batch in batches:
                for message in batch:
                    write(message)
            write(encode(grib.message("z", 0), ModelSurface(grib).height, {"paramId": PARAM_IDS["orog"], **SURFACE}))
            for message in self._extremes(grib):
                write(message)
        return count

    @staticmethod
    def _extremes(grib: ForecastGrib) -> list[bytes]:
        """Daily maximum and minimum at 2 m, each as one message over its whole window."""
        messages = []
        windows = grib.extreme_windows
        for kind in ("max", "min"):
            for day in grib.extreme_days(kind):
                template = grib.message(*windows.parts(kind, day)[0])
                start, end = windows.window(kind, day)
                messages.append(encode(template, grib.daily_extreme(kind, day),
                                       {"paramId": PARAM_IDS[kind], "stepRange": f"{start}-{end}"}))
        return messages
