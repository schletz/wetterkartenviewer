"""One chart image: map area in the pixel geometry of a Projection plus a legend strip below.

The map area is exactly the 1200x600 px of the open charts window, so
pixel positions from Projection.latlon_to_pixel hold on the
self-rendered charts too. The legend strip below it carries title, run,
valid time and the colour bar, so a chart can be read without any
side file.
"""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import numpy as np  # noqa: E402
from matplotlib.backends.backend_agg import FigureCanvasAgg  # noqa: E402
from matplotlib.collections import LineCollection, PolyCollection  # noqa: E402
from matplotlib.figure import Figure  # noqa: E402
from matplotlib import patheffects  # noqa: E402
from matplotlib.patches import Rectangle  # noqa: E402
from PIL import Image  # noqa: E402
from scipy.ndimage import minimum_filter, uniform_filter  # noqa: E402

from .base_map import BaseMap  # noqa: E402
from .colour_scale import ColourScale  # noqa: E402
from .contour_style import ContourStyle  # noqa: E402
from .projection import IMAGE_HEIGHT, IMAGE_WIDTH  # noqa: E402
from .symbol_style import SymbolStyle  # noqa: E402

LEGEND_HEIGHT = 90
# Colour bar in the legend strip: left edge and width in px; notes start right of it.
BAR = (8, 760)
NOTES_X = 800
SYMBOL_GAP_PX = 18
DPI = 100
WEBP_QUALITY = 90
# Drawing order, bottom to top.
Z_BACKGROUND, Z_SHADING, Z_GRATICULE, Z_OUTLINE, Z_CONTOUR, Z_ARROW, Z_MARKER = range(7)
# Centres closer than this to the image border are not marked; the field is cut there.
EXTREMA_BORDER_PX = 20
# Streamlines integrate on every n-th pixel; finer grids only cost time, the field is smooth at that scale.
STREAMLINE_GRID_PX = 4


def rgb(colour: tuple) -> tuple:
    """Matplotlib colour from 0..255 RGB."""
    return tuple(c / 255 for c in colour)


