"""Cutting global regular lat/lon GRIB messages to the box of the chart windows."""

import eccodes
import numpy as np

from .projection import Projection

# Extra grid points around the chart windows, so smoothing and bilinear
# interpolation have data up to the image border.
BOX_MARGIN_DEG = 1.0


class GribCropper:
    """Cuts global regular lat/lon messages to a box and re-encodes them."""

    def __init__(self, box: tuple[float, float, float, float]):
        """Set the box.

        Args:
            box: (lat_min, lat_max, lon_min, lon_max) in degrees, longitudes -180..180.
        """
        self.box = box
        self._indices = None  # (rows, cols) into the global grid, set by the first message

    @classmethod
    def for_windows(cls, projections: list[Projection], margin: float = BOX_MARGIN_DEG) -> "GribCropper":
        """Cropper for the 0.1 deg box that covers every chart window.

        The pole lies above the images, so the extremes lie on the image borders.
        """
        borders = [projection.border_latlon() for projection in projections]
        lat = np.concatenate([b[0] for b in borders])
        lon = np.concatenate([b[1] for b in borders])
        return cls((np.floor(lat.min() - margin), min(90.0, np.ceil(lat.max() + margin)),
                    np.floor(lon.min() - margin), np.ceil(lon.max() + margin)))

    def fit(self, gid: int) -> tuple[np.ndarray, np.ndarray]:
        """Row and column indices of the box in the global grid of ``gid``; columns run west to east across 0 deg.

        The first call fixes them and sets ``grid`` for all later messages,
        so a copy of a fitted cropper (e.g. in a worker process) needs no message of its own.
        """
        if self._indices is None:
            lat_min, lat_max, lon_min, lon_max = self.box
            ni, nj = eccodes.codes_get(gid, "Ni"), eccodes.codes_get(gid, "Nj")
            lat0 = eccodes.codes_get(gid, "latitudeOfFirstGridPointInDegrees")
            lon0 = eccodes.codes_get(gid, "longitudeOfFirstGridPointInDegrees")
            dlat = eccodes.codes_get(gid, "jDirectionIncrementInDegrees")
            dlon = eccodes.codes_get(gid, "iDirectionIncrementInDegrees")
            lats = lat0 - np.arange(nj) * dlat
            # Normalise to -180..180 and sort, so the box is contiguous whatever the grid origin.
            lons = (lon0 + np.arange(ni) * dlon + 180.0) % 360.0 - 180.0
            order = np.argsort(lons)
            eps = dlat / 10
            rows = np.flatnonzero((lats <= lat_max + eps) & (lats >= lat_min - eps))
            cols = order[(lons[order] >= lon_min - eps) & (lons[order] <= lon_max + eps)]
            self._indices = rows, cols
            self.grid = {
                "Ni": len(cols), "Nj": len(rows),
                "latitudeOfFirstGridPointInDegrees": float(lats[rows[0]]),
                "latitudeOfLastGridPointInDegrees": float(lats[rows[-1]]),
                "longitudeOfFirstGridPointInDegrees": float(lons[cols[0]]),
                "longitudeOfLastGridPointInDegrees": float(lons[cols[-1]]),
            }
        return self._indices

    def crop(self, gid: int) -> tuple[int, np.ndarray]:
        """New handle with the box grid and its values; the caller releases it."""
        rows, cols = self.fit(gid)
        ni, nj = eccodes.codes_get(gid, "Ni"), eccodes.codes_get(gid, "Nj")
        values = eccodes.codes_get_values(gid).reshape(nj, ni)[np.ix_(rows, cols)]
        return self.encode(gid, values), values

    def encode(self, template: int, values: np.ndarray, keys: dict | None = None) -> int:
        """Clone a message onto the box grid with new values and optional extra keys."""
        packing = eccodes.codes_get(template, "packingType")
        bits = eccodes.codes_get(template, "bitsPerValue")
        gid = eccodes.codes_clone(template)
        # The source's packed data section does not fit the smaller grid,
        # so the values are set with simple packing and repacked afterwards.
        eccodes.codes_set(gid, "packingType", "grid_simple")
        for key, value in {**self.grid, **(keys or {})}.items():
            eccodes.codes_set(gid, key, value)
        eccodes.codes_set(gid, "bitsPerValue", bits)
        eccodes.codes_set_values(gid, values.ravel())
        if packing != "grid_simple":
            eccodes.codes_set(gid, "packingType", packing)
        return gid
