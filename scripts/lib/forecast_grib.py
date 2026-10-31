"""Random access to the fields of a forecast file written by download_ecmwf_data.py."""

from datetime import date, datetime, timedelta
from functools import lru_cache
from pathlib import Path

import eccodes
import numpy as np

from .extreme_windows import EXTREME_PARAMS, ExtremeWindows
from .local_params import LOCAL_CATEGORY, LOCAL_NAMES
from .missing_field_error import MissingFieldError

# Decoded fields kept per instance: a chart or table row reads the same
# levels several times (profile, inversion, ground check). 64 fields of
# the Europe box are about 250 MB.
CACHED_FIELDS = 64


class ForecastGrib:
    """Index of one forecast file; fields are decoded on request and cached read-only.

    Besides the regular lat/lon files of download_ecmwf_data.py it reads
    the ICON files of download_icon_d2.py, whose fields have one value per
    cell of the unstructured grid (``grid`` is None, fields are 1-D).

    Attributes:
        base_time: run as a naive datetime in UTC.
        grid: dict with lat0, lon0 (-180..180), dlat, dlon, ni, nj of the
            regular lat/lon grid, rows north to south; None for an unstructured grid.
    """

    def __init__(self, path: Path, aliases: dict[str, str] | None = None):
        """Index a forecast file.

        Args:
            path: the GRIB2 file.
            aliases: names under which GRIB shortNames are indexed, e.g.
                {"prmsl": "msl"}, so the fields of another model carry the names the charts use.
        """
        self.path = Path(path)
        self._aliases = aliases or {}
        # (shortName, level, end step) -> (start step, byte offset)
        self._index: dict[tuple, tuple[int, int]] = {}
        # (shortName, level) -> typeOfLevel, in file order
        self._level_types: dict[tuple[str, int], str] = {}
        # index key -> whether every value is missing (a placeholder of missing_values.py), set on decoding
        self._empty: dict[tuple, bool] = {}
        with self.path.open("rb") as fh:
            while (gid := eccodes.codes_grib_new_from_file(fh, headers_only=True)) is not None:
                try:
                    # Steps in hours; ICON gives its time invariant fields in minutes ("0m").
                    eccodes.codes_set(gid, "stepUnits", 1)
                    key = (self._name(gid), eccodes.codes_get(gid, "level"), eccodes.codes_get(gid, "endStep"))
                    self._index[key] = (eccodes.codes_get(gid, "startStep"), int(eccodes.codes_get(gid, "offset")))
                    self._level_types.setdefault(key[:2], eccodes.codes_get(gid, "typeOfLevel"))
                    if not hasattr(self, "base_time"):
                        self._read_grid(gid)
                finally:
                    eccodes.codes_release(gid)
        if not self._index:
            raise ValueError(f"{self.path} holds no GRIB messages")
        self._decode = lru_cache(maxsize=CACHED_FIELDS)(self._read)

    def _name(self, gid: int) -> str:
        """Name of a message: its shortName or alias; the derived fields of the local category get theirs from local_params."""
        if (eccodes.codes_get(gid, "discipline") == 0
                and eccodes.codes_get(gid, "parameterCategory") == LOCAL_CATEGORY):
            number = eccodes.codes_get(gid, "parameterNumber")
            return LOCAL_NAMES.get(number, f"local{number}")
        name = eccodes.codes_get(gid, "shortName")
        return self._aliases.get(name, name)

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
        """(shortName, level, typeOfLevel) of every parameter in the file, in file order."""
        return [(name, level, level_type) for (name, level), level_type in self._level_types.items()]

    def steps(self, short_name: str) -> list[int]:
        """End steps in hours at which a parameter is available, ascending."""
        return sorted({end for name, _, end in self._index if name == short_name})

    def has(self, short_name: str, step: int, level: int | None = None) -> bool:
        """Whether a field has a message, possibly a placeholder without values."""
        return self._key(short_name, step, level) is not None

    def field(self, short_name: str, step: int, level: int | None = None) -> np.ndarray:
        """Values of one field as a read-only (nj, ni) float32 array; 1-D on an unstructured grid.

        Args:
            short_name: GRIB shortName, e.g. "t", "gh", "thick", "2t".
            step: end step in hours.
            level: pressure level; may be omitted for single level fields.

        Raises:
            MissingFieldError: if the file holds no such field, or only its placeholder with every value missing.
        """
        key = self._key(short_name, step, level)
        if key is None:
            raise MissingFieldError(f"{self._label(short_name, step, level)} not in {self.path.name}")
        values = self._decode(key)
        if self._empty[key]:
            raise MissingFieldError(f"{self._label(short_name, step, level)} lost, no data in {self.path.name}")
        return values

    def message(self, short_name: str, step: int, level: int | None = None) -> bytes:
        """The encoded GRIB message of one field, e.g. as template for a derived field.

        Raises:
            MissingFieldError: if the file holds no such field.
        """
        key = self._key(short_name, step, level)
        if key is None:
            raise MissingFieldError(f"{self._label(short_name, step, level)} not in {self.path.name}")
        with self.path.open("rb") as fh:
            fh.seek(self._index[key][1])
            gid = eccodes.codes_grib_new_from_file(fh)
            try:
                return eccodes.codes_get_message(gid)
            finally:
                eccodes.codes_release(gid)

    def _read(self, key: tuple) -> np.ndarray:
        with self.path.open("rb") as fh:
            fh.seek(self._index[key][1])
            gid = eccodes.codes_grib_new_from_file(fh)
            try:
                values = eccodes.codes_get_values(gid).astype(np.float32)
                # Derived fields mark points below the model ground as missing in a bitmap, ICON its boundary zone.
                if eccodes.codes_get(gid, "bitmapPresent"):
                    values[values == eccodes.codes_get(gid, "missingValue")] = np.nan
            finally:
                eccodes.codes_release(gid)
        self._empty[key] = bool(np.isnan(values).all())
        if self.grid is not None:
            values = values.reshape(self.grid["nj"], self.grid["ni"])
        # Shared by every caller through the cache, so nobody may change it in place.
        values.flags.writeable = False
        return values

    @staticmethod
    def _label(short_name: str, step: int, level: int | None) -> str:
        """"t 850 T+108" for messages."""
        return f"{short_name}{'' if level is None else f' {level}'} T+{step}"

    def _key(self, short_name: str, step: int, level: int | None):
        for key in self._index:
            if key[0] == short_name and key[2] == step and (level is None or key[1] == level):
                return key
        return None

    def valid_time(self, step: int) -> datetime:
        """Valid time of a step."""
        return self.base_time + timedelta(hours=step)

    def daily_extreme(self, kind: str, day: date) -> np.ndarray | None:
        """Daily maximum (``kind="max"``) or minimum ("min") of the 2 m temperature in K.

        The 3 and 6 hour extremes inside the window of the day (see
        extreme_windows.py) are combined. Returns None unless the run
        covers the whole window.
        """
        parts = self.extreme_windows.parts(kind, day)
        if parts is None:
            return None
        reduce = np.maximum if kind == "max" else np.minimum
        result = self.field(*parts[0])
        for part in parts[1:]:
            result = reduce(result, self.field(*part))
        return result

    def extreme_days(self, kind: str) -> list[date]:
        """Calendar days (UTC) for which the daily maximum (``kind="max"``) or minimum ("min") is complete."""
        return self.extreme_windows.days(kind, max(self.steps("2t")))

    @property
    def extreme_windows(self) -> ExtremeWindows:
        """The 3 and 6 hour 2 m extremes of the file as daily windows."""
        intervals = [(name, start_step, end_step) for (name, _, end_step), (start_step, _) in self._index.items()
                     if name in EXTREME_PARAMS["max"] + EXTREME_PARAMS["min"]]
        return ExtremeWindows(intervals, self.base_time)
