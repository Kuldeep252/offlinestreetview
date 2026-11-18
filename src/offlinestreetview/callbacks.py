"""callbacks.py - all Dash callbacks (wiring layout, utils, plots and tiles)."""
from __future__ import annotations

import os
import traceback
import io
import dash
import pandas as pd
from dash.dependencies import Input, Output, State
from dash.exceptions import PreventUpdate

from .config import (DEFAULT_BAR_COLS, DEFAULT_BAR_HEIGHT_VH, DEFAULT_CSV_NAME,
                     DEFAULT_CSV_PATH, DEFAULT_EXPORT_DIR, DEFAULT_IMG_HEIGHT_VH,
                     DEFAULT_IMG_WIDTH_PCT, DEFAULT_MAP_OPACITY, DEFAULT_PANEL_PCT,
                     DEFAULT_TILE_DIR, DEFAULT_TILE_ZOOM, DEFAULT_X_OFFSET_PX,
                     DEFAULT_Y_OFFSET_PX)
from .plots import bar_figure, map_figure
from .tiles import download_tiles_for_bbox
from .utils import (encode_image, export_shifted_csv, load_dashboard_data,
                    shifted_image_path)


# =========================================================================== #
#  CONFIG SCREEN <-> DASHBOARD  (ONE callback, two triggers - no duplicate outputs)
# =========================================================================== #
def register_config_callback(app):

    @app.callback(
        [Output("data-store", "data"),
         Output("config-store", "data"),
         Output("config-screen", "style"),
         Output("dashboard-screen", "style"),
         Output("bar-dropdown", "options"),
         Output("bar-dropdown", "value"),
         Output("image-slider", "max"),
         Output("cfg-csv-path", "value"),
         Output("cfg-csv-name", "value"),
         Output("cfg-bar-cols", "value"),
         Output("cfg-panel-pct", "value"),
         Output("cfg-img-width-pct", "value"),
         Output("cfg-img-height-vh", "value"),
         Output("cfg-img-x-offset", "value"),
         Output("cfg-img-y-offset", "value"),
         Output("cfg-offline", "value"),
         Output("cfg-tile-zoom", "value"),
         Output("cfg-bar-height-vh", "value"),
         Output("cfg-error", "children")],
        [Input("cfg-load-btn", "n_clicks"),
         Input("back-to-config-btn", "n_clicks")],
        [State("cfg-csv-path", "value"),
         State("cfg-csv-name", "value"),
         State("cfg-bar-cols", "value"),
         State("cfg-panel-pct", "value"),
         State("cfg-img-width-pct", "value"),
         State("cfg-img-height-vh", "value"),
         State("cfg-img-x-offset", "value"),
         State("cfg-img-y-offset", "value"),
         State("cfg-offline", "value"),
         State("cfg-tile-zoom", "value"),
         State("cfg-bar-height-vh", "value"),
         State("config-store", "data")],
        prevent_initial_call=True,
    )
    def handle_config(load_clicks, back_clicks,
                      csv_path, csv_name, bar_cols,
                      panel_pct, img_w, img_h, x_off, y_off,
                      offline, tile_zoom, bar_h, cfg):
        ctx = dash.callback_context
        if not ctx.triggered:
            raise PreventUpdate
        button = ctx.triggered[0]["prop_id"].split(".")[0]

        NO = dash.no_update
        NOTHING = (NO,) * 11          # outputs 8..18 (form values)
        cfg = cfg or {}

        # ------------------------------------------------------------------ #
        #  A) "Change Settings" -> back to config, pre-filled
        # ------------------------------------------------------------------ #
        if button == "back-to-config-btn" and back_clicks:
            return (
                NO, NO,
                {"display": "block"}, {"display": "none"},
                NO, NO, NO,
                cfg.get("csv_path", DEFAULT_CSV_PATH),
                cfg.get("csv_name", DEFAULT_CSV_NAME),
                ", ".join(cfg.get("loaded_bar_columns", DEFAULT_BAR_COLS)),
                cfg.get("panel_pct", DEFAULT_PANEL_PCT),
                cfg.get("img_width_pct", DEFAULT_IMG_WIDTH_PCT),
                cfg.get("img_height_vh", DEFAULT_IMG_HEIGHT_VH),
                cfg.get("x_offset", DEFAULT_X_OFFSET_PX),
                cfg.get("y_offset", DEFAULT_Y_OFFSET_PX),
                ["on"] if cfg.get("use_offline", False) else [],
                cfg.get("tile_zoom", DEFAULT_TILE_ZOOM),
                cfg.get("bar_height_vh", DEFAULT_BAR_HEIGHT_VH),
                "",
            )

        # ------------------------------------------------------------------ #
        #  B) "Load dashboard" -> read CSV, build dashboard
        # ------------------------------------------------------------------ #
        if button == "cfg-load-btn" and load_clicks:
            bar_columns = [c.strip() for c in str(bar_cols or "").split(",") if c.strip()]
            if not bar_columns:
                return (NO,) * 18 + ("⚠️ Please enter at least one numeric column.",)

            try:
                df, loaded, missing = load_dashboard_data(csv_path, csv_name, bar_columns)
            except Exception as exc:
                traceback.print_exc()
                return (NO,) * 18 + (f"❌ Load failed: {exc}",)

            if df.empty:
                return (NO,) * 18 + ("❌ The CSV produced an empty table.",)

            new_config = {
                "panel_pct": int(panel_pct or 40),
                "img_width_pct": int(img_w or 100),
                "img_height_vh": int(img_h or 45),
                "x_offset": int(x_off or 0),
                "y_offset": int(y_off or 0),
                "bar_height_vh": int(bar_h or DEFAULT_BAR_HEIGHT_VH),
                "use_offline": bool(offline),
                "tile_zoom": int(tile_zoom or 18),
                "loaded_bar_columns": loaded,
                "csv_path": csv_path,
                "csv_name": csv_name,
            }

            error = ""
            if new_config["use_offline"]:
                try:
                    download_tiles_for_bbox(
                        float(df["lat"].min()), float(df["lat"].max()),
                        float(df["lon"].min()), float(df["lon"].max()),
                        new_config["tile_zoom"],
                    )
                except Exception as exc:
                    traceback.print_exc()
                    error = (f"⚠️ Offline tiles could not be downloaded ({exc}). "
                             f"Press 'Download OSM Tiles' on the dashboard.")

            n_rows = len(df)
            options = [{"label": c, "value": c} for c in loaded]
            value = loaded[0] if loaded else None

            if missing:
                miss_msg = f"⚠️ Columns not found and ignored: {', '.join(missing)}"
                error = f"{error} {miss_msg}" if error else miss_msg

            return (
                df.to_json(date_format="iso", orient="split"),
                new_config,
                {"display": "none"}, {"display": "block"},
                options, value,
                n_rows - 1,
            ) + NOTHING + (error,)

        raise PreventUpdate


