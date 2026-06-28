"""
Page 1: Tournament Overview
Executive dashboard with tournament KPIs, power rankings, and predictions.
"""
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from pages._shared_enhanced import *
from data.bigquery_enhanced import *

# Load custom CSS
load_custom_css()

# Page header
page_header(
    "Tournament Overview",
    "Executive dashboard with tournament-wide KPIs, power rankings, and championship predictions",
    icon="🏆"
)

# ============================================================================
# LOAD DATA
# ============================================================================

with st.spinner("Loading tournament data..."):
    overview = get_tournament_overview()
    teams = get_teams()
    predictions = get_predictions()
    stage_probs = get_stage_probabilities()
    group_standings = get_group_standings()

if teams.empty:
    st.error("Failed to load tournament data. Please check BigQuery connection.")
    st.stop()

# ============================================================================
# TOP-LEVEL KPIs
# ============================================================================

st.subheader("📊 Tournament at a Glance")

# Extract KPI values
if not overview.empty:
    kpi_row = overview.iloc[0]
    sim_runs = int(kpi_row.get('simulation_runs', 10_000_000))
    team_count = int(kpi_row.get('team_count', 48))
    champion = kpi_row.get('predicted_champion', 'Spain')
    champ_prob = float(kpi_row.get('predicted_champion_probability', 15.35))
    second_fav = kpi_row.get('second_favorite', 'France')
    second_prob = float(kpi_row.get('second_favorite_probability', 9.09))
    total_fixtures = int(kpi_row.get('total_group_fixtures', 144))
    remaining = int(kpi_row.get('remaining_group_fixtures', 144))
else:
    sim_runs = 10_000_000
    team_count = 48
    champion = teams.iloc[0]['team_name'] if not teams.empty else 'N/A'
    champ_prob = teams.iloc[0]['championship_probability'] * 100 if not teams.empty else 0
    second_fav = teams.iloc[1]['team_name'] if len(teams) > 1 else 'N/A'
    second_prob = teams.iloc[1]['championship_probability'] * 100 if len(teams) > 1 else 0
    total_fixtures = 144
    remaining = 144

kpi_cards([
    ("Teams", team_count, ""),
    ("Simulations", f"{sim_runs/1_000_000:.0f}M", ""),
    ("Predicted Champion", champion, f"{champ_prob:.1f}%"),
    ("Group Fixtures", total_fixtures, f"{remaining} remaining"),
])

st.divider()

# ============================================================================
# POWER RANKINGS TOP 16
# ============================================================================

col1, col2 = st.columns([2, 1])

with col1:
    st.subheader("🏅 Power Rankings (Top 16)")
    
    # Create power rankings table
    top_16 = teams.head(16).copy()
    top_16['championship_pct'] = (top_16['championship_probability'] * 100).round(2)
    top_16['elo_formatted'] = top_16['elo_rating'].round(0).astype(int)
    top_16['market_value_b'] = (top_16['total_market_value_eur'] / 1e9).round(2)
    
    # Display as styled table
    display_cols = ['winner_rank', 'team_name', 'group_name', 'championship_pct', 'elo_formatted', 'market_value_b', 'contender_tier']
    display_df = top_16[display_cols].copy()
    display_df.columns = ['Rank', 'Team', 'Group', 'Win %', 'ELO', 'Value (€B)', 'Tier']
    
    st.dataframe(
        display_df.style.format({
            'Win %': '{:.2f}%'
        }).background_gradient(
            subset=['Win %'], cmap='Blues'
        ),
        use_container_width=True,
        hide_index=True,
        height=500
    )

with col2:
    st.subheader("📈 Championship Probability Distribution")
    
    # Top 12 probability bar chart
    top_12 = teams.head(12).copy()
    top_12['probability_pct'] = (top_12['championship_probability'] * 100).round(2)
    
    fig = px.bar(
        top_12,
        x='probability_pct',
        y='team_name',
        orientation='h',
        title='Top 12 Title Contenders',
        labels={'probability_pct': 'Probability (%)', 'team_name': 'Team'},
        color='probability_pct',
        color_continuous_scale='Blues'
    )
    
    fig.update_layout(
        height=500,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        xaxis=dict(gridcolor='#374151', linecolor='#6b7280'),
        yaxis=dict(gridcolor='#374151', linecolor='#6b7280'),
        font=dict(color='#ffffff', size=11),
        margin=dict(l=20, r=20, t=40, b=20)
    )
    
    st.plotly_chart(fig, use_container_width=True)

st.divider()

# ============================================================================
# CONFEDERATION ANALYSIS
# ============================================================================

st.subheader("🌍 Confederation Strength")

col1, col2, col3 = st.columns(3)

with col1:
    # Confederation win probabilities
    confed_probs = predictions.groupby('confederation')['championship_probability_pct'].sum().reset_index()
    confed_probs = confed_probs.sort_values('championship_probability_pct', ascending=False)
    
    fig_pie = px.pie(
        confed_probs,
        values='championship_probability_pct',
        names='confederation',
        title='Championship Probability by Confederation',
        color_discrete_sequence=px.colors.qualitative.Set2
    )
    
    fig_pie.update_layout(
        height=350,
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#ffffff', size=11),
        margin=dict(l=20, r=20, t=40, b=20)
    )
    
    st.plotly_chart(fig_pie, use_container_width=True)

