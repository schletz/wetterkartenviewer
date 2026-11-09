"""Build the county borders of Hungary as lines, for the chart window chmi-aladin.

One-off tool, run by hand. The input is the NUTS 3 layer of Eurostat GISCO
(1:1 million, EPSG:4326, © EuroGeographics for the administrative boundaries):

    https://gisco-services.ec.europa.eu/distribution/v2/nuts/geojson/NUTS_RG_01M_2021_4326_LEVL_3.geojson

Only the borders between counties are kept. The outer border of Hungary is left
out on purpose: the base map already draws it from another, generalized source,
and a second, slightly different line beside it would look like a double border.
Budapest is an enclave of Pest, its border is inner too.

Usage: python scripts/build_county_lines.py <NUTS level 3 geojson> [target.geojson]
"""

import argparse
import json
from pathlib import Path

import shapely
from shapely.geometry import MultiLineString, mapping, shape
from shapely.ops import linemerge, unary_union

TARGET = Path(__file__).resolve().parent / "lib" / "borders_hungary_counties.geojson"
COUNTRY = "HU"
# Tolerance of coverage_simplify in degrees: 0.2 px of the chart window at 1.1 km/px is about 220 m, or 0.002 deg.
SIMPLIFY_DEG = 0.002
# The outer border is removed with this margin, in degrees, so that rounding cannot leave splinters along it.
OUTER_MARGIN_DEG = 1e-7
DECIMALS = 5


def county_lines(source: Path) -> MultiLineString:
    """Return the borders between the counties of ``COUNTRY``, merged into as few lines as possible."""
    features = json.loads(source.read_text(encoding="utf-8"))["features"]
    counties = [shape(f["geometry"]) for f in features if f["properties"]["CNTR_CODE"] == COUNTRY]
    # Simplified as one coverage, so a border shared by two counties stays one line.
    simplified = list(shapely.coverage_simplify(counties, SIMPLIFY_DEG))
    outer = unary_union(simplified).boundary.buffer(OUTER_MARGIN_DEG)
    inner = unary_union([county.boundary for county in simplified]).difference(outer)
    merged = linemerge(inner)
    return merged if isinstance(merged, MultiLineString) else MultiLineString([merged])


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("source", type=Path, help="NUTS level 3 GeoJSON of GISCO in EPSG:4326")
    parser.add_argument("target", type=Path, nargs="?", default=TARGET)
    args = parser.parse_args()
    lines = shapely.set_precision(county_lines(args.source), 10 ** -DECIMALS)
    collection = {"type": "FeatureCollection", "features": [{
        "type": "Feature", "properties": {"COUNTRY": "Hungary", "ISO": "HU", "LEVEL": "state"},
        "geometry": mapping(lines)}]}
    args.target.write_text(json.dumps(collection, separators=(",", ":")), encoding="utf-8")
    print(f"{args.target}: {len(lines.geoms)} lines, {args.target.stat().st_size / 1e3:.0f} KB")


if __name__ == "__main__":
    main()