class ChartCanvas:
    """Draws one chart; call the layer methods bottom to top, then ``save``."""

    def __init__(self, base_map: BaseMap, title: str, time_label: str):
        self.base_map = base_map
        total = IMAGE_HEIGHT + LEGEND_HEIGHT
        self.fig = Figure(figsize=(IMAGE_WIDTH / DPI, total / DPI), dpi=DPI)
        FigureCanvasAgg(self.fig)
        self.ax = self.fig.add_axes((0, LEGEND_HEIGHT / total, 1, IMAGE_HEIGHT / total))
        self.legend = self.fig.add_axes((0, 0, 1, LEGEND_HEIGHT / total))
        for ax, height in ((self.ax, IMAGE_HEIGHT), (self.legend, LEGEND_HEIGHT)):
            ax.set_xlim(0, IMAGE_WIDTH)
            ax.set_ylim(height, 0)
            ax.set_axis_off()
        self.legend.add_patch(Rectangle((0, 0), IMAGE_WIDTH, LEGEND_HEIGHT, color="white"))
        # The valid time comes first: it is what a reader needs to match charts to the forecast days.
        self.legend.text(8, 14, time_label, fontsize=11, fontweight="bold", va="center")
        self.legend.text(IMAGE_WIDTH - 8, 14, title, fontsize=10, va="center", ha="right")
        # Further legend entries go to the right of the colour bar, one per line;
        # symbol keys go in a row below the colour bars.
        self._notes = []
        self._symbols: list[SymbolStyle] = []
        self._symbol_note = ""

    # Map layers

    def background(self, land: tuple, sea: tuple) -> None:
        """Fill sea and land, for charts whose shading leaves gaps."""
        self.ax.add_patch(Rectangle((0, 0), IMAGE_WIDTH, IMAGE_HEIGHT, color=rgb(sea), zorder=Z_BACKGROUND))
        self.ax.add_collection(PolyCollection(self.base_map.rings, facecolors=[rgb(land)], edgecolors="none",
                                              zorder=Z_BACKGROUND))

    def shade(self, values: np.ndarray, scale: ColourScale, mask: np.ndarray | None = None,
              mask_colour: tuple = (190, 190, 190), mask_label: str = "", bar: tuple = BAR) -> None:
        """Discrete colour bands of a (height, width) pixel field; ``mask`` and NaN pixels get ``mask_colour``.

        ``bar`` is (left, width) of the colour bar in the legend strip; two
        shaded layers share the strip with two narrower bars.
        """
        missing = np.isnan(values)
        if missing.any():
            mask = missing if mask is None else mask | missing
        colours = np.array([band[2] for band in scale.bands] + [mask_colour], dtype=np.uint8)
        index = np.clip(np.digitize(values, scale.bounds[1:-1]), 0, len(scale.bands) - 1)
        rgba = np.dstack([colours[index], np.full(values.shape, 255, np.uint8)])
        if mask is not None:
            rgba[mask, :3] = colours[-1]
        if scale.transparent_below is not None:
            rgba[values < scale.transparent_below, 3] = 0
        self.ax.imshow(rgba, extent=(0, IMAGE_WIDTH, IMAGE_HEIGHT, 0), interpolation="nearest", zorder=Z_SHADING)
        self._colour_bar(scale, *bar)
        if mask is not None:
            self._swatch(mask_colour, mask_label)

    def uncovered(self, covered: np.ndarray, colour: tuple, label: str) -> None:
        """Paint the pixels without model data (outside a limited area model) over every shading."""
        if covered.all():
            return
        rgba = np.zeros((*covered.shape, 4), np.uint8)
        rgba[~covered] = (*colour, 255)
        self.ax.imshow(rgba, extent=(0, IMAGE_WIDTH, IMAGE_HEIGHT, 0), interpolation="nearest", zorder=Z_SHADING)
        self._swatch(colour, label)

    def outlines(self) -> None:
        """Coastlines, country and state borders and a labelled graticule."""
        grey = dict(colors="#808080", linewidths=0.4, zorder=Z_GRATICULE)
        self.ax.add_collection(LineCollection(list(self.base_map.parallels.values()), **grey))
        self.ax.add_collection(LineCollection(list(self.base_map.meridians.values()), **grey))
        self.ax.add_collection(LineCollection(self.base_map.state_rings, colors="#303030", linewidths=0.4,
                                              linestyles=(0, (4, 2)), zorder=Z_OUTLINE))
        self.ax.add_collection(LineCollection(self.base_map.rings, colors="black", linewidths=0.6, zorder=Z_OUTLINE))
        projection = self.base_map.projection
        text = dict(fontsize=7, color="#404040", ha="center", va="center", zorder=Z_GRATICULE,
                    bbox=dict(boxstyle="square,pad=0.1", fc="white", ec="none", alpha=0.7))
        for lat, line in self.base_map.parallels.items():
            x, y = self._graticule_point(line, projection.label_lon, axis=1)
            if x is not None:
                self.ax.text(x, y, f"{lat}°N", **text)
        for lon, line in self.base_map.meridians.items():
            x, y = self._graticule_point(line, projection.label_lat, axis=0)
            if x is not None:
                self.ax.text(x, y, f"{abs(lon)}°{'E' if lon >= 0 else 'W'}" if lon else "0°", **text)

    @staticmethod
    def _graticule_point(line: np.ndarray, where: float, axis: int):
        """Pixel position on a graticule line closest to a meridian (axis=1) or parallel (axis=0)."""
        if axis == 1:
            # Sampling of the lines as built by BaseMap: every 0.5 deg.
            index = int(round((where + 180) * 2))
        else:
            index = int(round(where * 2))
        x, y = line[index]
        inside = 10 < x < IMAGE_WIDTH - 10 and 10 < y < IMAGE_HEIGHT - 10
        return (x, y) if inside else (None, None)

    def contours(self, values: np.ndarray, style: ContourStyle, label: str | None = None, boxed: bool = True,
                 fmt: str = "{:.0f}") -> None:
        """Labelled contour lines of a pixel field; ``label`` describes them in the legend."""
        levels = np.arange(np.floor(np.nanmin(values) / style.interval) * style.interval,
                           np.nanmax(values) + style.interval, style.interval)
        steps = np.round((levels - style.bold_base) / style.interval).astype(int)
        bold = (steps % style.bold_every == 0) if style.bold_every else np.zeros(len(levels), bool)
        widths = np.where(bold, 2.2 * style.width, style.width)
        cs = self.ax.contour(np.arange(IMAGE_WIDTH) + 0.5, np.arange(IMAGE_HEIGHT) + 0.5, values, levels=levels,
                             colors=style.colour, linewidths=widths, zorder=Z_CONTOUR)
        labelled = levels[steps % style.label_every == 0]
        texts = self.ax.clabel(cs, levels=labelled, inline=True, inline_spacing=3,
                               fontsize=9 if boxed else 7, fmt=lambda v: fmt.format(v))
        for text in texts:
            text.set_zorder(Z_CONTOUR)
            if boxed:
                text.set_bbox(dict(boxstyle="square,pad=0.1", fc="white", ec="none"))
        if label:
            self._notes.append(label)

    def isolines(self, values: np.ndarray, levels: tuple, colour: str, label: str | None,
                 dashed: bool = False, labelled: bool = True) -> None:
        """Lines at fixed values, e.g. thresholds; line width grows with |level|."""
        if np.nanmin(values) > max(levels) or np.nanmax(values) < min(levels):
            if label:
                self._notes.append(label)
            return
        widths = np.interp(np.abs(levels), (min(np.abs(levels)), max(np.abs(levels)) + 1e-9), (1.0, 2.0))
        cs = self.ax.contour(np.arange(IMAGE_WIDTH) + 0.5, np.arange(IMAGE_HEIGHT) + 0.5, values, levels=sorted(levels),
                             colors=colour, linewidths=widths[np.argsort(levels)],
                             linestyles="dashed" if dashed else "solid", zorder=Z_CONTOUR)
        if labelled:
            for text in self.ax.clabel(cs, inline=True, inline_spacing=3, fontsize=8, fmt=lambda v: f"{v:g}"):
                text.set_zorder(Z_CONTOUR)
        if label:
            self._notes.append(label)

    def extrema(self, values: np.ndarray, low_window_px: int, high_window_px: int, min_depth: float,
                fmt: str = "{:.0f}") -> None:
        """Mark centres of lows (L) and highs (H) with their central value.

        A centre is the extreme of a square window that lies at least
        ``min_depth`` below (above) the mean of that window, so flat
        plateaus and wiggles of the contours are not marked. Highs are
        broad and flat, so they need a larger window than lows.
        """
        for sign, window, letter, colour in ((1, low_window_px, "L", "#c00000"),
                                             (-1, high_window_px, "H", "#0030c0")):
            signed = sign * values
            depth = uniform_filter(signed, window, mode="nearest") - signed
            centre = (signed == minimum_filter(signed, window, mode="nearest")) & (depth >= min_depth)
            border = EXTREMA_BORDER_PX
            centre[:border], centre[-border:], centre[:, :border], centre[:, -border:] = False, False, False, False
            for y, x in zip(*np.nonzero(centre)):
                self.ax.text(x, y, letter, fontsize=17, fontweight="bold", color=colour, ha="center", va="center",
                             zorder=Z_MARKER)
                self.ax.text(x, y + 17, fmt.format(values[y, x]), fontsize=9, fontweight="bold", color=colour,
                             ha="center", va="center", zorder=Z_MARKER,
                             bbox=dict(boxstyle="square,pad=0.1", fc="white", ec="none", alpha=0.8))
        self._notes.append("L/H: low/high centre with central value")

    def hatch(self, values: np.ndarray, at_least: float, colour: str, label: str) -> None:
        """Hatch the area where a pixel field reaches a threshold."""
        top = np.nanmax(values)
        if top >= at_least:
            with matplotlib.rc_context({"hatch.color": colour, "hatch.linewidth": 1.0}):
                self.ax.contourf(np.arange(IMAGE_WIDTH) + 0.5, np.arange(IMAGE_HEIGHT) + 0.5, values,
                                 levels=[at_least, top + 1], colors="none", hatches=["////"], zorder=Z_CONTOUR)
        self._notes.append(label)

    def arrows(self, dx: np.ndarray, dy: np.ndarray, spacing: int, px_per_ms: float, reference_ms: float,
               label: str) -> None:
        """Wind arrows on a regular pixel lattice; length proportional to speed."""
        ys, xs = np.mgrid[spacing // 2:IMAGE_HEIGHT:spacing, spacing // 2:IMAGE_WIDTH:spacing]
        style = dict(angles="xy", scale_units="xy", scale=1 / px_per_ms, width=0.0013, headwidth=4,
                     headlength=4.5, headaxislength=4, color="black")
        self.ax.quiver(xs, ys, dx[ys, xs], dy[ys, xs], zorder=Z_ARROW, **style)
        # Reference arrow in the legend; legend y also points down.
        x0, y0 = IMAGE_WIDTH - 20 - reference_ms * px_per_ms, LEGEND_HEIGHT - 12
        self.legend.quiver([x0], [y0], [reference_ms], [0], **style)
        self.legend.text(x0 - 6, y0, f"{label}, arrow = {reference_ms:g} m/s", fontsize=8, ha="right", va="center")

    def streamlines(self, dx: np.ndarray, dy: np.ndarray, density: float, label: str) -> None:
        """Streamlines of a pixel vector field (dx right, dy down): lines along the flow at the valid time.

        Unlike isobars or isohypses they show convergence, divergence and the
        flow across the isobars near the ground; their spacing says nothing
        about the speed, which the shading has to give. NaN pixels end a line.
        """
        step = STREAMLINE_GRID_PX
        xs, ys = np.arange(step // 2, IMAGE_WIDTH, step), np.arange(step // 2, IMAGE_HEIGHT, step)
        grid = np.ix_(ys, xs)
        self.ax.streamplot(xs, ys, dx[grid], dy[grid], density=density, color="#5a5a5a", linewidth=0.5,
                           arrowsize=0.7, zorder=Z_ARROW)
        self._notes.append(label)

    def values(self, values: np.ndarray, spacing: int, where: np.ndarray, fmt: str, label: str) -> None:
        """Print the value of a pixel field, rounded to an integer, on a regular lattice where ``where`` is true.

        Reading a number is exact, reading a colour band gives a range of 4 K.
        """
        halo = [patheffects.withStroke(linewidth=2.5, foreground="white")]
        for y in range(spacing // 2, IMAGE_HEIGHT, spacing):
            for x in range(spacing // 2, IMAGE_WIDTH, spacing):
                if where[y, x]:
                    # Adding 0.0 turns the -0.0 of rounding into 0.0, so no "-0" appears.
                    self.ax.text(x, y, fmt.format(np.round(values[y, x]) + 0.0), fontsize=9, fontweight="bold",
                                 ha="center", va="center", zorder=Z_MARKER, path_effects=halo)
        self._notes.append(label)

    def symbols(self, where: np.ndarray, spacing: int, style: SymbolStyle, note: str = "") -> None:
        """Scatter a symbol on a regular pixel lattice where a (height, width) mask is true; the legend shows it.

        ``note`` follows the row of symbol keys, e.g. what the symbols leave out.
        """
        ys, xs = np.mgrid[spacing // 2:IMAGE_HEIGHT:spacing, spacing // 2:IMAGE_WIDTH:spacing]
        hit = where[ys, xs]
        if hit.any():
            self._plot_symbols(self.ax, xs[hit], ys[hit], style, Z_ARROW)
        self._symbols.append(style)
        self._symbol_note = note or self._symbol_note

    # Legend

    def _colour_bar(self, scale: ColourScale, x0: float, width: float) -> None:
        lo, hi = scale.legend_range or (scale.bounds[0], scale.bounds[-1])
        bands = [band for band in scale.bands if band[1] > lo and band[0] < hi]
        top, height = 42, 16
        box = width / len(bands)
        unshaded = f"   (unshaded < {scale.transparent_below:g})" if scale.transparent_below is not None else ""
        self.legend.text(x0, top - 8, scale.title + unshaded, fontsize=9, va="center")
        for i, (low, high, colour) in enumerate(bands):
            self.legend.add_patch(Rectangle((x0 + i * box, top), box, height, facecolor=rgb(colour),
                                            edgecolor="#606060", linewidth=0.4))
            if i:
                self.legend.text(x0 + i * box, top + height + 8, f"{low:g}", fontsize=8, ha="center", va="center")

    def _swatch(self, colour: tuple, label: str) -> None:
        self.legend.add_patch(Rectangle((776, 42), 16, 16, facecolor=rgb(colour), edgecolor="#606060",
                                        linewidth=0.4))
        self._notes.insert(0, label)

    @staticmethod
    def _plot_symbols(ax, xs, ys, style: SymbolStyle, zorder: int) -> None:
        halo = [patheffects.withStroke(linewidth=style.width + 1.8, foreground=style.halo)] if style.halo else None
        ax.plot(xs, ys, linestyle="none", marker=style.marker, ms=style.size, mew=style.width, mec=style.colour,
                mfc=style.fill or "none", path_effects=halo, zorder=zorder)

    def _symbol_row(self) -> None:
        """Keys of the symbols in one row below the colour bars; the notes column has no room for them."""
        x, y = BAR[0], 81
        for style in self._symbols:
            self._plot_symbols(self.legend, [x + 5], [y], style, Z_MARKER)
            label = self.legend.text(x + 14, y, style.label, fontsize=8, va="center")
            x = self.legend.transData.inverted().transform(
                label.get_window_extent(self.fig.canvas.get_renderer()))[1, 0] + SYMBOL_GAP_PX
        if self._symbol_note:
            self.legend.text(x, y, self._symbol_note, fontsize=8, va="center", color="#404040")

    def save(self, path: Path) -> None:
        """Write the chart as lossless WebP; flat colour areas compress well without artefacts."""
        for i, note in enumerate(self._notes):
            self.legend.text(NOTES_X, 34 + 13 * i, note, fontsize=8, va="center")
        if self._symbols:
            self._symbol_row()
        self.fig.canvas.draw()
        image = Image.fromarray(np.asarray(self.fig.canvas.buffer_rgba())[..., :3])
        path.parent.mkdir(parents=True, exist_ok=True)
        image.save(path, lossless=True)
