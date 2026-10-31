"""Which requests a run is downloaded with, and how many GRIB messages each must yield."""

from datetime import datetime
from pathlib import Path

import eccodes

from .constants import PROFILE_LEVELS, WEATHER_PARAMS
from .derived_writer import PER_STEP
from .extreme_windows import ExtremeWindows


class RequestPlan:
    """Requests of one run for the given steps, keyed by the name of their raw file.

    Every request is a cartesian product of param x levelist x step, so a
    group only combines params and levels that are all wanted.
    """

    def __init__(self, steps: list[int], base_time: datetime):
        self.steps, self.base_time = steps, base_time
        steps_3h = [s for s in steps if 0 < s <= 144]
        steps_6h = [s for s in steps if s > 144]
        groups = {
            "t": dict(param="t", levelist=PROFILE_LEVELS, step=steps),
            "gh": dict(param="gh", levelist=PROFILE_LEVELS, step=steps),
            "r": dict(param="r", levelist=PROFILE_LEVELS, step=steps),
            "uvw700": dict(param=["u", "v", "w"], levelist=700, step=steps),
            "uv_low": dict(param=["u", "v"], levelist=[850, 925, 1000], step=steps),
            "sfc": dict(param=["msl", "2t", "10u", "10v"], step=steps),
            # Static fields, only in the T+0 file: model orography, its sub-grid roughness and
            # the land-sea mask; levtype keeps z of the pressure levels out.
            "static": dict(param=["z", "sdor", "lsm"], levtype="sfc", step=[0]),
            "minmax3": dict(param=["mx2t3", "mn2t3"], step=steps_3h),
            "minmax6": dict(param=["mx2t6", "mn2t6"], step=steps_6h),
            "weather": dict(param=list(WEATHER_PARAMS), step=steps),
        }
        self.groups = {name: req for name, req in groups.items() if req["step"]}

    @staticmethod
    def expected(request: dict) -> int:
        """Number of messages a request must yield (open data drops missing params silently)."""
        def count(key):
            value = request.get(key, [None])
            return len(value) if isinstance(value, list) else 1
        return count("param") * count("levelist") * count("step")

    def fields(self) -> set[tuple[str, int | None, int]]:
        """(param, level, end step) of every raw message the groups ask for; level None without levelist."""
        def listed(value):
            return value if isinstance(value, list) else [value]
        return {(param, level, step) for request in self.groups.values() for param in listed(request["param"])
                for level in listed(request.get("levelist")) for step in request["step"]}

    def expected_total(self) -> int:
        """Messages of a complete forecast file: every group, then per step the thickness and the
        derived fields, the orography in m and one daily maximum or minimum per complete day."""
        raw = sum(self.expected(req) for req in self.groups.values())
        intervals = [(name, step - hours, step)
                     for group, hours in (("minmax3", 3), ("minmax6", 6)) if group in self.groups
                     for name in self.groups[group]["param"] for step in self.groups[group]["step"]]
        windows, last = ExtremeWindows(intervals, self.base_time), max(self.steps)
        extremes = len(windows.days("max", last)) + len(windows.days("min", last))
        return raw + len(self.steps) * (1 + PER_STEP) + 1 + extremes

    def output_complete(self, path: Path) -> bool:
        """Whether the output file holds exactly the messages of expected_total."""
        return count_messages(path) == self.expected_total()


def count_messages(path: Path) -> int:
    """Number of GRIB messages in a file, 0 if it does not exist."""
    if not path.exists():
        return 0
    with path.open("rb") as fh:
        return eccodes.codes_count_in_file(fh)
