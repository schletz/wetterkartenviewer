"""Colour legend of the 850 hPa temperature shading.

The axis endpoint of the open charts API delivers the legend of the
rendered map next to the image URL, so a legend built from it always
matches the shading of that very image. Maps that are read from disk
carry no such metadata; FALLBACK_LEGEND holds the values the API
returned for medium-z500-t850 and is used whenever no legend is
available from the API.
"""

from typing import NamedTuple

RGB = tuple[int, int, int]


class Legend(NamedTuple):
    """A colour bar: one colour per band, boundaries in between.

    Invariant: len(values) == len(colors) - 1. Every value is the
    boundary shared by two adjacent bands; the outer edges of the bar
    are not labelled. The values are rendered verbatim, therefore they
    are kept as the strings the API reports them in.
    """

    title: str
    values: list[str]
    colors: list[RGB]


# Legend of medium-z500-t850 as reported by the API. Used for locally
# supplied maps and whenever the API response carries no usable legend.
FALLBACK_LEGEND = Legend(
    title="850 hPa temperature (C)",
    values=["-70", "-60", "-52", "-48", "-44", "-40", "-36", "-32", "-28",
            "-24", "-20", "-16", "-12", "-8", "-4", "0", "4", "8", "12",
            "16", "20", "24", "28", "32", "36", "40", "44", "48", "52"],
    colors=[
        (255, 255, 255), (229, 229, 229), (204, 204, 204), (178, 178, 178),
        (173, 153, 173), (122, 102, 122), (71, 51, 71), (51, 0, 102),
        (89, 0, 127), (127, 0, 255), (0, 127, 255), (0, 204, 255),
        (0, 255, 255), (38, 229, 153), (102, 191, 38), (191, 229, 38),
        (255, 255, 127), (255, 255, 0), (255, 217, 0), (255, 176, 0),
        (255, 114, 0), (255, 0, 0), (204, 0, 0), (127, 0, 44),
        (204, 61, 110), (255, 0, 255), (255, 127, 255), (255, 191, 255),
        (229, 204, 229), (229, 229, 229),
    ],
)


def _parse_colour(text):
    """Parse a colour of the form "RGBA(r,g,b,a)" into an RGB triple.

    The alpha channel is dropped: the bar is drawn onto the opaque
    white legend box, so transparency would only wash out the colour.

    Args:
        text: colour string as reported by the API.

    Returns:
        The red, green and blue component as integers.

    Raises:
        ValueError: if the string does not have the expected shape.
    """
    inner = text[text.index("(") + 1:text.rindex(")")]
    components = inner.split(",")
    if len(components) < 3:
        raise ValueError(f"Unerwartete Farbangabe: {text}")
    return tuple(round(float(part)) for part in components[:3])


def parse_legend(result):
    """Build the temperature legend from a result of the axis endpoint.

    Args:
        result: the results[<value>] object of the API response, whose
            "legend" list holds one entry per plotted quantity.

    Returns:
        The colour bar of the temperature shading, or None if the
        response carries no usable one. The caller then falls back to
        FALLBACK_LEGEND.
    """
    for item in result.get("legend") or []:
        data = item.get("data") or {}
        # The same list also describes the geopotential contours, which
        # are of type "double-line" and carry no colour bands.
        if data.get("type") != "colorbar":
            continue
        entries = data.get("entries") or []
        try:
            colors = [_parse_colour(entry["colour"]) for entry in entries]
            values = [entry["max-range"] for entry in entries[:-1]]
        except (KeyError, ValueError, TypeError):
            continue  # malformed colour bar, try the next legend entry
        if not colors:
            continue
        # The API pads its titles with double spaces.
        title = " ".join((data.get("title") or "").split())
        return Legend(title or FALLBACK_LEGEND.title, values, colors)
    return None
