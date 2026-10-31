"""Writing the forecast file: every raw message cut to the box, plus the 1000-500 hPa thickness.

Cropping decodes and re-encodes a global 0.1 deg field per message, so it
runs in a process pool. The main process only finds the messages, writes
the results in the order of the raw files and adds the thickness. Fields
the server lost (a missing step file, a damaged message) are written as
placeholders with every value missing (missing_values.py).
"""

import mmap
import os
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import eccodes
import numpy as np

from .grib_cropper import GribCropper
from .missing_values import missing_message

THICKNESS_LEVELS = (500, 1000)
# GRIB2 discipline 0, category 3, number 12: thickness in gpm, between 1000 and 500 hPa.
THICKNESS_KEYS = {"discipline": 0, "parameterCategory": 3, "parameterNumber": 12,
                  "typeOfFirstFixedSurface": 100, "scaleFactorOfFirstFixedSurface": 0,
                  "scaledValueOfFirstFixedSurface": 100000,
                  "typeOfSecondFixedSurface": 100, "scaleFactorOfSecondFixedSurface": 0,
                  "scaledValueOfSecondFixedSurface": 50000}
# GRIB2 indicator section: "GRIB", 2 reserved octets, discipline, edition, total length (8 octets).
INDICATOR_LENGTH = 16
# Messages per pool task: enough to keep the overhead per task small, few enough to balance the load.
CHUNK_SIZE = 8
# Each worker holds a decoded global field (~100 MB); beyond 8 the main process writing
# the results limits the speed (measured: 15.8 ms/message with 8 workers, 14.3 with 20).
MAX_WORKERS = 8
# Lost fields named in a warning; the rest are counted.
SHOWN_FIELDS = 12

# State of a worker process, set once by init_worker.
_cropper: GribCropper | None = None

Span = tuple[Path, int, int]  # (file, offset, length) of one message
Field = tuple[str, int | None, int]  # (shortName, level or None for single level fields, end step)


def message_spans(path: Path) -> list[Span]:
    """Every intact GRIB2 message of a file, found by reading the indicator sections only.

    A message counts if its indicator section says GRIB edition 2 and the
    length given there ends on "7777"; anything else (a damaged download,
    random bytes) is skipped up to the next "GRIB".
    """
    spans = []
    if path.stat().st_size == 0:
        return spans
    with path.open("rb") as fh, mmap.mmap(fh.fileno(), 0, access=mmap.ACCESS_READ) as data:
        offset = data.find(b"GRIB")
        while offset >= 0:
            header = data[offset:offset + INDICATOR_LENGTH]
            length = int.from_bytes(header[8:16], "big") if len(header) == INDICATOR_LENGTH else 0
            if (header[7:8] == b"\x02" and length > INDICATOR_LENGTH
                    and data[offset + length - 4:offset + length] == b"7777"):
                spans.append((path, offset, length))
                offset = data.find(b"GRIB", offset + length)
            else:
                offset = data.find(b"GRIB", offset + 1)
    return spans


def read_message(span: Span) -> bytes:
    """The bytes of one message."""
    path, offset, length = span
    with path.open("rb") as fh:
        fh.seek(offset)
        return fh.read(length)


def init_worker(cropper: GribCropper) -> None:
    """Take over the fitted cropper once per process."""
    global _cropper  # pylint: disable=global-statement
    _cropper = cropper


def crop_message(span: Span) -> tuple[bytes, np.ndarray | None, Field] | None:
    """Worker: the cropped message, its values if it is gh on a thickness level, and its field;
    None if the message cannot be decoded."""
    try:
        src = eccodes.codes_new_from_message(read_message(span))
    except eccodes.CodesInternalError:
        return None
    try:
        gid, values = _cropper.crop(src)
    except (eccodes.CodesInternalError, ValueError):
        return None
    finally:
        eccodes.codes_release(src)
    try:
        field = (eccodes.codes_get(gid, "shortName"), eccodes.codes_get(gid, "level"),
                 eccodes.codes_get(gid, "endStep"))
        thickness_level = field[0] == "gh" and field[1] in THICKNESS_LEVELS
        return eccodes.codes_get_message(gid), values if thickness_level else None, field
    finally:
        eccodes.codes_release(gid)


