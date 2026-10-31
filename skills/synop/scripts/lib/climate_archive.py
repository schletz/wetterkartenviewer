"""The climatology GRIB files of a directory (data/era5_means/): which fields exist, their grid and their values.

Every ``*.grb2`` of the directory is read, however the fields are spread
over files. Each message is the mean or standard deviation of T850
(level 850) or T2m (level 2) in K, for one kind and calendar day. A kind ``HHz`` holds the
climatology of one time of day (UTC) per calendar day, ``daily`` the one
of the daily means per calendar day and ``monthly`` the one per calendar
month. The term hours are taken from the messages present, so a finer
archive (e.g. every 3 h) needs no code change. The calendar days pool all
years within +-5 days of the day; every calendar day, 29 February
included, is present.

Fields are identified by their product definition, not by shortName:
ecCodes names a field after the innermost statistical process, so the
standard deviations of ``daily`` and ``monthly`` are called avg_* like the
means.

Requires the packages eccodes and numpy.
"""

from pathlib import Path

import eccodes
import numpy as np

PERIOD = "1991–2020"
# Folder of the climatology next to the forecast GRIB in the data directory.
DIRECTORY = "era5_means"

# GRIB2 indicator section; the total message length is in bytes 8-15.
INDICATOR_LENGTH = 16
# Bytes read per message to reach the end of section 4 (it ends before byte 200 in era5_means.grb2).
HEADER_BYTES = 512
# Product definition template 4.8: average, accumulation, extreme values etc. over time ranges.
STATISTICS_TEMPLATE = 8
# Surface types of the product definition (GRIB2 code table 4.5) and their level as ecCodes reports it.
LEVEL_DIVISOR = {100: 100, 103: 1}  # isobaric surface in Pa -> hPa, height above ground in m
# Number of nested time ranges -> kind; a single range is the climatology of one time of day.
KIND_BY_RANGES = {2: "daily", 3: "monthly"}
# Statistical process of the outermost time range (GRIB2 code table 4.10).
STATISTIC = {0: "mean", 6: "std"}


