"""The GitHub release that holds the tile videos of maps/, so they never enter the git history.

Release assets have flat names, so a video maps/<window>/<product>.mp4 is
stored as the asset <window>.<product>.mp4 (window and product names
contain no dots). publish_maps.py uploads with the gh CLI; fetch_maps.py
downloads in the deploy workflow through the REST API, authenticated with the
workflow token. The anonymous github.com/.../releases/download/ URLs answer
with HTTP 504 for unauthenticated clients at times.
"""

TAG = "tile-videos"


def asset_name(file: str) -> str:
    """Asset of a video path relative to maps/: opencharts_europe/z500_t850.mp4 -> opencharts_europe.z500_t850.mp4."""
    return file.replace("/", ".")


def release_api_url(repository: str) -> str:
    """REST API URL of the release with the assets; repository is "owner/name"."""
    return f"https://api.github.com/repos/{repository}/releases/tags/{TAG}"
