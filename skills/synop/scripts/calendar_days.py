"""List the calendar days of the forecast with weekday and Austrian holiday.

The analysis names days by weekday and mentions public holidays next to
them. Weekdays and especially the movable feasts that hang on Easter are
easy to get wrong by mental arithmetic, so this script provides them.

Output: one line per day, "YYYY-MM-DD<TAB>Weekday<TAB>holiday or empty".
"""

import argparse
import sys
from datetime import date, timedelta

FIXED_HOLIDAYS = {
    (1, 1): "Neujahr",
    (1, 6): "Heilige Drei Könige",
    (5, 1): "Staatsfeiertag",
    (8, 15): "Mariä Himmelfahrt",
    (10, 26): "Nationalfeiertag",
    (11, 1): "Allerheiligen",
    (12, 8): "Mariä Empfängnis",
    (12, 25): "Christtag",
    (12, 26): "Stefanitag",
}

# Days after Easter Sunday.
EASTER_HOLIDAYS = {
    1: "Ostermontag",
    39: "Christi Himmelfahrt",
    50: "Pfingstmontag",
    60: "Fronleichnam",
}


def easter_sunday(year):
    """Date of Easter Sunday (Gregorian calendar, anonymous algorithm)."""
    a, b, c = year % 19, year // 100, year % 100
    d, e = b // 4, b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = c // 4, c % 4
    w = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * w) // 451
    month = (h + w - 7 * m + 114) // 31
    day = (h + w - 7 * m + 114) % 31 + 1
    return date(year, month, day)


def holiday(day):
    """Name of the Austrian public holiday on a date, or ""."""
    fixed = FIXED_HOLIDAYS.get((day.month, day.day))
    if fixed:
        return fixed
    return EASTER_HOLIDAYS.get((day - easter_sunday(day.year)).days, "")


def main(argv):
    """Print the requested range of days."""
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n", maxsplit=1)[0])
    parser.add_argument("--start", required=True, help="first day in YYYY-MM-DD (local date)")
    parser.add_argument("--days", type=int, default=10, help="number of days (default 10)")
    args = parser.parse_args(argv)
    try:
        start = date.fromisoformat(args.start)
    except ValueError as error:
        print(f"Invalid --start: {error}", file=sys.stderr)
        return 1

    # Holiday names contain umlauts; Windows consoles default to cp1252.
    sys.stdout.reconfigure(encoding="utf-8")
    for offset in range(args.days):
        day = start + timedelta(days=offset)
        print(f"{day:%Y-%m-%d}\t{day:%A}\t{holiday(day)}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
