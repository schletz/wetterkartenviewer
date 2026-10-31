"""Download of the request groups of one run into raw global GRIB files."""

import time
from datetime import datetime
from pathlib import Path

import requests
from ecmwf.opendata import Client

from .request_plan import RequestPlan, count_messages

RETRIES = 3
RETRY_DELAY = 30  # seconds, multiplied by the attempt number


def not_found(error: Exception) -> bool:
    """Whether an error of the client is a 404, i.e. the server lacks a file of the request."""
    return isinstance(error, requests.HTTPError) and error.response is not None and error.response.status_code == 404


class GroupDownloader:
    """Fetches request groups of one run into ``raw_dir``; a raw file that is already complete is kept.

    The server sometimes lacks a step file or delivers a damaged one. A
    group is then fetched step by step without the missing steps, and an
    incomplete raw file is kept with a warning: ForecastWriter replaces the
    lost fields by placeholders with missing values. Messages go to stdout,
    as the caller mutes stderr while downloading.
    """

    def __init__(self, client: Client, run: datetime, raw_dir: Path):
        self.client, self.run, self.raw_dir = client, run, raw_dir

    def retrieve(self, name: str, request: dict) -> Path:
        """Download one request group unless its raw file is already complete.

        Raises:
            RuntimeError: if the server has none of the steps of the group (run not published).
        """
        target = self.raw_dir / f"{name}.grib2"
        expected = RequestPlan.expected(request)
        if count_messages(target) == expected:
            print(f"{name}: already on disk", flush=True)
            return target
        started = time.monotonic()
        try:
            self._fetch(name, target, request)
        except requests.HTTPError as error:
            if not not_found(error):
                raise
            self._fetch_steps(name, target, request)
        found = count_messages(target)
        if found != expected:
            print(f"warning: {name}: {found} messages instead of {expected}, the others get missing values",
                  flush=True)
        print(f"{name}: {found} messages, {target.stat().st_size / 1e6:.0f} MB "
              f"in {time.monotonic() - started:.0f}s", flush=True)
        return target

    def _fetch(self, name: str, target: Path, request: dict) -> None:
        """One request with retries; a 404 is raised at once, other errors after the last attempt."""
        for attempt in range(1, RETRIES + 1):
            try:
                self.client.retrieve(date=self.run.strftime("%Y%m%d"), time=self.run.hour, type="fc", stream="oper",
                                     target=str(target), **request)
                return
            except Exception as error:  # pylint: disable=broad-except  # network and index errors alike
                if not_found(error) or attempt == RETRIES:
                    raise
                print(f"{name}: attempt {attempt} failed ({error}), retrying", flush=True)
                time.sleep(RETRY_DELAY * attempt)

    def _fetch_steps(self, name: str, target: Path, request: dict) -> None:
        """The group step by step into ``target``, leaving out the steps the server lacks.

        Raises:
            RuntimeError: if every step is missing.
        """
        parts, absent = [], []
        for step in request["step"]:
            part = target.with_name(f"{target.stem}.{step}.part")
            try:
                self._fetch(name, part, {**request, "step": [step]})
                parts.append(part)
            except requests.HTTPError as error:
                if not not_found(error):
                    raise
                absent.append(step)
        if not parts:
            raise RuntimeError(f"{name}: run {self.run:%Y%m%d%H} is not (or no longer) published")
        with target.open("wb") as fh:
            for part in parts:
                fh.write(part.read_bytes())
                part.unlink()
        if absent:
            print(f"warning: {name}: steps {', '.join(map(str, absent))} missing on the server", flush=True)
