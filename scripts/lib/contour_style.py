"""Settings of the line contours of a chart field."""

from dataclasses import dataclass


@dataclass(frozen=True)
class ContourStyle:
    """Line contours of a field.

    Attributes:
        interval: spacing of the contours.
        bold_every: every n-th contour (counted from ``bold_base``) is drawn bold.
        bold_base: value of one bold contour.
        label_every: every n-th contour gets labels.
        smooth_km: Gaussian smoothing before contouring; the 0.1 deg fields
            carry small scale noise (mountains) that would fray the lines.
        colour: line colour.
        width: line width of the thin contours in px.
    """

    interval: float
    bold_every: int
    bold_base: float
    label_every: int
    smooth_km: float
    colour: str = "black"
    width: float = 1.0
