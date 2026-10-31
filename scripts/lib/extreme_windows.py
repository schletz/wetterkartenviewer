"""Which 3 and 6 hour 2 m extremes of a run make up the daily maximum and minimum."""

from datetime import date, datetime, timedelta

# Synoptic convention for daily extremes, in UTC hours relative to the day:
# the maximum over 06-18 UTC covers the afternoon everywhere in Europe,
# the minimum over 18 UTC of the previous day to 06 UTC covers the night.
EXTREME_WINDOWS = {"max": (6, 18), "min": (-6, 6)}
EXTREME_PARAMS = {"max": ("mx2t3", "mx2t6"), "min": ("mn2t3", "mn2t6")}


class ExtremeWindows:
    """Daily windows tiled by the extreme intervals of one run.

    Works on (shortName, start step, end step) triples, so the same rule
    serves a forecast file (ForecastGrib) and a download that does not
    exist yet (RequestPlan).
    """

    def __init__(self, intervals: list[tuple[str, int, int]], base_time: datetime):
        self.intervals, self.base_time = intervals, base_time

    def parts(self, kind: str, day: date) -> list[tuple[str, int]] | None:
        """(shortName, end step) of the intervals that tile the window of a day, None if incomplete."""
        start, end = self.window(kind, day)
        parts, covered = [], 0
        for name, start_step, end_step in self.intervals:
            if name in EXTREME_PARAMS[kind] and start <= start_step and end_step <= end:
                parts.append((name, end_step))
                covered += end_step - start_step
        return parts if parts and covered == end - start else None

    def days(self, kind: str, last_step: int) -> list[date]:
        """Calendar days (UTC) up to the valid time of ``last_step`` whose window is complete."""
        last = (self.base_time + timedelta(hours=last_step)).date()
        first = self.base_time.date()
        candidates = [first + timedelta(days=n) for n in range((last - first).days + 1)]
        return [day for day in candidates if self.parts(kind, day)]

    def window(self, kind: str, day: date) -> tuple[int, int]:
        """(start step, end step) of the window of a day, in hours from the base time."""
        midnight = datetime(day.year, day.month, day.day)
        start, end = (int((midnight + timedelta(hours=hour) - self.base_time).total_seconds() // 3600)
                      for hour in EXTREME_WINDOWS[kind])
        return start, end
