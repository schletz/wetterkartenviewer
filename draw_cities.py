"""Draw European capitals onto a 500 hPa weather map.

The map uses a polar stereographic projection with the 0 degree
meridian vertical. Its parameters were determined once by a least
squares fit to nine measured control points (RMS error 0.45 px, the
fitted cone constant of 0.9983 was rounded to the exact stereographic
value 1) and are hard coded below.

Forward model (image coordinates, origin top left, y pointing down):

    rho = k * tan(45 deg - lat / 2)
    x   = x0 + rho * sin(lon)
    y   = y0 + rho * cos(lon)

Usage:
    python draw_cities.py europe.png 2026072312

The second argument is the valid time of the map in YYYYMMDDHH
format (hour in UTC); it is rendered into the top left corner.
The input image is overwritten in place.
"""

import math
import sys
from datetime import datetime

from PIL import Image, ImageDraw, ImageFont

# Polar stereographic projection parameters: image position of the
# north pole and radial scale factor.
POLE_X = 481.0
POLE_Y = -180.8
SCALE_K = 1320.8

# Target size after cropping the source image; the crop keeps the top
# left corner, so the projection parameters remain valid.
CROP_SIZE = (1000, 600)

# German weekday abbreviations (Monday first) and month names,
# independent of the system locale.
WEEKDAYS_DE = ["MO", "DI", "MI", "DO", "FR", "SA", "SO"]
MONTHS_DE = ["Januar", "Februar", "März", "April", "Mai", "Juni", "Juli",
             "August", "September", "Oktober", "November", "Dezember"]

# Temperature legend: boundary values in deg C between adjacent colour
# bands, i.e. len(LEGEND_COLORS) == len(LEGEND_VALUES) + 1. The colours
# are approximated from the reference chart.
LEGEND_TITLE = "850 hPa temperature (C)"
LEGEND_VALUES = [-80, -70, -60, -52, -48, -44, -40, -36, -32, -28, -24,
                 -20, -16, -12, -8, -4, 0, 4, 8, 12, 16, 20, 24, 28,
                 32, 36, 40, 44, 48, 52, 56]
LEGEND_COLORS = [
    "#e6e6e6", "#d7d7d7", "#c6c6c6", "#b4b4b4", "#a2a2a2", "#8f8f8f",
    "#7d7d7d", "#8a7794", "#71589e", "#5a3d9e", "#46299e", "#3333cc",
    "#3366ff", "#3399ff", "#00ccff", "#00b2a0", "#00a651", "#66cc33",
    "#b3e34b", "#ffff00", "#ffcc00", "#ff9900", "#ff6600", "#ff2a00",
    "#cc0000", "#990022", "#7a1040", "#cc3399", "#ff00ff", "#ff66ff",
    "#ffb3e6", "#ffe6f5",
]

# Cities: name -> (latitude deg N, longitude deg E)
CITIES = {
    "Madrid": (40.42, -3.70),
    "Paris": (48.86, 2.35),
    "London": (51.51, -0.13),
    "Berlin": (52.52, 13.40),
    "Wien": (48.21, 16.37),
    "Rom": (41.90, 12.50),
    "Bukarest": (44.43, 26.10),
    "Athen": (37.98, 23.73),
    "Stockholm": (59.33, 18.07),
    "Moskau": (55.76, 37.62),
    "Ankara": (39.93, 32.86),
    "Minsk": (53.90, 27.57),
    "Kairo": (30.04, 31.24),
}


def latlon_to_xy(lat, lon):
    """Project geographic coordinates to image pixel coordinates."""
    rho = SCALE_K * math.tan(math.radians(45 - lat / 2))
    lon_rad = math.radians(lon)
    return POLE_X + rho * math.sin(lon_rad), POLE_Y + rho * math.cos(lon_rad)


