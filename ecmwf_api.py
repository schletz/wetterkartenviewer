"""Download chart images from the ECMWF open charts API.

Both products are retrieved in two steps: a metadata request returns a
JSON document that carries the URL of the freshly rendered image on the
streaming host, and that URL is then fetched as the actual image.

The 500 hPa map is addressed by its valid time, the meteogram by a
geographic location; neither request needs authentication.
"""

import io
from typing import NamedTuple

import requests
from PIL import Image

API_BASE = "https://charts.ecmwf.int/opencharts-api/v1"

# 500 hPa geopotential height and 850 hPa temperature, European window.
MAP_PRODUCT = "medium-z500-t850"
MAP_PROJECTION = "opencharts_europe"

# Fifteen day ENS meteogram including the climate distribution; this is
# the variant whose layout METEOGRAM_BOX in draw_cities.py refers to.
METEOGRAM_TYPE = "classical_15d_with_climate"
METEOGRAM_LOCATION = {
    "type": "latlon",
    "lat": 48.0,
    "lon": 16.4,
    "station_name": "Traiskirchen",
}

# Seconds to wait per HTTP request. The API renders on demand, so the
# metadata request alone can take several seconds.
TIMEOUT = 60


class MapChart(NamedTuple):
    """A downloaded map together with the forecast run it belongs to."""

    image: Image.Image
    base_time: str | None  # run in YYYYMMDDHHmm format (UTC)


def _download_image(url):
    """Fetch an image URL and decode it into a PIL image.

    Args:
        url: absolute URL of the rendered chart image.

    Returns:
        The decoded image.

    Raises:
        requests.RequestException: on any transport or HTTP error.
    """
    response = requests.get(url, timeout=TIMEOUT)
    response.raise_for_status()
    return Image.open(io.BytesIO(response.content))


def fetch_map(timestamp):
    """Download the 500 hPa map for a given valid time.

    Args:
        timestamp: valid time as string in YYYYMMDDHH format (UTC).

    Returns:
        The uncropped map image as published by ECMWF and the run it
        was computed from; base_time is None if the API omits it.

    Raises:
        LookupError: if the API knows no chart for that valid time.
        requests.RequestException: on any transport or HTTP error.
    """
    # The axis endpoint expects minute precision.
    value = f"{timestamp}00"
    response = requests.get(
        f"{API_BASE}/packages/opencharts/products/{MAP_PRODUCT}"
        "/axis/valid_time/",
        params={"projection": MAP_PROJECTION, "values": value},
        timeout=TIMEOUT)
    response.raise_for_status()

    document = response.json()
    result = document.get("results", {}).get(value)
    if not result or not result.get("url"):
        raise LookupError(f"Keine Karte für den Zeitpunkt {value} verfügbar")
    base_time = document.get("values", {}).get("base_time")
    return MapChart(_download_image(result["url"]), base_time)


def fetch_meteogram(location=None):
    """Download the ENS meteogram for a location.

    Args:
        location: request payload describing the point, defaults to
            METEOGRAM_LOCATION.

    Returns:
        The meteogram image in the same layout as the chart images that
        can be passed on the command line.

    Raises:
        LookupError: if the API returns no image URL.
        requests.RequestException: on any transport or HTTP error.
    """
    payload = {
        "location": location or METEOGRAM_LOCATION,
        "axis": {},
        "epsgrams": METEOGRAM_TYPE,
    }
    response = requests.post(f"{API_BASE}/features/epsgrams/", json=payload,
                             timeout=TIMEOUT)
    response.raise_for_status()

    result = response.json().get("result", {})
    if not result.get("url"):
        raise LookupError("Kein Meteogramm für den Standort verfügbar")
    return _download_image(result["url"])
