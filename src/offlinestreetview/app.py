"""app.py - MAIN entry point of the Offline Street View dashboard.

Builds the layout, registers the callbacks and starts the server.
All heavy lifting is imported from utils.py / tiles.py / plots.py / callbacks.py.
"""
from __future__ import annotations

import argparse
import pathlib

import dash
from dash import dcc, html

from .callbacks import register_callbacks
from .config import (APP_NAME, DEFAULT_BAR_COLS, DEFAULT_BAR_HEIGHT_VH,
                     DEFAULT_CSV_NAME, DEFAULT_CSV_PATH, DEFAULT_IMG_HEIGHT_VH,
                     DEFAULT_IMG_WIDTH_PCT, DEFAULT_MAP_OPACITY,
                     DEFAULT_PANEL_PCT, DEFAULT_TILE_DIR, DEFAULT_TILE_ZOOM,
                     DEFAULT_X_OFFSET_PX, DEFAULT_Y_OFFSET_PX)
from .tiles import register_tile_server


# --------------------------------------------------------------------------- #
#  LAYOUT
# --------------------------------------------------------------------------- #
def _config_screen():
    """First screen: ask for data source, numeric columns and image size."""
    return html.Div(id="config-screen", children=[
        html.Div(style={"maxWidth": "900px", "margin": "0 auto",
                        "padding": "20px", "border": "1px solid #ddd",
                        "borderRadius": "8px", "backgroundColor": "#fafafa"},
                 children=[
            html.H2(f"{APP_NAME} - Setup", style={"textAlign": "center"}),

            html.H3("1) Data source"),
            html.Label("CSV folder:"),
            dcc.Input(id="cfg-csv-path", type="text", value=DEFAULT_CSV_PATH,
                      placeholder="e.g. /data/my_survey/",
                      style={"width": "100%", "marginBottom": "10px"}),
            html.Label("CSV filename:"),
            dcc.Input(id="cfg-csv-name", type="text", value=DEFAULT_CSV_NAME,
                      placeholder="e.g. 20211203.csv",
                      style={"width": "40%", "marginBottom": "10px"}),

            html.H3("2) Numeric columns for the bar plot (load ONLY these)"),
            html.Label("Comma-separated column names:"),
            dcc.Input(id="cfg-bar-cols", type="text",
                      value=", ".join(DEFAULT_BAR_COLS),
                      style={"width": "100%", "marginBottom": "10px"}),
            html.Div(id="cfg-error", style={"color": "red", "fontWeight": "bold"}),

            html.H3("3) Image frame - position & size (applied before loading)"),
            html.Label("Images panel width (% of screen):"),
            dcc.Slider(id="cfg-panel-pct", min=15, max=70, step=5, value=DEFAULT_PANEL_PCT,
                       marks={15: "15%", 40: "40%", 70: "70%"}),
            html.Label(f"Image width inside its frame (%): default {DEFAULT_IMG_WIDTH_PCT}%"),
            dcc.Slider(id="cfg-img-width-pct", min=10, max=100, step=5,
                       value=DEFAULT_IMG_WIDTH_PCT,
                       marks={10: "10%", 50: "50%", 100: "100%"}),
            html.Label(f"Image height (vh): default {DEFAULT_IMG_HEIGHT_VH}vh"),
            dcc.Slider(id="cfg-img-height-vh", min=5, max=90, step=5,
                       value=DEFAULT_IMG_HEIGHT_VH,
                       marks={5: "5", 45: "45", 90: "90"}),
            html.Div([
                html.Div([
                    html.Label("X offset (px):", style={"fontWeight": "bold"}),
                    dcc.Input(id="cfg-img-x-offset", type="number", value=DEFAULT_X_OFFSET_PX,
                              style={"width": "90px", "marginLeft": "8px"}),
                ], style={"display": "inline-block", "marginRight": "40px"}),
                html.Div([
                    html.Label("Y offset (px):", style={"fontWeight": "bold"}),
                    dcc.Input(id="cfg-img-y-offset", type="number", value=DEFAULT_Y_OFFSET_PX,
                              style={"width": "90px", "marginLeft": "8px"}),
                ], style={"display": "inline-block"}),
            ], style={"margin": "10px 0"}),

            # ---- CHANGE 4: bar plot WIDTH slider removed, only HEIGHT kept ----
            html.H3("4) Bar plot height"),
            html.Label(f"Bar plot height (vh): default {DEFAULT_BAR_HEIGHT_VH}vh"),
            dcc.Slider(id="cfg-bar-height-vh", min=10, max=60, step=5,
                       value=DEFAULT_BAR_HEIGHT_VH,
                       marks={10: "10", 25: "25", 60: "60"}),

            html.H3("5) Offline OpenStreetMap tiles (optional)"),
            dcc.Checklist(
                id="cfg-offline",
                options=[{"label": " Use offline tiles (works without internet)",
                          "value": "on"}],
                value=[],
                style={"marginBottom": "10px"},
            ),
            html.Label("Tile zoom level (higher = more detail, more tiles):"),
            dcc.Slider(id="cfg-tile-zoom", min=10, max=19, step=1, value=DEFAULT_TILE_ZOOM,
                       marks={10: "10", 14: "14", 18: "18", 19: "19"}),

            html.Button("Load dashboard", id="cfg-load-btn", n_clicks=0,
                        style={"marginTop": "20px", "padding": "10px 30px",
                               "fontSize": "16px", "backgroundColor": "#007BFF",
                               "color": "white", "border": "none",
                               "borderRadius": "4px"}),
        ]),
    ])


