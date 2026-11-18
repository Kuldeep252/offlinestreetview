# Offline Street View

Modular Dash dashboard for street-level surveys: two synced images, an
OpenStreetMap map (online **or** fully offline tiles), a bar chart of any
numeric CSV column, image-shift controls and a shifted-CSV export.

## Install
    pip install offlinestreetview

## Run
    python -m offlinestreetview          ## http://127.0.0.1:8050
    python offlinestreetview --port 8070 --debug
        

Options: `--host`, `--port`, `--debug`, `--tile-dir`.

## Offline map tiles
Enable "Use offline tiles" on the setup screen, or pre-download:

    offlinestreetview-tiles --lat-min 38.89 --lat-max 38.95 \
        --lon-min -77.06 --lon-max -77.00 --zoom 18

Tiles are stored in:
* `%LOCALAPPDATA%\offlinestreetview\osm_tiles` (Windows)
* `~/.local/share/offlinestreetview/osm_tiles` (Linux/macOS)

Override with the `OFFLINESTREETVIEW_HOME` environment variable, or `--tile-dir`.

## Expected CSV columns
`adj_time`, `lat`, `lon`, `path_fr`, `file_fr`, `path_bk`, `file_bk`
+ the numeric columns can be edited on the setup screen.
