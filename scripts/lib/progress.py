"""Line-wise progress of a long task, the same in a terminal and in a redirected log."""

import threading
import time

BAR_WIDTH = 20
# Seconds after which a finished item prints a line even within the same percent step.
HEARTBEAT_S = 30


class Progress:
    """Counts finished work and prints a line per ``every`` percent, with bar, count and time left.

    Only whole lines are written, never carriage returns: a log file, an agent
    reading the redirected output and update_maps.py, which passes the output of
    its subprocesses on line by line, see the same as a terminal. The first line
    is printed on construction, so a task announces its size before its first
    item finishes. ``every=0`` prints a line per item (few, slow items such as
    videos). The time left is extrapolated from the rate so far, so it is only
    meaningful if ``amount`` reflects the work of an item (e.g. MB for files of
    very different size). advance() may be called from several threads.

    Example line: ``render opencharts_europe [######..............] 30 % 390/1300 charts, 0:45, 1:45 left``
    """

    def __init__(self, label: str, total: float, unit: str = "", every: float = 10):
        self.label, self.total, self.unit, self.every = label, total, unit, every
        self.done = 0.0
        self.started = self.printed_at = time.monotonic()
        self.mark = 0
        self.lock = threading.Lock()
        self._print("")

    def advance(self, item: str = "", amount: float = 1) -> None:
        """Count ``amount`` as done and print a line if a step of ``every`` percent was passed.

        A line is also printed for the last item and HEARTBEAT_S after the previous one;
        ``item`` names what just finished and ends the line.
        """
        with self.lock:
            self.done += amount
            mark = int(self._percent() // self.every) if self.every else self.done
            now = time.monotonic()
            if mark != self.mark or self.done >= self.total or now - self.printed_at >= HEARTBEAT_S:
                self.mark, self.printed_at = mark, now
                self._print(item)

    def _percent(self) -> float:
        return min(100.0, 100 * self.done / self.total) if self.total else 100.0

    def _print(self, item: str) -> None:
        percent, elapsed = self._percent(), time.monotonic() - self.started
        filled = round(BAR_WIDTH * percent / 100)
        unit = f" {self.unit}" if self.unit else ""
        line = (f"{self.label} [{'#' * filled}{'.' * (BAR_WIDTH - filled)}] {percent:3.0f} % "
                f"{self.done:.0f}/{self.total:.0f}{unit}, {self.duration(elapsed)}")
        if 0 < self.done < self.total:
            line += f", {self.duration(elapsed * (self.total - self.done) / self.done)} left"
        print(line + (f": {item}" if item else ""), flush=True)

    @staticmethod
    def duration(seconds: float) -> str:
        """m:ss, or h:mm:ss from one hour on."""
        minutes, secs = divmod(round(seconds), 60)
        hours, minutes = divmod(minutes, 60)
        return f"{hours}:{minutes:02d}:{secs:02d}" if hours else f"{minutes}:{secs:02d}"
