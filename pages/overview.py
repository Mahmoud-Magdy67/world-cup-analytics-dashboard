"""
Page 1: Tournament Overview
Executive analytics dashboard with tournament KPIs, predictions, and cross-filtering.
Comparable to FIFA Analyst, Opta, and FiveThirtyEight standards.
"""
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import numpy as np
from pages._shared_enhanced import *
from data.bigquery_enhanced import *

# Load custom CSS
load_custom_css()

# Page header
page_header(
    "Executive Overview",
    "Tournament intelligence, championship projections, and cross-dimensional analytics",
    image_url="assets/logo.png"
)

# ============================================================================
# LOAD DATA
# ============================================================================
with st.spinner("Loading executive analytics..."):
    overview = get_tournament_overview()
    teams = get_teams()
    predictions = get_predictions()
    stage_probs = get_stage_probabilities()

if predictions.empty:
    st.error("Failed to load prediction data. Please check BigQuery connection.")
    st.stop()

# Merge tournament_status and elimination_stage from teams (v16 table) into predictions
# teams has the updated v16 data with tournament_status/elimination_stage
# predictions comes from the old view without these columns
if 'tournament_status' in teams.columns and 'elimination_stage' in teams.columns:
    # Create a lookup dict from teams
    status_lookup = teams.set_index('team_name')[['tournament_status', 'elimination_stage']].to_dict('index')
    
    # Merge into predictions
    def get_status(team):
        return status_lookup.get(team, {}).get('tournament_status', 'Unknown')
    def get_elim_stage(team):
        return status_lookup.get(team, {}).get('elimination_stage', None)
    
    predictions['tournament_status'] = predictions['team_name'].map(get_status)
    predictions['elimination_stage'] = predictions['team_name'].map(get_elim_stage)

# ============================================================================
# GLOBAL CROSS-FILTERING (SESSION STATE)
# ============================================================================
st.markdown("### 🎛️ Global Analytics Filters")
col_f1, col_f2, col_f3 = st.columns(3)

# Extract unique values safely
confeds = sorted(predictions['confederation'].dropna().unique().tolist()) if 'confederation' in predictions.columns else []
groups = sorted(predictions['group_name'].dropna().unique().tolist()) if 'group_name' in predictions.columns else []

selected_confed = col_f1.selectbox("🌐 Confederation", ["All"] + confeds, index=0)
selected_group = col_f2.selectbox("📊 Group Stage", ["All"] + groups, index=0)

# Apply filters
filtered_preds = predictions.copy()
if selected_confed != "All":
    filtered_preds = filtered_preds[filtered_preds['confederation'] == selected_confed]
if selected_group != "All":
    filtered_preds = filtered_preds[filtered_preds['group_name'] == selected_group]

# Highlight Team (after filtering to ensure valid choices)
available_teams = sorted(filtered_preds['team_name'].tolist()) if 'team_name' in filtered_preds.columns else []
highlight_team = col_f3.selectbox("🎯 Highlight Specific Team", ["None"] + available_teams, index=0)

if filtered_preds.empty:
    st.warning("No teams match the current filter selection.")
    st.stop()

st.divider()

# ============================================================================
# EXECUTIVE KPIs
# ============================================================================
# Determine dynamic stats
sim_runs = overview.iloc[0].get('simulation_runs', 10000000) if not overview.empty else 10000000
model_meth = filtered_preds.iloc[0].get('model_method', 'Monte Carlo') if 'model_method' in filtered_preds.columns else 'Monte Carlo'
top_team_name = filtered_preds.iloc[0].get('team_name', 'N/A')
top_team_prob = filtered_preds.iloc[0].get('championship_probability_pct', 0.0)

# Calculate dynamic KPIs based on Highlight Team
if highlight_team != "None":
    team_row = filtered_preds[filtered_preds['team_name'] == highlight_team].iloc[0]
    tracked_count = 1
    fav_label = "Selected Team"
    top_team_name = highlight_team
    top_team_prob = team_row.get('championship_probability_pct', 0.0)
    team_val = team_row.get('total_market_value_eur', 0)
    val_str = f"€{team_val / 1e9:.2f}B" if team_val > 0 else "N/A"
    val_label = "Squad Value"
else:
    tracked_count = len(filtered_preds)
    fav_label = "Current Favorite"
    top_team_name = filtered_preds.iloc[0].get('team_name', 'N/A')
    top_team_prob = filtered_preds.iloc[0].get('championship_probability_pct', 0.0)
    
    if 'total_market_value_eur' in filtered_preds.columns:
        total_val = filtered_preds['total_market_value_eur'].sum()
        val_str = f"€{total_val / 1e9:.1f}B" if total_val > 0 else "N/A"
    else:
        val_str = "N/A"
    val_label = "Total Squad Value"

