"""Build the borders of the Austria chart window: the world countries with the Austrian states inside.

The country outlines come from lib/world_countries.geojson (Esri, generalized);
Austria and its nine states come from the administrative boundaries of BEV
(VGD 1:50 000, cadastral communities in MGI / Austria Lambert, EPSG:31287),
dissolved to states and simplified. Tyrol consists of two areas (North and
East Tyrol), so the states are ten polygons.

The generalized Austria of Esri does not follow the detailed border, so
its neighbours would draw a second border line next to it. The neighbours
are therefore cut along the detailed border: what the detailed Austria
covers is removed from them, and the slivers between the two Austrias are
given to the neighbour they touch most.

Every feature keeps COUNTRY and ISO and gets LEVEL: "country" or "state"
(states also NAME). Only countries near Europe are kept, so the file stays
small; BaseMap drops what lies outside a window anyway.

Needs pyshp, shapely (>= 2.1 for coverage_simplify) and pyproj; the pipeline
reads only the written GeoJSON. Run once when the source data changes:

    python scripts/build_borders.py <VGD_50_generalisiert.shp> [scripts/lib/borders_austria.geojson]
"""

import argparse
import json
from collections import defaultdict
from pathlib import Path

import numpy as np
import shapefile
import shapely
from pyproj import Transformer
from shapely.geometry import box, mapping, shape

LIB = Path(__file__).resolve().parent / "lib"
WORLD = LIB / "world_countries.geojson"
TARGET = LIB / "borders_austria.geojson"
SOURCE_CRS = "EPSG:31287"
# Tolerance in m of coverage_simplify (Visvalingam-Whyatt, shared borders stay shared): 0.2 px of the
# Austria window (0.75 km/px); finer detail is never seen.
SIMPLIFY_M = 150.0
# Parts smaller than this (km2) are slivers of the dissolve, not real exclaves.
MIN_PART_KM2 = 0.5
# Countries are kept if they reach into this lon/lat box: the crop box of the Europe window.
KEEP_BOX = box(-71.0, 11.0, 77.0, 76.0)
# Decimal places of the written coordinates: 1e-5 deg is about 1 m.
DECIMALS = 5


def read_states(path: Path) -> dict[str, shapely.Geometry]:
    """Cadastral communities dissolved to one (multi)polygon per state, in the source CRS (m)."""
    parts = defaultdict(list)
    with shapefile.Reader(str(path), encoding="utf-8") as reader:
        for record in reader.iterShapeRecords():
            parts[record.record["BL"]].append(shapely.make_valid(shape(record.shape.__geo_interface__)))
    return {name: shapely.union_all(polygons) for name, polygons in parts.items()}


def without_slivers(geometry: shapely.Geometry) -> shapely.Geometry:
    """Polygon parts above MIN_PART_KM2, holes of the same size dropped too."""
    polygons = [p for p in getattr(geometry, "geoms", [geometry]) if p.geom_type == "Polygon"]
    kept = [shapely.Polygon(p.exterior, [h for h in p.interiors if shapely.Polygon(h).area >= MIN_PART_KM2 * 1e6])
            for p in polygons if p.area >= MIN_PART_KM2 * 1e6]
    return shapely.MultiPolygon(kept) if len(kept) > 1 else kept[0]


def simplified_states(path: Path) -> dict[str, shapely.Geometry]:
    """States simplified as one coverage, so neighbouring states keep a common border."""
    states = {name: without_slivers(geometry) for name, geometry in read_states(path).items()}
    names = sorted(states)
    simplified = shapely.coverage_simplify([states[name] for name in names], SIMPLIFY_M)
    to_wgs84 = Transformer.from_crs(SOURCE_CRS, "EPSG:4326", always_xy=True).transform
    project = lambda xy: np.column_stack(to_wgs84(xy[:, 0], xy[:, 1]))  # noqa: E731
    return {name: shapely.transform(geometry, project) for name, geometry in zip(names, simplified)}


def fit_neighbours(features: list[dict], esri_austria: shapely.Geometry, austria: shapely.Geometry) -> None:
    """Cut the neighbours of Austria along the detailed border, in place."""
    near = esri_austria.buffer(0.2)
    neighbours = [f for f in features if f["geometry"].intersects(near)]
    for feature in neighbours:
        feature["geometry"] = shapely.make_valid(feature["geometry"]).difference(austria)
    slivers = esri_austria.difference(austria)
    for sliver in getattr(slivers, "geoms", [slivers]):
        if sliver.is_empty or sliver.geom_type != "Polygon":
            continue
        # The neighbour with the longest common edge, else the nearest one.
        owner = max(neighbours, key=lambda f: (f["geometry"].buffer(1e-4).intersection(sliver.boundary).length,
                                               -f["geometry"].distance(sliver)))
        owner["geometry"] = owner["geometry"].union(sliver)


def feature(geometry: shapely.Geometry, **properties) -> dict:
    rounded = shapely.set_precision(geometry, 10.0 ** -DECIMALS)
    return {"type": "Feature", "properties": properties, "geometry": mapping(rounded)}


def build(source: Path, target: Path) -> None:
    world = json.loads(WORLD.read_text(encoding="utf-8"))["features"]
    countries = [{"properties": f["properties"], "geometry": shape(f["geometry"])} for f in world]
    countries = [c for c in countries if c["geometry"].intersects(KEEP_BOX)]
    esri_austria = next(c for c in countries if c["properties"]["ISO"] == "AT")
    countries.remove(esri_austria)

    states = simplified_states(source)
    austria = shapely.union_all(list(states.values()))
    fit_neighbours(countries, esri_austria["geometry"], austria)

    features = [feature(c["geometry"], COUNTRY=c["properties"]["COUNTRY"], ISO=c["properties"]["ISO"], LEVEL="country")
                for c in countries if not c["geometry"].is_empty]
    features.append(feature(austria, COUNTRY="Austria", ISO="AT", LEVEL="country"))
    features += [feature(geometry, COUNTRY="Austria", ISO="AT", LEVEL="state", NAME=name)
                 for name, geometry in states.items()]
    target.write_text(json.dumps({"type": "FeatureCollection", "features": features}, separators=(",", ":")),
                      encoding="utf-8")
    parts = sum(len(getattr(g, "geoms", [g])) for g in states.values())
    print(f"{target}: {len(features)} features, {len(states)} states in {parts} polygons, "
          f"{target.stat().st_size / 1e6:.1f} MB")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("source", type=Path, help="VGD shapefile (.shp) of BEV in MGI / Austria Lambert")
    parser.add_argument("target", type=Path, nargs="?", default=TARGET, help=f"GeoJSON to write (default {TARGET})")
    args = parser.parse_args()
    build(args.source, args.target)


if __name__ == "__main__":
    main()
