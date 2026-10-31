"""SVG diagram of T850 and the 1000-500 hPa thickness over the forecast, with the T850 anomaly.

A grey line shows the climate mean of T850 for the time of day and year
of every valid time. The area between it and the forecast is red where
the forecast is warmer and blue where it is colder, one shade darker
beyond every standard deviation, so sign and size of the anomaly of the
air mass show at a glance.

Every valid time has a hover target with a native tooltip and a
crosshair, so the SVG needs no script. Colours follow the light or dark
colour scheme of the viewer.
"""

from xml.sax.saxutils import escape

from .anomaly_bands import WARM, AnomalyBands
from .coupled_axes import CoupledAxes
from .diagram_layout import HEIGHT, MARGIN_TOP, PLOT_BOTTOM, PLOT_LEFT, PLOT_RIGHT, PLOT_TOP, WIDTH
from .diagram_row import DiagramRow
from .time_axis import TimeAxis

# Each anomaly layer adds LAYER_OPACITY of red or blue on top.
LAYER_OPACITY = 0.2

# T850 is drawn in the ink colour, so it never mixes up with the red and
# blue anomaly areas; the thickness is additionally dashed so the series
# never differ by colour alone.
STYLE = """
.synop-chart { --surface:#fcfcfb; --ink:#0b0b0b; --ink-2:#52514e; --grid:#e3e2de;
  --axis:#a9a8a2; --t850:#0b0b0b; --thickness:#eb6834; --climate:#8a8984;
  --warm:#e0453a; --cold:#3a7be0;
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif; }
@media (prefers-color-scheme: dark) {
  .synop-chart { --surface:#1a1a19; --ink:#f0efec; --ink-2:#c3c2b7; --grid:#33322f;
    --axis:#6b6a65; --t850:#f0efec; --thickness:#d95926; --climate:#9c9b95;
    --warm:#f0645a; --cold:#5a95f0; }
}
.synop-chart .bg { fill: var(--surface); }
.synop-chart .grid { stroke: var(--grid); stroke-width: 1; }
.synop-chart .zero { stroke: var(--axis); stroke-width: 1; stroke-dasharray: 4 3; }
.synop-chart .axis { stroke: var(--axis); stroke-width: 1; }
.synop-chart text { fill: var(--ink-2); font-size: 12px; }
.synop-chart .title { fill: var(--ink); font-size: 13px; font-weight: 600; }
.synop-chart .line { fill: none; stroke-width: 2; stroke-linejoin: round; stroke-linecap: round; }
.synop-chart .t850 { stroke: var(--t850); }
.synop-chart .thickness { stroke: var(--thickness); stroke-dasharray: 7 4; }
.synop-chart .climate { stroke: var(--climate); stroke-width: 1.5; }
.synop-chart .warm { fill: var(--warm); }
.synop-chart .cold { fill: var(--cold); }
.synop-chart .dot-t850 { fill: var(--t850); }
.synop-chart .dot-thickness { fill: var(--thickness); }
.synop-chart .hit circle { stroke: var(--surface); stroke-width: 2; }
.synop-chart .hit rect { fill: transparent; pointer-events: all; }
.synop-chart .hit .cross { stroke: var(--ink-2); stroke-width: 1; }
.synop-chart .hit .cross, .synop-chart .hit circle { opacity: 0; }
.synop-chart .hit:hover .cross, .synop-chart .hit:hover circle { opacity: 1; }
""" + f".synop-chart .warm, .synop-chart .cold {{ fill-opacity: {LAYER_OPACITY}; }}\n"


