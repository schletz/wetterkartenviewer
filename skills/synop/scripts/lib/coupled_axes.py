"""Value axes of the diagram: T850 on the left, the 1000-500 hPa thickness on the right.

Both quantities measure the temperature of the air mass, so the two
scales are coupled: thickness = 544 dam + 1.6 dam/K * T850. With that
coupling both curves lie on top of each other for typical Central
European air masses; where they part, the column is colder or warmer
than the 850 hPa level suggests.

Without explicit limits the T850 axis is fitted to the data, so that
changes of a few kelvin stay visible: it runs from 4 * (min // 4) to
4 * (max // 4 + 1), where min and max cover T850, the climate mean and
the thickness converted to its T850 equivalent, so no curve is clipped.
A missing thickness limit follows from the T850 axis through the
coupling. The gridlines follow the T850 axis in whole kelvin; the
thickness axis has its own ticks in whole multiples of 4 dam.
"""

import math

from .diagram_layout import PLOT_BOTTOM, PLOT_LEFT, PLOT_RIGHT, PLOT_TOP
from .diagram_row import DiagramRow

THICKNESS_AT_ZERO = 544.0
THICKNESS_PER_KELVIN = 1.6
AXIS_ROUNDING = 4.0  # K, the automatic T850 limits are multiples of it

# Candidate spacings of the T850 gridlines and the thickness ticks; the
# first one yielding at most MAX_GRID_INTERVALS wins. Whole numbers keep
# decimals off the axes; 4 dam is one band of the thickness shading.
GRID_STEPS = (2.0, 4.0, 8.0, 16.0)
THICKNESS_STEPS = (4.0, 8.0, 16.0, 32.0)
MAX_GRID_INTERVALS = 12
FALLBACK_GRID_INTERVALS = 10  # for explicit limits no step divides evenly
THICKNESS_TICK_LENGTH = 5


class CoupledAxes:
    """The T850 range (deg C) and thickness range (dam) of the plot height."""

    def __init__(self, t_range: tuple[float, float], z_range: tuple[float, float]):
        """Set both ranges.

        Raises:
            ValueError: unless each range is finite with its minimum below its maximum.
        """
        if not (t_range[0] < t_range[1] and z_range[0] < z_range[1]) or not all(
                map(math.isfinite, t_range + z_range)):
            raise ValueError("Each axis needs a finite minimum below its maximum")
        self.t_range, self.z_range = t_range, z_range

    @classmethod
    def fit(cls, rows: list[DiagramRow], t_min=None, t_max=None, z_min=None, z_max=None) -> "CoupledAxes":
        """Axes fitted to the data; every limit that is given replaces its fitted value.

        Every limit that is not given falls back on its own, so a single
        explicit limit does not discard the fitted other one.

        Raises:
            ValueError: if the data holds no value at all, or the limits are invalid.
        """
        auto = cls._auto_t850_range(rows)
        t_range = (auto[0] if t_min is None else t_min, auto[1] if t_max is None else t_max)
        z_range = (cls.coupled_thickness(t_range[0]) if z_min is None else z_min,
                   cls.coupled_thickness(t_range[1]) if z_max is None else z_max)
        return cls(t_range, z_range)

    @staticmethod
    def coupled_thickness(t850: float) -> float:
        """Thickness in dam that corresponds to a T850 value on the axes."""
        return THICKNESS_AT_ZERO + THICKNESS_PER_KELVIN * t850

    @staticmethod
    def _auto_t850_range(rows: list[DiagramRow]) -> tuple[float, float]:
        values = [row.t850 for row in rows if row.t850 is not None]
        values += [row.climate for row in rows if row.climate is not None]
        values += [(row.thickness - THICKNESS_AT_ZERO) / THICKNESS_PER_KELVIN
                   for row in rows if row.thickness is not None]
        if not values:
            raise ValueError("no T850 or thickness values")
        step = AXIS_ROUNDING
        return step * (min(values) // step), step * (max(values) // step + 1)

    def t_y(self, value: float) -> float:
        """Pixel row of a T850 value."""
        return self._y(value, *self.t_range)

    def z_y(self, value: float) -> float:
        """Pixel row of a thickness value."""
        return self._y(value, *self.z_range)

    @staticmethod
    def _y(value: float, low: float, high: float) -> float:
        return PLOT_TOP + (high - value) / (high - low) * (PLOT_BOTTOM - PLOT_TOP)

    def svg(self) -> list[str]:
        """Gridlines labelled with T850 on the left, thickness ticks on the right."""
        parts = []
        t_range = self.t_range
        intervals = self._grid_intervals()
        for i in range(intervals + 1):
            share = i / intervals
            y = PLOT_TOP + share * (PLOT_BOTTOM - PLOT_TOP)
            t_value = t_range[1] - share * (t_range[1] - t_range[0])
            parts.append(f'<line class="grid" x1="{PLOT_LEFT}" x2="{PLOT_RIGHT}" y1="{y:.1f}" y2="{y:.1f}"/>')
            parts.append(f'<text x="{PLOT_LEFT - 8}" y="{y + 4:.1f}" text-anchor="end">{label(t_value)}</text>')
        parts.append(f'<line class="axis" x1="{PLOT_RIGHT}" x2="{PLOT_RIGHT}" y1="{PLOT_TOP}" y2="{PLOT_BOTTOM}"/>')
        for z_value in self._thickness_ticks():
            y = self.z_y(z_value)
            parts.append(f'<line class="axis" x1="{PLOT_RIGHT}" x2="{PLOT_RIGHT + THICKNESS_TICK_LENGTH}" '
                         f'y1="{y:.1f}" y2="{y:.1f}"/>')
            parts.append(f'<text x="{PLOT_RIGHT + 8}" y="{y + 4:.1f}">{label(z_value)}</text>')
        if t_range[0] < 0 < t_range[1]:
            y = self.t_y(0)
            parts.append(f'<line class="zero" x1="{PLOT_LEFT}" x2="{PLOT_RIGHT}" y1="{y:.1f}" y2="{y:.1f}"/>')
        return parts

    def _grid_intervals(self) -> int:
        """Number of gridline intervals of the T850 range.

        Prefers a spacing from GRID_STEPS that divides the range evenly, so
        the labels are round numbers; explicit odd limits fall back to a
        fixed count.
        """
        span = self.t_range[1] - self.t_range[0]
        for step in GRID_STEPS:
            count = span / step
            if count <= MAX_GRID_INTERVALS and abs(count - round(count)) < 1e-9:
                return round(count)
        return FALLBACK_GRID_INTERVALS

    def _thickness_ticks(self) -> list[float]:
        """Multiples of the coarsest fitting step within the thickness range.

        The thickness axis is labelled independently of the T850 gridlines:
        with the coupling of 1.6 dam/K, a whole number of kelvin rarely maps
        to a whole number of decametres.
        """
        z_range = self.z_range
        for step in THICKNESS_STEPS:
            if (z_range[1] - z_range[0]) / step <= MAX_GRID_INTERVALS:
                break
        first = math.ceil(z_range[0] / step - 1e-9)
        last = math.floor(z_range[1] / step + 1e-9)
        return [n * step for n in range(first, last + 1)]


def label(value: float) -> str:
    """Format an axis value without needless decimals."""
    return f"{round(value, 2):g}".replace("-", "−")
