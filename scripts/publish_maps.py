"""Publish maps/: upload the tile videos to the release, commit the manifest and push.

maps/ holds only the manifest and one video per tile layer (update_maps.py
encodes them from the charts in data/), so viewer.config.json alone
decides what is published. The videos (about 50 MB per ECMWF run) replace
the assets of the release (maps_release.py); only videos that changed since
their upload are sent again (another size, or a file newer than the asset),
so a new ICON-D2 run every 3 h uploads only its own videos. Assets the
manifest no longer lists are deleted. Only maps/manifest.json enters the
history, as one commit "Data update <run>z" (plus the runs of other models),
so the repository does not grow with the videos. The push triggers the Pages deployment, which downloads the videos
the manifest lists (fetch_maps.py); uploading first means it never finds a
manifest without its videos.

Requires the GitHub CLI gh, logged in with write access to the repository.

Usage: python scripts/publish_maps.py maps
"""

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from maps_manifest import MANIFEST, read_run, read_window_runs, video_files
from maps_release import TAG, asset_name

ROOT = Path(__file__).resolve().parent.parent


def call(*command: str) -> str:
    """Run a command in the repository root and return its output; exit with its stderr if it fails."""
    result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, encoding="utf-8")
    if result.returncode:
        sys.exit(f"{' '.join(command)} failed:\n{result.stderr.strip()}")
    return result.stdout.strip()


def ensure_release() -> None:
    """Create the release on first use; it is not marked latest, as it holds no version of the app."""
    if subprocess.run(["gh", "release", "view", TAG], cwd=ROOT, capture_output=True).returncode:
        call("gh", "release", "create", TAG, "--title", "Tile videos", "--latest=false",
             "--notes", "Videos of the current run; every run replaces them (scripts/publish_maps.py).")
        print(f"created release {TAG}")


def changed_videos(maps: Path, files: list[str]) -> list[str]:
    """Videos without an asset of the same size uploaded after the file was written."""
    assets = {asset["name"]: asset for asset in json.loads(call("gh", "release", "view", TAG, "--json", "assets"))["assets"]}
    changed = []
    for file in files:
        asset, local = assets.get(asset_name(file)), (maps / file).stat()
        written = datetime.fromtimestamp(local.st_mtime, timezone.utc)
        if asset is None or asset["size"] != local.st_size or datetime.fromisoformat(asset["updatedAt"]) < written:
            changed.append(file)
    return changed


def upload_videos(maps: Path, files: list[str]) -> None:
    """Upload the videos under their asset names, replacing assets of the same name."""
    with tempfile.TemporaryDirectory() as staging:
        # gh names an asset after its file, so the videos are copied under the flat asset names first.
        paths = []
        for file in files:
            paths.append(str(Path(staging) / asset_name(file)))
            shutil.copyfile(maps / file, paths[-1])
        call("gh", "release", "upload", TAG, *paths, "--clobber")
    print(f"uploaded {len(files)} videos to release {TAG}")


def prune_assets(files: list[str]) -> None:
    """Delete the assets of videos the manifest no longer lists."""
    keep = {asset_name(file) for file in files}
    for name in call("gh", "release", "view", TAG, "--json", "assets", "--jq", ".assets[].name").splitlines():
        if name not in keep:
            call("gh", "release", "delete-asset", TAG, name, "--yes")
            print(f"deleted asset {name}")


def commit_message(maps: Path, run: str) -> str:
    """"Data update <run>z", followed by the runs of windows of other models, e.g. ", icon-d2 2026103109z"."""
    others = sorted({(window, window_run) for window, window_run in read_window_runs(maps).items() if window_run != run})
    return f"Data update {run}z" + "".join(f", {window} {window_run}z" for window, window_run in others)


def commit_manifest(maps: Path, run: str) -> None:
    """Commit the manifest alone, if it changed; other staged changes stay staged."""
    manifest = str((maps / MANIFEST).resolve())
    call("git", "add", manifest)
    if subprocess.run(["git", "diff", "--cached", "--quiet", "--", manifest], cwd=ROOT).returncode:
        message = commit_message(maps, run)
        call("git", "commit", "-q", "-m", message, "--", manifest)
        print(f"committed {message}")
    else:
        print("manifest unchanged")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("maps", type=Path, help="video directory of the viewer")
    args = parser.parse_args()
    run, files = read_run(args.maps), video_files(args.maps)
    if run is None or not files:
        sys.exit(f"{args.maps / MANIFEST} is missing or lists no video; run update_maps.py first")
    missing = [file for file in files if not (args.maps / file).is_file()]
    if missing:
        sys.exit(f"videos listed in the manifest are missing: {', '.join(missing)}; run update_maps.py")
    ensure_release()
    changed = changed_videos(args.maps, files)
    if changed:
        upload_videos(args.maps, changed)
    else:
        print("every video is up to date in the release")
    prune_assets(files)
    commit_manifest(args.maps, run)
    # Pushes also local commits of code changes; a push of an unchanged HEAD is a no-op.
    call("git", "push", "-q", "origin", "HEAD")
    print(f"charts of run {run} published")


if __name__ == "__main__":
    main()