class ForecastDiagram:
    """Assembles the SVG document from the rows and their axes."""

    def __init__(self, rows: list[DiagramRow], time_axis: TimeAxis, axes: CoupledAxes, bands: AnomalyBands,
                 climate_label: str):
        """Wire the parts.

        Args:
            rows: valid times in ascending order.
            time_axis: horizontal axis over the valid times.
            axes: T850 and thickness axes.
            bands: sigma layers of the anomaly areas.
            climate_label: name of the climate mean, e.g. "Ø 1991–2020".
        """
        self.rows, self.time_axis, self.axes, self.bands = rows, time_axis, axes, bands
        self.climate_label = climate_label

    def svg(self) -> str:
        """The complete SVG document."""
        rows = self.rows
        summary = (f"T850 and 1000-500 hPa thickness from {rows[0].valid:%d.%m.%Y %H} UTC "
                   f"to {rows[-1].valid:%d.%m.%Y %H} UTC")
        parts = [f'<svg xmlns="http://www.w3.org/2000/svg" class="synop-chart" viewBox="0 0 {WIDTH} {HEIGHT}" '
                 f'role="img" aria-label="{escape(summary)}">',
                 f"<title>{escape(summary)}</title>",
                 f"<style>{STYLE}</style>",
                 f'<rect class="bg" width="{WIDTH}" height="{HEIGHT}"/>',
                 '<defs><clipPath id="synop-plot">'
                 f'<rect x="{PLOT_LEFT}" y="{PLOT_TOP}" width="{PLOT_RIGHT - PLOT_LEFT}" '
                 f'height="{PLOT_BOTTOM - PLOT_TOP}"/></clipPath></defs>']
        parts += self.axes.svg()
        parts += self.time_axis.svg()
        parts.append('<g clip-path="url(#synop-plot)">')
        # Anomaly areas and climate mean underneath, thickness next, so the
        # T850 line of the left axis stays on top.
        climate = any(row.climate is not None for row in rows)
        if climate:
            parts += self._anomaly_areas()
            parts.append(f'<path class="line climate" d="{self._series_path("climate", self.axes.t_y)}"/>')
        parts.append(f'<path class="line thickness" d="{self._series_path("thickness", self.axes.z_y)}"/>')
        parts.append(f'<path class="line t850" d="{self._series_path("t850", self.axes.t_y)}"/>')
        parts.append("</g>")
        parts += self._legend(climate)
        parts += self._hover()
        parts.append("</svg>")
        return "\n".join(parts) + "\n"

    def _series_path(self, attribute: str, to_y) -> str:
        """SVG path data of one series; missing values break the line."""
        commands, pen_down = [], False
        for row in self.rows:
            value = getattr(row, attribute)
            if value is None:
                pen_down = False
                continue
            point = f"{self.time_axis.x(row.valid):.1f},{to_y(value):.1f}"
            commands.append(("L" if pen_down else "M") + point)
            pen_down = True
        return " ".join(commands)

    def _anomaly_areas(self) -> list[str]:
        """Filled areas between T850 and its climate mean in steps of the standard deviation.

        For every step k one translucent area covers the part of T850 above
        mean + k sigma (red) or below mean - k sigma (blue). Stacked, they
        shade the anomaly darker with every sigma, so the reader sees how
        unusual the air mass is, not only its sign.
        """
        points = [None if row.t850 is None or row.climate is None
                  else (self.time_axis.x(row.valid), row.t850, row.climate, row.climate_std) for row in self.rows]
        parts = []
        for side, vertices in self.bands.polygons(points):
            coordinates = " ".join(f"{x:.1f},{self.axes.t_y(value):.1f}" for x, value in vertices)
            parts.append(f'<polygon class="{"warm" if side == WARM else "cold"}" points="{coordinates}"/>')
        return parts

    def _legend(self, climate: bool) -> list[str]:
        """Series names above the axis they belong to, with a line swatch."""
        y = MARGIN_TOP - 18
        parts = [
            f'<line class="line t850" x1="{PLOT_LEFT}" x2="{PLOT_LEFT + 24}" y1="{y}" y2="{y}"/>',
            f'<text class="title" x="{PLOT_LEFT + 30}" y="{y + 4}">T850 °C</text>',
        ]
        if climate:
            steps = self.bands.sigma_steps
            x, step_width = PLOT_LEFT + 110, 8
            width = step_width * len(steps)
            # Stacked like the areas: every step starts further right, so the swatch darkens to the right.
            for i, _ in enumerate(steps):
                left = x + i * step_width
                parts += [f'<rect class="warm" x="{left}" y="{y - 7}" width="{x + width - left}" height="7"/>',
                          f'<rect class="cold" x="{left}" y="{y}" width="{x + width - left}" height="7"/>']
            parts += [
                f'<line class="line climate" x1="{x}" x2="{x + width}" y1="{y}" y2="{y}"/>',
                f'<text class="title" x="{x + width + 6}" y="{y + 4}">'
                f'{self.climate_label}, ±{"/".join(str(k) for k in steps[1:])} σ</text>',
            ]
        return parts + [
            f'<line class="line thickness" x1="{PLOT_RIGHT - 24}" x2="{PLOT_RIGHT}" y1="{y}" y2="{y}"/>',
            f'<text class="title" x="{PLOT_RIGHT - 30}" y="{y + 4}" text-anchor="end">Z1000–500 dam</text>',
        ]

    def _tooltip(self, row: DiagramRow) -> str:
        """Text of the native tooltip of one valid time."""
        parts = [f"{row.valid:%d.%m. %H} UTC"]
        if row.t850 is not None:
            parts.append(f"T850 {row.t850:.0f} °C")
        if row.climate is not None:
            parts.append(f"{self.climate_label} {row.climate:.0f} °C")
            if row.t850 is not None and row.climate_std:
                parts.append(f"{(row.t850 - row.climate) / row.climate_std:+.1f} σ")
        if row.thickness is not None:
            parts.append(f"Z1000–500 {row.thickness:.0f} dam")
        if row.rh700:
            parts.append(f"RH700 {row.rh700}")
        return " · ".join(parts)

    def _hover(self) -> list[str]:
        """One hover column per valid time with crosshair, dots and tooltip.

        Each column reaches halfway to its neighbours, so the whole plot
        width is covered without overlaps despite the 3 h / 6 h steps.
        """
        rows = self.rows
        xs = [self.time_axis.x(row.valid) for row in rows]
        parts = []
        for i, row in enumerate(rows):
            left = PLOT_LEFT if i == 0 else (xs[i - 1] + xs[i]) / 2
            right = PLOT_RIGHT if i == len(rows) - 1 else (xs[i] + xs[i + 1]) / 2
            group = [f"<title>{escape(self._tooltip(row))}</title>",
                     f'<rect x="{left:.1f}" y="{PLOT_TOP}" width="{right - left:.1f}" '
                     f'height="{PLOT_BOTTOM - PLOT_TOP}"/>',
                     f'<line class="cross" x1="{xs[i]:.1f}" x2="{xs[i]:.1f}" '
                     f'y1="{PLOT_TOP}" y2="{PLOT_BOTTOM}"/>']
            for value, value_range, to_y, css in ((row.t850, self.axes.t_range, self.axes.t_y, "dot-t850"),
                                                  (row.thickness, self.axes.z_range, self.axes.z_y, "dot-thickness")):
                if value is not None and value_range[0] <= value <= value_range[1]:
                    group.append(f'<circle class="{css}" cx="{xs[i]:.1f}" cy="{to_y(value):.1f}" r="4"/>')
            parts.append('<g class="hit">' + "".join(group) + "</g>")
        return parts
