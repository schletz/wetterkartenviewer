"""Static fields of a CHMI ALADIN forecast file: model orography and land-sea mask."""

import numpy as np

from .constants import GRAVITY
from .forecast_grib import ForecastGrib


class AladinSurface:
    """Time invariant fields of an ALADIN file (step 0), flat like its other fields; the counterpart of ModelSurface.

    Attributes:
        height: model orography in m.
        sdor: None; ALADIN publishes no sub-grid orography.
        land: land fraction 0..1.
    """

    def __init__(self, grib: ForecastGrib):
        self.height: np.ndarray = grib.field("z", 0) / GRAVITY
        self.sdor = None
        self.land: np.ndarray = grib.field("lsm", 0)
