"""Download the bz2 files of one ICON-D2 run and join them into a single GRIB2 file."""

import bz2
import time
from pathlib import Path

import eccodes
import requests

from .forecast_writer import message_spans, read_message

RETRIES = 3
RETRY_DELAY = 10
TIMEOUT_S = 60


class IconDownloader:
    """Fetches the files of a run into a raw folder, keeping only messages on whole hours.

    tot_prec files also hold the sums at :15, :30 and :45 of the hour
    before; the charts use hourly steps only, and ForecastGrib indexes
    steps in hours. A raw file that exists is complete (written via .part),
    so an interrupted call can simply be repeated.
    """

    def __init__(self, raw_dir: Path):
        self.raw_dir = raw_dir

    def fetch(self, url: str) -> Path:
        """Raw GRIB2 file of one URL with the hourly messages, downloaded unless it is already there."""
        target = self.raw_dir / url.rsplit("/", 1)[1].removesuffix(".bz2")
        if target.exists():
            return target
        for attempt in range(1, RETRIES + 1):
            try:
                response = requests.get(url, timeout=TIMEOUT_S)
                response.raise_for_status()
                break
            except requests.RequestException:
                if attempt == RETRIES:
                    raise
                time.sleep(RETRY_DELAY * attempt)
        part = target.with_name(target.name + ".part")
        part.write_bytes(bz2.decompress(response.content))
        hourly = [message for message in map(read_message, message_spans(part)) if self._on_full_hour(message)]
        part.write_bytes(b"".join(hourly))
        part.replace(target)
        return target

    @staticmethod
    def _on_full_hour(message: bytes) -> bool:
        """Whether the step of a message is a whole number of hours (time invariant fields: 0)."""
        gid = eccodes.codes_new_from_message(message)
        try:
            # "12" in hours, or minutes with a unit: "0m" (time invariant), "675m" (11:15).
            step = eccodes.codes_get_string(gid, "endStep")
        finally:
            eccodes.codes_release(gid)
        return not step.endswith("m") or int(step[:-1]) % 60 == 0

    @staticmethod
    def join(raw_files: list[Path], target: Path) -> int:
        """Concatenate the raw files in the given order; returns the number of messages."""
        with target.open("wb") as out:
            for raw in raw_files:
                out.write(raw.read_bytes())
        return len(message_spans(target))
