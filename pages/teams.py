"""
Page 2: Team Analytics
Comprehensive analysis of 2026 World Cup teams.
Matches the official FWC26 Light Theme.
"""
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import numpy as np
from pages._shared_enhanced import load_custom_css, page_header, info_card
from data.bigquery_enhanced import get_teams, get_team_attributes

# Apply CSS
load_custom_css()

# Header
page_header(
    "Team Analytics",
    "Deep dive into team strengths, tactical balances, and market valuations.",
    image_url="https://upload.wikimedia.org/wikipedia/en/thumb/7/7b/2026_FIFA_World_Cup_Logo.svg/512px-2026_FIFA_World_Cup_Logo.svg.png"
)

# ============================================================================
# LOAD DATA
# ============================================================================
with st.spinner("Loading team metrics..."):
    teams = get_teams()
    team_attrs = get_team_attributes()

if teams.empty or team_attrs.empty:
    st.error("Failed to load team data from BigQuery.")
    st.stop()

# Merge data for comprehensive view
df = pd.merge(
    teams, 
    team_attrs[['team_name', 'continent', 'confederation', 'avg_ovr_top11', 'gk_strength', 'defense_strength', 'midfield_strength', 'attack_strength']], 
    on='team_name', 
    how='inner'
)

# ============================================================================
# FILTERS
# ============================================================================
st.markdown("### 🎛️ Analytics Filters")
c1, c2, c3 = st.columns(3)
confeds = sorted(df['confederation_x'].dropna().unique().tolist()) if 'confederation_x' in df.columns else sorted(df['confederation'].dropna().unique().tolist()) if 'confederation' in df.columns else []
groups = sorted(df['group_name'].dropna().unique().tolist()) if 'group_name' in df.columns else []

sel_confed = c1.selectbox("🌐 Confederation", ["All"] + confeds)
sel_group = c2.selectbox("📊 Group Stage", ["All"] + groups)

filtered = df.copy()
# Handle potential _x or _y suffixes from merge
confed_col = 'confederation_x' if 'confederation_x' in filtered.columns else 'confederation'

if sel_confed != "All":
    filtered = filtered[filtered[confed_col] == sel_confed]
if sel_group != "All":
    filtered = filtered[filtered['group_name'] == sel_group]

sel_team = c3.selectbox("🎯 Spotlight Team", ["None"] + sorted(filtered['team_name'].tolist()))

if filtered.empty:
    st.warning("No teams match filters.")
    st.stop()

st.divider()

# ============================================================================
# KPIs
# ============================================================================
if sel_team != "None":
    kpi_df = filtered[filtered['team_name'] == sel_team]
    label_prefix = f"{sel_team} "
else:
    kpi_df = filtered
    label_prefix = "Avg "

col_k1, col_k2, col_k3, col_k4 = st.columns(4)
with col_k1:
    st.metric("Teams in View", len(kpi_df))
with col_k2:
    st.metric(f"{label_prefix}ELO", f"{kpi_df['elo_rating'].mean():.0f}")
with col_k3:
    val = kpi_df['total_market_value_eur'].sum() / 1e9
    st.metric("Squad Value", f"€{val:.2f}B" if val > 0 else "N/A")
with col_k4:
    st.metric(f"{label_prefix}Top 11 OVR", f"{kpi_df['avg_ovr_top11'].mean():.1f}")

st.divider()

