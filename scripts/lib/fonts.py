"""TrueType fonts for text drawn with PIL."""

from PIL import ImageFont

# PIL matches font file names exactly: Windows ships arial.ttf/arialbd.ttf, macOS Arial.ttf and
# "Arial Bold.ttf" (Supplemental), Linux usually only DejaVu.
_NAMES = {False: ("arial.ttf", "Arial.ttf", "DejaVuSans.ttf"),
          True: ("arialbd.ttf", "Arial Bold.ttf", "DejaVuSans-Bold.ttf")}


def load_font(size: int, bold: bool = False):
    """Arial (Windows, macOS) or DejaVu Sans if available, else PIL's default font at ``size``."""
    for name in _NAMES[bold]:
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default(size)