class ClimateArchive:
    """Index and decoded fields of the climatology files of one directory.

    The message headers are parsed from their bytes on first use (well under
    a second for 13 224 messages, against about 5 s with ecCodes); values are
    decoded on demand and cached.

    Attributes:
        period: reference period for labels, e.g. "1991–2020".
    """

    def __init__(self, directory: Path, period: str = PERIOD):
        self._directory = Path(directory)
        self.period = period
        self._files = sorted(self._directory.glob("*.grb2"))
        if not self._files:
            raise FileNotFoundError(f"no *.grb2 in {self._directory}")
        self._index = None   # (kind, statistic, level, month, day) -> (path, offset, length)
        self._values = {}    # same key -> decoded field
        self._grid = None

    @property
    def kinds(self) -> tuple[str, ...]:
        """The kinds present, e.g. ("00z", "03z", ..., "daily", "monthly")."""
        return tuple(sorted({key[0] for key in self._load()}))

    @property
    def term_hours(self) -> tuple[int, ...]:
        """UTC hours with a climatology of their own, ascending."""
        return tuple(sorted(int(kind[:2]) for kind in self.kinds if kind.endswith("z")))

    def term_kind(self, hour: int) -> str:
        """Kind of the climatology of one time of day.

        Raises:
            ValueError: if the archive has no climatology for that hour.
        """
        if hour not in self.term_hours:
            raise ValueError(f"no climatology for {hour:02d} UTC; the archive has {self.term_hours} UTC")
        return f"{hour:02d}z"

    def keys(self, kind: str) -> list[tuple]:
        """(statistic, level, month, day) of every field of one kind; day is None for monthly values."""
        return [key[1:] for key in self._load() if key[0] == kind]

    def field(self, kind: str, statistic: str, level: int, month: int, day: int | None) -> np.ndarray:
        """Decoded values of one message in K as a flat float32 array, in GRIB order (rows north to south).

        Args:
            kind: "HHz", "daily" or "monthly".
            statistic: "mean" or "std".
            level: 850 (T850) or 2 (T2m).
            day: None for monthly values.

        Raises:
            KeyError: if the archive has no such field.
        """
        key = (kind, statistic, level, month, day)
        if key not in self._values:
            self._values[key] = self._read_values(key)
        return self._values[key]

    @property
    def grid(self) -> dict:
        """lat0, lon0 (-180..180), dlat, dlon, ni, nj as in ForecastGrib.grid, plus the point arrays lat and lon."""
        if self._grid is None:
            gid = eccodes.codes_new_from_message(self._message(next(iter(self._load()))))
            try:
                self._grid = self._read_grid(gid)
            finally:
                eccodes.codes_release(gid)
        return self._grid

    def nearest(self, lat: float, lng: float) -> int:
        """Index of the grid point nearest to a location, by distance in degrees.

        Raises:
            ValueError: if the location lies more than one grid spacing from every point.
        """
        grid = self.grid
        distance = np.hypot(grid["lon"] - lng, grid["lat"] - lat)
        index = int(np.argmin(distance))
        if distance[index] > max(grid["dlat"], grid["dlon"]):
            raise ValueError(f"{lat} N {lng} E lies outside the climatology grid")
        return index

    def _read_values(self, key: tuple) -> np.ndarray:
        gid = eccodes.codes_new_from_message(self._message(key))
        try:
            return eccodes.codes_get_values(gid).astype(np.float32)
        finally:
            eccodes.codes_release(gid)

    def _message(self, key: tuple) -> bytes:
        path, offset, length = self._load()[key]
        with path.open("rb") as fh:
            fh.seek(offset)
            return fh.read(length)

    def _load(self) -> dict:
        """Index the messages of all files by their headers without reading the data sections."""
        if self._index is None:
            self._index = {}
            for path in self._files:
                for offset, length, identification, product in _headers(path):
                    self._index[_key(identification, product)] = (path, offset, length)
        return self._index

    @staticmethod
    def _read_grid(gid: int) -> dict:
        get = lambda key: eccodes.codes_get(gid, key)  # noqa: E731
        lon = eccodes.codes_get_array(gid, "longitudes")
        return {"lat0": get("latitudeOfFirstGridPointInDegrees"),
                "lon0": (get("longitudeOfFirstGridPointInDegrees") + 180.0) % 360.0 - 180.0,
                "dlat": get("jDirectionIncrementInDegrees"), "dlon": get("iDirectionIncrementInDegrees"),
                "ni": get("Ni"), "nj": get("Nj"),
                "lat": eccodes.codes_get_array(gid, "latitudes"), "lon": np.where(lon > 180, lon - 360, lon)}


def _headers(path: Path):
    """Yield (offset, length, section 1, section 4) of every GRIB2 message of a file, reading only its header."""
    with path.open("rb") as fh:
        offset = 0
        while head := fh.read(HEADER_BYTES):
            if head[:4] != b"GRIB" or head[7] != 2:
                raise ValueError(f"{path}: no GRIB2 message at byte {offset}")
            length = int.from_bytes(head[8:16], "big")
            sections, position = {}, INDICATOR_LENGTH
            while 4 not in sections:
                size = int.from_bytes(head[position:position + 4], "big")
                if position + size > len(head):
                    raise ValueError(f"{path}: header of the message at byte {offset} exceeds {HEADER_BYTES} bytes")
                sections[head[position + 4]] = head[position:position + size]
                position += size
            yield offset, length, sections[1], sections[4]
            offset += length
            fh.seek(offset)


def _key(identification: bytes, product: bytes) -> tuple:
    """(kind, statistic, level, month, day) of a message from its sections 1 and 4.

    Byte positions are the octets of the GRIB2 specification minus one.
    Section 1 holds the reference time (octets 13-19); its year is the
    first year of the period and irrelevant here. Template 4.8 holds the
    first fixed surface (octets 23-28), the number of time ranges (octet
    42) and from octet 47 one 12-octet specification per range, outermost
    first, each starting with its statistical process.
    """
    template = int.from_bytes(product[7:9], "big")
    if template != STATISTICS_TEMPLATE:
        raise ValueError(f"product definition template 4.{template}, expected 4.{STATISTICS_TEMPLATE}")
    month, day, hour = identification[14], identification[15], identification[16]
    level = int.from_bytes(product[24:28], "big") // 10 ** product[23] // LEVEL_DIVISOR[product[22]]
    ranges = product[41]
    kind = KIND_BY_RANGES.get(ranges) or f"{hour:02d}z"
    return kind, STATISTIC[product[46]], level, month, None if kind == "monthly" else day