# ============================================================================
# TEAM SPOTLIGHT (RADAR CHART)
# ============================================================================
if sel_team != "None":
    st.subheader(f"🔍 Tactical Profile: {sel_team}")
    team_data = filtered[filtered['team_name'] == sel_team].iloc[0]
    
    # Calculate Tournament Averages for radar
    avg_attack = df['attack_strength'].mean()
    avg_mid = df['midfield_strength'].mean()
    avg_def = df['defense_strength'].mean()
    avg_gk = df['gk_strength'].mean()
    avg_ovr = df['avg_ovr_top11'].mean()

    cats = ['Attack', 'Midfield', 'Defense', 'Goalkeeping', 'Top 11 OVR']
    team_vals = [team_data['attack_strength'], team_data['midfield_strength'], team_data['defense_strength'], team_data['gk_strength'], team_data['avg_ovr_top11']]
    avg_vals = [avg_attack, avg_mid, avg_def, avg_gk, avg_ovr]

    fig_radar = go.Figure()
    fig_radar.add_trace(go.Scatterpolar(
        r=team_vals + [team_vals[0]],
        theta=cats + [cats[0]],
        fill='toself',
        name=sel_team,
        line_color='#FF004D',
        fillcolor='rgba(255, 0, 77, 0.4)'
    ))
    fig_radar.add_trace(go.Scatterpolar(
        r=avg_vals + [avg_vals[0]],
        theta=cats + [cats[0]],
        fill='toself',
        name='Tournament Avg',
        line_color='#000000',
        fillcolor='rgba(0, 0, 0, 0.1)'
    ))
    fig_radar.update_layout(
        polar=dict(
            radialaxis=dict(visible=True, range=[60, 95])
        ),
        showlegend=True,
        paper_bgcolor='#ffffff',
        font=dict(color='#000000', family='Noto Sans'),
        title=dict(text=f"{sel_team} Attributes vs Tournament Average", font=dict(family='Bebas Neue', size=20))
    )
    
    r1, r2 = st.columns([2, 1])
    with r1:
        st.plotly_chart(fig_radar, width='stretch')
    with r2:
        st.markdown(f"### {sel_team} Quick Stats")
        st.markdown(f"**Group Stage:** {team_data['group_name']}")
        st.markdown(f"**Confederation:** {team_data.get('confederation_x', team_data.get('confederation', 'N/A'))}")
        st.markdown(f"**Global ELO:** {team_data['elo_rating']:.0f}")
        st.markdown(f"**Tournament Win Prob:** {team_data.get('championship_probability', 0)*100:.1f}%")
        
        strongest = cats[np.argmax(team_vals[:-1])]  # exclude OVR from strongest attribute calc
        info_card("Tactical Insight", f"Based on ML-hybrid FIFA attributes, {sel_team}'s strongest distinct tactical attribute is their {strongest}.")
    st.divider()

# ============================================================================
# SCATTER PLOT
# ============================================================================
st.subheader("⚔️ Attack vs Defense Matrix")
scatter_df = filtered.copy()
scatter_df['Color'] = 'Standard'
if sel_team != "None":
    scatter_df.loc[scatter_df['team_name'] == sel_team, 'Color'] = 'Highlighted'

fig_scatter = px.scatter(
    scatter_df,
    x='defense_strength', y='attack_strength',
    color='Color' if sel_team != "None" else confed_col,
    color_discrete_map={'Highlighted': '#FF004D', 'Standard': '#A0A0A0'} if sel_team != "None" else None,
    color_discrete_sequence=['#FF004D', '#7B00FF', '#00F0FF', '#00FF00', '#FF4D00'] if sel_team == "None" else None,
    size='avg_ovr_top11',
    hover_name='team_name',
    title="Bubble Size = Top 11 Overall Rating",
    labels={
        'defense_strength': 'Defense Strength (OVR)',
        'attack_strength': 'Attack Strength (OVR)',
        confed_col: 'Confederation'
    }
)

# Add quadrants
avg_atk = df['attack_strength'].mean()
avg_def = df['defense_strength'].mean()
fig_scatter.add_vline(x=avg_def, line_dash="dash", line_color="#000000", opacity=0.5)
fig_scatter.add_hline(y=avg_atk, line_dash="dash", line_color="#000000", opacity=0.5)

fig_scatter.add_annotation(
    x=scatter_df['defense_strength'].max(), 
    y=scatter_df['attack_strength'].max(), 
    text="Elite Balance", 
    showarrow=False, 
    yshift=20, 
    font=dict(color="#FF004D", size=16, family='Bebas Neue')
)

fig_scatter.update_layout(
    paper_bgcolor='#ffffff', 
    plot_bgcolor='#ffffff', 
    font=dict(color='#000000', family='Noto Sans')
)

st.plotly_chart(fig_scatter, width='stretch')
info_card("AI Insight", "Teams in the top-right quadrant possess both elite attacking and defensive capabilities—a hallmark of deep tournament runs. Teams in the top-left rely heavily on outscoring opponents to compensate for defensive frailties.")

st.divider()

# ============================================================================
# DATA TABLE
# ============================================================================
st.subheader("📋 Team Roster Intelligence")

display_cols = ['team_name', confed_col, 'elo_rating', 'avg_ovr_top11', 'attack_strength', 'defense_strength', 'total_market_value_eur']

st.dataframe(
    filtered[display_cols].sort_values('elo_rating', ascending=False),
    column_config={
        "team_name": st.column_config.TextColumn("Team"),
        confed_col: st.column_config.TextColumn("Confed"),
        "elo_rating": st.column_config.NumberColumn("ELO", format="%d"),
        "avg_ovr_top11": st.column_config.NumberColumn("Top 11 OVR", format="%.1f"),
        "attack_strength": st.column_config.ProgressColumn("Attack OVR", min_value=60, max_value=95, format="%.1f"),
        "defense_strength": st.column_config.ProgressColumn("Defense OVR", min_value=60, max_value=95, format="%.1f"),
        "total_market_value_eur": st.column_config.NumberColumn("Squad Value", format="€%d")
    },
    hide_index=True,
    width='stretch',
    height=500
)
