"""TrueType fonts for text drawn with PIL."""

from PIL import ImageFont

_NAMES = {False: ("arial.ttf", "DejaVuSans.ttf"), True: ("arialbd.ttf", "DejaVuSans-Bold.ttf")}


def load_font(size: int, bold: bool = False):
    """Arial or DejaVu Sans if available, else PIL's default font."""
    for name in _NAMES[bold]:
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()
