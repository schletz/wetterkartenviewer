"""Mirror data/ into the Azure blob container the synop skill reads, so the skill works apart from this repository.

The container is readable and listable without credentials:

    https://<account>.blob.core.windows.net/forecastdata/<path relative to data/>

It holds the data directory of the skill: ecmwf_<run>.grb2, icon-d2_<run>.grb2, charts.md,
era5_means/ and the chart windows (opencharts_europe/, opencharts_central_europe/, icon-d2/).
Unfinished downloads (*.part, *.raw/) are left out; the videos of maps/ are never in data/.

The container keeps no history: blobs without a local file (older runs, charts of past steps)
are deleted, and soft delete is off. A file is uploaded if its blob is missing or differs in
size or in the local modification time stored as blob metadata, so a call without a new run
only lists the container. Uploads go first and deletions last: a reader finds the GRIB of the
old run until the new one is complete; re-rendered charts are replaced in place.

Blobs are written in the hot tier although the account defaults to cool: cool blobs deleted
within 30 days are billed for the full 30 days, and every run replaces several GB.

Credentials: BLOB_STORAGE_ID (account name or its resource ID) and BLOB_STORAGE_KEY (account
key) from the environment or from .env in the repository root. Without them nothing happens.

Usage: python scripts/blob_mirror.py data
"""

import argparse
import os
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from azure.storage.blob import BlobServiceClient, ContainerClient, ContentSettings, StandardBlobTier

ENV_FILE = Path(__file__).resolve().parent.parent / ".env"
ACCOUNT_VARIABLE, KEY_VARIABLE = "BLOB_STORAGE_ID", "BLOB_STORAGE_KEY"
CONTAINER = "forecastdata"
# Suffixes of unfinished downloads (download_ecmwf_data.py, download_icon_d2.py).
UNFINISHED = (".part", ".raw")
CONTENT_TYPES = {".grb2": "application/octet-stream", ".md": "text/markdown; charset=utf-8",
                 ".json": "application/json", ".webp": "image/webp"}
MTIME = "mtime"
# Files uploaded at once; a large GRIB is split into blocks sent BLOCK_UPLOADS at a time.
PARALLEL_UPLOADS = 8
BLOCK_UPLOADS = 4
# Upper limit of one batch delete request.
DELETE_BATCH = 256
MB = 1024 * 1024


def credentials() -> tuple[str, str] | None:
    """(account name, account key) from the environment, else from .env; None if one is missing.

    BLOB_STORAGE_ID may be the resource ID of the account (/subscriptions/.../storageAccounts/<name>).
    """
    values = {}
    if ENV_FILE.is_file():
        for line in ENV_FILE.read_text(encoding="utf-8-sig").splitlines():
            name, separator, value = line.partition("=")
            if separator and not name.strip().startswith("#"):
                values[name.strip()] = value.strip().strip("\"'")
    values |= {name: os.environ[name] for name in (ACCOUNT_VARIABLE, KEY_VARIABLE) if os.environ.get(name)}
    account, key = values.get(ACCOUNT_VARIABLE), values.get(KEY_VARIABLE)
    if not account or not key:
        return None
    return account.rstrip("/").rsplit("/", 1)[-1], key


def container_client(account: str, key: str) -> ContainerClient:
    """Client of the container, authorised with the account key."""
    service = BlobServiceClient(f"https://{account}.blob.core.windows.net", credential=key)
    return service.get_container_client(CONTAINER)


def local_files(data: Path) -> dict[str, Path]:
    """Blob name (path relative to data/, with /) → file, for every finished file in data/."""
    files = {}
    for path in data.rglob("*"):
        relative = path.relative_to(data)
        if path.is_file() and not any(part.endswith(UNFINISHED) for part in relative.parts):
            files[relative.as_posix()] = path
    return files


def stamp(path: Path) -> str:
    """Local modification time as stored in the metadata of its blob."""
    return str(path.stat().st_mtime_ns)


def stale_files(files: dict[str, Path], blobs: dict) -> list[str]:
    """Names of files whose blob is missing or has another size or modification time."""
    return [name for name, path in files.items() if name not in blobs
            or blobs[name].size != path.stat().st_size or (blobs[name].metadata or {}).get(MTIME) != stamp(path)]


def upload(container: ContainerClient, name: str, path: Path) -> None:
    """Upload one file in the hot tier, replacing its blob, with its modification time as metadata."""
    settings = ContentSettings(content_type=CONTENT_TYPES.get(path.suffix, "application/octet-stream"))
    with path.open("rb") as stream:
        container.upload_blob(name, stream, length=path.stat().st_size, overwrite=True,
                              metadata={MTIME: stamp(path)}, content_settings=settings,
                              standard_blob_tier=StandardBlobTier.HOT, max_concurrency=BLOCK_UPLOADS)


def delete(container: ContainerClient, names: list[str]) -> None:
    """Delete blobs in batch requests."""
    for start in range(0, len(names), DELETE_BATCH):
        container.delete_blobs(*names[start:start + DELETE_BATCH])


def mirror(data: Path) -> None:
    """Make the container hold exactly the finished files of data/; skipped without credentials.

    Raises azure.core.exceptions.AzureError on network or service errors; files uploaded
    until then stay, the next call sends the rest.
    """
    login = credentials()
    if login is None:
        print(f"blob mirror skipped: {ACCOUNT_VARIABLE} and {KEY_VARIABLE} are not set (environment or {ENV_FILE})")
        return
    started = time.monotonic()
    container = container_client(*login)
    files = local_files(data)
    blobs = {blob.name: blob for blob in container.list_blobs(include=["metadata"])}
    uploads = stale_files(files, blobs)
    with ThreadPoolExecutor(PARALLEL_UPLOADS) as pool:
        # list() collects the results, so the first failed upload raises here.
        list(pool.map(lambda name: upload(container, name, files[name]), uploads))
    obsolete = sorted(set(blobs) - set(files))
    delete(container, obsolete)
    size = sum(files[name].stat().st_size for name in uploads) / MB
    print(f"blob mirror {container.url}: uploaded {len(uploads)} files ({size:.0f} MB), "
          f"deleted {len(obsolete)} blobs in {time.monotonic() - started:.0f} s")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("data", type=Path, help="data directory written by update_maps.py")
    mirror(parser.parse_args().data)


if __name__ == "__main__":
    main()
