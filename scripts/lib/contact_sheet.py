"""Contact sheet: several charts of one product reduced to tiles on one image.

A sheet shows the evolution over many days at the cost of about two
single charts, which suits the overview step of an analysis: where the
troughs and ridges go. Labels of the contours are too small to read on
the tiles; values come from the single charts.
"""

from pathlib import Path

from PIL import Image, ImageDraw

from .chart_canvas import LEGEND_HEIGHT, WEBP_QUALITY
from .fonts import load_font
from .projection import IMAGE_HEIGHT, IMAGE_WIDTH

# Two columns of 580 px keep the sheet of ten tiles under 1568 px, the
# size above which images are scaled down before a model sees them.
COLUMNS = 2
TILE_WIDTH = 580
HEADER_HEIGHT = 26
# The first line of a chart's legend strip holds its own valid time and is replaced by the sheet header.
LEGEND_SKIP = 26


class ContactSheet:
    """Layout of the sheets: writes them and gives the position of their tiles."""

    def __init__(self, columns: int = COLUMNS, tile_width: int = TILE_WIDTH):
        self.columns, self.tile_width = columns, tile_width
        self.scale = tile_width / IMAGE_WIDTH
        self.tile_height = round(IMAGE_HEIGHT * self.scale)
        self.legend_height = round((LEGEND_HEIGHT - LEGEND_SKIP) * columns * self.scale)

    def build(self, tiles: list[tuple[Path, str]], title: str, out: Path) -> None:
        """Write a sheet of (chart path, caption) tiles, left to right and top to bottom.

        The colour bar is taken from the legend strip of the first chart.
        """
        rows = -(-len(tiles) // self.columns)
        width = self.columns * self.tile_width
        sheet = Image.new("RGB", (width, HEADER_HEIGHT + rows * self.tile_height + self.legend_height), "white")
        draw = ImageDraw.Draw(sheet)
        draw.text((8, HEADER_HEIGHT // 2), title, fill="black", font=load_font(15, bold=True), anchor="lm")
        caption_font = load_font(15, bold=True)

        for (path, caption), (x, y) in zip(tiles, self.origins(len(tiles))):
            with Image.open(path) as chart:
                if (x, y) == (0, HEADER_HEIGHT):
                    strip = chart.crop((0, IMAGE_HEIGHT + LEGEND_SKIP, IMAGE_WIDTH, IMAGE_HEIGHT + LEGEND_HEIGHT))
                    legend = strip.resize((width, self.legend_height), Image.LANCZOS)
                tile = chart.crop((0, 0, IMAGE_WIDTH, IMAGE_HEIGHT)).resize((self.tile_width, self.tile_height),
                                                                             Image.LANCZOS)
            sheet.paste(tile, (x, y))
            box = draw.textbbox((x + 6, y + 4), caption, font=caption_font)
            draw.rectangle((box[0] - 3, box[1] - 2, box[2] + 3, box[3] + 2), fill="white", outline="black")
            draw.text((x + 6, y + 4), caption, fill="black", font=caption_font)
            # Thin separators between the tiles.
            draw.rectangle((x, y, x + self.tile_width - 1, y + self.tile_height - 1), outline="white")
        sheet.paste(legend, (0, HEADER_HEIGHT + rows * self.tile_height))
        out.parent.mkdir(parents=True, exist_ok=True)
        sheet.save(out, quality=WEBP_QUALITY)

    def origins(self, count: int) -> list[tuple[int, int]]:
        """Top left corners of the first ``count`` tiles, left to right and top to bottom."""
        return [((i % self.columns) * self.tile_width, HEADER_HEIGHT + (i // self.columns) * self.tile_height)
                for i in range(count)]
