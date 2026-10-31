"""Time axis of the diagram: valid times onto the plot width, day gridlines and ticks."""

from datetime import datetime, timedelta

from .diagram_layout import PLOT_BOTTOM, PLOT_LEFT, PLOT_RIGHT, PLOT_TOP

TICK_HOURS = 3
MIN_DAY_LABEL_WIDTH = 36  # px; narrower partial days stay unlabelled


class TimeAxis:
    """Linear mapping of valid times onto the plot width."""

    def __init__(self, start: datetime, end: datetime):
        self.start, self.end = start, end
        self.hours = (end - start).total_seconds() / 3600

    def x(self, moment: datetime) -> float:
        """Pixel column of a valid time."""
        hours = (moment - self.start).total_seconds() / 3600
        return PLOT_LEFT + hours / self.hours * (PLOT_RIGHT - PLOT_LEFT)

    def svg(self) -> list[str]:
        """Day gridlines at 00 UTC, centred date labels and 3-hourly ticks."""
        parts = [f'<line class="axis" x1="{PLOT_LEFT}" x2="{PLOT_RIGHT}" '
                 f'y1="{PLOT_BOTTOM}" y2="{PLOT_BOTTOM}"/>']
        first_day = self.start.replace(hour=0)
        day = first_day
        while day <= self.end:
            segment_start, segment_end = max(day, self.start), min(day + timedelta(days=1), self.end)
            if day >= self.start:
                x = self.x(day)
                parts.append(f'<line class="grid" x1="{x:.1f}" x2="{x:.1f}" y1="{PLOT_TOP}" y2="{PLOT_BOTTOM}"/>')
            left, right = self.x(segment_start), self.x(segment_end)
            if right - left >= MIN_DAY_LABEL_WIDTH:
                parts.append(f'<text x="{(left + right) / 2:.1f}" y="{PLOT_BOTTOM + 28}" '
                             f'text-anchor="middle">{day:%d.%m.}</text>')
            day += timedelta(days=1)

        # Minor ticks every 3 h, a longer one at 12 UTC and the longest at 00 UTC.
        tick = first_day
        while tick <= self.end:
            if tick >= self.start:
                length = 10 if tick.hour == 0 else 7 if tick.hour == 12 else 4
                x = self.x(tick)
                parts.append(f'<line class="axis" x1="{x:.1f}" x2="{x:.1f}" '
                             f'y1="{PLOT_BOTTOM}" y2="{PLOT_BOTTOM + length}"/>')
            tick += timedelta(hours=TICK_HOURS)
        parts.append(f'<text x="{PLOT_RIGHT + 8}" y="{PLOT_BOTTOM + 28}">UTC</text>')
        return parts
