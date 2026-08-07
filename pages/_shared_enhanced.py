"""
Shared components and utilities for World Cup Analytics Dashboard.
Professional UI components, custom CSS, and reusable visualizations.
"""
try:
    import streamlit as st
except ImportError:
    # Fallback dummy streamlit for environments where Streamlit is unavailable (e.g., audit scripts)
    class DummySt:
        def __init__(self):
            # Provide a dummy column_config submodule with NumberColumn
            class DummyColumnConfig:
                            def __getattr__(self, name):
                                # Return a dummy placeholder for any column config attribute
                                def dummy(*args, **kwargs):
                                    return None
                                return dummy
            self.column_config = DummyColumnConfig()
        def __enter__(self):
            return self
        def __exit__(self, exc_type, exc, tb):
            return False
        def __getattr__(self, name):
            # Return a dummy function for any Streamlit API
            def dummy(*args, **kwargs):
                # Specific handling for UI input widgets to return sensible defaults
                if name in ('selectbox', 'radio'):
                    # args: label, options, ...
                    if len(args) >= 2:
                        opts = args[1]
                        return opts[0] if opts else None
                    return None
                if name == 'multiselect':
                    # Return empty list or first option list
                    return []
                if name == 'checkbox':
                    return False
                if name == 'slider' or name == 'number_input':
                    # Return the default value if provided, else 0
                    if 'value' in kwargs:
                        return kwargs['value']
                    return 0
                if name == 'text_input' or name == 'textarea':
                    return ''
                if name == 'columns':
                    # Accept either an integer count or an iterable of column ratios
                    arg = args[0] if args else 1
                    if isinstance(arg, (list, tuple)):
                        count = len(arg)
                    else:
                        try:
                            count = int(arg)
                        except Exception:
                            count = 1
                    return [DummySt() for _ in range(count)]
                if name == 'expander' or name == 'container':
                    return DummySt()
                if name == 'spinner':
                    # Return a dummy context manager for spinner
                    class DummySpinner:
                        def __enter__(self):
                            return self
                        def __exit__(self, exc_type, exc, tb):
                            return False
                        def success(self, *a, **kw):
                            return None
                        def empty(self):
                            return None
                    return DummySpinner()
                if name == 'empty' or name == 'progress' or name == 'write' or name == 'markdown' or name == 'subheader' or name == 'metric' or name == 'divider' or name == 'caption' or name == 'error' or name == 'warning' or name == 'info' or name == 'success' or name == 'dataframe':
                    # No-op functions
                    return None
                # For other calls, return a DummySt to allow chaining or context use
                return DummySt()
            return dummy
    st = DummySt()
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from typing import List, Dict, Any, Optional, Tuple
import numpy as np

# Explicit public API — guarantees `from pages._shared_enhanced import *`
# exposes page_hero and the other helpers on every Python/Streamlit version.
__all__ = [
    'load_custom_css', 'page_header', 'page_hero', 'apply_dark_text_theme',
    'kpi_cards', 'info_card', 'probability_badge', 'team_tier_badge',
    'create_radar_chart',
]

# ============================================================================
# CUSTOM CSS - Professional Dark Theme
# ============================================================================

