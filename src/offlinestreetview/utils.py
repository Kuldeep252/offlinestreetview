"""utils.py - all reusable functionality of the Washington Viewer.

Every file/data operation lives here so main (app.py) and the callbacks stay
small and focused.
"""
from __future__ import annotations

import base64
import os
from datetime import datetime

import pandas as pd

from .config import DEFAULT_EXPORT_DIR, DEFAULT_IMAGE_COLS, LEGACY_PATH_REPLACEMENTS as LEGACY_DRIVE_REPLACEMENTS

# legacy drive mappings used in the original project
LEGACY_DRIVE_REPLACEMENTS = {
    "/media/kuldeep/Elements1/Washington_proh_sep23/GoPro_video/": "K:/washington_project_app/",
}


# --------------------------------------------------------------------------- #
#  DATA LOADING  (feature 3: load ONLY the requested numeric columns)
# --------------------------------------------------------------------------- #
def build_image_paths(df: pd.DataFrame, image_cols: dict | None = None) -> pd.DataFrame:
    """Add image_path1/image_path2 columns combining path + file for both cameras."""
    image_cols = image_cols or DEFAULT_IMAGE_COLS
    out = df.copy()
    out["image_path1"] = out[image_cols["front_path"]].astype(str) + out[image_cols["front_file"]].astype(str)
    out["image_path2"] = out[image_cols["back_path"]].astype(str) + out[image_cols["back_file"]].astype(str)
    for col in ("image_path1", "image_path2"):
        for old, new in LEGACY_DRIVE_REPLACEMENTS.items():
            out[col] = out[col].str.replace(old, new, regex=False)
    return out


def load_dashboard_data(
    csv_path: str,
    csv_name: str,
    bar_columns: list[str],
    lat_col: str = "lat",
    lon_col: str = "lon",
    time_col: str = "adj_time",
    image_cols: dict | None = None,
):
    """Read a lean dataframe containing ONLY the columns that are needed.

    - geo/time columns,
    - the four image path/file columns,
    - the numeric columns the user asked for on the config screen.

    Returns: (dataframe, loaded_bar_columns, missing_bar_columns)
    """
    image_cols = image_cols or DEFAULT_IMAGE_COLS
    full_path = os.path.join(csv_path, csv_name)

    # check which requested numeric columns actually exist
    columns_in_file = list(pd.read_csv(full_path, nrows=1).columns)
    loaded = [c for c in bar_columns if c in columns_in_file]
    missing = [c for c in bar_columns if c not in columns_in_file]

    # columns that are always required
    required = [time_col, lat_col, lon_col] + list(image_cols.values())
    keep = list(dict.fromkeys(required + loaded))  # preserve order, drop dups

    # load ONLY those columns -> fast & memory-lean
    df = pd.read_csv(full_path, usecols=lambda c: c in keep)

    # normalise geo/time column names for the rest of the app
    df = df.rename(columns={time_col: "adj_time", lat_col: "lat", lon_col: "lon"})
    df = build_image_paths(df, image_cols)

    order = ["adj_time", "lat", "lon",
             image_cols["front_path"], image_cols["front_file"],
             image_cols["back_path"], image_cols["back_file"],
             "image_path1", "image_path2"] + loaded
    df = df[[c for c in order if c in df.columns]]
    return df, loaded, missing


# --------------------------------------------------------------------------- #
#  IMAGE HELPERS
# --------------------------------------------------------------------------- #
def encode_image(path: str) -> str:
    """Return a base64 data URI for an image file ("" if it cannot be read)."""
    try:
        with open(path, "rb") as fh:
            data = base64.b64encode(fh.read()).decode("ascii")
        return "data:image/png;base64," + data
    except Exception:
        return ""


def clamp_index(idx: int, total_rows: int) -> int:
    """Clamp an index into the valid 0..total_rows-1 range."""
    return max(0, min(total_rows - 1, idx))


def shifted_image_path(df: pd.DataFrame, row: int, shift: int, which: str) -> str:
    """Image path for row+shift (clamped), used when image shifts are applied."""
    idx = clamp_index(row + shift, len(df))
    return df.iloc[idx][which]


# --------------------------------------------------------------------------- #
#  EXPORT (shifted file assignments -> csv + summary)
# --------------------------------------------------------------------------- #
def export_shifted_csv(
    df: pd.DataFrame,
    shift1: int = 0,
    shift2: int = 0,
    file_fr_col: str = "file_fr",
    file_bk_col: str = "file_bk",
    out_root: str | None = None,
):
    """Write a new CSV that only shifts file_fr/file_bk, leaving paths intact."""
    out_root = out_root or str(DEFAULT_EXPORT_DIR)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    export_path = os.path.join(out_root, f"exported_shifted_data_{timestamp}")
    os.makedirs(export_path, exist_ok=True)

    df_export = df.copy()
    original_fr = df_export[file_fr_col].astype(str).copy()
    original_bk = df_export[file_bk_col].astype(str).copy()
    total = len(df_export)

    if shift1:
        for idx in range(total):
            df_export.at[idx, file_fr_col] = original_fr.iloc[clamp_index(idx + shift1, total)]
    if shift2:
        for idx in range(total):
            df_export.at[idx, file_bk_col] = original_bk.iloc[clamp_index(idx + shift2, total)]

    csv_path = os.path.join(export_path, f"shifted_data_{timestamp}.csv")
    df_export.to_csv(csv_path, index=False)

    summary_path = os.path.join(export_path, "shift_summary.txt")
    with open(summary_path, "w") as f:
        f.write("File Shift Summary\n")
        f.write(f"Export Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Total rows processed: {total}\n")
        f.write(f"file_fr Shift: {shift1} positions\n")
        f.write(f"file_bk Shift: {shift2} positions\n")
        f.write("Only file_fr and file_bk were shifted; path_fr/path_bk are unchanged.\n")

    fr_changes = int(sum(df_export[file_fr_col].astype(str) != original_fr)) if shift1 else 0
    bk_changes = int(sum(df_export[file_bk_col].astype(str) != original_bk)) if shift2 else 0
    return csv_path, fr_changes, bk_changes