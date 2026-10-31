"""Pixel geometry of the chart windows.

Every window is a conformal conic projection on the sphere with a 1200x600
image; the windows differ in cone, central meridian, scale and offset. The
forward model, in image coordinates with the origin at the top left and the
y axis pointing down, is

    rho = scale_k * tan(45 deg - lat / 2) ** cone
    x   = pole_x + rho * sin(cone * (lon - lon0))
    y   = pole_y + rho * cos(cone * (lon - lon0))

cone = 1 is the polar stereographic projection of the ECMWF open charts
windows (lon0 = 0, a vertical zero meridian); 0 < cone < 1 is Lambert's
conformal conic projection with two standard parallels (``Projection.lambert``).
(pole_x, pole_y) is the apex of the cone, where every meridian meets.

The open charts parameters come from least squares fits to measured control
points: "opencharts_europe" RMS 0.45 px, "opencharts_central_europe" RMS 0.4 px
(three points; a free central meridian came out at 0.04 deg, i.e. none).
The central Europe window is the rectangle x 316-770, y 205-432 of the
Europe window enlarged 2.645 times. The north pole lies above every image.

Both directions accept scalars and numpy arrays, so whole pixel grids or
coastlines can be projected in one call.
"""

from dataclasses import dataclass
from pathlib import Path

import numpy as np

IMAGE_WIDTH = 1200
IMAGE_HEIGHT = 600
EARTH_RADIUS_KM = 6371.0
WORLD_COUNTRIES = Path(__file__).with_name("world_countries.geojson")
AUSTRIA_BORDERS = Path(__file__).with_name("borders_austria.geojson")


@dataclass(frozen=True)
class Projection:
    """One chart window.

    Attributes:
        name: window name, also the folder of its charts.
        pole_x, pole_y: pixel position of the apex of the cone (the north pole).
        scale_k: projection scale in pixels.
        graticule_step: spacing of the drawn graticule in degrees.
        cone: cone constant n; 1 = polar stereographic.
        lon0: central meridian in degrees east; it runs vertically through the apex.
        borders: GeoJSON of the country (and state) outlines drawn on the window.
        label_lon: meridian along which the parallels are labelled.
        label_lat: parallel along which the meridians are labelled.
    """

    name: str
    pole_x: float
    pole_y: float
    scale_k: float
    graticule_step: int
    width: int = IMAGE_WIDTH
    height: int = IMAGE_HEIGHT
    cone: float = 1.0
    lon0: float = 0.0
    borders: Path = WORLD_COUNTRIES
    label_lon: float = 0.0
    label_lat: float = 40.0

    @classmethod
    def lambert(cls, name: str, parallels: tuple[float, float], lon0: float, centre: tuple[float, float],
                km_per_px: float, graticule_step: int, **options) -> "Projection":
        """Lambert conformal conic window with the given standard parallels, centred on (lat, lon).

        ``km_per_px`` holds on the standard parallels; between them the
        scale is slightly larger, outside slightly smaller.
        """
        lat1, lat2 = np.radians(parallels)
        cone = np.log(np.cos(lat1) / np.cos(lat2)) / np.log(np.tan(np.pi / 4 + lat2 / 2) / np.tan(np.pi / 4 + lat1 / 2))
        # Spherical LCC: rho = R F tan(45 - lat/2)^n with F = cos(lat1) tan(45 + lat1/2)^n / n.
        scale_k = EARTH_RADIUS_KM * np.cos(lat1) * np.tan(np.pi / 4 + lat1 / 2) ** cone / cone / km_per_px
        probe = cls(name, 0.0, 0.0, float(scale_k), graticule_step, cone=float(cone), lon0=lon0, **options)
        x, y = probe.latlon_to_pixel(*centre)
        return cls(name, float(probe.width / 2 - x), float(probe.height / 2 - y), float(scale_k), graticule_step,
                   cone=float(cone), lon0=lon0, **options)

    def latlon_to_pixel(self, lat, lon):
        """Project a geographic position (deg N, deg E) onto the image; returns (x, y)."""
        rho = self.scale_k * np.tan(np.radians(45.0 - np.asarray(lat) / 2.0)) ** self.cone
        theta = self.cone * np.radians(self._relative_lon(lon))
        return self.pole_x + rho * np.sin(theta), self.pole_y + rho * np.cos(theta)

    def pixel_to_latlon(self, x, y):
        """Invert latlon_to_pixel; returns (lat, lon) in degrees, longitudes in -180..180."""
        dx = np.asarray(x, dtype=float) - self.pole_x
        dy = np.asarray(y, dtype=float) - self.pole_y
        lat = 90.0 - 2.0 * np.degrees(np.arctan((np.hypot(dx, dy) / self.scale_k) ** (1.0 / self.cone)))
        lon = np.degrees(np.arctan2(dx, dy)) / self.cone + self.lon0
        return lat, (lon + 180.0) % 360.0 - 180.0

    def km_per_px(self, lat: float) -> float:
        """Length of one pixel on the ground at a latitude (the same in every direction, conformal)."""
        rho = self.scale_k * np.tan(np.radians(45.0 - lat / 2.0)) ** self.cone
        return float(EARTH_RADIUS_KM * np.cos(np.radians(lat)) / (self.cone * rho))

    def north_east(self) -> tuple[np.ndarray, np.ndarray]:
        """Unit vectors of north and east in image coordinates (y down) at every pixel centre.

        North points to the apex, where the meridians meet. Both arrays have
        the shape (2, height, width): x and y component.
        """
        px, py = np.meshgrid(np.arange(self.width) + 0.5, np.arange(self.height) + 0.5)
        north = np.array([self.pole_x - px, self.pole_y - py])
        north /= np.hypot(*north)
        return north, np.array([-north[1], north[0]])

    def border_latlon(self):
        """(lat, lon) arrays of every pixel on the image border."""
        xs = np.r_[np.arange(self.width + 1), np.full(self.height + 1, self.width),
                   np.arange(self.width + 1), np.zeros(self.height + 1)]
        ys = np.r_[np.zeros(self.width + 1), np.arange(self.height + 1),
                   np.full(self.width + 1, self.height), np.arange(self.height + 1)]
        return self.pixel_to_latlon(xs, ys)

    def _relative_lon(self, lon):
        """Longitude relative to the central meridian in -180..180, so the cut lies opposite to it."""
        return (np.asarray(lon) - self.lon0 + 180.0) % 360.0 - 180.0


EUROPE = Projection("opencharts_europe", pole_x=481.0, pole_y=-180.8, scale_k=1320.8, graticule_step=10)
CENTRAL_EUROPE = Projection("opencharts_central_europe", pole_x=435.35, pole_y=-1021.0, scale_k=3493.4,
                            graticule_step=5)
# ICON-D2 for Austria and its surroundings: the parallels of the Austrian Lambert projection
# (EPSG:31287); 0.75 km per pixel is about 8 px per model cell, as dense as ECMWF on the
# central Europe window, so the chart suggests no more detail than the model has. The centre lies
# west of Austria's, because the model domain ends near 18.3 E; the window (5.7-18.2 E,
# 45.3-49.6 N) lies wholly inside it and shows the weather coming from the west.
ICON_D2 = Projection.lambert("icon-d2", parallels=(46.0, 49.0), lon0=13.0 + 1.0 / 3.0, centre=(47.6, 12.0),
                             km_per_px=0.75, graticule_step=2, borders=AUSTRIA_BORDERS, label_lon=7.0,
                             label_lat=46.0)
PROJECTIONS = {p.name: p for p in (EUROPE, CENTRAL_EUROPE, ICON_D2)}
