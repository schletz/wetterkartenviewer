"""Random access to the forecast files in the data directory.

ecmwf_<run>.grb2 holds the ECMWF fields of one run and the fields the viewer
derives from them (charts.md in the data directory, section "GRIB-Datei"):
values at 2000/2500/3000 m, freezing level, snow line, inversion, boundary
layer humidity, precipitation signal, free atmosphere wind, orography in m
and daily 2 m extremes. Fields of the local category 192 have no shortName in
ecCodes and are named here by parameterNumber. Points below the model
ground are missing and read as NaN.

icon-d2_<run>.grb2 holds the raw ICON-D2 fields (section "ICON-D2-Datei"),
one value per cell of the unstructured grid; they carry the viewer's names
(ICON_NAMES), the cell centres are clat/clon and the boundary zone is NaN.
"""

from datetime import datetime, timedelta
from functools import lru_cache
from pathlib import Path

import eccodes
import numpy as np

from .constants import ICON_NAMES

LOCAL_CATEGORY = 192
# parameterNumber -> name of the derived fields without WMO or ECMWF parameter (fixed by the viewer).
LOCAL_NAMES = {0: "inv", 1: "rhbl", 2: "psig", 3: "snowl", 4: "uf", 5: "vf"}
# Decoded fields kept per instance; 64 fields of the Europe box are about 250 MB.
CACHED_FIELDS = 64


class ForecastGrib:
    """Index of one forecast file; fields are decoded on request and cached read-only.

    Attributes:
        base_time: run as a naive datetime in UTC.
        grid: dict with lat0, lon0 (-180..180), dlat, dlon, ni, nj of the
            regular lat/lon grid, rows north to south; None for the
            unstructured ICON grid, whose fields are 1-D.
    """

    def __init__(self, path: Path):
        self.path = Path(path)
        self._offsets: dict[tuple, int] = {}               # (name, level, end step) -> byte offset
        self._level_types: dict[tuple[str, int], str] = {}  # (name, level) -> typeOfLevel, in file order
        with self.path.open("rb") as fh:
            while (gid := eccodes.codes_grib_new_from_file(fh, headers_only=True)) is not None:
                try:
                    # Steps in hours; ICON gives its time invariant fields in minutes ("0m").
                    eccodes.codes_set(gid, "stepUnits", 1)
                    key = (self._name(gid), eccodes.codes_get(gid, "level"), eccodes.codes_get(gid, "endStep"))
                    self._offsets[key] = int(eccodes.codes_get(gid, "offset"))
                    self._level_types.setdefault(key[:2], eccodes.codes_get(gid, "typeOfLevel"))
                    if not hasattr(self, "base_time"):
                        self._read_grid(gid)
                finally:
                    eccodes.codes_release(gid)
        if not self._offsets:
            raise ValueError(f"{self.path} holds no GRIB messages")
        self._decode = lru_cache(maxsize=CACHED_FIELDS)(self._read)

    @staticmethod
    def _name(gid: int) -> str:
        if (eccodes.codes_get(gid, "discipline") == 0
                and eccodes.codes_get(gid, "parameterCategory") == LOCAL_CATEGORY):
            number = eccodes.codes_get(gid, "parameterNumber")
            return LOCAL_NAMES.get(number, f"local{number}")
        name = eccodes.codes_get(gid, "shortName")
        return ICON_NAMES.get(name, name)

    def _read_grid(self, gid: int) -> None:
        get = lambda key: eccodes.codes_get(gid, key)  # noqa: E731
        self.base_time = datetime.strptime(f"{get('dataDate')}{get('dataTime'):04d}", "%Y%m%d%H%M")
        if get("gridType") != "regular_ll":
            self.grid = None
            return
        self.grid = {"lat0": get("latitudeOfFirstGridPointInDegrees"),
                     "lon0": (get("longitudeOfFirstGridPointInDegrees") + 180.0) % 360.0 - 180.0,
                     "dlat": get("jDirectionIncrementInDegrees"), "dlon": get("iDirectionIncrementInDegrees"),
                     "ni": get("Ni"), "nj": get("Nj")}

    def parameters(self) -> list[tuple[str, int, str]]:
        """(name, level, typeOfLevel) of every parameter in the file, in file order."""
        return [(name, level, level_type) for (name, level), level_type in self._level_types.items()]

    def steps(self, name: str) -> list[int]:
        """End steps in hours at which a parameter is available, ascending."""
        return sorted({end for key_name, _, end in self._offsets if key_name == name})

    def has(self, name: str, step: int, level: int | None = None) -> bool:
        """Whether a field exists."""
        return self._key(name, step, level) is not None

    def field(self, name: str, step: int, level: int | None = None) -> np.ndarray:
        """Values of one field as a read-only (nj, ni) float32 array, NaN where missing; 1-D on the ICON grid.

        Args:
            name: GRIB shortName, local or ICON name, e.g. "t", "thick", "deg0l", "inv", "ceiling".
            step: end step in hours.
            level: pressure level in hPa or height in m (t, r, u, v at 2000/2500/3000);
                may be omitted for single level fields.

        Raises:
            KeyError: if the file holds no such field.
        """
        key = self._key(name, step, level)
        if key is None:
            raise KeyError(f"{name} level {level} step {step} not in {self.path.name}")
        return self._decode(key)

    def valid_time(self, step: int) -> datetime:
        """Valid time of a step."""
        return self.base_time + timedelta(hours=step)

    def _read(self, key: tuple) -> np.ndarray:
        with self.path.open("rb") as fh:
            fh.seek(self._offsets[key])
            gid = eccodes.codes_grib_new_from_file(fh)
            try:
                values = eccodes.codes_get_values(gid).astype(np.float32)
                if eccodes.codes_get(gid, "bitmapPresent"):
                    values[values == eccodes.codes_get(gid, "missingValue")] = np.nan
            finally:
                eccodes.codes_release(gid)
        if self.grid is not None:
            values = values.reshape(self.grid["nj"], self.grid["ni"])
        # Shared by every caller through the cache, so nobody may change it in place.
        values.flags.writeable = False
        return values

    def _key(self, name: str, step: int, level: int | None):
        for key in self._offsets:
            if key[0] == name and key[2] == step and (level is None or key[1] == level):
                return key
        return None