# =========================================================================== #
#  IMAGE SHIFTS
# =========================================================================== #
def register_shift_callbacks(app):

    @app.callback(
        [Output("shift-store", "data"),
         Output("shift-status", "children")],
        [Input("apply-shift1-btn", "n_clicks"),
         Input("apply-shift2-btn", "n_clicks"),
         Input("reset-shifts-btn", "n_clicks")],
        [State("image1-shift-input", "value"),
         State("image2-shift-input", "value"),
         State("shift-store", "data")],
    )
    def update_shifts(s1, s2, reset, v1, v2, store):
        shifts = dict(store or {"image1_shift": 0, "image2_shift": 0})
        ctx = dash.callback_context
        if not ctx.triggered:
            return shifts, (f"Current shifts - Image 1: {shifts['image1_shift']}, "
                            f"Image 2: {shifts['image2_shift']}")

        button = ctx.triggered[0]["prop_id"].split(".")[0]
        if button == "apply-shift1-btn" and s1:
            shifts["image1_shift"] = int(v1 or 0)
        elif button == "apply-shift2-btn" and s2:
            shifts["image2_shift"] = int(v2 or 0)
        elif button == "reset-shifts-btn" and reset:
            shifts = {"image1_shift": 0, "image2_shift": 0}

        status = (f"Image 1 shift: {shifts['image1_shift']} | "
                  f"Image 2 shift: {shifts['image2_shift']}")
        if button == "apply-shift1-btn" and s1:
            status = (f"Image 1 shift applied: {shifts['image1_shift']} | "
                      f"Image 2: {shifts['image2_shift']}")
        elif button == "apply-shift2-btn" and s2:
            status = (f"Image 1: {shifts['image1_shift']} | "
                      f"Image 2 shift applied: {shifts['image2_shift']}")
        elif button == "reset-shifts-btn" and reset:
            status = "All shifts reset to 0"
        return shifts, status


# =========================================================================== #
#  EXPORT
# =========================================================================== #
def register_export_callback(app):

    @app.callback(
        Output("export-status", "children"),
        Input("export-btn", "n_clicks"),
        [State("data-store", "data"),
         State("shift-store", "data")],
        prevent_initial_call=True,
    )
    def export_changes(n_clicks, data_json, shifts):
        if not n_clicks:
            return ""
        try:
            df = pd.read_json(io.StringIO(data_json), orient="split")
            sh = shifts or {}
            csv_path, fr, bk = export_shifted_csv(
                df,
                shift1=int(sh.get("image1_shift", 0)),
                shift2=int(sh.get("image2_shift", 0)),
                out_root=str(DEFAULT_EXPORT_DIR),
            )
            return (f"✅ Export successful! CSV saved to: {csv_path} | "
                    f"Changes: {fr} file_fr, {bk} file_bk")
        except Exception as exc:
            traceback.print_exc()
            return f"❌ Export failed: {str(exc)}"