# Format simulations
if sim_runs >= 1_000_000:
    sim_runs_str = f"{sim_runs / 1_000_000:g}M"
elif sim_runs >= 1_000:
    sim_runs_str = f"{sim_runs / 1_000:g}K"
else:
    sim_runs_str = str(sim_runs)

# Build custom metrics row
col_k1, col_k2, col_k3, col_k4 = st.columns(4)
with col_k1:
    st.metric(label="Teams Tracked", value=tracked_count)
with col_k2:
    st.metric(label="Simulations Executed", value=sim_runs_str)
with col_k3:
    st.metric(label=fav_label, value=top_team_name, delta=f"{top_team_prob:.1f}% Win Prob", delta_color="normal")
with col_k4:
    st.metric(label=val_label, value=val_str)

st.write("") # Spacing

# ============================================================================
# LIVE TOURNAMENT STATUS BANNER
# ============================================================================
st.markdown("### 🔴 LIVE TOURNAMENT STATUS — Updated July 4, 2026 (Round of 16 Begins Today)")

status_col1, status_col2, status_col3 = st.columns(3)
with status_col1:
    st.metric(label="🏆 Teams Alive (R16)", value=16, delta="8 R16 matches today", delta_color="normal")
with status_col2:
    st.metric(label="❌ Eliminated (R32)", value=16, delta="Including Germany, Netherlands, Ghana", delta_color="inverse")
with status_col3:
    st.metric(label="❌ Eliminated (Group Stage)", value=16, delta="Including Türkiye, Uruguay, Iran", delta_color="inverse")

st.info("📊 **Predictions updated through Round of 32 (July 4, 2026).** Championship probabilities recalculated for the 16 remaining teams. Eliminated teams show 0% probability.")
st.caption("Next update: After today's Round of 16 matches (Canada vs Morocco, Paraguay vs France, Colombia 1-0 Ghana ✅)")

st.divider()

# ============================================================================
# TREEMAP: TOURNAMENT LANDSCAPE (Alive Teams Only)
# ============================================================================
st.subheader("🗺️ Tournament Landscape (Probability Distribution — Alive Teams Only)")

# Filter to only alive teams for the treemap (eliminated teams have 0% probability)
if 'tournament_status' in filtered_preds.columns:
    alive_preds = filtered_preds[filtered_preds['tournament_status'].str.startswith('Alive', na=False)].copy()
else:
    alive_preds = filtered_preds.copy()

if 'confederation' in alive_preds.columns and 'group_name' in alive_preds.columns and 'elo_rating' in alive_preds.columns:
    tree_df = alive_preds.copy()
    tree_df['Tournament'] = 'World Cup 2026'
    
    fig_tree = px.treemap(
        tree_df, 
        path=['Tournament', 'confederation', 'group_name', 'team_name'], 
        values='elo_rating',
        color='championship_probability_pct',
        color_continuous_scale=['#FFFFFF', '#00F0FF', '#7B00FF', '#FF004D'],
        hover_data=['championship_probability_pct', 'elo_rating', 'total_market_value_eur', 'tournament_status'],
        title="World Cup Power Hierarchy — Alive Teams Only (Box Size = Team Strength, Color = Tournament Win Probability)",
        labels={
            'championship_probability_pct': 'Win Probability (%)',
            'elo_rating': 'Overall Team Strength (ELO)',
            'total_market_value_eur': 'Squad Value (€)',
            'confederation': 'Confederation',
            'group_name': 'Group',
            'team_name': 'Team',
            'tournament_status': 'Status'
        }
    )
    fig_tree.update_layout(
        margin=dict(t=30, l=10, r=10, b=10),
        paper_bgcolor='#ffffff',
        font=dict(color='#000000', size=14, family='Bebas Neue')
    )
    st.plotly_chart(fig_tree, width='stretch')
    
    # AI Insight
    best_confed = tree_df.groupby('confederation')['championship_probability_pct'].mean().idxmax()
    info_card("AI Insight", f"The treemap reveals the concentration of power among the 16 alive teams. Based on average win probability, the {best_confed} confederation dominates the updated prediction model. Eliminated teams (Group Stage and R32) are excluded as their championship probability is 0%.")
else:
    st.info("⚠️ Required columns for landscape treemap are missing.")

st.divider()

# ============================================================================
# PROFESSIONAL DATA TABLE
# ============================================================================
st.subheader("📋 Executive Probability Board")

