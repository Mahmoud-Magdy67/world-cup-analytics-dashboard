"""
Shared components and utilities for World Cup Analytics Dashboard.
Professional UI components, custom CSS, and reusable visualizations.
"""
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from typing import List, Dict, Any, Optional, Tuple
import numpy as np

# ============================================================================
# CUSTOM CSS - Professional Dark Theme
# ============================================================================

def load_custom_css():
    """Inject custom CSS for official FWC26 light theme."""
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans:wght@400;700;900&family=Bebas+Neue&display=swap');
    
    /* Global Styles */
    .stApp {
        background-color: #ffffff;
        color: #000000;
    }
    
    /* Headers */
    h1, h2, h3, h4, h5, h6 {
        color: #000000 !important;
        font-family: 'Bebas Neue', 'Noto Sans', sans-serif !important;
        letter-spacing: 0.03em !important;
        text-transform: uppercase;
    }
    
    h1 { font-size: 3.5rem !important; margin-bottom: 0.5rem !important; }
    h2 { font-size: 2.5rem !important; }
    h3 { font-size: 2rem !important; }
    
    /* Text */
    p, span, div, li, td, th {
        font-family: 'Noto Sans', sans-serif !important;
        color: #000000;
    }
    
    /* Metric Cards */
    [data-testid="stMetric"] {
        background: #ffffff;
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
        font-size: 3rem !important;
        font-weight: 900 !important;
        font-family: 'Bebas Neue', sans-serif !important;
    }
    
    [data-testid="stMetricLabel"] {
        color: #000000 !important;
        font-size: 1rem !important;
        text-transform: uppercase !important;
        font-weight: 900 !important;
    }
    
    [data-testid="stMetricDelta"] {
        color: #00B347 !important; /* WC26 Green */
        font-size: 1rem !important;
        font-weight: 700 !important;
    }
    
    /* Sidebar */
    [data-testid="stSidebar"] {
        background-color: #f3f4f6;
        border-right: 4px solid #000000;
    }
    
    /* Buttons */
    .stButton > button {
        background-color: #000000;
        color: #ffffff !important;
        border: none;
        border-radius: 0px;
        padding: 0.5rem 1.5rem;
        font-weight: 900;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        font-family: 'Noto Sans', sans-serif !important;
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
        background: #ffffff !important;
    }
    
    /* Select boxes */
    [data-testid="stSelectbox"] > div {
        background: #ffffff;
        border: 2px solid #000000;
        border-radius: 0px;
        color: #000000;
    }
    
    /* Info Cards (WC26 Pattern Vibes) */
    .info-card {
        background: #ffffff;
        border-radius: 0px;
        padding: 1.5rem;
        margin: 1rem 0;
        border: 3px solid #000000;
        border-left: 8px solid #00F0FF; /* WC26 Cyan */
        box-shadow: 4px 4px 0px #000000;
    }
    
    .info-card h4 {
        color: #000000 !important;
        margin-top: 0 !important;
        font-family: 'Bebas Neue', sans-serif !important;
    }
    
    .info-card p {
        color: #000000 !important;
        line-height: 1.6 !important;
        font-weight: 600;
    }
    
    /* Probability badges */
    .prob-badge {
        display: inline-block;
        padding: 0.25rem 0.75rem;
        border-radius: 0px;
        font-size: 0.8rem;
        font-weight: 900;
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
    </style>
    """, unsafe_allow_html=True)


# ============================================================================
# PAGE COMPONENTS
# ============================================================================

def page_header(title: str, description: str, icon: str = "⚽", image_url: str = None):
    """Create a professional page header with icon/image and description."""
    col1, col2 = st.columns([1, 10])
    with col1:
        if image_url:
            st.markdown(f"<img src='{image_url}' style='width: 80px; height: auto; max-width: 100%; border-radius: 12px; margin-top: 5px;'>", unsafe_allow_html=True)
        else:
            st.markdown(f"<div style='font-size: 3.5rem; text-align: center;'>{icon}</div>", unsafe_allow_html=True)
    with col2:
        st.title(title)
        st.markdown(f"<p style='color: #000000; font-size: 1.1rem; margin-top: -1rem;'>{description}</p>", unsafe_allow_html=True)
    st.divider()

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
    """Create an info card with title and content."""
    st.markdown(f"""
    <div class="info-card">
        <h4>{icon} {title}</h4>
        <p>{content}</p>
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
