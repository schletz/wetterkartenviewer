"""Common interface of the samplers that read field values at one location."""

import math
from abc import ABC, abstractmethod

import numpy as np


class PointSampler(ABC):
    """Value of a field at one location; subclasses know the grid of the forecast file."""

    @abstractmethod
    def __call__(self, values: np.ndarray) -> float:
        """Interpolated value at the location, NaN if a neighbour is missing."""

    def wind(self, u: np.ndarray, v: np.ndarray) -> tuple[float, float] | None:
        """Wind as (direction it blows from in degrees, speed in m/s); None where a component is missing."""
        east, north = self(u), self(v)
        if math.isnan(east) or math.isnan(north):
            return None
        return (math.degrees(math.atan2(-east, -north)) + 360.0) % 360.0, math.hypot(east, north)
