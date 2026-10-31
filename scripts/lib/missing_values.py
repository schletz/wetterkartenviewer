"""Encoding values with missing points, and placeholders for messages the server did not deliver intact.

A placeholder is a copy of another message of the same field (another
step) with the step of the lost one and every value missing in a bitmap.
ForecastGrib reads it back as NaN and raises MissingFieldError, so the
forecast file keeps one message per expected field and the charts of
that step say "No data available".
"""

import eccodes
import numpy as np


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


def step_keys(template: bytes, end_step: int) -> dict:
    """Keys that move a message to another end step (hours), keeping its kind of time range.

    Instantaneous fields get the step, sums since T+0 (precipitation) the
    range 0-N, extremes over a fixed interval (mx2t3) the range of that length.
    """
    gid = eccodes.codes_new_from_message(template)
    try:
        eccodes.codes_set(gid, "stepUnits", 1)
        start, end = eccodes.codes_get(gid, "startStep"), eccodes.codes_get(gid, "endStep")
    finally:
        eccodes.codes_release(gid)
    if start == end:
        return {"stepUnits": 1, "step": end_step}
    first = 0 if start == 0 else end_step - (end - start)
    return {"stepUnits": 1, "stepRange": f"{first}-{end_step}"}


def missing_message(template: bytes, end_step: int, keys: dict | None = None) -> bytes:
    """Placeholder at ``end_step``: the template's field with every value missing; ``keys`` change more."""
    gid = eccodes.codes_new_from_message(template)
    try:
        size = eccodes.codes_get(gid, "numberOfDataPoints")
    finally:
        eccodes.codes_release(gid)
    return encode(template, np.full(size, np.nan), {**step_keys(template, end_step), **(keys or {})})
