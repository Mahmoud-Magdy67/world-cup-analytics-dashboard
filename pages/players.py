"""
Page 3: Player Analytics
Deep-dive into individual player performance across all World Cup nations.
Matches the official FWC26 Light Theme.
"""
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import numpy as np
from pages._shared_enhanced import load_custom_css, page_header, info_card
from data.bigquery_enhanced import get_players, get_player_percentiles, get_player_tournament_stats

# Apply CSS
load_custom_css()

# Header
page_header(
    "Player Analytics",
    "Individual performance intelligence across 500+ World Cup players.",
    image_url="assets/logo.png"
)

# ============================================================================
# LOAD DATA
# ============================================================================
with st.spinner("Loading player metrics..."):
    df = get_players()
    percentiles = get_player_percentiles()
    tournament_stats = get_player_tournament_stats()

if df.empty:
    st.error("Failed to load player data from BigQuery.")
    st.stop()

# ============================================================================
# WORLD CUP 2026 TOURNAMENT LEADERS (LIVE/HYBRID)
# ============================================================================
st.markdown("### 🏆 World Cup 2026 Tournament Leaders")
if not tournament_stats.empty:
    merged_tournament = tournament_stats.merge(
        df[['player_name', 'nation_code', 'position', 'club_team', 'league', 'minutes']].drop_duplicates('player_name'),
        on='player_name',
        how='left'
    )
    merged_tournament['goal_contribution'] = merged_tournament['wc26_goals'] + merged_tournament['wc26_assists']
    merged_tournament = merged_tournament.sort_values(['wc26_goals', 'wc26_assists'], ascending=[False, False]).reset_index(drop=True)

    t1, t2 = st.columns(2)
    with t1:
        st.markdown("#### ⚽ Top Scorers")
        goals_df = merged_tournament.nlargest(10, 'wc26_goals')[['player_name', 'nation_code', 'wc26_goals', 'wc26_assists', 'club_team']].copy()
        goals_df.columns = ['Player', 'Nation', 'Goals', 'Assists', 'Club']
        st.dataframe(
            goals_df,
            column_config={
                "Player": st.column_config.TextColumn("Player"),
                "Nation": st.column_config.TextColumn("Nation"),
                "Goals": st.column_config.NumberColumn("Goals", format="%d"),
                "Assists": st.column_config.NumberColumn("Assists", format="%d"),
                "Club": st.column_config.TextColumn("Club"),
            },
            hide_index=True,
            width='stretch'
        )

    with t2:
        st.markdown("#### 🅰️ Top Assist Providers")
        assists_df = merged_tournament.nlargest(10, 'wc26_assists')[['player_name', 'nation_code', 'wc26_goals', 'wc26_assists', 'club_team']].copy()
        assists_df.columns = ['Player', 'Nation', 'Goals', 'Assists', 'Club']
        st.dataframe(
            assists_df,
            column_config={
                "Player": st.column_config.TextColumn("Player"),
                "Nation": st.column_config.TextColumn("Nation"),
                "Goals": st.column_config.NumberColumn("Goals", format="%d"),
                "Assists": st.column_config.NumberColumn("Assists", format="%d"),
                "Club": st.column_config.TextColumn("Club"),
            },
            hide_index=True,
            width='stretch'
        )

    info_card("Tournament Stats Source",
        "Live stats are fetched from **ESPN's World Cup statistics API** and cached for 10 minutes. "
        "If the live feed is unavailable, the dashboard falls back to the cached BigQuery table `raw_wc26_player_stats_espn`. "
        "These numbers reflect **actual World Cup 2026 match performance only** — not club season data.")
else:
    st.warning("World Cup 2026 tournament statistics are not yet available.")

st.divider()

# ============================================================================
# FILTERS
# ============================================================================
st.markdown("### 🎛️ Tournament Filters")
c1, c2, c3, c4 = st.columns(4)

positions = sorted(df['position'].dropna().unique().tolist()) if 'position' in df.columns else []
nations = sorted(df['nation_code'].dropna().unique().tolist()) if 'nation_code' in df.columns else []
clubs = sorted(df['club_team'].dropna().unique().tolist()) if 'club_team' in df.columns else []

sel_pos = c1.selectbox("📍 Position", ["All"] + positions)
sel_nat = c2.selectbox("🏳️ Nation", ["All"] + nations)
sel_club = c3.selectbox("🏟️ Club", ["All"] + clubs)
sel_player = c4.selectbox("🎯 Spotlight Player", ["None"] + sorted(df['player_name'].tolist()))

filtered = df.copy()
if sel_pos != "All":
    filtered = filtered[filtered['position'] == sel_pos]
if sel_nat != "All":
    filtered = filtered[filtered['nation_code'] == sel_nat]
if sel_club != "All":
    filtered = filtered[filtered['club_team'] == sel_club]

if filtered.empty:
    st.warning("No players match the selected filters.")
    st.stop()

st.divider()

# ============================================================================
# TOURNAMENT-ONLY PLAYER TABLES
# ============================================================================
if not tournament_stats.empty:
    st.markdown("### 📊 Full Tournament Player Rankings")
    full_ranked = tournament_stats.copy()
    full_ranked['tournament_contribution'] = full_ranked['wc26_goals'] + full_ranked['wc26_assists']
    full_ranked = full_ranked.sort_values(['wc26_goals', 'wc26_assists'], ascending=[False, False]).reset_index(drop=True)

    st.dataframe(
        full_ranked[['player_name', 'wc26_goals', 'wc26_assists', 'tournament_contribution']].head(50),
        column_config={
            "player_name": st.column_config.TextColumn("Player"),
            "wc26_goals": st.column_config.NumberColumn("WC26 Goals", format="%d"),
            "wc26_assists": st.column_config.NumberColumn("WC26 Assists", format="%d"),
            "tournament_contribution": st.column_config.NumberColumn("Total Contributions", format="%d"),
        },
        hide_index=True,
        width='stretch'
    )

    info_card("Tournament Scope",
        "This table includes only **World Cup 2026** match statistics. "
        "Club season data is intentionally excluded to avoid mixing seasons/tournaments.")
else:
    st.warning("Tournament player rankings are unavailable.")

st.divider()
