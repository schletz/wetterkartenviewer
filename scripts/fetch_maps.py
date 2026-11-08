"""Put the committed manifest and the files it lists from the release into the Pages build.

Runs in the deploy workflow: copies maps/manifest.json to <target> and
downloads every video and series file it lists from the release
(maps_release.py) to the same path below <target>, e.g.
<target>/<window>/<product>.mp4 or <target>/austria/t850.json. The files are
fetched through the REST API, authenticated with the token in the environment
variable GITHUB_TOKEN (optional for a public repository, but unauthenticated
requests are rate limited and the anonymous download URLs are unreliable).
Needs only the standard library.

Usage: python3 scripts/fetch_maps.py maps dist/maps --repository owner/name
"""

import argparse
import http.client
import json
import os
import shutil
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

from maps_manifest import MANIFEST, published_files
from maps_release import asset_name, release_api_url

TIMEOUT_S = 60
# One failed file would stop the whole deployment, so short outages of the release server are waited out.
ATTEMPTS = 3
RETRY_PAUSE_S = 10
FIRST_SERVER_ERROR = 500


class DropAuthOnRedirect(urllib.request.HTTPRedirectHandler):
    """Keep the token on the API host: the storage the API redirects to is pre-signed and rejects an extra Authorization header."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        redirected = super().redirect_request(req, fp, code, msg, headers, newurl)
        if redirected is not None:
            redirected.remove_header("Authorization")
        return redirected


OPENER = urllib.request.build_opener(DropAuthOnRedirect)


def api_request(url: str, accept: str) -> urllib.request.Request:
    """GET request for the GitHub REST API; sends the token from GITHUB_TOKEN if set."""
    request = urllib.request.Request(url, headers={"Accept": accept, "X-GitHub-Api-Version": "2022-11-28"})
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        request.add_header("Authorization", f"Bearer {token}")
    return request


def with_retries(action, label: str):
    """Return ``action()``, retrying up to ``ATTEMPTS`` times on transient errors; exits with a message if it does not succeed."""
    for attempt in range(1, ATTEMPTS + 1):
        try:
            return action()
        # URLError is an OSError, like a timeout or a reset while reading; a truncated body is an HTTPException.
        except (OSError, http.client.HTTPException) as error:
            if attempt == ATTEMPTS or not is_transient(error):
                sys.exit(f"{label}: {error}")
            print(f"{label}: {error}; attempt {attempt + 1} of {ATTEMPTS} in {RETRY_PAUSE_S} s", flush=True)
            time.sleep(RETRY_PAUSE_S)


def release_assets(repository: str) -> dict[str, str]:
    """API download URL of every asset of the release, by asset name."""
    def load() -> dict:
        with OPENER.open(api_request(release_api_url(repository), "application/vnd.github+json"), timeout=TIMEOUT_S) as response:
            return json.load(response)

    release = with_retries(load, release_api_url(repository))
    return {asset["name"]: asset["url"] for asset in release["assets"]}


def is_transient(error: Exception) -> bool:
    """Whether another attempt can help: a server error or a network failure, not a client error such as 404."""
    return not isinstance(error, urllib.error.HTTPError) or error.code >= FIRST_SERVER_ERROR


def download(url: str, target: Path) -> None:
    """Write the asset behind the API URL ``url`` to ``target``, retrying on transient errors."""
    def fetch() -> None:
        # "wb" also discards the part of a file an earlier attempt lost its connection in.
        with OPENER.open(api_request(url, "application/octet-stream"), timeout=TIMEOUT_S) as response, target.open("wb") as out:
            shutil.copyfileobj(response, out)
            # read() returns short without an error when the connection ends early.
            expected = response.headers["Content-Length"]
            if expected is not None and out.tell() != int(expected):
                raise ConnectionError(f"only {out.tell()} of {expected} bytes received")

    with_retries(fetch, url)


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
    assets = release_assets(args.repository)
    for file in files:
        url = assets.get(asset_name(file))
        if url is None:
            sys.exit(f"{file}: no asset {asset_name(file)} in the release")
        target = args.target / file
        target.parent.mkdir(parents=True, exist_ok=True)
        download(url, target)
        print(f"{file}: {target.stat().st_size} bytes")


if __name__ == "__main__":
    main()
