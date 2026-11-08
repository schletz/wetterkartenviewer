"""Put the committed manifest and the files it lists from the release into the Pages build.

Runs in the deploy workflow: copies maps/manifest.json to <target> and
downloads every video and series file it lists from the release
(maps_release.py) to the same path below <target>, e.g.
<target>/<window>/<product>.mp4 or <target>/austria/t850.json. The repository is public, so the downloads
need no token. Needs only the standard library.

Usage: python3 scripts/fetch_maps.py maps dist/maps --repository owner/name
"""

import argparse
import http.client
import shutil
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

from maps_manifest import MANIFEST, published_files
from maps_release import download_url

TIMEOUT_S = 60
# One failed file would stop the whole deployment, so short outages of the release server are waited out.
ATTEMPTS = 3
RETRY_PAUSE_S = 10
FIRST_SERVER_ERROR = 500


def is_transient(error: Exception) -> bool:
    """Whether another attempt can help: a server error or a network failure, not a client error such as 404."""
    return not isinstance(error, urllib.error.HTTPError) or error.code >= FIRST_SERVER_ERROR


def download(url: str, target: Path) -> None:
    """Write ``url`` to ``target``, up to ``ATTEMPTS`` times; exits with a message if it does not succeed."""
    for attempt in range(1, ATTEMPTS + 1):
        try:
            # "wb" also discards the part of a file an earlier attempt lost its connection in.
            with urllib.request.urlopen(url, timeout=TIMEOUT_S) as response, target.open("wb") as out:
                shutil.copyfileobj(response, out)
                # read() returns short without an error when the connection ends early.
                expected = response.headers["Content-Length"]
                if expected is not None and out.tell() != int(expected):
                    raise ConnectionError(f"only {out.tell()} of {expected} bytes received")
            return
        # URLError is an OSError, like a timeout or a reset while reading; a truncated body is an HTTPException.
        except (OSError, http.client.HTTPException) as error:
            if attempt == ATTEMPTS or not is_transient(error):
                sys.exit(f"{url}: {error}")
            print(f"{url}: {error}; attempt {attempt + 1} of {ATTEMPTS} in {RETRY_PAUSE_S} s", flush=True)
            time.sleep(RETRY_PAUSE_S)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("maps", type=Path, help="directory with the committed manifest.json")
    parser.add_argument("target", type=Path, help="chart directory of the build, e.g. dist/maps")
    parser.add_argument("--repository", required=True, help="owner/name of the repository with the release")
    args = parser.parse_args()
    files = published_files(args.maps)
    if not files:
        sys.exit(f"{args.maps / MANIFEST} is missing or lists no file")
    args.target.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(args.maps / MANIFEST, args.target / MANIFEST)
    for file in files:
        target = args.target / file
        target.parent.mkdir(parents=True, exist_ok=True)
        download(download_url(args.repository, file), target)
        print(f"{file}: {target.stat().st_size} bytes")


if __name__ == "__main__":
    main()
