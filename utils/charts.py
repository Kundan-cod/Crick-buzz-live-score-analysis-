"""Plotly visualization helpers styled for the Midnight Cricket + Electric Lime theme.

Ensures consistent typography, transparent/dark background integration,
accessible contrast, and clean tooltips across analytical charts.
Guarantees that chart titles, axes, and traces never emit undefined labels.
"""

from typing import List, Optional
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from utils.theme import (
    COLOR_ACCENT_GREEN,
    COLOR_ACCENT_LIME,
    COLOR_BG_MIDNIGHT,
    COLOR_BORDER,
    COLOR_CARD_SURFACE,
    COLOR_PANEL_DARK,
    COLOR_TEXT_PRIMARY,
    COLOR_TEXT_SECONDARY,
    COLOR_WARNING,
)

# Cohesive Palette for Multi-Series Data
THEME_PALETTE = [
    COLOR_ACCENT_LIME,   # Primary highlight
    COLOR_ACCENT_GREEN,  # Secondary metric
    "#38BDF8",           # Sky blue
    COLOR_WARNING,       # Amber
    "#F43F5E",           # Coral / Wickets
    "#A855F7",           # Violet
]


def apply_chart_theme(
    fig: go.Figure,
    height: int = 380,
    title: Optional[str] = None,
    show_legend: bool = True,
    x_label: Optional[str] = None,
    y_label: Optional[str] = None,
) -> go.Figure:
    """Apply unified Midnight Cricket styling to any Plotly figure.

    Args:
        fig: Plotly figure to style.
        height: Height in pixels.
        title: Optional title override. If None or empty, title text is set to empty string.
        show_legend: Toggle legend visibility.
        x_label: Optional custom x-axis label.
        y_label: Optional custom y-axis label.

    Returns:
        The styled Plotly figure.
    """
    clean_title = str(title).strip() if (title is not None and str(title).strip() != "") else ""
    title_config = (
        dict(
            text=f"<b>{clean_title}</b>",
            font=dict(size=15, color=COLOR_TEXT_PRIMARY),
            x=0.02,
            y=0.96,
        )
        if clean_title
        else dict(text="")
    )

    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(17, 28, 46, 0.6)",
        font=dict(family="Inter, sans-serif", color=COLOR_TEXT_SECONDARY, size=12),
        title=title_config,
        height=height,
        margin=dict(l=40, r=30, t=50 if clean_title else 20, b=40),
        showlegend=show_legend,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            font=dict(size=11, color=COLOR_TEXT_SECONDARY),
        ),
        hoverlabel=dict(
            bgcolor=COLOR_PANEL_DARK,
            font_size=12,
            font_family="Inter, sans-serif",
            bordercolor=COLOR_BORDER,
        ),
    )

    # Style X & Y Axes and guard against undefined labels
    x_axis_kwargs = dict(
        showgrid=True,
        gridcolor=COLOR_BORDER,
        gridwidth=0.5,
        zeroline=False,
        linecolor=COLOR_BORDER,
        tickfont=dict(color=COLOR_TEXT_SECONDARY, size=11),
        title_font=dict(color=COLOR_TEXT_SECONDARY, size=12),
    )
    if x_label is not None:
        x_axis_kwargs["title_text"] = str(x_label)
    fig.update_xaxes(**x_axis_kwargs)

    y_axis_kwargs = dict(
        showgrid=True,
        gridcolor=COLOR_BORDER,
        gridwidth=0.5,
        zeroline=False,
        linecolor=COLOR_BORDER,
        tickfont=dict(color=COLOR_TEXT_SECONDARY, size=11),
        title_font=dict(color=COLOR_TEXT_SECONDARY, size=12),
    )
    if y_label is not None:
        y_axis_kwargs["title_text"] = str(y_label)
    fig.update_yaxes(**y_axis_kwargs)

    # Sanitize traces to ensure no undefined or None trace names
    for trace in fig.data:
        if hasattr(trace, "name"):
            if trace.name is None or str(trace.name).lower() in ("none", "undefined"):
                trace.name = ""

    return fig


def create_bar_chart(
    df: pd.DataFrame,
    x_col: str,
    y_col: str,
    title: Optional[str] = None,
    color_col: Optional[str] = None,
    text_auto: bool = True,
    height: int = 380,
    x_label: Optional[str] = None,
    y_label: Optional[str] = None,
) -> go.Figure:
    """Create a vertical bar chart with theme styling."""
    fig = px.bar(
        df,
        x=x_col,
        y=y_col,
        color=color_col,
        color_discrete_sequence=THEME_PALETTE,
        text_auto=".1f" if text_auto else None,
    )
    if not color_col:
        fig.update_traces(marker_color=COLOR_ACCENT_LIME, marker_line_color=COLOR_BORDER, marker_line_width=1)
    return apply_chart_theme(fig, height=height, title=title, x_label=x_label, y_label=y_label)


