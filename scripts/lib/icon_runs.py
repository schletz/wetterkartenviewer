"""Which ICON-D2 runs are published on the open data server of DWD, and which files make up one."""

import re
from datetime import datetime

import requests

from .icon_run import IconRun

BASE_URL = "https://opendata.dwd.de/weather/nwp/icon-d2/grib/"
# One folder per run hour, each holding the newest run of that hour; the model starts every 3 h.
RUN_HOURS = tuple(f"{hour:02d}" for hour in range(0, 24, 3))
MAX_STEP = 48
TIMEOUT_S = 30
# "<a href="clct/">clct/</a>   31-Oct-2026 07:22:12   -" in the nginx listings.
FOLDER = re.compile(r'<a href="([^"/]+)/">[^<]*</a>\s+(\d{2}-\w{3}-\d{4} \d{2}:\d{2}:\d{2})')
# icon-d2_germany_icosahedral_single-level_2026103106_012_2d_clct.grib2.bz2; the level is "2d" for
# single level fields, "0" for time invariant ones, hPa on pressure levels, a number on model levels.
FILE = re.compile(r'href="(icon-d2_germany_icosahedral_[a-z-]+_(\d{10})_(\d{3})_([0-9a-z]+)_[^"]+\.grib2\.bz2)"')
# Level of a parameter given without "@<level>".
SINGLE_LEVEL, TIME_INVARIANT = "2d", "0"


class IconRuns:
    """Finds the newest complete ICON-D2 run of a set of parameters (raw icosahedral grid).

    The time stamps of the run folders (00/, 03/ ...) never change; those
    of the parameter folders inside do, whenever a run is written. Their
    maximum per run folder orders the runs by age. A run counts once every
    forecast parameter reaches T+48; the newest folder may still be written,
    then the one before is taken.
    """

    def __init__(self, forecast_params: tuple[str, ...], static_params: tuple[str, ...]):
        """Parameters as named by the folders, e.g. "clct", "tot_prec", with "@<hPa>" on pressure levels ("t@850").

        Static parameters are time invariant.
        """
        self.forecast_params, self.static_params = forecast_params, static_params

    def latest(self) -> IconRun:
        """The newest complete run.

        Raises:
            RuntimeError: if no run folder holds a complete run.
        """
        for hour in sorted(RUN_HOURS, key=self._folder_time, reverse=True):
            run = self.complete_run(hour)
            if run is not None:
                return run
        raise RuntimeError(f"no complete ICON-D2 run on {BASE_URL}")

    def run(self, run: str) -> IconRun:
        """A given run (YYYYMMDDHH), if its folder still holds it complete.

        Raises:
            RuntimeError: if the run is no longer (or not yet completely) published.
        """
        found = self.complete_run(run[8:10])
        if found is None or found.run != run:
            raise RuntimeError(f"ICON-D2 run {run} is not (or no longer) completely published")
        return found

    def complete_run(self, hour: str) -> IconRun | None:
        """The run in the folder of one run hour, or None while it is incomplete."""
        params = (*self.static_params, *self.forecast_params)
        listings = {}
        files = {}
        for param in params:
            folder, level = self._split(param)
            if folder not in listings:
                listings[folder] = self._files(hour, folder)
            files[param] = [(run, step, name) for run, step, file_level, name in listings[folder] if file_level == level]
        runs = {run for listed in files.values() for run, _, _ in listed}
        if len(runs) != 1:
            # Old and new run side by side while the folder is rewritten, or no files at all.
            return None
        run = runs.pop()
        # DWD writes the steps in order, so a parameter with T+48 is complete.
        if any(not files[p] for p in params) or any(
                max(step for _, step, _ in files[p]) < MAX_STEP for p in self.forecast_params):
            return None
        url = lambda param, name: f"{BASE_URL}{hour}/{self._split(param)[0]}/{name}"  # noqa: E731
        static = [url(p, name) for p in self.static_params for _, _, name in files[p]]
        steps = sorted((step, params.index(p), url(p, name)) for p in self.forecast_params for _, step, name in files[p])
        return IconRun(run, tuple(static + [u for _, _, u in steps]))

    def _split(self, param: str) -> tuple[str, str]:
        """(folder, level in the file name) of a parameter."""
        folder, _, level = param.partition("@")
        return folder, level or (TIME_INVARIANT if param in self.static_params else SINGLE_LEVEL)

    def _folder_time(self, hour: str) -> datetime:
        """Newest time stamp of the parameter folders of a run folder; the oldest possible if unreadable."""
        try:
            listing = requests.get(f"{BASE_URL}{hour}/", timeout=TIMEOUT_S).text
        except requests.RequestException:
            return datetime.min
        wanted = {self._split(param)[0] for param in (*self.static_params, *self.forecast_params)}
        times = [datetime.strptime(stamp, "%d-%b-%Y %H:%M:%S") for name, stamp in FOLDER.findall(listing)
                 if name in wanted]
        return max(times, default=datetime.min)

    @staticmethod
    def _files(hour: str, folder: str) -> list[tuple[str, int, str, str]]:
        """(run, step, level, file name) of the icosahedral files in a parameter folder of a run folder."""
        listing = requests.get(f"{BASE_URL}{hour}/{folder}/", timeout=TIMEOUT_S)
        listing.raise_for_status()
        return [(run, int(step), level, name) for name, run, step, level in FILE.findall(listing.text)]