def load_font(size=16, bold=True):
    """Load a TrueType font, falling back to PIL's built-in font."""
    names = ("arialbd.ttf", "DejaVuSans-Bold.ttf") if bold \
        else ("arial.ttf", "DejaVuSans.ttf")
    for name in names:
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def render_timestamp(draw, timestamp):
    """Render the map's valid time into the top left corner.

    The style follows the usual weather chart header: a date line and
    below it a larger hour line, both with a contrasting outline.

    Args:
        draw: ImageDraw instance of the target image.
        timestamp: valid time as string in YYYYMMDDHH format (UTC).
    """
    dt = datetime.strptime(timestamp, "%Y%m%d%H")
    date_line = (f"{WEEKDAYS_DE[dt.weekday()]}, {dt.day}. "
                 f"{MONTHS_DE[dt.month - 1]} {dt.year}")
    hour_line = f"{dt.hour}h UTC"

    blue = (30, 30, 200)
    cyan = (0, 190, 255)
    draw.text((10, 8), date_line, font=load_font(26),
              fill=cyan, stroke_width=2, stroke_fill=blue)
    draw.text((10, 34), hour_line, font=load_font(26),
              fill=cyan, stroke_width=2, stroke_fill=blue)


def render_legend(draw, width, height):
    """Render the temperature colour legend into the bottom right corner.

    A white box contains the title, one colour patch per temperature
    band and the boundary values centred between adjacent patches.

    Args:
        draw: ImageDraw instance of the target image.
        width: image width in pixels.
        height: image height in pixels.
    """
    sw = 19        # width of one colour patch
    bar_h = 22     # height of the colour bar
    pad = 10       # inner padding of the white box
    bar_w = sw * len(LEGEND_COLORS)
    box_w = bar_w + 2 * pad
    box_h = pad + 18 + 14 + bar_h + pad  # title, labels, colour bar
    x0 = width - box_w
    y0 = height - box_h
    draw.rectangle([x0, y0, width, height], fill="white")

    draw.text((x0 + box_w / 2, y0 + pad), LEGEND_TITLE,
              font=load_font(14, bold=False), fill="black", anchor="ma")

    bar_x = x0 + pad
    bar_y = y0 + box_h - pad - bar_h
    for i, color in enumerate(LEGEND_COLORS):
        draw.rectangle([bar_x + i * sw, bar_y,
                        bar_x + (i + 1) * sw, bar_y + bar_h], fill=color)

    # Boundary values sit exactly between adjacent colour patches.
    label_font = load_font(10, bold=False)
    for j, value in enumerate(LEGEND_VALUES):
        draw.text((bar_x + (j + 1) * sw, bar_y - 4), str(value),
                  font=label_font, fill="black", anchor="ms")


def draw_cities(image_path, timestamp):
    """Draw city markers and the valid time onto the map image."""
    image = Image.open(image_path).convert("RGBA")
    image = image.crop((0, 0, *CROP_SIZE))
    draw = ImageDraw.Draw(image)
    font = load_font(13)

    r = 4  # marker radius in pixels
    for name, (lat, lon) in CITIES.items():
        x, y = latlon_to_xy(lat, lon)
        draw.ellipse([x - r, y - r, x + r, y + r],
                     fill="black", outline="white", width=1)
        draw.text((x + r + 3, y), name, font=font, anchor="lm",
                  fill="black")
        print(f"  {name}: ({x:.0f}, {y:.0f})")

    render_timestamp(draw, timestamp)
    render_legend(draw, *image.size)

    image.save(image_path)
    print(f"Bild gespeichert: {image_path}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Aufruf: python draw_cities.py <bild.png> <YYYYMMDDHH>",
              file=sys.stderr)
        sys.exit(1)
    try:
        draw_cities(sys.argv[1], sys.argv[2])
    except ValueError:
        print(f"Ungültige Zeitangabe: {sys.argv[2]} (erwartet YYYYMMDDHH)",
              file=sys.stderr)
        sys.exit(1)
