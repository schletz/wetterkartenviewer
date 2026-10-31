"""Static fields of an ICON forecast file: cell centres, model orography and the land fraction."""

import numpy as np

from .forecast_grib import ForecastGrib


class IconSurface:
    """Time invariant fields of an ICON file (step 0), one value per cell; the counterpart of ModelSurface.

    Attributes:
        lat, lon: cell centres in degrees.
        height: model orography in m.
        sdor: None; ICON publishes no sub-grid orography for the charts.
        land: land fraction 0..1.
        valid: False for the cells of the boundary zone, which carry no values.
    """

    def __init__(self, grib: ForecastGrib):
        self.lat: np.ndarray = grib.field("clat", 0)
        self.lon: np.ndarray = grib.field("clon", 0)
        self.height: np.ndarray = grib.field("hsurf", 0)
        self.sdor = None
        self.land: np.ndarray = grib.field("lsm", 0)
        self.valid: np.ndarray = ~np.isnan(self.height)