def load_custom_css():
    """Inject custom CSS for official FWC26 light theme with background."""
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Bebas+Neue&display=swap');
    
    /* Global Styles & Background */
    .stApp, [data-testid="stAppViewContainer"], [data-testid="stHeader"] {
        background-color: #ffffff;
        background-image: linear-gradient(rgba(255, 255, 255, 0.93), rgba(255, 255, 255, 0.93)), url('https://images.unsplash.com/photo-1518605368461-1e125228114e?q=80&w=2000&auto=format&fit=crop') !important;
        background-size: cover !important;
        background-position: center !important;
        background-attachment: fixed !important;
    }
    
    /* Fix sidebar collapse/expand icon — use a proper hamburger menu */
    [data-testid="collapsedControl"] {
        /* Streamlit renders an SVG arrow inside; replace visuals with CSS */
    }
    [data-testid="collapsedControl"] svg {
        display: none !important;
    }
    /* Inject a hamburger icon via ::before */
    [data-testid="collapsedControl"]::before {
        content: "";
        display: inline-block;
        width: 22px;
        height: 3px;
        background: #000000;
        box-shadow: 0 6px 0 #000000, 0 12px 0 #000000;
        margin: 8px 4px;
        border-radius: 2px;
    }
    
    
    /* Force Bebas Neue on main text but preserve Material Icons for Streamlit UI */
    h1, h2, h3, h4, h5, h6, p, span, div, li, td, th, label, button {
        font-family: 'Bebas Neue', sans-serif;
        letter-spacing: 0.05em;
    }
    
    /* Explicitly protect material icons so arrows don't break */
    .material-icons, [class^="st-"] {
        font-family: inherit !important;
        letter-spacing: normal !important;
    }
    
    h1, h2, h3, h4, h5, h6 {
        color: #000000 !important;
        text-transform: uppercase;
    }
    
    h1 { font-size: 3.5rem !important; margin-bottom: 0.5rem !important; }
    h2 { font-size: 2.5rem !important; }
    h3 { font-size: 2rem !important; }
    
    p, span, div, li, td, th {
        color: #000000;
        font-size: 1.1rem;
    }
    
    /* Metric Cards */
    [data-testid="stMetric"] {
        background: rgba(255, 255, 255, 0.9);
        border-radius: 0px;
        padding: 1.5rem;
        border: 4px solid #000000;
        box-shadow: 6px 6px 0px #FF004D;
        transition: all 0.2s ease;
    }
    
    [data-testid="stMetric"]:hover {
        transform: translate(-2px, -2px);
        box-shadow: 8px 8px 0px #7B00FF;
    }
    
    [data-testid="stMetricValue"] {
        color: #000000 !important;
        font-size: 3.5rem !important;
        font-weight: 400 !important;
    }
    
    [data-testid="stMetricLabel"] {
        color: #000000 !important;
        font-size: 1.2rem !important;
        text-transform: uppercase !important;
    }
    
    [data-testid="stMetricDelta"] {
        color: #00B347 !important;
        font-size: 1.2rem !important;
    }
    
    /* Sidebar */
    [data-testid="stSidebar"] {
        background-color: #f3f4f6;
        border-right: 4px solid #000000;
    }
    
    /* Buttons */
    .stButton > button {
        background-color: #ffffff;
        color: #000000 !important;
        border: 2px solid #000000;
        border-radius: 0px;
        padding: 0.5rem 1.5rem;
        font-size: 1.2rem !important;
        text-transform: uppercase;
        transition: all 0.2s ease;
    }
    
    .stButton > button:hover {
        background-color: #FF004D;
        color: #ffffff !important;
        transform: translateY(-2px);
        box-shadow: 4px 4px 0px #000000;
    }
    
    /* Dataframes */
    [data-testid="stDataFrame"] {
        border-radius: 0px;
        overflow: hidden;
        border: 2px solid #000000;
        background: rgba(255, 255, 255, 0.9) !important;
    }
    
    /* Select boxes */
    [data-testid="stSelectbox"] > div {
        background: #ffffff;
        border: 2px solid #000000;
        border-radius: 0px;
        color: #000000;
    }
    
    /* Info Cards */
    .info-card {
        background: rgba(255, 255, 255, 0.95);
        border-radius: 0px;
        padding: 1.5rem;
        margin: 1rem 0;
        border: 3px solid #000000;
        border-left: 8px solid #00F0FF;
        box-shadow: 4px 4px 0px #000000;
    }
    
    .info-card h4 {
        color: #000000 !important;
        margin-top: 0 !important;
        font-size: 1.8rem !important;
    }
    
    .info-card p {
        color: #000000 !important;
        font-size: 1.2rem !important;
        line-height: 1.4 !important;
    }
    
    /* Probability badges */
    .prob-badge {
        display: inline-block;
        padding: 0.25rem 0.75rem;
        border-radius: 0px;
        font-size: 1rem;
        margin: 0.25rem;
        text-transform: uppercase;
        border: 2px solid #000000;
    }
    
    .prob-high { background: #FF004D; color: white; }
    .prob-medium { background: #7B00FF; color: white; }
    .prob-low { background: #00FF00; color: black; }
    
    /* Team tier badges */
    .tier-favorite { background: #000000; color: white; }
    .tier-contender { background: #7B00FF; color: white; }
    .tier-dark-horse { background: #00F0FF; color: black; }
    .tier-underdog { background: #ffffff; color: black; border: 2px solid #000000; }

    /* ===== POLISH / ANIMATION LAYER (FWC26, CSS-only, no logic) ===== */
    @keyframes wc-fade-up { from { opacity: 0; transform: translateY(18px); } to { opacity: 1; transform: translateY(0); } }
    @keyframes wc-shimmer { 0% { background-position: -200% 0; } 100% { background-position: 200% 0; } }
    @keyframes wc-ball-spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
    @keyframes wc-grad-flow { 0% { background-position: 0% 50%; } 50% { background-position: 100% 50%; } 100% { background-position: 0% 50%; } }
    @keyframes wc-pulse { 0%, 100% { transform: scale(1); } 50% { transform: scale(1.06); } }

    .stApp .block-container > div { animation: wc-fade-up 0.5s ease both; }

    [data-testid="stMetric"] {
        animation: wc-fade-up 0.6s ease both;
        transition: transform 0.2s ease, box-shadow 0.2s ease;
        position: relative;
        overflow: hidden;
    }
    [data-testid="stMetric"]:hover {
        transform: translate(-3px, -3px);
        box-shadow: 10px 10px 0px #7B00FF, 0 0 24px rgba(0, 240, 255, 0.35) !important;
    }
    [data-testid="stMetric"]::after {
        content: "";
        position: absolute; top: 0; left: 0;
        width: 100%; height: 100%;
        background: linear-gradient(120deg, transparent 30%, rgba(255,255,255,0.55) 50%, transparent 70%);
        background-size: 200% 100%;
        opacity: 0;
        pointer-events: none;
    }
    [data-testid="stMetric"]:hover::after { opacity: 1; animation: wc-shimmer 0.9s ease; }

    h1 {
        background: linear-gradient(90deg, #000000, #FF004D, #7B00FF, #00F0FF, #000000);
        background-size: 300% 100%;
        -webkit-background-clip: text; background-clip: text;
        -webkit-text-fill-color: transparent; color: transparent;
        animation: wc-grad-flow 8s ease infinite;
    }
    h2 {
        background: linear-gradient(90deg, #000000, #7B00FF, #00F0FF, #000000);
        background-size: 300% 100%;
        -webkit-background-clip: text; background-clip: text;
        -webkit-text-fill-color: transparent; color: transparent;
        animation: wc-grad-flow 10s ease infinite;
    }

    .wc-hero {
        position: relative;
        background: linear-gradient(120deg, #000000 0%, #7B00FF 35%, #FF004D 65%, #00F0FF 100%);
        background-size: 200% 100%;
        animation: wc-grad-flow 10s ease infinite;
        border-radius: 0px;
        padding: 2.4rem 2rem;
        margin-bottom: 1.5rem;
        box-shadow: 10px 10px 0px #000000;
        color: #ffffff;
        overflow: hidden;
    }
    .wc-hero h1 { margin: 0; font-size: 3.6rem !important; color: #ffffff !important; -webkit-text-fill-color: #ffffff; text-shadow: 3px 3px 0px #000000; letter-spacing: 0.06em; }
    .wc-hero p { color: #ffffff !important; font-size: 1.35rem; margin: 0.4rem 0 0; letter-spacing: 0.04em; opacity: 0.95; }
    .wc-hero .ball { position: absolute; font-size: 2.6rem; opacity: 0.5; animation: wc-ball-spin 6s linear infinite; pointer-events: none; }
    .wc-hero .trophy { position: absolute; font-size: 4rem; right: 2rem; top: 50%; transform: translateY(-50%); animation: wc-pulse 3s ease-in-out infinite; }

    .wc-chips { display: flex; flex-wrap: wrap; gap: 0.6rem; margin: 0.8rem 0 0; }
    .wc-chip {
        background: rgba(255,255,255,0.18);
        border: 1px solid rgba(255,255,255,0.5);
        border-radius: 999px;
        padding: 0.3rem 0.9rem;
        color: #fff; font-size: 0.95rem; letter-spacing: 0.05em;
        backdrop-filter: blur(3px);
        display: inline-flex; align-items: center; gap: 0.3rem;
    }
    .wc-chip .mini-ball { display: inline-block; animation: wc-ball-spin 4s linear infinite; }

    [data-testid="stDataFrame"] { border-top: 6px solid #FF004D; }
    .stButton > button { transition: transform 0.15s ease, box-shadow 0.15s ease; }
    .stButton > button:hover { transform: translateY(-2px) scale(1.01); box-shadow: 5px 5px 0px #000000; }
    .info-card { animation: wc-fade-up 0.5s ease both; }
    h3 { position: relative; padding-left: 0.9rem; }
    h3::before { content: ""; position: absolute; left: 0; top: 12%; height: 78%; width: 6px; background: linear-gradient(#FF004D, #00F0FF); border-radius: 3px; }
    </style>
    """, unsafe_allow_html=True)

# ============================================================================
# PAGE COMPONENTS
# ============================================================================

def page_header(title: str, description: str, icon: str = "⚽", image_url: str = None):
    """Create a professional page header with icon/image and description."""
    import os
    import base64
    
    col1, col2 = st.columns([1, 10])
    with col1:
        if image_url:
            # If it's a local file path
            if os.path.exists(image_url):
                with open(image_url, "rb") as image_file:
                    encoded_string = base64.b64encode(image_file.read()).decode()
                # Detect MIME type from extension
                ext = os.path.splitext(image_url)[1].lower()
                mime = "image/svg+xml" if ext == ".svg" else "image/png"
                st.markdown(f"<img src='data:{mime};base64,{encoded_string}' style='width: 80px; height: auto; max-width: 100%; border-radius: 12px; margin-top: 5px;'>", unsafe_allow_html=True)
            else:
                st.markdown(f"<img src='{image_url}' style='width: 80px; height: auto; max-width: 100%; border-radius: 12px; margin-top: 5px;'>", unsafe_allow_html=True)
        else:
            st.markdown(f"<div style='font-size: 3.5rem; text-align: center;'>{icon}</div>", unsafe_allow_html=True)
    with col2:
        st.title(title)
        st.markdown(f"<p style='color: #000000; font-size: 1.1rem; margin-top: -1rem;'>{description}</p>", unsafe_allow_html=True)
    st.divider()


def page_hero(
    title: str,
    description: str,
    chips: Optional[List[str]] = None,
    trophy: str = "🏆",
):
    """Animated WC-style hero banner: flowing brand gradient, trophy, and chips.

    Purely presentational — no logic. Calls st.markdown with the .wc-hero classes
    defined in load_custom_css(). Use in place of page_header() for a bolder look.
    """
    chips = chips or []
    chip_html = ""
    if chips:
        chips_html = "".join(
            f'<span class="wc-chip"><span class="mini-ball">⚽</span>{c}</span>'
            for c in chips
        )
        chip_html = f'<div class="wc-chips">{chips_html}</div>'
    st.markdown(
        f'<div class="wc-hero">'
        f'<span class="ball" style="left:8%; top:15%;">⚽</span>'
        f'<span class="ball" style="left:22%; bottom:10%; font-size:1.8rem;">🏁</span>'
        f'<span class="ball" style="left:60%; top:20%; font-size:2rem;">⚽</span>'
        f'<span class="trophy" style="right:3rem;">{trophy}</span>'
        f'<h1>{title}</h1>'
        f'<p>{description}</p>'
        f'{chip_html}'
        f'</div>',
        unsafe_allow_html=True,
    )

def apply_dark_text_theme(fig):
    """Force chart text to a dark color on a white background.

    This function makes Plotly figures readable in both Streamlit light and dark themes
    by overriding background colors and font colors. It safely applies settings only to
    primary axes (xaxis, yaxis) to avoid ``Invalid property`` errors.
    """
    DARK = '#2B1E16'
    WHITE = '#ffffff'
    # Base layout overrides
    fig.update_layout(
        paper_bgcolor=WHITE,
        plot_bgcolor=WHITE,
        font=dict(color=DARK, family='Noto Sans'),
        legend=dict(font=dict(color=DARK, family='Noto Sans')),
        title=dict(font=dict(color=DARK, family='Bebas Neue')),
    )
    # Update only primary axes (xaxis, yaxis)
    for axis_name in ['xaxis', 'yaxis']:
        if axis_name in fig.layout:
            fig.update_layout(**{
                f'{axis_name}_tickfont': dict(color=DARK, family='Noto Sans'),
                f'{axis_name}_title_font': dict(color=DARK, family='Noto Sans'),
                f'{axis_name}_gridcolor': '#e0e0e0',
            })
    # Color axis (for heatmaps) if present
    if 'coloraxis' in fig.layout:
        fig.update_layout(coloraxis_colorbar=dict(tickfont=dict(color=DARK)))
    return fig


def kpi_cards(items: List[Tuple[str, Any, Optional[str]]], cols: Optional[int] = None):
    """
    Create professional KPI cards with icons and deltas.
    
    Args:
        items: List of (label, value, delta) tuples
        cols: Number of columns (default: len(items))
    """
    if cols is None:
        cols = len(items)
    
    columns = st.columns(cols)
    for i, (col, (label, value, delta)) in enumerate(zip(columns, items)):
        with col:
            st.metric(
                label=label.upper(),
                value=value,
                delta=delta,
                delta_color="normal"
            )

def info_card(title: str, content: str, icon: str = "ℹ️"):
    """Create an info card with title and content.
    Converts markdown **bold** to <strong> for HTML rendering."""
    import re
    # Convert markdown **bold** to HTML <strong>
    html_content = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', content)
    st.markdown(f"""
    <div class="info-card">
        <h4>{icon} {title}</h4>
        <p>{html_content}</p>
    </div>
    """, unsafe_allow_html=True)

def probability_badge(prob: float, format_type: str = "percent") -> str:
    """
    Create a colored probability badge.
    
    Args:
        prob: Probability value (0-100 for percent, 0-1 for decimal)
        format_type: 'percent' or 'decimal'
    """
    if format_type == "percent":
        pct = prob
    else:
        pct = prob * 100
    
    if pct >= 50:
        css_class = "prob-high"
    elif pct >= 20:
        css_class = "prob-medium"
    else:
        css_class = "prob-low"
    
    return f'<span class="prob-badge {css_class}">{pct:.1f}%</span>'

def team_tier_badge(tier: str) -> str:
    """Create a team tier badge."""
    tier_map = {
        "Top 5": "tier-favorite",
        "Top 10": "tier-contender",
        "Dark Horse": "tier-dark-horse",
        "Underdog": "tier-underdog"
    }
    css_class = tier_map.get(tier, "tier-underdog")
    return f'<span class="prob-badge {css_class}">{tier}</span>'

# ============================================================================
# VISUALIZATION COMPONENTS
# ============================================================================

def create_radar_chart(
    data: pd.DataFrame,
    categories: List[str],
    values: List[float],
    title: str = "Player Radar",
    max_values: Optional[List[float]] = None
) -> go.Figure:
    """
    Create a professional radar chart.
    
    Args:
        data: DataFrame with player stats
        categories: List of stat categories
        values: List of values for each category
        title: Chart title
        max_values: Optional max values for each category
    """
    fig = go.Figure()
    
    # Add player data
    fig.add_trace(go.Scatterpolar(
        r=values,
        theta=categories,
        fill='toself',
        name='Player',
        line=dict(color='#60a5fa', width=3),
        fillcolor='rgba(96, 165, 250, 0.3)'
    ))
    
    # Add max values if provided
    if max_values:
        fig.add_trace(go.Scatterpolar(
            r=max_values,
            theta=categories,
            fill='toself',
            name='Max',
            line=dict(color='#374151', width=2, dash='dash'),
            fillcolor='rgba(55, 65, 81, 0.1)',
            showlegend=False
        ))
    
    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, max(max_values) if max_values else max(values)],
                gridcolor='#374151',
                linecolor='#6b7280'
            ),
            angularaxis=dict(
                gridcolor='#374151',
                linecolor='#6b7280',
                tickfont=dict(size=12, color='#9ca3af')
            ),
            bgcolor='rgba(0,0,0,0)'
        ),
        showlegend=True,
        title=dict(
            text=title,
            font=dict(size=18, color='#ffffff'),
            y=0.95
        ),
        height=500,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        margin=dict(l=20, r=20, t=60, b=20)
    )
    
    return fig

def create_funnel_chart(
    stages: List[str],
    values: List[float],
    title: str = "Tournament Funnel"
) -> go.Figure:
    """Create a funnel chart for stage probabilities."""
    fig = go.Figure(go.Funnel(
        y=stages,
        x=values,
        textposition="inside",
        textinfo="value+percent initial",
        opacity=0.85,
        marker=dict(
            color=["#7c3aed", "#60a5fa", "#3b82f6", "#10b981", "#f59e0b", "#dc2626"],
            line=dict(width=[3, 3, 3, 3, 3, 3], color=["white"]*len(stages))
        ),
        connector=dict(line=dict(color="#374151", dash="dash", width=2))
    ))
    
    fig.update_layout(
        title=dict(
            text=title,
            font=dict(size=18, color='#ffffff'),
            y=0.95
        ),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#ffffff', size=12),
        height=400,
        margin=dict(l=20, r=20, t=60, b=20)
    )
    
    return fig

def create_heatmap(
    data: pd.DataFrame,
    x_col: str,
    y_col: str,
    z_col: str,
    title: str = "Heatmap",
    colorscale: str = "Blues"
) -> go.Figure:
    """Create a professional heatmap."""
    fig = go.Figure(data=go.Heatmap(
        z=data[z_col],
        x=data[x_col],
        y=data[y_col],
        colorscale=colorscale,
        hovertemplate='%{y} vs %{x}<extra></extra><br>Value: %{z:.2f}'
    ))
    
    fig.update_layout(
        title=dict(
            text=title,
            font=dict(size=18, color='#ffffff'),
            y=0.95
        ),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        xaxis=dict(gridcolor='#374151', linecolor='#6b7280'),
        yaxis=dict(gridcolor='#374151', linecolor='#6b7280'),
        height=500,
        margin=dict(l=60, r=20, t=60, b=60)
    )
    
    return fig

def create_scatter_with_trend(
    data: pd.DataFrame,
    x_col: str,
    y_col: str,
    hover_name: str,
    color_col: Optional[str] = None,
    title: str = "Scatter Plot",
    trendline: str = "ols"
) -> go.Figure:
    """Create a scatter plot with trendline."""
    fig = px.scatter(
        data,
        x=x_col,
        y=y_col,
        hover_name=hover_name,
        color=color_col,
        trendline=trendline,
        title=title,
        color_discrete_sequence=px.colors.sequential.Blues
    )
    
    fig.update_layout(
        title=dict(
            text=title,
            font=dict(size=18, color='#ffffff'),
            y=0.95
        ),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        xaxis=dict(gridcolor='#374151', linecolor='#6b7280'),
        yaxis=dict(gridcolor='#374151', linecolor='#6b7280'),
        legend=dict(
            bgcolor='rgba(0,0,0,0)',
            font=dict(color='#ffffff')
        ),
        height=500,
        margin=dict(l=60, r=20, t=60, b=60)
    )
    
    return fig

def create_treemap(
    data: pd.DataFrame,
    path: List[str],
    values: str,
    title: str = "Treemap",
    color: Optional[str] = None
) -> go.Figure:
    """Create a treemap visualization."""
    fig = px.treemap(
        data,
        path=path,
        values=values,
        color=color,
        title=title,
        color_continuous_scale="Blues",
        hover_data=['values'] if values else None
    )
    
    fig.update_layout(
        title=dict(
            text=title,
            font=dict(size=18, color='#ffffff'),
            y=0.95
        ),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        margin=dict(l=10, r=10, t=60, b=10),
        height=600
    )
    
    return fig

def create_sunburst(
    data: pd.DataFrame,
    path: List[str],
    values: str,
    title: str = "Sunburst"
) -> go.Figure:
    """Create a sunburst chart."""
    fig = px.sunburst(
        data,
        path=path,
        values=values,
        title=title,
        color_continuous_scale="Blues",
        hover_data=['values'] if values else None
    )
    
    fig.update_layout(
        title=dict(
            text=title,
            font=dict(size=18, color='#ffffff'),
            y=0.95
        ),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        margin=dict(l=10, r=10, t=60, b=10),
        height=600
    )
    
    return fig

# ============================================================================
# FILTER COMPONENTS
# ============================================================================

def create_team_filter(teams_df: pd.DataFrame, key_prefix: str = "filter") -> Dict[str, Any]:
    """
    Create a comprehensive team filter sidebar.
    
    Returns dict with selected filters.
    """
    st.sidebar.subheader("🔍 Filters")
    
    # Confederation filter
    confederations = ["All"] + sorted(teams_df['confederation'].dropna().unique().tolist())
    selected_confed = st.sidebar.selectbox(
        "Confederation",
        confederations,
        key=f"{key_prefix}_confed"
    )
    
    # Group filter
    groups = ["All"] + sorted(teams_df['group_name'].dropna().unique().tolist())
    selected_group = st.sidebar.selectbox(
        "Group",
        groups,
        key=f"{key_prefix}_group"
    )
    
    # Contender tier filter
    tiers = ["All"] + sorted(teams_df['contender_tier'].dropna().unique().tolist())
    selected_tier = st.sidebar.selectbox(
        "Contender Tier",
        tiers,
        key=f"{key_prefix}_tier"
    )
    
    # Build filter query
    filters = {}
    if selected_confed != "All":
        filters['confederation'] = selected_confed
    if selected_group != "All":
        filters['group_name'] = selected_group
    if selected_tier != "All":
        filters['contender_tier'] = selected_tier
    
    return filters

def apply_filters(df: pd.DataFrame, filters: Dict[str, Any]) -> pd.DataFrame:
    """Apply filters to a DataFrame."""
    filtered = df.copy()
    for col, value in filters.items():
        if col in filtered.columns:
            filtered = filtered[filtered[col] == value]
    return filtered

# ============================================================================
# LOADING STATES
# ============================================================================

def show_loading(message: str = "Loading data..."):
    """Show a professional loading spinner."""
    with st.spinner(message):
        pass

def show_error(message: str, retry_function=None):
    """Show an error message with optional retry button."""
    st.error(f"❌ {message}")
    if retry_function:
        if st.button("🔄 Retry"):
            retry_function()
            st.rerun()

def show_success(message: str):
    """Show a success message."""
    st.success(f"✅ {message}")