def create_horizontal_bar_chart(
    df: pd.DataFrame,
    x_col: str,
    y_col: str,
    title: Optional[str] = None,
    color_col: Optional[str] = None,
    height: int = 380,
    x_label: Optional[str] = None,
    y_label: Optional[str] = None,
) -> go.Figure:
    """Create a horizontal bar chart with theme styling."""
    fig = px.bar(
        df,
        x=x_col,
        y=y_col,
        orientation="h",
        color=color_col,
        color_discrete_sequence=THEME_PALETTE,
        text_auto=True,
    )
    if not color_col:
        fig.update_traces(marker_color=COLOR_ACCENT_LIME, marker_line_color=COLOR_BORDER, marker_line_width=1)
    fig.update_layout(yaxis=dict(autorange="reversed"))
    return apply_chart_theme(fig, height=height, title=title, x_label=x_label, y_label=y_label)


def create_line_chart(
    df: pd.DataFrame,
    x_col: str,
    y_col: str,
    title: Optional[str] = None,
    color_col: Optional[str] = None,
    markers: bool = True,
    height: int = 380,
    x_label: Optional[str] = None,
    y_label: Optional[str] = None,
) -> go.Figure:
    """Create an interactive line chart with markers."""
    fig = px.line(
        df,
        x=x_col,
        y=y_col,
        color=color_col,
        markers=markers,
        color_discrete_sequence=THEME_PALETTE,
    )
    if not color_col:
        fig.update_traces(line_color=COLOR_ACCENT_LIME, line_width=2.5, marker=dict(size=6, color=COLOR_ACCENT_GREEN))
    return apply_chart_theme(fig, height=height, title=title, x_label=x_label, y_label=y_label)


def create_donut_chart(
    df: pd.DataFrame,
    names_col: str,
    values_col: str,
    title: Optional[str] = None,
    height: int = 360,
) -> go.Figure:
    """Create an elegant donut chart for categorical distributions."""
    fig = px.pie(
        df,
        names=names_col,
        values=values_col,
        hole=0.55,
        color_discrete_sequence=THEME_PALETTE,
    )
    fig.update_traces(
        textposition="inside",
        textinfo="percent+label",
        marker=dict(line=dict(color=COLOR_PANEL_DARK, width=2)),
    )
    return apply_chart_theme(fig, height=height, title=title, show_legend=True)


def create_scatter_plot(
    df: pd.DataFrame,
    x_col: str,
    y_col: str,
    hover_name: Optional[str] = None,
    title: Optional[str] = None,
    color_col: Optional[str] = None,
    size_col: Optional[str] = None,
    height: int = 380,
    x_label: Optional[str] = None,
    y_label: Optional[str] = None,
) -> go.Figure:
    """Create a scatter plot for correlation analysis (e.g., Strike Rate vs Avg)."""
    fig = px.scatter(
        df,
        x=x_col,
        y=y_col,
        hover_name=hover_name,
        color=color_col,
        size=size_col,
        color_discrete_sequence=THEME_PALETTE,
    )
    fig.update_traces(
        marker=dict(
            size=10 if not size_col else None,
            line=dict(width=1, color=COLOR_PANEL_DARK),
            opacity=0.85,
        )
    )
    return apply_chart_theme(fig, height=height, title=title, x_label=x_label, y_label=y_label)


def create_grouped_bar_chart(
    df: pd.DataFrame,
    x_col: str,
    y_cols: List[str],
    labels: List[str],
    title: Optional[str] = None,
    height: int = 380,
    x_label: Optional[str] = None,
    y_label: Optional[str] = None,
) -> go.Figure:
    """Create a grouped bar chart comparing multiple metric columns."""
    fig = go.Figure()
    for idx, (y_col, label) in enumerate(zip(y_cols, labels)):
        color = THEME_PALETTE[idx % len(THEME_PALETTE)]
        fig.add_trace(
            go.Bar(
                name=str(label),
                x=df[x_col],
                y=df[y_col],
                marker_color=color,
                marker_line=dict(width=1, color=COLOR_BORDER),
            )
        )
    fig.update_layout(barmode="group")
    return apply_chart_theme(fig, height=height, title=title, x_label=x_label, y_label=y_label)
