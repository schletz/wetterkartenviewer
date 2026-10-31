"""Put the committed manifest and the videos it lists from the release into the Pages build.

Runs in the deploy workflow: copies maps/manifest.json to <target> and
downloads every video it lists from the release (maps_release.py) to
<target>/<window>/<product>.mp4. The repository is public, so the downloads
need no token. Needs only the standard library.

Usage: python3 scripts/fetch_maps.py maps dist/maps --repository owner/name
"""

import argparse
import shutil
import sys
import urllib.error
import urllib.request
from pathlib import Path

from maps_manifest import MANIFEST, video_files
from maps_release import download_url

TIMEOUT_S = 60


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("maps", type=Path, help="directory with the committed manifest.json")
    parser.add_argument("target", type=Path, help="chart directory of the build, e.g. dist/maps")
    parser.add_argument("--repository", required=True, help="owner/name of the repository with the release")
    args = parser.parse_args()
    files = video_files(args.maps)
    if not files:
        sys.exit(f"{args.maps / MANIFEST} is missing or lists no video")
    args.target.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(args.maps / MANIFEST, args.target / MANIFEST)
    for file in files:
        target = args.target / file
        target.parent.mkdir(parents=True, exist_ok=True)
        url = download_url(args.repository, file)
        try:
            with urllib.request.urlopen(url, timeout=TIMEOUT_S) as response, target.open("wb") as out:
                shutil.copyfileobj(response, out)
        except urllib.error.URLError as error:
            sys.exit(f"{url}: {error}")
        print(f"{file}: {target.stat().st_size} bytes")


if __name__ == "__main__":
    main()
