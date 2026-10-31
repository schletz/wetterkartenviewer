"""Download the bz2 files of one ICON-D2 run and join them into a single GRIB2 file."""

import bz2
import re
import sys
import time
from pathlib import Path

import eccodes
import requests

from .forecast_writer import message_spans, read_message
from .missing_values import missing_message

RETRIES = 3
RETRY_DELAY = 10
TIMEOUT_S = 60
# Step in a DWD file name: icon-d2_germany_icosahedral_single-level_2026103109_012_2d_clct.grib2
STEP = re.compile(r"_\d{10}_(\d{3})_")


class IconDownloader:
    """Fetches the files of a run into a raw folder, keeping only messages on whole hours.

    tot_prec files also hold the sums at :15, :30 and :45 of the hour
    before; the charts use hourly steps only, and ForecastGrib indexes
    steps in hours. A raw file that exists was written via .part, so an
    interrupted call can simply be repeated. A file the server lacks or
    delivers damaged becomes a placeholder with missing values when the
    files are joined.
    """

    def __init__(self, raw_dir: Path):
        self.raw_dir = raw_dir

    def raw_file(self, url: str) -> Path:
        """Raw file of a URL in the raw folder."""
        return self.raw_dir / url.rsplit("/", 1)[1].removesuffix(".bz2")

    def fetch(self, url: str) -> Path | None:
        """Raw GRIB2 file of one URL with the hourly messages, downloaded unless it is already there;
        None if the server lacks the file or it stays damaged after the last attempt."""
        target = self.raw_file(url)
        if target.exists():
            return target
        part = target.with_name(target.name + ".part")
        for attempt in range(1, RETRIES + 1):
            try:
                response = requests.get(url, timeout=TIMEOUT_S)
                response.raise_for_status()
                part.write_bytes(bz2.decompress(response.content))
                hourly = [message for message in map(read_message, message_spans(part)) if self._on_full_hour(message)]
                break
            except (requests.RequestException, OSError, ValueError, EOFError, eccodes.CodesInternalError) as error:
                if attempt == RETRIES:
                    print(f"warning: {target.name}: {error}", file=sys.stderr, flush=True)
                    part.unlink(missing_ok=True)
                    return None
                time.sleep(RETRY_DELAY * attempt)
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

    def join(self, urls: list[str], raw_files: list[Path | None], target: Path) -> int:
        """Concatenate the raw files in the given order; returns the number of messages.

        A file that is missing (None) or holds no intact message is replaced
        by a placeholder copied from the same field at another step; without
        such a file it is left out, and the count falls short.
        """
        intact = [raw is not None and bool(self._messages(raw)) for raw in raw_files]
        # Field of a file: its name without the step; the first intact file of a field is the template.
        field = lambda url: STEP.sub("_", url.rsplit("/", 1)[1], count=1)  # noqa: E731
        templates = {}
        for url, raw, ok in zip(urls, raw_files, intact):
            if ok:
                templates.setdefault(field(url), raw)
        replaced, lost = [], []
        count = 0
        with target.open("wb") as out:
            for url, raw, ok in zip(urls, raw_files, intact):
                if ok:
                    messages = self._messages(raw)
                elif field(url) in templates:
                    template = self._messages(templates[field(url)])[0]
                    messages = [missing_message(template, int(STEP.search(url).group(1)))]
                    replaced.append(self.raw_file(url).name)
                else:
                    lost.append(self.raw_file(url).name)
                    continue
                for message in messages:
                    out.write(message)
                count += len(messages)
        if replaced:
            print(f"warning: {len(replaced)} files lost on the server, written with missing values: "
                  f"{', '.join(replaced)}", file=sys.stderr, flush=True)
        if lost:
            print(f"warning: {len(lost)} files lost without a template: {', '.join(lost)}", file=sys.stderr, flush=True)
        return count

    @staticmethod
    def _messages(raw: Path) -> list[bytes]:
        """Intact messages of a raw file whose header decodes."""
        messages = []
        for message in map(read_message, message_spans(raw)):
            try:
                eccodes.codes_release(eccodes.codes_new_from_message(message))
            except eccodes.CodesInternalError:
                continue
            messages.append(message)
        return messages