def _dashboard_screen():
    """Second screen: the viewer (row selector, map, bar chart, images, shifts)."""
    return html.Div(id="dashboard-screen", style={"display": "none"}, children=[

        # -------- header with "Change Settings" button ---------------------
        html.Div(
            html.Button(
                "⚙️ Change Settings",
                id="back-to-config-btn",
                n_clicks=0,
                style={"backgroundColor": "#6C757D", "color": "white",
                       "border": "none", "padding": "6px 16px",
                       "borderRadius": "4px"},
            ),
            style={"textAlign": "right", "padding": "5px 20px"},
        ),

        # ================= CHANGE 5: row / timestamp selector on TOP =======
        html.Div([
            dcc.Slider(
                id="image-slider",
                min=0, max=0, step=1, value=0,
                marks={},                       # <-- no tick labels any more
                tooltip={"placement": "bottom"},
            ),
            html.Div(
                id="bar-subheading",
                style={"textAlign": "center", "fontWeight": "bold",
                       "fontSize": "16px", "margin": "10px 0 4px 0"},
            ),
        ], style={"width": "95%", "margin": "5px auto 10px auto"}),

        # -------- middle: map + bar plot (left), images (right) -----------
        html.Div(style={"width": "100%", "display": "flex"}, children=[
            html.Div(id="plots-column", style={"width": "60%", "float": "left"},
                     children=[

                # ============ CHANGE 3: map transparency ABOVE the map ====
                html.Div([
                    html.Label("Map transparency (0 = transparent, 1 = opaque):",
                               style={"fontWeight": "bold", "display": "block",
                                      "marginBottom": "0"}),
                    dcc.Slider(
                        id="map-opacity-slider",
                        min=0, max=1, step=0.05,
                        value=DEFAULT_MAP_OPACITY,
                        marks={0: "Transparent", 0.5: "Semi", 1: "Opaque"},
                    ),
                ], style={"width": "100%", "textAlign": "center",
                          "margin": "0 0 8px 0"}),

                dcc.Graph(id="map", style={"width": "100%", "height": "50vh"}),

                # ============ CHANGE 2: "Bubble color column" dropdown removed
                html.Div([
                    dcc.Checklist(
                        id="show-all-points",
                        options=[{"label": " Show all data points (bubble / heatmap)",
                                  "value": "on"}],
                        value=[],
                        style={"display": "inline-block"},
                    ),
                ], style={"textAlign": "center", "margin": "5px", "width": "100%"}),

                dcc.Dropdown(id="bar-dropdown", clearable=False,
                             placeholder="Select a numeric column"),
                dcc.Graph(id="bar-plot", style={"width": "100%", "height": "25vh"}),
            ]),
            html.Div(id="images-column", style={"width": "40%"}, children=[
                html.Img(id="image1"),
                html.Img(id="image2"),
            ]),
        ]),

        # -------- shift controls -----------------------------------------
        html.Div([
            html.H4("Image Shift Controls", style={"textAlign": "center",
                                                   "marginTop": "20px"}),
            html.Div([
                html.Div([
                    html.Label("Image 1 Shift:", style={"fontWeight": "bold"}),
                    dcc.Input(id="image1-shift-input", type="number", value=0, step=1,
                              style={"width": "80px", "marginLeft": "10px"}),
                    html.Button("Apply Shift 1", id="apply-shift1-btn", n_clicks=0,
                                style={"marginLeft": "10px", "backgroundColor": "#007BFF",
                                       "color": "white", "border": "none",
                                       "padding": "5px 10px", "borderRadius": "3px"}),
                ], style={"display": "inline-block", "marginRight": "30px"}),
                html.Div([
                    html.Label("Image 2 Shift:", style={"fontWeight": "bold"}),
                    dcc.Input(id="image2-shift-input", type="number", value=0, step=1,
                              style={"width": "80px", "marginLeft": "10px"}),
                    html.Button("Apply Shift 2", id="apply-shift2-btn", n_clicks=0,
                                style={"marginLeft": "10px", "backgroundColor": "#28A745",
                                       "color": "white", "border": "none",
                                       "padding": "5px 10px", "borderRadius": "3px"}),
                ], style={"display": "inline-block", "marginRight": "30px"}),
                html.Div([
                    html.Button("Reset Shifts", id="reset-shifts-btn", n_clicks=0,
                                style={"backgroundColor": "#FFC107", "color": "black",
                                       "border": "none", "padding": "5px 15px",
                                       "borderRadius": "3px"}),
                ], style={"display": "inline-block", "marginRight": "30px"}),
                html.Div([
                    html.Button("Export Changes", id="export-btn", n_clicks=0,
                                style={"backgroundColor": "#DC3545", "color": "white",
                                       "border": "none", "padding": "5px 15px",
                                       "borderRadius": "3px"}),
                ], style={"display": "inline-block"}),
                html.Div([
                    html.Button("Download OSM Tiles (offline)", id="download-tiles-btn",
                                n_clicks=0,
                                style={"backgroundColor": "#6F42C1", "color": "white",
                                       "border": "none", "padding": "5px 15px",
                                       "borderRadius": "3px"}),
                ], style={"display": "inline-block", "marginLeft": "30px"}),
            ], style={"textAlign": "center", "margin": "10px"}),

            html.Div(id="shift-status", style={"textAlign": "center", "margin": "6px",
                                               "fontWeight": "bold"}),
            html.Div(id="export-status", style={"textAlign": "center", "margin": "6px",
                                                "fontWeight": "bold"}),
            html.Div(id="tile-status", style={"textAlign": "center", "margin": "6px",
                                              "fontWeight": "bold", "color": "#6F42C1"}),
        ]),

        # -------- hidden stores -------------------------------------------
        dcc.Store(id="data-store"),
        dcc.Store(id="config-store"),
        dcc.Store(id="shift-store", data={"image1_shift": 0, "image2_shift": 0}),
    ])


