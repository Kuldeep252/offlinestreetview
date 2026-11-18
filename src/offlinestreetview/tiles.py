"""tiles.py - offline OpenStreetMap tile downloader + local tile server."""
from __future__ import annotations

import argparse
import math
import pathlib
import urllib.request

from .config import DEFAULT_TILE_DIR, DEFAULT_TILE_ZOOM, OSM_TILE_SERVER, __version__

USER_AGENT = f"offlinestreetview/{__version__} (+https://pypi.org/project/offlinestreetview/)"


def deg2num(lat_deg: float, lon_deg: float, zoom: int) -> tuple[int, int]:
    """Convert a lat/lon pair to the OSM (x, y) tile coordinate at a zoom level."""
    lat_rad = math.radians(lat_deg)
    n = 2.0 ** zoom
    xtile = int((lon_deg + 180.0) / 360.0 * n)
    ytile = int((1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0 * n)
    return xtile, ytile


def download_tile(zoom: int, x: int, y: int, tile_dir=None, server=None) -> pathlib.Path:
    """Download a single OSM tile into the local offline folder (skips if cached)."""
    tile_dir = pathlib.Path(tile_dir or DEFAULT_TILE_DIR)
    server = server or OSM_TILE_SERVER
    dest = tile_dir / str(zoom) / str(x) / f"{y}.png"
    if dest.exists():
        return dest

    dest.parent.mkdir(parents=True, exist_ok=True)
    url = f"{server}/{zoom}/{x}/{y}.png"
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=15) as resp, open(dest, "wb") as fh:
        fh.write(resp.read())
    return dest


def download_tiles_for_bbox(lat_min: float, lat_max: float,
                            lon_min: float, lon_max: float,
                            zoom: int, tile_dir=None, server=None) -> tuple[int, int]:
    """Download every tile covering a bounding box. Returns (downloaded, cached)."""
    x0, y0 = deg2num(lat_max, lon_min, zoom)   # top-left tile
    x1, y1 = deg2num(lat_min, lon_max, zoom)   # bottom-right tile
    base = pathlib.Path(tile_dir or DEFAULT_TILE_DIR)
    downloaded, cached = 0, 0
    for x in range(x0, x1 + 1):
        for y in range(y0, y1 + 1):
            if (base / str(zoom) / str(x) / f"{y}.png").exists():
                cached += 1
            else:
                download_tile(zoom, x, y, tile_dir, server)
                downloaded += 1
    return downloaded, cached


def tile_url_template(base_url: str = None, zoom: int = 18) -> str:
    """Plotly raster source template pointing at the LOCAL tile server."""
    base = (base_url or "").rstrip("/")
    return f"{base}/{{z}}/{{x}}/{{y}}.png"


def register_tile_server(app, tile_dir=None):
    """Mount a Flask route on the Dash app: /osm_tiles/<z>/<x>/<y>.png"""
    from flask import abort, send_from_directory

    tile_dir = pathlib.Path(tile_dir or DEFAULT_TILE_DIR)
    tile_dir.mkdir(parents=True, exist_ok=True)

    @app.server.route("/osm_tiles/<int:zoom>/<int:x>/<int:y>.png",
                      endpoint="offlinestreetview_osm_tiles")
    def _serve_osm_tile(zoom: int, x: int, y: int):
        dest = tile_dir / str(zoom) / str(x) / f"{y}.png"
        if not dest.exists():
            try:
                download_tile(zoom, x, y, tile_dir)
            except Exception:
                abort(404)
        return send_from_directory(tile_dir, f"{zoom}/{x}/{y}.png")


def cli():
    parser = argparse.ArgumentParser(prog="offlinestreetview-tiles",
                                     description="Download offline OpenStreetMap tiles")
    parser.add_argument("--lat-min", type=float, required=True)
    parser.add_argument("--lat-max", type=float, required=True)
    parser.add_argument("--lon-min", type=float, required=True)
    parser.add_argument("--lon-max", type=float, required=True)
    parser.add_argument("--zoom", type=int, default=DEFAULT_TILE_ZOOM)
    parser.add_argument("--tile-dir", default=None)
    args = parser.parse_args()

    dl, cached = download_tiles_for_bbox(
        args.lat_min, args.lat_max, args.lon_min, args.lon_max,
        args.zoom, tile_dir=args.tile_dir,
    )
    print(f"done: {dl} downloaded, {cached} already cached (zoom {args.zoom}) "
          f"-> {args.tile_dir or DEFAULT_TILE_DIR}")


if __name__ == "__main__":
    cli()