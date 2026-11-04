"""Discrete colour bands of a shaded chart field."""

from dataclasses import dataclass


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