def make_layout():
    return html.Div([
        html.H1(APP_NAME, style={"textAlign": "center"}),
        _config_screen(),
        _dashboard_screen(),
    ])


# --------------------------------------------------------------------------- #
#  MAIN
# --------------------------------------------------------------------------- #
def main(argv=None):
    parser = argparse.ArgumentParser(prog="offlinestreetview",
                                     description=f"{APP_NAME} dashboard")
    parser.add_argument("--host", default="127.0.0.1", help="host to bind")
    parser.add_argument("--port", default=8050, type=int, help="port to bind")
    parser.add_argument("--debug", action="store_true", help="run in debug mode")
    parser.add_argument("--tile-dir", default=None,
                        help="folder for offline OSM tiles (default: user data dir)")
    args = parser.parse_args(argv)

    tile_dir = pathlib.Path(args.tile_dir).expanduser() if args.tile_dir else DEFAULT_TILE_DIR

    app = dash.Dash(__name__, title=APP_NAME)

    register_tile_server(app, tile_dir)

    app.layout = make_layout()
    register_callbacks(app)

    print(f" * {APP_NAME}: http://{args.host}:{args.port}")
    print(f" * Offline tiles folder: {tile_dir}")
    run = getattr(app, "run", None) or app.run_server   # dash >= 2.17 renamed it
    run(host=args.host, port=args.port, debug=args.debug, use_reloader=False)


if __name__ == "__main__":
    main()