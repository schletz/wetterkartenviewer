"""Render the T850 and 1000-500 hPa thickness series as an SVG diagram.

Input is the TSV written by location_table.py --tsv. The x axis runs in
UTC over the whole forecast with a gridline at every 00 UTC, the date
centred under each day and minor ticks every 3 h. T850 uses the left
axis, the thickness the right one; both are coupled (lib/coupled_axes.py).

A grey line shows the mean T850 of the climatology (lib/t850_climate.py)
at the nearest climatology grid point of --lat/--lng, for the time of day
and year of every valid time. The area between it and the forecast is red
where the forecast is warmer and blue where it is colder, one shade
darker beyond every standard deviation (lib/forecast_diagram.py).

Without explicit limits the T850 axis is fitted to the data; a missing
thickness limit follows from the T850 axis through the coupling.
"""

import argparse
import sys
from pathlib import Path

# Keep imports working under "python -I", which drops the script directory.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib.anomaly_bands import AnomalyBands  # noqa: E402
from lib.climate_archive import ClimateArchive  # noqa: E402
from lib.coupled_axes import CoupledAxes  # noqa: E402
from lib.diagram_row import DiagramRow  # noqa: E402
from lib.forecast_diagram import ForecastDiagram  # noqa: E402
from lib.forecast_tsv import ForecastTsv  # noqa: E402
from lib.t850_climate import T850Climate  # noqa: E402
from lib.time_axis import TimeAxis  # noqa: E402

# Anomaly layers beyond mean +- k sigma.
SIGMA_STEPS = (0, 1, 2, 3)


def read_rows(tsv: ForecastTsv, climate: T850Climate, lat: float, lng: float) -> list[DiagramRow]:
    """Rows of the TSV with the climate of every valid time, sorted by valid time.

    Raises:
        ValueError: if the file holds fewer than two rows or malformed values.
    """
    series = sorted(tsv.air_mass(), key=lambda row: row[0])
    if len(series) < 2:
        raise ValueError("need at least two valid times")
    means = climate.at_point([row[0] for row in series], lat, lng)
    return [DiagramRow(valid, t850, thickness, f"{rh700:.0f}" if rh700 is not None else "", mean, std)
            for (valid, _, t850, thickness, rh700), (mean, std) in zip(series, means)]


def main(argv):
    """Parse the arguments, read the TSV and write the SVG."""
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n", maxsplit=1)[0])
    parser.add_argument("data", help="TSV written by location_table.py --tsv")
    parser.add_argument("--climate", type=Path, required=True,
                        help="climatology directory era5_means/ of the data directory")
    parser.add_argument("--lat", type=float, required=True, help="latitude of the location (deg N), for the climate mean")
    parser.add_argument("--lng", type=float, required=True, help="longitude of the location (deg E), for the climate mean")
    parser.add_argument("--min-850", type=float, help="lower end of the T850 axis in degC; default: from the data")
    parser.add_argument("--max-850", type=float, help="upper end of the T850 axis in degC; default: from the data")
    parser.add_argument("--min-thickness", type=float,
                        help="lower end of the thickness axis in dam; default: coupled to --min-850")
    parser.add_argument("--max-thickness", type=float,
                        help="upper end of the thickness axis in dam; default: coupled to --max-850")
    parser.add_argument("--out", help="SVG file to write; default stdout")
    args = parser.parse_args(argv)

    climate = T850Climate(ClimateArchive(args.climate))
    try:
        rows = read_rows(ForecastTsv(args.data), climate, args.lat, args.lng)
    except (OSError, ValueError, KeyError) as error:
        print(f"Cannot read {args.data}: {error}", file=sys.stderr)
        return 1
    try:
        axes = CoupledAxes.fit(rows, args.min_850, args.max_850, args.min_thickness, args.max_thickness)
    except ValueError as error:
        print(error, file=sys.stderr)
        return 1

    diagram = ForecastDiagram(rows, TimeAxis(rows[0].valid, rows[-1].valid), axes, AnomalyBands(SIGMA_STEPS),
                              f"Ø {climate.period}")
    svg = diagram.svg()
    if args.out:
        Path(args.out).write_text(svg, encoding="utf-8")
    else:
        # Windows consoles default to cp1252, which lacks "−" and "–".
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stdout.write(svg)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
