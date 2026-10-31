"""The TSV of one location: every parameter of the forecast file per step, in GRIB units.

Columns are valid_utc (YYYYMMDDHH) and step_h, then the field name, with the
level appended on pressure levels (t850, uf1000) and heights (t2000m), bare
otherwise (msl, 2t, thick, deg0l, ...). Missing values are empty.
"""

import csv
import math
from datetime import datetime
from pathlib import Path

from .constants import KELVIN


class ForecastTsv:
    """Writes the TSV and reads the air mass series back from it."""

    def __init__(self, path: Path):
        self.path = Path(path)

    def write(self, valid_times: list[datetime], steps: list[int], values: list[dict[str, float | None]]) -> None:
        """One row per step; ``values`` holds the GRIB values of each step keyed by column."""
        columns = list(values[0])
        lines = ["\t".join(["valid_utc", "step_h", *columns])]
        for valid, step, row in zip(valid_times, steps, values):
            lines.append("\t".join([f"{valid:%Y%m%d%H}", str(step), *(self._number(row[column]) for column in columns)]))
        self.path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    def air_mass(self) -> list[tuple[datetime, int | None, float | None, float | None, float | None]]:
        """(valid time, step, T850 deg C, thickness dam, RH700 %) per row in file order; None where empty."""
        def value(text: str | None, offset: float = 0.0, factor: float = 1.0) -> float | None:
            return (float(text) + offset) * factor if text and text.strip() else None

        with self.path.open(encoding="utf-8", newline="") as stream:
            return [(datetime.strptime(record["valid_utc"], "%Y%m%d%H"),
                     int(record["step_h"]) if record.get("step_h") else None,
                     value(record.get("t850"), offset=-KELVIN), value(record.get("thick"), factor=0.1),
                     value(record.get("r700")))
                    for record in csv.DictReader(stream, delimiter="\t")]

    @staticmethod
    def _number(value: float | None) -> str:
        """Three decimals without trailing zeros (omega in Pa/s needs them), empty for missing values."""
        if value is None or math.isnan(value):
            return ""
        text = f"{round(value, 3) + 0.0:.3f}".rstrip("0").rstrip(".")
        return "0" if text == "-0" else text
