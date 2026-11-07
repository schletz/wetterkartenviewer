"""Derived fields appended to an ICON-D2 file, so the synop skill reads them like those of the IFS file.

    wbt at 2 m    wet-bulb temperature in K from 2t, 2d and sp (moist_air.py), every step of 2t;
                  GRIB2 0/0/27, the same field derived_writer.py appends to the IFS file; on the DWD
                  template ecCodes names it TW_2M, which constants.ICON_NAMES maps to wbt

Cells of the boundary zone stay missing; a step whose inputs are lost
(placeholders of missing_values.py) is written with every value missing.
"""

from pathlib import Path

import numpy as np

from .derived_writer import PARAM_IDS, wet_bulb
from .forecast_grib import ForecastGrib
from .missing_field_error import MissingFieldError
from .missing_values import encode

# DWD folder whose files set the steps of the derived fields: one wet-bulb message per file of it.
SOURCE_FOLDER = "t_2m"


class IconDerivedWriter:
    """Appends the derived fields to an ICON-D2 file joined by IconDownloader."""

    @staticmethod
    def expected(urls: list[str]) -> int:
        """Derived messages of a run with these file URLs: one per file of SOURCE_FOLDER."""
        return sum(1 for url in urls if url.endswith(f"_{SOURCE_FOLDER}.grib2.bz2"))

    @staticmethod
    def append(path: Path) -> int:
        """Compute the wet-bulb temperature of every step and append it; returns the message count."""
        grib = ForecastGrib(path)
        messages = []
        for step in grib.steps("2t"):
            template = grib.message("2t", step)
            try:
                values = wet_bulb(grib, step)
            except MissingFieldError:
                values = np.full(len(grib.field("clat", 0)), np.nan)
            # The template of 2t keeps the level 2 m above ground.
            messages.append(encode(template, values, {"paramId": PARAM_IDS["wbt"]}))
        with path.open("ab") as fh:
            for message in messages:
                fh.write(message)
        return len(messages)
