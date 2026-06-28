"""
Page 5: Winner Predictions
Professional prediction system with Monte Carlo simulation results.
"""
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from pages._shared_enhanced import *
from data.bigquery_enhanced import *

load_custom_css()

page_header(
    "Winner Predictions",
    "Monte Carlo tournament simulation with 10M runs - Championship probabilities and stage forecasts",
    icon="🔮"
)

# Load data
with st.spinner("Loading prediction models..."):
    predictions = get_predictions()
    stage_probs = get_stage_probabilities()
    group_standings = get_group_standings()
    teams = get_teams()

if predictions.empty:
    st.error("Failed to load prediction data.")
    st.stop()

# Executive Summary
st.subheader("🎯 Executive Summary")
top_5 = predictions.head(5)
cols = st.columns(5)
for i, (col, row) in enumerate(zip(cols, top_5.itertuples())):
    with col:
        st.metric(
            label=f"#{i+1} {row.team_name}",
            value=f"{row.championship_probability_pct:.1f}%",
            delta=f"Rank: {row.winner_rank}"
        )

st.divider()

# Main Chart
st.subheader("🏆 Championship Probability - All Teams")

all_teams = predictions.copy()
all_teams['probability_pct'] = all_teams['championship_probability_pct'].round(2)

fig = px.bar(
    all_teams,
    x='probability_pct',
    y='team_name',
    orientation='h',
    title='Championship Probability - All 48 Teams',
    color='probability_pct',
    color_continuous_scale='Blues',
    hover_data=['confederation', 'group_name', 'winner_rank']
)

fig.update_layout(
    height=800,
    paper_bgcolor='rgba(0,0,0,0)',
    plot_bgcolor='rgba(0,0,0,0)',
    xaxis=dict(gridcolor='#374151', linecolor='#6b7280'),
    yaxis=dict(categoryorder='total ascending'),
    font=dict(color='#ffffff', size=11),
    margin=dict(l=20, r=20, t=40, b=20)
)

st.plotly_chart(fig, width='stretch')

st.divider()

# Stage Probability Heatmap
st.subheader("🎯 Stage Probability Heatmap")

heatmap_data = stage_probs.pivot(
    index='team_name', 
    columns='stage', 
    values='probability_pct'
)

stage_order = ['Round of 32', 'Round of 16', 'Quarter-finals', 'Semi-finals', 'Final', 'Winner']
available_stages = [s for s in stage_order if s in heatmap_data.columns]
heatmap_data = heatmap_data[available_stages]
heatmap_data = heatmap_data.sort_values('Winner', ascending=False)

fig_heatmap = go.Figure(data=go.Heatmap(
    z=heatmap_data.values,
    x=heatmap_data.columns,
    y=heatmap_data.index,
    colorscale='Blues',
    hovertemplate='%{y} - %{x}<extra></extra><br>Probability: %{z:.1f}%'
))

fig_heatmap.update_layout(
    title='Stage Progression Probabilities',
    paper_bgcolor='rgba(0,0,0,0)',
    plot_bgcolor='rgba(0,0,0,0)',
    height=700,
    margin=dict(l=150, r=20, t=60, b=20)
)

st.plotly_chart(fig_heatmap, width='stretch')

info_card(
    "How to Read This Heatmap",
    "Each row shows a team's probability of reaching each stage. Darker blue = higher probability. "
    "Teams are sorted by championship probability (top = favorites)."
)

st.divider()

# Team Comparison
st.subheader("⚔️ Team Comparison")

all_team_names = predictions['team_name'].tolist()
selected_teams = st.multiselect(
    "Select teams to compare",
    all_team_names,
    default=all_team_names[:4],
    max_selections=6
)

if selected_teams:
    comparison_data = predictions[predictions['team_name'].isin(selected_teams)]
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### Stage Probabilities Radar")
        
        stages_for_radar = ['championship_probability_pct', 'final_probability_pct', 
                           'semifinal_probability_pct', 'quarterfinal_probability_pct',
                           'round16_probability_pct']
        stage_labels = ['Winner', 'Final', 'Semi-Final', 'Quarter-Final', 'Round of 16']
        
        fig_radar = go.Figure()
        
        for _, team in comparison_data.iterrows():
            values = [team[stage] for stage in stages_for_radar]
            fig_radar.add_trace(go.Scatterpolar(
                r=values,
                theta=stage_labels,
                fill='toself',
                name=team['team_name'],
                line=dict(width=3)
            ))
        
        fig_radar.update_layout(
            polar=dict(
                radialaxis=dict(visible=True),
                bgcolor='rgba(0,0,0,0)'
            ),
            showlegend=True,
            paper_bgcolor='rgba(0,0,0,0)',
            height=500
        )
        
        st.plotly_chart(fig_radar, width='stretch')
    
    with col2:
        st.markdown("#### Key Metrics")
        
        metrics_cols = ['championship_probability_pct', 'elo_rating', 'total_market_value_eur']
        display_df = comparison_data[['team_name'] + metrics_cols].copy()
        display_df.columns = ['Team', 'Win %', 'ELO', 'Value (€)']
        display_df['Value (€)'] = (display_df['Value (€)'] / 1e9).round(2)
        
        st.dataframe(display_df.style.background_gradient(cmap='Blues'), 
                    width='stretch', hide_index=True)

st.divider()

# Model Info
st.subheader("📊 Model Details")

col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Model", "V15_LIVE_FULL_MONTE_CARLO")
with col2:
    st.metric("Simulations", "10M")
with col3:
    st.metric("Teams", len(predictions))

with st.expander("📖 Model Methodology"):
    st.markdown("""
    ### Monte Carlo Tournament Simulation
    
    **Input Features**:
    - Team ELO ratings
    - Market value and squad strength
    - Player performance metrics
    - Recent club form
    
    **Process**:
    1. Group stage matches simulated using ELO-based probabilities
    2. Top 2 + best 4 third-place teams advance
    3. Knockout stages simulated
    4. Repeated 10M times
    
    **Limitations**:
    - No injury modeling
    - Assumes constant team strength
    - Historical ELO limitations
    """)

st.divider()

status = get_data_source_status()
st.caption(f"📊 Data source: BigQuery | Last refresh: {status.last_refresh}")