def describe(fields: list[Field]) -> str:
    """"t 850 T+108, msl T+60, ..." for a warning."""
    text = ", ".join(f"{name}{'' if level is None else f' {level}'} T+{step}"
                     for name, level, step in fields[:SHOWN_FIELDS])
    return text + (f" and {len(fields) - SHOWN_FIELDS} more" if len(fields) > SHOWN_FIELDS else "")


class ForecastWriter:
    """Crops raw global files into one forecast file and adds the thickness per step."""

    def __init__(self, cropper: GribCropper, workers: int = min(os.cpu_count() or 1, MAX_WORKERS)):
        self.cropper = cropper
        self.workers = workers

    def write(self, raw_files: list[Path], target: Path, expected: set[Field]) -> int:
        """Crop every raw message into ``target`` (overwritten), add the thickness and return the message count.

        The messages keep the order of ``raw_files``; each thickness follows
        the second of gh 500/1000 hPa of its step. At the end follow the
        placeholders: one per field of ``expected`` without an intact
        message, copied from another step of that field, and one per step
        without a thickness. A field without any message to copy from is
        reported on stderr and left out, so the file counts as incomplete.

        Raises:
            RuntimeError: if no raw message can be decoded.
        """
        spans = [span for raw in raw_files for span in message_spans(raw)]
        self._fit(spans)
        missing = set(expected)
        templates = {}  # (shortName, level) -> first cropped message, the template of its placeholders
        gh = {}  # step -> {level: (handle, values)} until both thickness levels of a step are there
        thick = set()  # steps with a thickness
        count = 0
        with (target.open("wb") as fh,
              ProcessPoolExecutor(self.workers, initializer=init_worker, initargs=(self.cropper,)) as pool):
            for result in pool.map(crop_message, spans, chunksize=CHUNK_SIZE):
                if result is None:
                    continue
                message, values, field = result
                fh.write(message)
                count += 1
                # Single level fields are requested without a level (2t is on 2 m, 10u on 10 m).
                if field not in expected:
                    field = (field[0], None, field[2])
                missing.discard(field)
                templates.setdefault(field[:2], message)
                if values is None:
                    continue
                gid = eccodes.codes_new_from_message(message)
                # The order of 500 and 1000 hPa within a step is not guaranteed.
                levels = gh.setdefault(field[2], {})
                levels[field[1]] = (gid, values)
                if len(levels) == len(THICKNESS_LEVELS):
                    fh.write(self._thickness(levels))
                    count += 1
                    thick.add(field[2])
                    for handle, _ in levels.values():
                        eccodes.codes_release(handle)
                    levels.clear()
            for levels in gh.values():
                for handle, _ in levels.values():
                    eccodes.codes_release(handle)
            lost = sorted(missing, key=lambda f: (f[0], f[1] or 0, f[2]))
            replaced = [field for field in lost if field[:2] in templates]
            for name, level, step in replaced:
                fh.write(missing_message(templates[(name, level)], step))
            count += len(replaced)
            if ("gh", 500) in templates:
                for step in sorted({step for name, _, step in expected if name == "gh"} - thick):
                    fh.write(missing_message(templates[("gh", 500)], step, THICKNESS_KEYS))
                    count += 1
        if replaced:
            print(f"warning: {len(replaced)} fields lost on the server, written with missing values: "
                  f"{describe(replaced)}", file=sys.stderr, flush=True)
        if unknown := [field for field in lost if field[:2] not in templates]:
            print(f"warning: {len(unknown)} fields have no message to copy from and are left out: "
                  f"{describe(unknown)}", file=sys.stderr, flush=True)
        return count

    def _fit(self, spans: list[Span]) -> None:
        """Fit the cropper on the first message that decodes, so the workers get it fitted and
        the caller can read its grid."""
        for span in spans:
            try:
                first = eccodes.codes_new_from_message(read_message(span))
            except eccodes.CodesInternalError:
                continue
            try:
                self.cropper.fit(first)
                return
            finally:
                eccodes.codes_release(first)
        raise RuntimeError("no raw message can be decoded")

    def _thickness(self, levels: dict) -> bytes:
        """gh500 - gh1000 as a 1000-500 hPa layer message based on the 500 hPa message."""
        template, gh500 = levels[500]
        _, gh1000 = levels[1000]
        gid = self.cropper.encode(template, gh500 - gh1000, THICKNESS_KEYS)
        try:
            return eccodes.codes_get_message(gid)
        finally:
            eccodes.codes_release(gid)
