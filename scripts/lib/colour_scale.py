"""Discrete colour bands of a shaded chart field."""

from dataclasses import dataclass, replace


@dataclass(frozen=True)
class ColourScale:
    """Discrete colour bands of a shaded field.

    Attributes:
        title: legend text including the unit.
        bands: (min, max, (r, g, b)) in ascending order, contiguous.
        legend_range: (min, max) of the bands shown in the legend; the
            outer bands of the open charts scales (e.g. -80 deg C) never
            occur over Europe and would only squeeze the legend.
        transparent_below: values below this stay unshaded (None = shade all).
    """

    title: str
    bands: tuple
    legend_range: tuple | None = None
    transparent_below: float | None = None

    @property
    def bounds(self) -> list[float]:
        """Band boundaries, len(bands) + 1 values."""
        return [self.bands[0][0]] + [band[1] for band in self.bands]

    def shifted(self, offset: float, title: str) -> "ColourScale":
        """The same colours with every band bound (and the legend range) moved by ``offset``."""
        legend_range = None if self.legend_range is None else tuple(v + offset for v in self.legend_range)
        transparent_below = None if self.transparent_below is None else self.transparent_below + offset
        return replace(self, title=title, bands=tuple((low + offset, high + offset, rgb) for low, high, rgb in self.bands),
                       legend_range=legend_range, transparent_below=transparent_below)
