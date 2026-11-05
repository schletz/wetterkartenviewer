#!/bin/sh
# Bring the checkout to origin/main (git fetch + reset --hard, so code pushed from other machines is
# what runs), then download the newest ECMWF run into data/, render the charts there, encode the tiles
# as videos in maps/ and publish them (release upload, manifest commit, push). Without a new run only
# missing videos are encoded.
# Both scripts get all options: with --force update_maps.py renders everything again and publish_maps.py
# deploys even if the manifest stays the same.
#
# The reset discards changes to tracked files and local commits. If anything besides unpushed manifest
# commits (left by a failed push) would get lost, the script asks first; WETTER_RESET_CONFIRMED=1 skips
# the question (download_loop.sh asks once at its start). data/ and maps/ are ignored by git and stay.

BRANCH=main

log() {
    echo "[$(date '+%H:%M:%S')] $*"
}

# What the reset would discard: changed tracked files and unpushed commits that touch more than the
# manifest. Prints nothing if nothing of value is lost.
at_risk() {
    git status --short --untracked-files=no
    if git diff --name-only "origin/$BRANCH...HEAD" | grep -qv '^maps/manifest\.json$'; then
        git log --oneline "origin/$BRANCH..HEAD"
    fi
}

confirm_reset() {
    lost=$(at_risk)
    if [ -z "$lost" ] || [ "$WETTER_RESET_CONFIRMED" = 1 ]; then
        return 0
    fi
    echo "git reset --hard origin/$BRANCH would discard:"
    echo "$lost"
    printf 'Continue? [y/N] '
    # Without a terminal (cron, ssh without tty) the read fails and the reset is refused.
    { read -r answer < /dev/tty; } 2>/dev/null || { echo; return 1; }
    case "$answer" in
        y|Y|yes|j|J|ja) return 0 ;;
        *) return 1 ;;
    esac
}

# Fetch and reset; a failure stops the script, so the pipeline never runs on stale code.
sync_checkout() {
    if [ "$(git rev-parse --abbrev-ref HEAD)" != "$BRANCH" ]; then
        echo "the checkout is not on branch $BRANCH; check it out first" >&2
        return 1
    fi
    git fetch -q origin "$BRANCH" || { echo "git fetch failed" >&2; return 1; }
    confirm_reset || { echo "aborted, nothing changed" >&2; return 1; }
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
        exec ./download_data.sh "$@"
    fi
    python3 scripts/update_maps.py data maps "$@" && python3 scripts/publish_maps.py maps "$@"
}

# Calling main and exiting on the same line keeps the shell from reading on in a file that git reset
# replaced mid-run.
main "$@"; exit
