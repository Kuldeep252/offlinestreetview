"""config.py - centralised configuration for Offline Street View."""
from __future__ import annotations

import os
import pathlib

__version__ = "0.1.0"

APP_NAME = "Offline Street View"
PACKAGE_NAME = "offlinestreetview"


# --------------------------------------------------------------------------- #
#  user data (tiles, exports) - never write inside site-packages
# --------------------------------------------------------------------------- #
def _user_data_dir() -> pathlib.Path:
    env = os.environ.get("OFFLINESTREETVIEW_HOME")
    if env:
        return pathlib.Path(env).expanduser()
    if os.name == "nt":
        base = pathlib.Path(os.environ.get("LOCALAPPDATA") or pathlib.Path.home())
    else:
        base = pathlib.Path(os.environ.get("XDG_DATA_HOME")
                            or (pathlib.Path.home() / ".local" / "share"))
    return base / PACKAGE_NAME


USER_DATA_DIR = _user_data_dir()
DEFAULT_TILE_DIR = USER_DATA_DIR / "osm_tiles"
DEFAULT_EXPORT_DIR = USER_DATA_DIR / "exports"

# --- data source defaults (overridable on the configuration screen) ---
DEFAULT_CSV_PATH = os.environ.get("OFFLINESTREETVIEW_CSV_PATH", "")
DEFAULT_CSV_NAME = os.environ.get("OFFLINESTREETVIEW_CSV_NAME", "")

DEFAULT_LAT_COL = "lat"
DEFAULT_LON_COL = "lon"
DEFAULT_TIME_COL = "adj_time"

# columns used to build the front/back image file paths
DEFAULT_IMAGE_COLS = {
    "front_path": "path_fr",
    "front_file": "file_fr",
    "back_path": "path_bk",
    "back_file": "file_bk",
}

# legacy drive mappings used in the original project data
LEGACY_PATH_REPLACEMENTS = {
    "/media/kuldeep/Elements1/Washington_proh_sep23/GoPro_video/":
        "K:/washington_project_app/",
}

# numeric columns offered for the bar plot (only these are loaded)
DEFAULT_BAR_COLS = ["cpc_cor", "sp_cor", "bcc_kd_60sec"]

# --- image frame defaults (position & size, set before loading) ---
DEFAULT_IMG_WIDTH_PCT = 100   # image width inside its frame (%)
DEFAULT_IMG_HEIGHT_VH = 45    # image height (view-height units)
DEFAULT_X_OFFSET_PX = 0       # move images right (+) / left (-)
DEFAULT_Y_OFFSET_PX = 0       # move images down (+) / up (-)
DEFAULT_PANEL_PCT = 40        # width of the right images panel (% of screen)

# --- bar plot defaults (width slider removed; width is always 100%) ---
DEFAULT_BAR_HEIGHT_VH = 25    # bar plot height (vh)

# --- offline OpenStreetMap tiles ---
OSM_TILE_SERVER = "https://tile.openstreetmap.org"
DEFAULT_TILE_ZOOM = 18
OSM_TILE_BASE_URL = "/osm_tiles"   # relative -> served by this same app

# --- map defaults ---
DEFAULT_MAP_ZOOM = 18
DEFAULT_MAP_OPACITY = 1.0   # 0.0 = transparent tiles, 1.0 = fully opaque