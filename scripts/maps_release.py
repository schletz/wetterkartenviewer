"""The GitHub release that holds the tile videos of maps/, so they never enter the git history.

Release assets have flat names, so a video maps/<window>/<product>.mp4 is
stored as the asset <window>.<product>.mp4 (window and product names
contain no dots). publish_maps.py uploads with the gh CLI; fetch_maps.py
downloads in the deploy workflow without a token, which works because the
repository is public.
"""

TAG = "tile-videos"


def asset_name(file: str) -> str:
    """Asset of a video path relative to maps/: opencharts_europe/z500_t850.mp4 -> opencharts_europe.z500_t850.mp4."""
    return file.replace("/", ".")


def download_url(repository: str, file: str) -> str:
    """Public download URL of the asset of a video path; repository is "owner/name"."""
    return f"https://github.com/{repository}/releases/download/{TAG}/{asset_name(file)}"
