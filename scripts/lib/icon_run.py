"""One complete ICON-D2 run as found on the open data server."""

from dataclasses import dataclass


@dataclass(frozen=True)
class IconRun:
    """One complete run: its base time and the URL of every file, static fields first, then by step."""

    run: str
    urls: tuple[str, ...]
