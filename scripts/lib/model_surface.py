"""Static surface fields of a forecast file: model orography, its roughness and the land-sea mask."""

import numpy as np

from .constants import GRAVITY
from .forecast_grib import ForecastGrib


class ModelSurface:
    """Fields of T+0 that describe the model ground, on the model grid.

    Attributes:
        height: model orography in m (geopotential / g).
        sdor: sub-grid standard deviation of the orography in m.
        land: land fraction 0..1 (land-sea mask).
    """

    def __init__(self, grib: ForecastGrib):
        self.height: np.ndarray = grib.field("z", 0) / GRAVITY
        self.sdor: np.ndarray = grib.field("sdor", 0)
        self.land: np.ndarray = grib.field("lsm", 0)
