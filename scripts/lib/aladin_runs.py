"""Find the runs of CHMI ALADIN (2.3 km) in the directory listings of the CHMI open data server."""

import re
import time

import requests

BASE_URL = "https://opendata.chmi.cz/meteorology/weather/nwp_aladin/Lambert_2.3km/"
CYCLES = ("00", "06", "12", "18")
# File in a listing: ALADLAMB4opendata_2026110900_CLSTEMPERATURE.grb.bz2
FILE = re.compile(r'href="ALADLAMB4opendata_(\d{10})_([0-9A-Z_]+)\.grb\.bz2"')
RETRIES = 3
RETRY_DELAY = 10
TIMEOUT_S = 60


class AladinRuns:
    """The runs on the server; the server keeps each cycle for about three days."""

    def __init__(self, variables: tuple[str, ...]):
        """Look for the runs that hold the given variables, named as in the file names."""
        self.variables = set(variables)

    def latest(self) -> str:
        """Newest run (YYYYMMDDHH) with a file of every variable.

        Raises:
            RuntimeError: if no run has all of them.
        """
        complete = [run for run, found in self._listing().items() if self.variables <= found]
        if not complete:
            raise RuntimeError("no complete CHMI ALADIN run on the server")
        return max(complete)

    def has(self, run: str) -> bool:
        """Whether a run has a file of every variable; older runs are gone from the server."""
        return self.variables <= self._listing().get(run, set())

    @staticmethod
    def url(run: str, variable: str) -> str:
        """URL of the file of one variable of a run."""
        return f"{BASE_URL}{run[-2:]}/ALADLAMB4opendata_{run}_{variable}.grb.bz2"

    @staticmethod
    def _listing() -> dict[str, set[str]]:
        """Variables per run, over the folders of all cycles."""
        found: dict[str, set[str]] = {}
        for cycle in CYCLES:
            for run, variable in FILE.findall(AladinRuns._page(f"{BASE_URL}{cycle}/")):
                found.setdefault(run, set()).add(variable)
        return found

    @staticmethod
    def _page(url: str) -> str:
        """Text of a listing; a failure after the last attempt raises."""
        for attempt in range(1, RETRIES + 1):
            try:
                response = requests.get(url, timeout=TIMEOUT_S)
                response.raise_for_status()
                return response.text
            except requests.RequestException:
                if attempt == RETRIES:
                    raise
                time.sleep(RETRY_DELAY)
        raise AssertionError("unreachable")
