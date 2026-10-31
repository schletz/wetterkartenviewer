"""Look of a point symbol scattered over a chart area, e.g. snow."""

from dataclasses import dataclass


@dataclass(frozen=True)
class SymbolStyle:
    """Marker of matplotlib's plot plus an optional dark halo, so it stays visible on any shading.

    Attributes:
        label: legend text.
        marker: matplotlib marker, e.g. "D" or (6, 2, 0) for an asterisk.
        size: marker size in points.
        colour: line colour of the marker (for line markers the only colour).
        fill: face colour of filled markers, None for line markers.
        width: line width in points.
        halo: colour of a stroke drawn below the marker, None for none.
    """

    label: str
    marker: str | tuple
    size: float
    colour: str
    fill: str | None = None
    width: float = 1.0
    halo: str | None = None
