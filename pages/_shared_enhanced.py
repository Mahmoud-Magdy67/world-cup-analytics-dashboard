"""Shared components and utilities for World Cup Analytics Dashboard.
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

# ============================================================================
# CUSTOM CSS - Professional Dark Theme
# ============================================================================

def load_custom_css(page: str = "default"):
    """Inject custom CSS for official FWC26 light theme with background.

    Args:
        page: Page identifier to select appropriate background image.
              Options: 'overview', 'teams', 'players', 'matches', 'predictions', 'methodology', 'default'
    """
    # Page-specific background images (high-quality football/WC images from Unsplash)
    bg_images = {
        "overview": "https://images.unsplash.com/photo-1431324155629-1a6deb1dec8d?q=80&w=2000&auto=format&fit=crop",  # stadium aerial
            "teams": "https://images.unsplash.com/photo-1574629810360-7efbbe195018?q=80&w=2000&auto=format&fit=crop",  # team huddle
            "players": "https://images.unsplash.com/photo-1471295253337-3ceaaedca402?q=80&w=2000&auto=format&fit=crop",  # player action
            "matches": "https://images.unsplash.com/photo-1495567720989-cebdbdd97913?q=80&w=2000&auto=format&fit=crop",  # match night
            "predictions": "https://images.unsplash.com/photo-1574629810360-7efbbe195018?q=80&w=2000&auto=format&fit=crop",  # tactical
            "methodology": "https://images.unsplash.com/photo-1551288049-bebda4e38f71?q=80&w=2000&auto=format&fit=crop",  # data/analytics
            "default": "https://images.unsplash.com/photo-1431324155629-1a6deb1dec8d?q=80&w=2000&auto=format&fit=crop",
    }
    bg_url = bg_images.get(page, bg_images["default"])

    st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Bebas+Neue&display=swap');

    /* Global Styles & Background */
    .stApp, [data-testid="stAppViewContainer"], [data-testid="stHeader"] {{
        background-color: #ffffff;
        background-image: linear-gradient(rgba(255, 255, 255, 0.93), rgba(255, 255, 255, 0.93)), url('{bg_url}') !important;
        background-size: cover !important;
        background-position: center !important;
        background-attachment: fixed !important;
    }}

    /* Fix sidebar collapse/expand icon — use a proper hamburger menu */
    [data-testid="collapsedControl"] {{
        /* Streamlit renders an SVG arrow inside; replace visuals with CSS */
    }}
    [data-testid="collapsedControl"] svg {{
        display: none !important;
    }}
    /* Inject a hamburger icon via ::before */
    [data-testid="collapsedControl"]::before {{
        content: "";
        display: inline-block;
        width: 22px;
        height: 3px;
        background: #000000;
        box-shadow: 0 6px 0 #000000, 0 12px 0 #000000;
        margin: 8px 4px;
        border-radius: 2px;
    }}


    /* Force Bebas Neue on main text but preserve Material Icons for Streamlit UI */
    h1, h2, h3, h4, h5, h6, p, span, div, li, td, th, label, button {{
        font-family: 'Bebas Neue', sans-serif;
        letter-spacing: 0.05em;
    }}

    /* Explicitly protect material icons so arrows don't break */
    .material-icons, [class^="st-"] {{
        font-family: inherit !important;
        letter-spacing: normal !important;
    }}

    h1, h2, h3, h4, h5, h6 {{
        color: #000000 !important;
        text-transform: uppercase;
    }}

    h1 {{ font-size: 3.5rem !important; margin-bottom: 0.5rem !important; }}
    h2 {{ font-size: 2.5rem !important; }}
    h3 {{ font-size: 2rem !important; }}

    p, span, div, li, td, th {{
        color: #000000;
        font-size: 1.1rem;
    }}

    /* Metric Cards */
    [data-testid="stMetric"] {{
        background: rgba(255, 255, 255, 0.9);
        border-radius: 0px;
        padding: 1.5rem;
        border: 4px solid #000000;
        box-shadow: 6px 6px 0px #FF004D;
        transition: all 0.2s ease;
    }}

    [data-testid="stMetric"]:hover {{
        transform: translate(-2px, -2px);
        box-shadow: 8px 8px 0px #7B00FF;
    }}

    [data-testid="stMetricValue"] {{
        color: #000000 !important;
        font-size: 3.5rem !important;
        font-weight: 400 !important;
    }}

    [data-testid="stMetricLabel"] {{
        color: #000000 !important;
        font-size: 1.2rem !important;
        text-transform: uppercase !important;
    }}

    [data-testid="stMetricDelta"] {{
        color: #00B347 !important;
        font-size: 1.2rem !important;
    }}

    /* Sidebar */
    [data-testid="stSidebar"] {{
        background-color: #f3f4f6;
        border-right: 4px solid #000000;
    }}

    /* Buttons */
    .stButton > button {{
        background-color: #ffffff;
        color: #000000 !important;
        border: 2px solid #000000;
        border-radius: 0px;
        padding: 0.5rem 1.5rem;
        font-size: 1.2rem !important;
        text-transform: uppercase;
        transition: all 0.2s ease;
    }}

    .stButton > button:hover {{
        background-color: #FF004D;
        color: #ffffff !important;
        transform: translateY(-2px);
        box-shadow: 4px 4px 0px #000000;
    }}

    /* Dataframes */
    [data-testid="stDataFrame"] {{
        border-radius: 0px;
        overflow: hidden;
        border: 2px solid #000000;
        background: rgba(255, 255, 255, 0.9) !important;
    }}

    /* Select boxes */
    [data-testid="stSelectbox"] > div {{
        background: #ffffff;
        border: 2px solid #000000;
        border-radius: 0px;
        color: #000000;
    }}

    /* Info Cards */
    .info-card {{
        background: rgba(255, 255, 255, 0.95);
        border-radius: 0px;
        padding: 1.5rem;
        margin: 1rem 0;
        border: 3px solid #000000;
        border-left: 8px solid #00F0FF;
        box-shadow: 4px 4px 0px #000000;
    }}

    .info-card h4 {{
        color: #000000 !important;
        margin-top: 0 !important;
        font-size: 1.8rem !important;
    }}

    .info-card p {{
        color: #000000 !important;
        font-size: 1.2rem !important;
        line-height: 1.4 !important;
    }}

    /* Probability badges */
    .prob-badge {{
        display: inline-block;
        padding: 0.25rem 0.75rem;
        border-radius: 0px;
        font-size: 1rem;
        margin: 0.25rem;
        text-transform: uppercase;
        border: 2px solid #000000;
    }}

    .prob-high {{ background: #FF004D; color: white; }}
    .prob-medium {{ background: #7B00FF; color: white; }}
    .prob-low {{ background: #00FF00; color: black; }}

    /* Team tier badges */
    .tier-favorite {{ background: #000000; color: white; }}
    .tier-contender {{ background: #7B00FF; color: white; }}
    .tier-dark-horse {{ background: #00F0FF; color: black; }}
    .tier-underdog {{ background: #ffffff; color: black; border: 2px solid #000000; }}
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
            fig.update_layout(**{{
                f'{axis_name}_tickfont': dict(color=DARK, family='Noto Sans'),
                f'{axis_name}_title_font': dict(color=DARK, family='Noto Sans'),
                f'{axis_name}_gridcolor': '#e0e0e0',
            }})
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
    tier_map = {{
        "Top 5": "tier-favorite",
        "Top 10": "tier-contender",
        "Dark Horse": "tier-dark-horse",
        "Underdog": "tier-underdog"
    }}
    css_class = tier_map.get(tier, "tier-underdog")
    return f'<span class="prob-badge {css_class}">{tier}</span>'

# ============================================================================
# VISUALIZATION COMPONENTS
# ============================================================================

def create_radar_chart(
    data: pd.DataFrame,
    categories: List[str],
    values: List[float],
    title: str = "Radar Chart",
    color: str = "#FF004D",
    max_val: Optional[float] = None
):
    """Create a radar chart for player/team stats."""
    if max_val is None:
        max_val = max(values) * 1.2

    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(
        r=values,
        theta=categories,
        fill='toself',
        line=dict(color=color, width=3),
        fillcolor=color.replace('#', '#') + '40',
        name=title
    ))
    fig.update_layout(
        polar=dict(
            radialaxis=dict(visible=True, range=[0, max_val], color='#000000'),
            angularaxis=dict(color='#000000'),
        ),
        paper_bgcolor='#ffffff',
        plot_bgcolor='#ffffff',
        font=dict(color='#2B1E16', family='Noto Sans'),
        title=dict(text=title, font=dict(color='#000000', family='Bebas Neue', size=20)),
    )
    return fig


def create_conf_scatter(
    x_vals: List[float],
    y_vals: List[float],
    labels: List[str],
    x_label: str,
    y_label: str,
    title: str = "Scatter Plot",
    colors: Optional[List[str]] = None
):
    """Create a scatter plot with confidence intervals or groupings."""
    if colors is None:
        colors = ['#FF004D'] * len(x_vals)

    fig = go.Figure()
    for i, (x, y, label) in enumerate(zip(x_vals, y_vals, labels)):
        fig.add_trace(go.Scatter(
            x=[x],
            y=[y],
            mode='markers+text',
            text=[label],
            textposition='top center',
            marker=dict(size=14, color=colors[i], line=dict(width=2, color='#000000')),
            name=label,
            showlegend=False
        ))
    fig.update_layout(
        xaxis_title=x_label,
        yaxis_title=y_label,
        paper_bgcolor='#ffffff',
        plot_bgcolor='#ffffff',
        font=dict(color='#2B1E16', family='Noto Sans'),
        title=dict(text=title, font=dict(color='#000000', family='Bebas Neue')),
    )
    return fig