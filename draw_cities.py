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
    python draw_cities.py europe.png chart.png 2026072312
    python draw_cities.py 2026072312

The last argument is the valid time of the map in YYYYMMDDHH
format (hour in UTC); it is rendered into the top left corner.
If a chart image is given as well, the meteogram strip is cut out of
it and stacked on top of the map. The map image is overwritten in
place in both cases.
Without any image argument both the map and the meteogram are
downloaded from charts.ecmwf.int and the result is written to
DEFAULT_OUTPUT. In that mode the bare map is offered in
ANNOTATION_FILE first and the script waits, so it can be annotated in
an image editor before the overlays are rendered on top of those
annotations.
"""

import math
import os
import sys
from datetime import datetime

try:
    import msvcrt
except ImportError:  # not running on Windows
    msvcrt = None

import requests
from PIL import Image, ImageDraw, ImageFont

import ecmwf_api
from upscale import magic_kernel_sharp_resize

# Polar stereographic projection parameters: image position of the
# north pole and radial scale factor.
POLE_X = 481.0
POLE_Y = -180.8
SCALE_K = 1320.8

# Target size after cropping the source image; the crop keeps the top
# left corner, so the projection parameters remain valid.
CROP_SIZE = (1000, 600)

# Region of the chart image holding the temperature meteogram
# (left, upper, right, lower).
METEOGRAM_BOX = (25, 547, 605, 680)

# File the combined image is written to when no map path is given on
# the command line.
DEFAULT_OUTPUT = "map.webp"

# Working file the bare map is offered in for manual annotation and
# that is removed once it has been read back. PNG is used deliberately:
# an image editor writes it back without loss, so no encoding
# generation is added between download and final rendering.
ANNOTATION_FILE = "map.png"

# Layout of the combined image: the meteogram is scaled to the map
# width and sits on top, separated from the map by this gap. The gap
# is chosen so that the total height stays a multiple of eight, which
# suits block based image formats.
METEOGRAM_GAP = 11

# Colours of the chart labels: a bright fill on a dark outline so the
# text stays readable over every temperature shading.
LABEL_FILL = (0, 190, 255)
LABEL_STROKE = (30, 30, 200)

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

    draw.text((10, 8), date_line, font=load_font(26),
              fill=LABEL_FILL, stroke_width=2, stroke_fill=LABEL_STROKE)
    draw.text((10, 34), hour_line, font=load_font(26),
              fill=LABEL_FILL, stroke_width=2, stroke_fill=LABEL_STROKE)


def render_base_time(draw, base_time, height):
    """Render the forecast run into the bottom left corner.

    Args:
        draw: ImageDraw instance of the target image.
        base_time: run of the forecast as string in YYYYMMDDHHmm
            format (UTC), as reported by the API.
        height: image height in pixels.
    """
    dt = datetime.strptime(base_time, "%Y%m%d%H%M")
    text = (f"Lauf: {WEEKDAYS_DE[dt.weekday()]}, {dt.day}. "
            f"{MONTHS_DE[dt.month - 1]} {dt.year}, {dt.hour}h UTC")
    # The font is small enough that even the longest month name keeps
    # the line clear of the legend box in the opposite corner.
    draw.text((10, height - 10), text, font=load_font(16), anchor="ls",
              fill=LABEL_FILL, stroke_width=2, stroke_fill=LABEL_STROKE)


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


def draw_cities(map_image, timestamp, base_time=None):
    """Draw city markers and the valid time onto the map image.

    Args:
        map_image: source map image as published by ECMWF.
        timestamp: valid time as string in YYYYMMDDHH format (UTC).
        base_time: run the forecast was computed from, in YYYYMMDDHHmm
            format (UTC). Only known for downloaded maps; if None, no
            run is rendered.

    Returns:
        The cropped map image with all annotations, not yet saved.
    """
    image = map_image.convert("RGBA").crop((0, 0, *CROP_SIZE))
    draw = ImageDraw.Draw(image)
    font = load_font(13)

    r = 4  # marker radius in pixels
    for name, (lat, lon) in CITIES.items():
        x, y = latlon_to_xy(lat, lon)
        draw.ellipse([x - r, y - r, x + r, y + r],
                     fill="black", outline="white", width=1)
        draw.text((x + r + 3, y), name, font=font, anchor="lm",
                  fill="black")

    render_timestamp(draw, timestamp)
    if base_time is not None:
        render_base_time(draw, base_time, image.height)
    render_legend(draw, *image.size)
    return image


def combine_with_meteogram(map_image, chart_image):
    """Stack the meteogram of a chart image on top of the map.

    The meteogram strip is upscaled to the map width; Magic Kernel
    Sharp is used so the small axis labels stay legible.

    Args:
        map_image: annotated map image as returned by draw_cities().
        chart_image: chart image containing the meteogram.

    Returns:
        A new image holding the meteogram strip and the map below it.
    """
    strip = chart_image.convert("RGBA").crop(METEOGRAM_BOX)
    width = map_image.width
    strip = magic_kernel_sharp_resize(
        strip, (width, round(strip.height * width / strip.width)))

    map_y = strip.height + METEOGRAM_GAP
    combined = Image.new("RGBA", (width, map_y + map_image.height), "white")
    combined.paste(strip, (0, 0))
    combined.paste(map_image, (0, map_y))
    return combined


def load_sources(map_path, chart_path, timestamp):
    """Provide the two source images, downloading them when necessary.

    Args:
        map_path: path of the map image, or None to download both
            images from charts.ecmwf.int.
        chart_path: path of the chart image, or None if no meteogram
            should be added to a locally supplied map.
        timestamp: valid time as string in YYYYMMDDHH format (UTC).

    Returns:
        A tuple of map image, chart image and forecast run. The chart
        image is None if the map was read locally without a chart; the
        run is None for local maps, as it is not part of the image.
    """
    if map_path is not None:
        chart_image = Image.open(chart_path) if chart_path is not None \
            else None
        return Image.open(map_path), chart_image, None

    print("Lade Karte und Meteogramm von charts.ecmwf.int ...")
    chart = ecmwf_api.fetch_map(timestamp)
    return chart.image, ecmwf_api.fetch_meteogram(), chart.base_time


def wait_for_keypress():
    """Block until the user presses a key.

    Terminals without the Windows console API fall back to reading a
    line, where the key has to be confirmed with Enter.
    """
    if msvcrt is not None:
        msvcrt.getch()
    else:
        input()


def pause_for_annotations(map_image, image_path):
    """Write out the bare map and wait for the user to annotate it.

    Lows, fronts and similar marks are drawn by hand in an image
    editor. They have to be added before draw_cities() runs, so that
    the city markers, the labels and the legend end up on top of them
    rather than being covered.

    Args:
        map_image: freshly downloaded map image.
        image_path: working file the map is written to, read back from
            and removed again.

    Returns:
        The image as the editor left it on disk.
    """
    # Crop before saving so nothing is annotated in the strip that the
    # final crop would discard; draw_cities() crops again, which then
    # has no further effect.
    map_image.crop((0, 0, *CROP_SIZE)).save(image_path)
    print(f"Wetterkarte für die Bearbeitung in {image_path} geladen. "
          "Drücke eine Taste um fortzusetzen.")
    wait_for_keypress()

    # copy() decodes the file completely, so the working copy can be
    # removed right away.
    with Image.open(image_path) as annotated:
        image = annotated.copy()
    try:
        os.remove(image_path)
    except OSError as error:
        # A still open editor can keep the file locked. That must not
        # discard the rendering the user has just worked for.
        print(f"Zwischendatei {image_path} nicht gelöscht: {error}",
              file=sys.stderr)
    return image


def main(argv):
    """Run the requested mode and write the annotated map to disk."""
    if len(argv) == 2:
        map_path, chart_path, timestamp = None, None, argv[1]
    elif len(argv) == 3:
        map_path, chart_path, timestamp = argv[1], None, argv[2]
    elif len(argv) == 4:
        map_path, chart_path, timestamp = argv[1], argv[2], argv[3]
    else:
        print("Aufruf: python draw_cities.py [<karte> [<diagramm>]] "
              "<YYYYMMDDHH>", file=sys.stderr)
        return 1

    # Validate before any download so a typo does not cost a request.
    try:
        datetime.strptime(timestamp, "%Y%m%d%H")
    except ValueError:
        print(f"Ungültige Zeitangabe: {timestamp} (erwartet YYYYMMDDHH)",
              file=sys.stderr)
        return 1

    try:
        map_image, chart_image, base_time = load_sources(
            map_path, chart_path, timestamp)
    except (requests.RequestException, LookupError) as error:
        print(f"Abruf von charts.ecmwf.int fehlgeschlagen: {error}",
              file=sys.stderr)
        return 1

    output_path = map_path if map_path is not None else DEFAULT_OUTPUT
    if map_path is None:
        map_image = pause_for_annotations(map_image, ANNOTATION_FILE)

    image = draw_cities(map_image, timestamp, base_time)
    if chart_image is not None:
        image = combine_with_meteogram(image, chart_image)

    # WebP defaults to lossy encoding, which frays the thin contour
    # lines and the small meteogram labels; the argument is ignored by
    # formats that are lossless anyway.
    image.save(output_path, lossless=True)
    print(f"Bild gespeichert: {output_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
