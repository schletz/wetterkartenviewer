"""Which ECMWF open data runs are published, at 0.1 deg and at 0.25 deg."""

import re
from datetime import datetime, timedelta

import requests
from ecmwf.opendata import Client

MAX_STEP = 240
# Directory listing of a run; its 0p1/ folder appears once the run is complete at 0.1 deg,
# about 2 h after the 0p25/ folder, and the next 00z or 12z run follows 12 h later.
LISTING_URL = "https://data.ecmwf.int/forecasts/{run:%Y%m%d}/{run:%H}z/ifs/"
RUN_INTERVAL = timedelta(hours=12)


class OpenDataRuns:
    """Finds the newest complete run and notices one that is still on its way."""

    def __init__(self, client: Client, preview_client: Client):
        """Use two clients of the same source.

        Args:
            client: client of the resolution that is downloaded (0.1 deg).
            preview_client: client of the coarser resolution that is published first (0.25 deg).
        """
        self.client, self.preview_client = client, preview_client

    def latest(self, client: Client | None = None) -> datetime:
        """Newest run that already has T+240, i.e. the newest complete 00z or 12z run."""
        return (client or self.client).latest(type="fc", stream="oper", step=MAX_STEP, param="t", levelist=850)

    def pending_notice(self, run: datetime) -> str | None:
        """Notice if a newer 00z or 12z run is already out at the preview resolution only."""
        try:
            newer = self.latest(self.preview_client)
        except Exception:  # pylint: disable=broad-except  # only a hint, never a reason to fail
            return None
        if newer <= run:
            return None
        published = self.folder_time(run)
        expected = f"; expected around {published + RUN_INTERVAL:%d.%m. %H:%M} UTC" if published else ""
        return f"run {newer:%Y%m%d%H} is published at 0.25 deg but not yet at 0.1 deg{expected}"

    @staticmethod
    def folder_time(run: datetime) -> datetime | None:
        """Time stamp (UTC) of the 0p1/ folder of a run on data.ecmwf.int, None if it cannot be read."""
        try:
            listing = requests.get(LISTING_URL.format(run=run), timeout=30).text
        except requests.RequestException:
            return None
        match = re.search(r"\b0p1/\s+(\d{2}-\d{2}-\d{4} \d{2}:\d{2})", re.sub(r"<[^>]+>", " ", listing))
        return datetime.strptime(match.group(1), "%d-%m-%Y %H:%M") if match else None