# =========================================================================== #
#  MAIN DASHBOARD (images + map + bar chart + map opacity)
# =========================================================================== #
def register_dashboard_callback(app):

    @app.callback(
        [Output("image1", "src"),
         Output("image2", "src"),
         Output("plots-column", "style"),
         Output("images-column", "style"),
         Output("image1", "style"),
         Output("image2", "style"),
         Output("map", "figure"),
         Output("bar-plot", "figure"),
         Output("bar-subheading", "children"),
         Output("bar-plot", "style")],
        [Input("image-slider", "value"),
         Input("bar-dropdown", "value"),
         Input("apply-shift1-btn", "n_clicks"),
         Input("apply-shift2-btn", "n_clicks"),
         Input("reset-shifts-btn", "n_clicks"),
         Input("map-opacity-slider", "value"),
         Input("show-all-points", "value")],
        [State("data-store", "data"),
         State("config-store", "data"),
         State("shift-store", "data")],
    )
    def update_dashboard(row, column, s1, s2, reset, map_opacity,
                         show_all, data_json, config, shifts):
        if not data_json:
            raise PreventUpdate

        try:
            df = pd.read_json(io.StringIO(data_json), orient="split")
            cfg = config or {}
            sh = shifts or {"image1_shift": 0, "image2_shift": 0}
            shift1, shift2 = int(sh.get("image1_shift", 0)), int(sh.get("image2_shift", 0))
            row = int(row)

            # ---- image shifts ----------------------------------------------
            image1_src = encode_image(shifted_image_path(df, row, shift1, "image_path1"))
            image2_src = encode_image(shifted_image_path(df, row, shift2, "image_path2"))

            # ---- frame position & size (set on the config screen) ----------
            panel_pct = int(cfg.get("panel_pct", 40))
            plots_style = {"width": f"{max(15, 100 - panel_pct)}%", "float": "left"}
            images_style = {"width": f"{panel_pct}%", "display": "flex",
                            "flexDirection": "column", "alignItems": "center"}
            img_style = {
                "width": f"{int(cfg.get('img_width_pct', 100))}%",
                "height": f"{int(cfg.get('img_height_vh', 45))}vh",
                "objectFit": "contain",
                "marginLeft": f"{int(cfg.get('x_offset', 0))}px",
                "marginTop": f"{int(cfg.get('y_offset', 0))}px",
            }

            # ---- bar plot: width fixed at 100%, only height is adjustable ---
            bar_style = {
                "width": "100%",
                "height": f"{int(cfg.get('bar_height_vh', DEFAULT_BAR_HEIGHT_VH))}vh",
            }

            # ---- map (dot + optional bubbles) + bar chart -------------------
            use_offline = bool(cfg.get("use_offline", False))
            zoom = int(cfg.get("tile_zoom", 18))
            opacity = DEFAULT_MAP_OPACITY if map_opacity is None else float(map_opacity)

            # CHANGE 2: the bubble dropdown is gone -> colour by the selected column
            map_fig = map_figure(
                df, row,
                use_offline=use_offline, zoom=zoom, map_opacity=opacity,
                show_all_points=bool(show_all), bubble_column=column,
            )
            bar_fig = bar_figure(df, row, column)

            ts = df.iloc[row]["adj_time"]
            shift_info = (f" | Shifts Applied - Img1: {shift1}, Img2: {shift2}"
                          if (shift1 or shift2) else "")
            subheading = f"Row: {row} | Timestamp: {ts}{shift_info}"

            return (image1_src, image2_src, plots_style, images_style,
                    img_style, img_style, map_fig, bar_fig, subheading, bar_style)

        except Exception as exc:
            traceback.print_exc()
            return ((dash.no_update,) * 8
                    + (f"❌ ERROR: {exc}",   # bar-subheading -> children, str is fine
                       dash.no_update))      # bar-plot style -> must remain a dict


# =========================================================================== #
#  OFFLINE TILE DOWNLOAD
# =========================================================================== #
def register_tile_download_callback(app):

    @app.callback(
        Output("tile-status", "children"),
        Input("download-tiles-btn", "n_clicks"),
        [State("data-store", "data"),
         State("config-store", "data")],
        prevent_initial_call=True,
    )
    def download_tiles(n_clicks, data_json, config):
        if not n_clicks or not data_json:
            return ""
        try:
            df = pd.read_json(io.StringIO(data_json), orient="split")
            zoom = int((config or {}).get("tile_zoom", 18))
            dl, cached = download_tiles_for_bbox(
                float(df["lat"].min()), float(df["lat"].max()),
                float(df["lon"].min()), float(df["lon"].max()),
                zoom,
            )
            return (f"🗺️ Offline tiles ready: {dl} downloaded, {cached} cached "
                    f"(zoom {zoom}). Stored in: {DEFAULT_TILE_DIR}")
        except Exception as exc:
            traceback.print_exc()
            return f"❌ Tile download failed: {str(exc)}"


# --------------------------------------------------------------------------- #
#  register everything
# --------------------------------------------------------------------------- #
def register_callbacks(app):
    register_config_callback(app)
    register_shift_callbacks(app)
    register_export_callback(app)
    register_dashboard_callback(app)
    register_tile_download_callback(app)