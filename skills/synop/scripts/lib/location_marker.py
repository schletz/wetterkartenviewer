"""Point or lat/lon box drawn onto rendered charts and contact sheets."""

import numpy as np
from PIL import Image, ImageDraw

from .chart_geometry import ChartGeometry
from .fonts import load_font

MARKER_RADIUS = 5
LABEL_SIZE = 16
# Points per box edge: the edges of a lat/lon box are curved on the polar stereographic charts.
EDGE_POINTS = 50


class LocationMarker:
    """The marker of one location or region on the charts of one window."""

    def __init__(self, geometry: ChartGeometry, label: str = "",
                 point: tuple[float, float] | None = None, bbox: tuple[float, float, float, float] | None = None):
        """Project the marker.

        Args:
            geometry: projection and contact sheet layout of the chart window.
            label: text next to the marker on single charts.
            point: (lat, lng) of a location, or
            bbox: (south, north, west, east) of a region in degrees.

        Raises:
            ValueError: unless exactly one of point and bbox is given.
        """
        if (point is None) == (bbox is None):
            raise ValueError("give either a point or a bbox")
        self.geometry, self.label = geometry, label
        self.points = self._outline(point, bbox)

    def _outline(self, point, bbox) -> np.ndarray:
        """Pixel coordinates of the marker: one point, or the closed outline of the box."""
        if bbox is None:
            x, y = self.geometry.latlon_to_pixel(*point)
            return np.array([[x, y]])
        south, north, west, east = bbox
        edge = np.linspace(0.0, 1.0, EDGE_POINTS)
        lats = np.r_[np.full(EDGE_POINTS, south), south + edge * (north - south),
                     np.full(EDGE_POINTS, north), north - edge * (north - south)]
        lons = np.r_[west + edge * (east - west), np.full(EDGE_POINTS, east),
                     east - edge * (east - west), np.full(EDGE_POINTS, west)]
        x, y = self.geometry.latlon_to_pixel(lats, lons)
        return np.column_stack([x, y])

    @property
    def visible(self) -> bool:
        """Whether any part of the marker lies on the chart."""
        x, y = self.points[:, 0], self.points[:, 1]
        return bool(np.any((x >= 0) & (x < self.geometry.width) & (y >= 0) & (y < self.geometry.height)))

    def mark_chart(self, image: Image.Image) -> None:
        """Draw the marker with its label onto a single chart."""
        self._draw(image, (0, 0), 1.0, self.label)

    def mark_sheet(self, image: Image.Image, product: str) -> None:
        """Draw the marker without label onto every tile of the contact sheet of a product."""
        for origin in self.geometry.sheet_tiles.get(product, []):
            self._draw(image, origin, self.geometry.sheet_scale, "")

    def _draw(self, image: Image.Image, origin: tuple, scale: float, label: str) -> None:
        """Draw point or box, scaled by ``scale`` and shifted to ``origin``, clipped to the map area there."""
        x0, y0 = origin
        area = (x0, y0, x0 + round(self.geometry.width * scale), y0 + round(self.geometry.height * scale))
        # Drawing on a crop keeps boxes that reach beyond the map off the legend and the neighbour tiles.
        tile = image.crop(area)
        draw = ImageDraw.Draw(tile)
        xy = [(float(x) * scale, float(y) * scale) for x, y in self.points]
        font = load_font(max(10, round(LABEL_SIZE * scale ** 0.5)), bold=True)
        if len(xy) == 1:
            (x, y), r = xy[0], max(3, round(MARKER_RADIUS * scale ** 0.5))
            draw.ellipse((x - r, y - r, x + r, y + r), fill="black", outline="white", width=2)
            anchor, position = "lm", (x + r + 4, y)
        else:
            draw.line(xy, fill="white", width=4)
            draw.line(xy, fill="black", width=2)
            top = min(xy, key=lambda p: p[1])
            anchor, position = "lb", (top[0], top[1] - 4)
        if label:
            draw.text(position, label, fill="black", font=font, anchor=anchor, stroke_width=2, stroke_fill="white")
        image.paste(tile, area[:2])
