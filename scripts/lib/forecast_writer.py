"""Writing the forecast file: every raw message cut to the box, plus the 1000-500 hPa thickness.

Cropping decodes and re-encodes a global 0.1 deg field per message, so it
runs in a process pool. The main process only finds the messages, writes
the results in the order of the raw files and adds the thickness.
"""

import os
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import eccodes
import numpy as np

from .grib_cropper import GribCropper

THICKNESS_LEVELS = (500, 1000)
# GRIB2 discipline 0, category 3, number 12: thickness in gpm.
THICKNESS_PARAM = {"discipline": 0, "parameterCategory": 3, "parameterNumber": 12}
# GRIB2 indicator section: "GRIB", 2 reserved octets, discipline, edition, total length (8 octets).
INDICATOR_LENGTH = 16
# Messages per pool task: enough to keep the overhead per task small, few enough to balance the load.
CHUNK_SIZE = 8
# Each worker holds a decoded global field (~100 MB); beyond 8 the main process writing
# the results limits the speed (measured: 15.8 ms/message with 8 workers, 14.3 with 20).
MAX_WORKERS = 8

# State of a worker process, set once by init_worker.
_cropper: GribCropper | None = None

Span = tuple[Path, int, int]  # (file, offset, length) of one message


def message_spans(path: Path) -> list[Span]:
    """Every GRIB2 message of a file, found by reading the indicator sections only.

    Raises:
        ValueError: if the file holds anything but consecutive GRIB2 messages.
    """
    spans = []
    offset = 0
    with path.open("rb") as fh:
        while header := fh.read(INDICATOR_LENGTH):
            if len(header) < INDICATOR_LENGTH or header[:4] != b"GRIB" or header[7] != 2:
                raise ValueError(f"no GRIB2 message at byte {offset} of {path}")
            length = int.from_bytes(header[8:16], "big")
            spans.append((path, offset, length))
            offset += length
            fh.seek(offset)
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


def crop_message(span: Span) -> tuple[bytes, np.ndarray | None]:
    """Worker: the cropped message, plus its values if it is gh on a thickness level."""
    src = eccodes.codes_new_from_message(read_message(span))
    try:
        gid, values = _cropper.crop(src)
    finally:
        eccodes.codes_release(src)
    try:
        thickness_level = (eccodes.codes_get(gid, "shortName") == "gh"
                           and eccodes.codes_get(gid, "level") in THICKNESS_LEVELS)
        return eccodes.codes_get_message(gid), values if thickness_level else None
    finally:
        eccodes.codes_release(gid)


class ForecastWriter:
    """Crops raw global files into one forecast file and adds the thickness per step."""

    def __init__(self, cropper: GribCropper, workers: int = min(os.cpu_count() or 1, MAX_WORKERS)):
        self.cropper = cropper
        self.workers = workers

    def write(self, raw_files: list[Path], target: Path) -> int:
        """Crop every raw message into ``target`` (overwritten), add the thickness and return the message count.

        The messages keep the order of ``raw_files``; each thickness follows
        the second of gh 500/1000 hPa of its step.

        Raises:
            RuntimeError: if gh 500 or 1000 hPa is missing for a step.
        """
        spans = [span for raw in raw_files for span in message_spans(raw)]
        # Fitted once here, so the workers get the box grid with the cropper and the caller can read it.
        first = eccodes.codes_new_from_message(read_message(spans[0]))
        try:
            self.cropper.fit(first)
        finally:
            eccodes.codes_release(first)
        gh = {}  # step -> {level: (handle, values)} until both thickness levels of a step are there
        count = 0
        with (target.open("wb") as fh,
              ProcessPoolExecutor(self.workers, initializer=init_worker, initargs=(self.cropper,)) as pool):
            for message, values in pool.map(crop_message, spans, chunksize=CHUNK_SIZE):
                fh.write(message)
                count += 1
                if values is None:
                    continue
                gid = eccodes.codes_new_from_message(message)
                # The order of 500 and 1000 hPa within a step is not guaranteed.
                levels = gh.setdefault(eccodes.codes_get(gid, "step"), {})
                levels[eccodes.codes_get(gid, "level")] = (gid, values)
                if len(levels) == len(THICKNESS_LEVELS):
                    fh.write(self._thickness(levels))
                    count += 1
                    for handle, _ in levels.values():
                        eccodes.codes_release(handle)
                    levels.clear()
        if any(gh.values()):
            raise RuntimeError("gh 500/1000 hPa incomplete for some steps")
        return count

    def _thickness(self, levels: dict) -> bytes:
        """gh500 - gh1000 as a 1000-500 hPa layer message based on the 500 hPa message."""
        template, gh500 = levels[500]
        _, gh1000 = levels[1000]
        keys = {**THICKNESS_PARAM,
                "typeOfFirstFixedSurface": 100, "scaleFactorOfFirstFixedSurface": 0,
                "scaledValueOfFirstFixedSurface": 100000,
                "typeOfSecondFixedSurface": 100, "scaleFactorOfSecondFixedSurface": 0,
                "scaledValueOfSecondFixedSurface": 50000}
        gid = self.cropper.encode(template, gh500 - gh1000, keys)
        try:
            return eccodes.codes_get_message(gid)
        finally:
            eccodes.codes_release(gid)
