#!/bin/sh
# Download the newest ECMWF run into data/, render the charts there, encode the tiles as videos
# in maps/ and publish them (release upload, manifest commit, push). Without a new run only missing videos are encoded.
cd "$(dirname "$0")" || exit 1
python3 scripts/update_maps.py data maps "$@" && python3 scripts/publish_maps.py maps