with col2:
    # Average ELO by confederation
    teams_with_confed = teams.merge(
        predictions[['team_name', 'confederation']], on='team_name'
    )
    confed_elo = teams_with_confed.groupby('confederation')['elo_rating'].mean().reset_index()
    confed_elo = confed_elo.sort_values('elo_rating', ascending=False)
    
    fig_bar = px.bar(
        confed_elo,
        x='confederation',
        y='elo_rating',
        title='Average ELO by Confederation',
        color='elo_rating',
        color_continuous_scale='Blues'
    )
    
    fig_bar.update_layout(
        height=350,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        xaxis=dict(gridcolor='#374151', linecolor='#6b7280'),
        yaxis=dict(gridcolor='#374151', linecolor='#6b7280'),
        font=dict(color='#ffffff', size=11),
        margin=dict(l=20, r=20, t=40, b=20)
    )
    
    st.plotly_chart(fig_bar, use_container_width=True)

with col3:
    # Teams per confederation
    confed_counts = predictions['confederation'].value_counts().reset_index()
    confed_counts.columns = ['confederation', 'count']
    
    fig_donut = px.donut(
        confed_counts,
        values='count',
        names='confederation',
        title='Teams per Confederation',
        color_discrete_sequence=px.colors.qualitative.Pastel
    )
    
    fig_donut.update_layout(
        height=350,
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#ffffff', size=11),
        margin=dict(l=20, r=20, t=40, b=20)
    )
    
    st.plotly_chart(fig_donut, use_container_width=True)

st.divider()

# ============================================================================
# GROUP STAGE PREDICTIONS
# ============================================================================

st.subheader("📋 Expected Group Standings")

# Create tabs for each group
groups = sorted(teams['group_name'].unique())
tabs = st.tabs([f"Group {g}" for g in groups])

for tab, group in zip(tabs, groups):
    with tab:
        group_data = group_standings[group_standings['group_name'] == group].copy()
        group_data = group_data.sort_values('avg_group_points', ascending=False)
        
        # Display expected standings
        display_cols = [
            'team_name', 'avg_group_points', 'avg_group_goal_difference',
            'group_winner_probability_pct', 'group_runner_up_probability_pct',
            'round32_probability_pct'
        ]
        
        styled = group_data[display_cols].style.format({
            'avg_group_points': '{:.2f}',
            'avg_group_goal_difference': '{:+.2f}',
            'group_winner_probability_pct': '{:.1f}%',
            'group_runner_up_probability_pct': '{:.1f}%',
            'round32_probability_pct': '{:.1f}%'
        }).background_gradient(
            subset=['avg_group_points'], cmap='Blues'
        )
        
        st.dataframe(styled, use_container_width=True, hide_index=True, height=300)

st.divider()

# ============================================================================
# TOURNAMENT FUNNEL
# ============================================================================

st.subheader("🎯 Tournament Stage Funnel")

col1, col2 = st.columns(2)

with col1:
    # Funnel for top team
    top_team = teams.iloc[0]['team_name']
    team_funnel = stage_probs[stage_probs['team_name'] == top_team].copy()
    team_funnel = team_funnel.sort_values('stage_order')
    
    stages = team_funnel['stage'].tolist()
    probs = team_funnel['probability_pct'].tolist()
    
    fig_funnel = create_funnel_chart(
        stages, probs,
        title=f"{top_team} - Stage Probabilities"
    )
    
    st.plotly_chart(fig_funnel, use_container_width=True)

with col2:
    # Funnel for second team
    second_team = teams.iloc[1]['team_name']
    team_funnel2 = stage_probs[stage_probs['team_name'] == second_team].copy()
    team_funnel2 = team_funnel2.sort_values('stage_order')
    
    stages2 = team_funnel2['stage'].tolist()
    probs2 = team_funnel2['probability_pct'].tolist()
    
    fig_funnel2 = create_funnel_chart(
        stages2, probs2,
        title=f"{second_team} - Stage Probabilities"
    )
    
    st.plotly_chart(fig_funnel2, use_container_width=True)

st.divider()

# ============================================================================
# MARKET VALUE vs PERFORMANCE
# ============================================================================

st.subheader("💰 Market Value vs Championship Probability")

# Scatter plot
scatter_data = teams.merge(
    predictions[['team_name', 'championship_probability_pct']], 
    on='team_name'
)
scatter_data['market_value_b'] = scatter_data['total_market_value_eur'] / 1e9
scatter_data['probability_pct'] = scatter_data['championship_probability_pct']

fig_scatter = create_scatter_with_trend(
    scatter_data,
    x_col='market_value_b',
    y_col='probability_pct',
    hover_name='team_name',
    color_col='contender_tier',
    title="Market Value vs Win Probability",
    trendline="ols"
)

st.plotly_chart(fig_scatter, use_container_width=True)

info_card(
    "Key Insight",
    "Market value shows moderate correlation with championship probability, but ELO ratings and recent form are equally important predictors. Dark horses like Croatia (2018) and Morocco (2022) demonstrate that team chemistry and tactics can overcome financial disparities."
)

st.divider()

# ============================================================================
# DATA SOURCE INFO
# ============================================================================

status = get_data_source_status()
if status.bigquery_enabled:
    st.caption(f"📊 Data source: BigQuery ({status.tables_available}) | Last refresh: {status.last_refresh}")
else:
    st.caption(f"⚠️ Data source: {status.note}")
