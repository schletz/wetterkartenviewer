#!/bin/sh
# Unattended publishing (e.g. on an always-on Mac): every INTERVAL seconds, bring the checkout to
# origin/main (git fetch + reset --hard, so code changes and manifests pushed from other machines
# arrive) and run download_data.sh. publish_maps.py commits the manifest only when a new run was
# rendered and pushes it; without a new run nothing is committed. data/ and maps/ are ignored by git,
# so the reset keeps the downloaded runs and the encoded videos.
#
# Usage: ./download_loop.sh [--yes]     (--yes skips the confirmation, e.g. after a restart)

INTERVAL=600
BRANCH=main
# Absolute path, so the restart and the change check work after the cd into the repository.
SELF="$(cd "$(dirname "$0")" && pwd)/$(basename "$0")"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"
}

confirm() {
    echo "This script runs 'git reset --hard origin/$BRANCH' in $(pwd) every $((INTERVAL / 60)) minutes."
    echo "Uncommitted changes to tracked files and local commits that are not pushed get lost:"
    git status --short --untracked-files=no
    git log --oneline "origin/$BRANCH..HEAD" 2>/dev/null
    printf 'Continue? [y/N] '
    read -r answer < /dev/tty
    case "$answer" in
        y|Y|yes|j|J|ja) ;;
        *) echo "aborted"; exit 1 ;;
    esac
}

# One pass: sync with origin, then download, render and publish. A failed fetch skips the pass,
# so a network outage never runs the pipeline on stale code.
update() {
    if ! git fetch -q origin "$BRANCH"; then
        log "git fetch failed, skipping this pass"
        return
    fi
    script=$(git hash-object "$SELF")
    git reset -q --hard "origin/$BRANCH" || { log "git reset failed, skipping this pass"; return; }
    log "at $(git log -1 --format='%h %s')"
    # The shell has read this file once; a changed version takes effect by starting it again.
    if [ "$(git hash-object "$SELF")" != "$script" ]; then
        log "download_loop.sh changed, restarting it"
        exec "$SELF" --yes
    fi
    if ./download_data.sh; then
        log "pass finished"
    else
        log "pass failed (exit $?), retrying in the next pass"
    fi
}

main() {
    cd "$(dirname "$SELF")" || exit 1
    if [ "$(git rev-parse --abbrev-ref HEAD)" != "$BRANCH" ]; then
        echo "the checkout is not on branch $BRANCH; check it out first" >&2
        exit 1
    fi
    [ "$1" = "--yes" ] || confirm
    while :; do
        start=$(date +%s)
        update
        # Passes start every INTERVAL seconds; a pass that took longer is followed by the next at once.
        wait=$((start + INTERVAL - $(date +%s)))
        if [ "$wait" -gt 0 ]; then
            log "next pass in $((wait / 60)) min"
            sleep "$wait"
        fi
    done
}

# main never returns; calling it and exiting on the same line keeps the shell from reading a file
# that git reset replaced mid-run.
main "$@"; exit
