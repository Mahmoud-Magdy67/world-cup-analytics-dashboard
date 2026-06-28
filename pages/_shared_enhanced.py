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
    """Inject custom CSS for professional dark theme."""
    st.markdown("""
    <style>
    /* Global Styles */
    .stApp {
        background: linear-gradient(135deg, #0f1419 0%, #1a1f2e 100%);
    }
    
    /* Headers */
    h1, h2, h3, h4, h5, h6 {
        color: #ffffff !important;
        font-family: 'Segoe UI', system-ui, sans-serif !important;
        font-weight: 600 !important;
    }
    
    h1 { font-size: 2.5rem !important; margin-bottom: 0.5rem !important; }
    h2 { font-size: 2rem !important; }
    h3 { font-size: 1.5rem !important; }
    
    /* Text */
    p, span, div {
        font-family: 'Segoe UI', system-ui, sans-serif !important;
    }
    
    /* Metric Cards */
    [data-testid="stMetric"] {
        background: linear-gradient(135deg, #1e2a3a 0%, #2d3748 100%);
        border-radius: 12px;
        padding: 1.5rem;
        border: 1px solid #374151;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
    }
    
    [data-testid="stMetricValue"] {
        color: #60a5fa !important;
        font-size: 2.5rem !important;
        font-weight: 700 !important;
    }
    
    [data-testid="stMetricLabel"] {
        color: #9ca3af !important;
        font-size: 0.875rem !important;
        text-transform: uppercase !important;
        letter-spacing: 0.05em !important;
    }
    
    [data-testid="stMetricDelta"] {
        color: #34d399 !important;
        font-size: 0.875rem !important;
    }
    
    /* Sidebar */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #111827 0%, #1f2937 100%);
        border-right: 1px solid #374151;
    }
    
    /* Buttons */
    .stButton > button {
        background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
        color: white;
        border: none;
        border-radius: 8px;
        padding: 0.5rem 1.5rem;
        font-weight: 600;
        transition: all 0.2s ease;
    }
    
    .stButton > button:hover {
        background: linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%);
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(59, 130, 246, 0.4);
    }
    
    /* Dataframes */
    [data-testid="stDataFrame"] {
        border-radius: 12px;
        overflow: hidden;
        border: 1px solid #374151;
    }
    
    /* Select boxes */
    [data-testid="stSelectbox"] > div {
        background: #1f2937;
        border: 1px solid #374151;
        border-radius: 8px;
    }
    
    /* Success/Error messages */
    [data-testid="stAlert"] {
        border-radius: 8px;
        border: none;
    }
    
    /* Hide Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* Custom card */
    .info-card {
        background: linear-gradient(135deg, #1e2a3a 0%, #2d3748 100%);
        border-radius: 12px;
        padding: 1.5rem;
        margin: 1rem 0;
        border: 1px solid #374151;
    }
    
    .info-card h4 {
        color: #60a5fa !important;
        margin-top: 0 !important;
    }
    
    .info-card p {
        color: #9ca3af !important;
        line-height: 1.6 !important;
    }
    
    /* Probability badges */
    .prob-badge {
        display: inline-block;
        padding: 0.25rem 0.75rem;
        border-radius: 9999px;
        font-size: 0.75rem;
        font-weight: 600;
        margin: 0.25rem;
    }
    
    .prob-high { background: #dc2626; color: white; }
    .prob-medium { background: #f59e0b; color: white; }
    .prob-low { background: #10b981; color: white; }
    
    /* Team tier badges */
    .tier-favorite { background: #7c3aed; color: white; }
    .tier-contender { background: #3b82f6; color: white; }
    .tier-dark-horse { background: #10b981; color: white; }
    .tier-underdog { background: #6b7280; color: white; }
    </style>
    """, unsafe_allow_html=True)

# ============================================================================
# PAGE COMPONENTS
# ============================================================================

def page_header(title: str, description: str, icon: str = "⚽"):
    """Create a professional page header with icon and description."""
    col1, col2 = st.columns([1, 10])
    with col1:
        st.markdown(f"<div style='font-size: 2.5rem'>{icon}</div>", unsafe_allow_html=True)
    with col2:
        st.title(title)
        st.caption(description)
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
