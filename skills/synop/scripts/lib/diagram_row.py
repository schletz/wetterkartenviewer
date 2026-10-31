"""One valid time of the T850/thickness diagram."""

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class DiagramRow:
    """Values of one valid time; None where missing."""

    valid: datetime
    t850: float | None
    thickness: float | None  # dam
    rh700: str
    climate: float | None = None  # mean T850 of the climatology at this time of day and year, deg C
    climate_std: float | None = None  # its standard deviation, K
