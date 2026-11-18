"""plots.py - figure factories for the map and the bar chart."""
from __future__ import annotations

from uuid import uuid4

import numpy as np
import pandas as pd
import plotly.graph_objects as go


# English labels for known instruments (fallback = the column name itself)
BAR_LABELS = {
    "cpc_cor": "Particle Number Concentration",
    "sp_cor": "Concentration (µg/m³)",
    "bcc_kd_60sec": "Concentration",
}


def _empty_figure():
    return go.Figure()


def _new_uids(fig: go.Figure) -> go.Figure:
    """Assign a fresh uid to every trace.

    Workaround for the known plotly.js bug where Scattermapbox markers vanish
    after a Plotly.react update if the trace uid stays the same (the hover area
    remains but the marker is not painted).
    """
    for tr in fig.data:
        tr.uid = str(uuid4())
    return fig


# --------------------------------------------------------------------------- #
#  MAP - dot + crosshair (+ optional ALL-DATA bubble/heatmap layer)
# --------------------------------------------------------------------------- #
def map_figure(df: pd.DataFrame, row: int, use_offline: bool = False,
               zoom: int = 18, map_opacity: float = 1.0,
               show_all_points: bool = False, bubble_column: str | None = None):
    """Map centred on the current row.

    - Red DOT at the current row; hovering pops the timestamp
    - Floating red crosshair intersecting at the centroid of the map square
    - Optional bubbble/heatmap layer: every (lat, lon, value) point of the
      loaded CSV, coloured by the selected numeric column
    - No legend
    """
    if df.empty or row < 0 or row >= len(df):
        return _empty_figure()

    lat, lon = float(df.iloc[row]["lat"]), float(df.iloc[row]["lon"])
    timestamp = str(df.iloc[row]["adj_time"])

    centroid_lat = float((df["lat"].min() + df["lat"].max()) / 2.0)
    centroid_lon = float((df["lon"].min() + df["lon"].max()) / 2.0)

    lat_span = float(df["lat"].max() - df["lat"].min()) or 1e-6
    lon_span = float(df["lon"].max() - df["lon"].min()) or 1e-6
    lat_pad = max(lat_span * 0.6, 0.0006)
    lon_pad = max(lon_span * 0.6, 0.0006)

    opacity = max(0.0, min(1.0, float(map_opacity)))

    fig = go.Figure()
    
    # # ---- crosshair: vertical line -----------------------------------------
    # fig.add_trace(go.Scattermapbox(
    #     lat=[centroid_lat - lat_pad, centroid_lat + lat_pad],
    #     lon=[centroid_lon, centroid_lon],
    #     mode="lines", line=dict(color="red", width=3),
    #     opacity=0.85, hoverinfo="skip", showlegend=False, name="",
    # ))

    # # ---- crosshair: horizontal line ---------------------------------------
    # fig.add_trace(go.Scattermapbox(
    #     lat=[centroid_lat, centroid_lat],
    #     lon=[centroid_lon - lon_pad, centroid_lon + lon_pad],
    #     mode="lines", line=dict(color="red", width=3),
    #     opacity=0.85, hoverinfo="skip", showlegend=False, name="",
    # ))

    # ---- OPTIONAL: all-data bubble / heatmap layer -------------------------
    if show_all_points and bubble_column and bubble_column in df.columns:
        vals = pd.to_numeric(df[bubble_column], errors="coerce")
        valid = vals.notna()
        if valid.sum() > 0:
            sub_lat = df.loc[valid, "lat"].astype(float)
            sub_lon = df.loc[valid, "lon"].astype(float)
            v = vals[valid].astype(float)
            vmin, vmax = float(v.min()), float(v.max())

            # bubble size proportional to magnitude (sqrt scaling)
            if vmax > vmin:
                size = 5.0 + 22.0 * np.sqrt((v - vmin) / (vmax - vmin))
            else:
                size = np.full(len(v), 12.0)

            hover_text = [
                f"{t}<br>{bubble_column}: {val:,.2f}"
                for t, val in zip(df.loc[valid, "adj_time"], v)
            ]

            fig.add_trace(go.Scattermapbox(
                lat=sub_lat, lon=sub_lon,
                mode="markers",
                marker=dict(
                    size=size,
                    color=v,
                    colorscale="YlOrRd",
                    showscale=True,
                    opacity=0.65,
                    colorbar=dict(title=bubble_column, thickness=12, len=0.6),
                ),
                text=hover_text,
                hoverinfo="text",
                hovertemplate="%{text}<extra></extra>",
                showlegend=False, name="",
            ))

    # ---- red DOT at current location (drawn LAST so it stays on top) -------
    fig.add_trace(go.Scattermapbox(
        lat=[lat], lon=[lon],
        mode="markers",
        marker=dict(size=14, color="red", opacity=0.95),
        text=[timestamp],
        hoverinfo="text",
        hovertemplate="%{text}<extra></extra>",
        showlegend=False, name="",
    ))

    # ---- map background ----------------------------------------------------
    if use_offline:
        fig.update_layout(mapbox=dict(
            style="white-bg",
            center={"lat": lat, "lon": lon},
            zoom=zoom,
            layers=[dict(sourcetype="raster",
                         source=["/osm_tiles/{z}/{x}/{y}.png"],
                         below="traces", opacity=opacity)],
        ))
    elif opacity >= 0.99:
        fig.update_layout(mapbox=dict(
            style="open-street-map",
            center={"lat": lat, "lon": lon}, zoom=zoom,
        ))
    else:
        fig.update_layout(mapbox=dict(
            style="white-bg",
            center={"lat": lat, "lon": lon}, zoom=zoom,
            layers=[dict(sourcetype="raster",
                         source=["https://tile.openstreetmap.org/{z}/{x}/{y}.png"],
                         below="traces", opacity=opacity)],
        ))

    fig.update_layout(
        showlegend=False,
        margin=dict(l=0, r=0, t=0, b=0),
        uirevision="washington-map",   # keep the user's pan/zoom while sliding
    )
    return _new_uids(fig)


# --------------------------------------------------------------------------- #
#  BAR CHART - one row, dynamic axis range for any numeric column
# --------------------------------------------------------------------------- #
def bar_figure(df: pd.DataFrame, row: int, column: str):
    if df.empty or not column or column not in df.columns:
        return _empty_figure()

    values = pd.to_numeric(df[column], errors="coerce").dropna()
    value = float(values.iloc[row]) if row < len(values) else 0.0
    col_max = float(values.max()) if len(values) else 1.0
    x_range = [0.0, col_max * 1.05 + 1e-6] if col_max > 0 else [0.0, 1.0]

    fig = go.Figure(go.Bar(
        x=[value], y=[column], orientation="h", marker=dict(color="blue"),
    ))
    fig.update_layout(
        xaxis=dict(title=BAR_LABELS.get(column, column), range=x_range),
        showlegend=False, margin=dict(l=0, r=0, t=0, b=0),
    )
    return fig