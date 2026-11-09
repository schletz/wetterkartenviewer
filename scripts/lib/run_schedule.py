"""When the next run of a model can be on its server, so that a download need not ask any earlier."""

from datetime import datetime, timedelta, timezone
from pathlib import Path


class RunSchedule:
    """Publication rhythm of one model and the run files it leaves in a data directory.

    Only a time before which asking is pointless: a run that comes late is simply found
    by a later call, and a run older than the rhythm allows is looked for at once.
    """

    def __init__(self, prefix: str, suffix: str, interval: timedelta, ready_after: timedelta):
        """Describe one model.

        Args:
            prefix, suffix: name of a run file around its YYYYMMDDHH, e.g. "icon-d2_" and ".grb2".
            interval: time between two runs.
            ready_after: time after the start of a run from which it can be complete; the earliest
                time measured less a margin, since a later value would hold back runs that come early.
        """
        self.prefix, self.suffix, self.interval, self.ready_after = prefix, suffix, interval, ready_after

    def next_check(self, run: datetime) -> datetime:
        """Time from which the run after `run` can be complete."""
        return run + self.interval + self.ready_after

    def file_until_next_run(self, directory: Path, now: datetime | None = None) -> Path | None:
        """The newest finished run file if the run after it cannot be complete yet, else None.

        None also without a file and for a target that is no directory. Unfinished downloads end
        in .part or .raw and do not match.

        Args:
            directory: target given to the downloader.
            now: time in UTC, naive; default the current time.
        """
        if not directory.is_dir():
            return None
        files = sorted(directory.glob(f"{self.prefix}*{self.suffix}"))
        if not files:
            return None
        try:
            run = datetime.strptime(files[-1].name.removeprefix(self.prefix).removesuffix(self.suffix), "%Y%m%d%H")
        except ValueError:
            return None
        check = self.next_check(run)
        if (now or datetime.now(timezone.utc).replace(tzinfo=None)) >= check:
            return None
        print(f"run {run + self.interval:%Y%m%d%H} cannot be complete before {check:%d.%m. %H:%M} UTC, keeping {files[-1].name}")
        return files[-1].resolve()