disp_cols = ['winner_rank', 'team_name', 'confederation', 'tournament_status', 'championship_probability_pct', 'final_probability_pct', 'elo_rating', 'total_market_value_eur']
exist_disp = [c for c in disp_cols if c in filtered_preds.columns]

if exist_disp:
    df_table = filtered_preds[exist_disp].copy()
    max_prob = df_table['championship_probability_pct'].max() if 'championship_probability_pct' in df_table else 100
    max_final = df_table['final_probability_pct'].max() if 'final_probability_pct' in df_table else 100
    
    # Add status styling
    def highlight_status(row):
        if 'tournament_status' in row:
            if row['tournament_status'] and 'Eliminated' in str(row['tournament_status']):
                return ['background-color: #ffe6e6'] * len(row)
            elif row['tournament_status'] and 'Alive' in str(row['tournament_status']):
                return ['background-color: #e6ffe6'] * len(row)
        return [''] * len(row)
    
    st.dataframe(
        df_table.style.apply(highlight_status, axis=1),
        column_config={
            "winner_rank": st.column_config.NumberColumn("Rank", format="%d"),
            "team_name": st.column_config.TextColumn("Team"),
            "confederation": st.column_config.TextColumn("Confederation"),
            "tournament_status": st.column_config.TextColumn("Tournament Status"),
            "championship_probability_pct": st.column_config.ProgressColumn(
                "Win Probability",
                help="Probability of winning the tournament",
                format="%.1f%%",
                min_value=0,
                max_value=float(max_prob) if not pd.isna(max_prob) else 100.0,
            ),
            "final_probability_pct": st.column_config.ProgressColumn(
                "Reach Final",
                help="Probability of reaching the Final",
                format="%.1f%%",
                min_value=0,
                max_value=float(max_final) if not pd.isna(max_final) else 100.0,
            ),
            "elo_rating": st.column_config.NumberColumn(
                "ELO Rating",
                help="Current objective team strength",
                format="%d"
            ),
            "total_market_value_eur": st.column_config.NumberColumn(
                "Squad Value",
                help="Total market value in Euros",
                format="€%d"
            )
        },
        hide_index=True,
        width='stretch',
        height=500
    )
    
    top_3 = df_table['team_name'].head(3).tolist() if len(df_table) >= 3 else ["the top teams"]
    info_card("AI Insight", f"The simulation heavily favors {', '.join(top_3[:-1])} and {top_3[-1]}. Notice how ELO ratings strongly correlate with progression probabilities, overriding squad market value in several key matchups. Teams with 'Eliminated' status have 0% championship probability.")

st.divider()

# ============================================================================
# ADVANCED HEATMAP: KNOCKOUT PROGRESSION (Top 8 Alive Teams Only)
# ============================================================================
st.subheader("🔥 Projected Knockout Progression Heatmap")

prob_cols = {
    'round16_probability_pct': 'R16',
    'quarterfinal_probability_pct': 'QF',
    'semifinal_probability_pct': 'SF',
    'final_probability_pct': 'Final',
    'championship_probability_pct': 'Champion'
}
heat_cols = [c for c in prob_cols.keys() if c in filtered_preds.columns]

# Filter to only alive teams (tournament_status starts with 'Alive'), then take top 8 by winner_rank
if 'tournament_status' in filtered_preds.columns:
    alive_preds = filtered_preds[filtered_preds['tournament_status'].str.startswith('Alive', na=False)].copy()
else:
    alive_preds = filtered_preds.copy()

if heat_cols and 'team_name' in alive_preds.columns and not alive_preds.empty:
    # Top 8 alive teams by winner_rank (current standings)
    heat_df = alive_preds.nsmallest(8, 'winner_rank').set_index('team_name')[heat_cols]
    heat_df.columns = [prob_cols[c] for c in heat_cols]
    
    fig_heat = px.imshow(
        heat_df, 
        text_auto=".1f", 
        aspect="auto", 
        color_continuous_scale=['#FFFFFF', '#00FF00', '#00F0FF', '#7B00FF', '#FF004D'],
        labels=dict(x="Tournament Stage", y="Team", color="Probability (%)"),
        title="Projected Knockout Progression — Top 8 Alive Teams (Quarter-Finalists)"
    )
    fig_heat.update_layout(
        paper_bgcolor='#ffffff',
        plot_bgcolor='#ffffff',
        font=dict(color='#000000', family='Bebas Neue')
    )
    st.plotly_chart(fig_heat, width='stretch')
    info_card("AI Insight", "The heatmap shows projected survival rates for the 8 teams currently projected to reach the Quarter-Finals. Notice the sharp attrition from R16→QF→SF — only the elite separate themselves in the later stages. Eliminated teams (0% probability) are excluded.")
