#!/bin/sh
# Bring the checkout to origin/main (git fetch + reset --hard, so code pushed from other machines is
# what runs), then download the newest ECMWF run into data/, render the charts there, encode the tiles
# as videos in maps/ and publish them (release upload, manifest commit, push). Without a new run only
# missing videos are encoded.
# Both scripts get all options: with --force update_maps.py renders everything again and publish_maps.py
# deploys even if the manifest stays the same.
#
# The reset discards changes to tracked files and local commits without asking, as the name says.
# data/ and maps/ are ignored by git and stay.

BRANCH=main

log() {
    echo "[$(date '+%H:%M:%S')] $*"
}

# Fetch and reset; a failure stops the script, so the pipeline never runs on stale code.
sync_checkout() {
    if [ "$(git rev-parse --abbrev-ref HEAD)" != "$BRANCH" ]; then
        echo "the checkout is not on branch $BRANCH; check it out first" >&2
        return 1
    fi
    git fetch -q origin "$BRANCH" || { echo "git fetch failed" >&2; return 1; }
    git reset -q --hard "origin/$BRANCH" || { echo "git reset failed" >&2; return 1; }
    log "at $(git log -1 --format='%h %s')"
}

main() {
    cd "$(dirname "$0")" || exit 1
    if [ "$WETTER_SYNCED" != 1 ]; then
        sync_checkout || exit 1
        # The shell keeps reading the version it started with; the reset may have changed this file,
        # so the pipeline runs from a fresh start of the current version, without a second sync.
        WETTER_SYNCED=1
        export WETTER_SYNCED
        exec ./download_data_with_reset.sh "$@"
    fi
    python3 scripts/update_maps.py data maps "$@" && python3 scripts/publish_maps.py maps "$@"
}

# Calling main and exiting on the same line keeps the shell from reading on in a file that git reset
# replaced mid-run.
main "$@"; exit
