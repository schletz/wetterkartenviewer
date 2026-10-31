@echo off
rem Download the newest ECMWF run into data\, render the charts there, encode the tiles as videos
rem in maps\ and publish them (release upload, manifest commit, push). Without a new run only missing videos are encoded.
cd /d "%~dp0"
python scripts\update_maps.py data maps %* && python scripts\publish_maps.py maps