else:
    st.info("⚠️ Stage probability columns missing for heatmap generation.")

st.divider()

# ============================================================================
# SCATTER PLOT: VALUE VS WIN PROBABILITY (Alive Teams Only)
# ============================================================================
st.subheader("💰 Market Value vs. Win Probability — Alive Teams Only")

# Filter to alive teams only
if 'tournament_status' in filtered_preds.columns:
    alive_scatter = filtered_preds[filtered_preds['tournament_status'].str.startswith('Alive', na=False)].copy()
else:
    alive_scatter = filtered_preds.copy()

if 'total_market_value_eur' in alive_scatter.columns and 'championship_probability_pct' in alive_scatter.columns:
    scatter_df = alive_scatter.copy()
    scatter_df['market_value_b'] = scatter_df['total_market_value_eur'] / 1e9
    
    # Highlight logic
    scatter_df['Color_Group'] = 'Standard'
    if highlight_team != "None":
        scatter_df.loc[scatter_df['team_name'] == highlight_team, 'Color_Group'] = 'Highlighted'
    
    fig_scatter = px.scatter(
        scatter_df,
        x='market_value_b',
        y='championship_probability_pct',
        hover_name='team_name',
        size='elo_rating',
        color='Color_Group' if highlight_team != "None" else 'confederation',
        color_discrete_map={'Highlighted': '#FF004D', 'Standard': '#A0A0A0'} if highlight_team != "None" else None,
        title="Bubble Size = Overall Team Strength (ELO) — 16 Alive Teams Only",
        labels={
            'market_value_b': 'Market Value (€ Billions)', 
            'championship_probability_pct': 'Win Probability (%)',
            'elo_rating': 'Overall Team Strength (ELO)',
            'Color_Group': 'Highlight Status',
            'confederation': 'Confederation'
        }
    )
    
    # Add annotations for top 3 teams
    for i, row in scatter_df.head(3).iterrows():
        fig_scatter.add_annotation(
            x=row['market_value_b'],
            y=row['championship_probability_pct'],
            text=row['team_name'],
            showarrow=True,
            arrowhead=1,
            yshift=10
        )
        
    fig_scatter.update_layout(
        paper_bgcolor='#ffffff',
        plot_bgcolor='#ffffff',
        font=dict(color='#000000', family='Bebas Neue')
    )
    st.plotly_chart(fig_scatter, width='stretch')
    
    info_card("AI Insight", "While squad market value provides a baseline for quality, tactical cohesion and historical ELO (bubble size) are the true differentiators. Teams above the diagonal trend line are 'overperforming' their financial valuation. Eliminated teams (0% probability) are excluded.")
else:
    st.info("⚠️ Required columns missing for scatter plot generation.")

# ============================================================================
# TOURNAMENT CONTEXT & HOSTING IMPACT
# ============================================================================
st.subheader("🏟️ Tournament Context & Hosting Impact")

ctx_c1, ctx_c2 = st.columns(2)
with ctx_c1:
    st.markdown('''
    ### THE LARGEST WORLD CUP IN HISTORY
    THE 2026 EDITION EXPANDS TO 48 TEAMS AND 104 MATCHES, FUNDAMENTALLY ALTERING THE PATH TO THE FINAL. 
    A NEW ROUND OF 32 INTRODUCES AN EXTRA KNOCKOUT HURDLE, INCREASING VARIANCE AND REDUCING THE PREDICTABILITY OF THE CHAMPION. 
    TEAMS MUST NOW SURVIVE 8 MATCHES TO LIFT THE TROPHY INSTEAD OF 7.
    ''')
    
with ctx_c2:
    st.markdown('''
    ### TRAVEL AND ALTITUDE DYNAMICS
    HOSTED ACROSS 16 CITIES IN THE USA, MEXICO, AND CANADA, GEOGRAPHIC STRATEGY IS CRITICAL. 
    TEAMS PLAYING IN MEXICO CITY (7,350 FT ELEVATION) FACE SEVERE PHYSIOLOGICAL DEMANDS. 
    OUR PREDICTION MODELS FACTOR IN "HOST CONTINENT ADVANTAGE" FOR CONCACAF TEAMS, WHILE TRAVEL FATIGUE PENALIZES SQUADS DRAWN INTO CROSS-COUNTRY GROUP ASSIGNMENTS.
    ''')

st.divider()
