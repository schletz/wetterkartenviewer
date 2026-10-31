"""Download of the request groups of one run into raw global GRIB files."""

import time
from datetime import datetime
from pathlib import Path

import requests
from ecmwf.opendata import Client

from .request_plan import RequestPlan, count_messages

RETRIES = 3
RETRY_DELAY = 30  # seconds, multiplied by the attempt number


class GroupDownloader:
    """Fetches request groups of one run into ``raw_dir``; a raw file that is already complete is kept."""

    def __init__(self, client: Client, run: datetime, raw_dir: Path):
        self.client, self.run, self.raw_dir = client, run, raw_dir

    def retrieve(self, name: str, request: dict) -> Path:
        """Download one request group unless its raw file is already complete.

        Raises:
            RuntimeError: if the run is not published or a group stays incomplete.
        """
        target = self.raw_dir / f"{name}.grib2"
        expected = RequestPlan.expected(request)
        if count_messages(target) == expected:
            print(f"{name}: already on disk", flush=True)
            return target
        for attempt in range(1, RETRIES + 1):
            try:
                started = time.monotonic()
                self.client.retrieve(date=self.run.strftime("%Y%m%d"), time=self.run.hour, type="fc", stream="oper",
                                     target=str(target), **request)
                break
            except Exception as error:  # pylint: disable=broad-except  # network and index errors alike
                not_found = isinstance(error, requests.HTTPError) and error.response.status_code == 404
                if not_found:
                    raise RuntimeError(f"{name}: run {self.run:%Y%m%d%H} is not (or no longer) published") from error
                if attempt == RETRIES:
                    raise
                print(f"{name}: attempt {attempt} failed ({error}), retrying", flush=True)
                time.sleep(RETRY_DELAY * attempt)
        found = count_messages(target)
        if found != expected:
            raise RuntimeError(f"{name}: {found} messages instead of {expected}")
        print(f"{name}: {found} messages, {target.stat().st_size / 1e6:.0f} MB "
              f"in {time.monotonic() - started:.0f}s", flush=True)
        return target
