"""
Page 3: Player Analytics — Real World Cup 2026 Performance
Derived from the open Kaggle dataset mominullptr/fifa-world-cup-2026-dataset (CC0).
1,248 WC26 squad players, 48 nations, verified stats from sofascore.com.
Matches the official FWC26 Light Theme.
"""
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import numpy as np
from pages._shared_enhanced import load_custom_css, page_header, info_card
from data.real_wc26_players import (
    get_real_wc26_players, get_real_wc26_player_summary,
    get_real_wc26_top_scorers, get_real_wc26_top_assists,
    get_real_wc26_top_contributors,
    get_real_wc26_nation_contributions, get_real_wc26_position_breakdown,
    get_real_wc26_gk_leaders,
)

load_custom_css()

page_header(
    "Player Analytics",
    "Real World Cup 2026 individual performance — 1,248 squad players across 48 nations.",
    image_url="assets/logo.png"
)

FWC26_RED = "#C8102E"
FWC26_BLACK = "#1A1A1A"
FWC26_WHITE = "#FFFFFF"
FWC26_GOLD = "#F4C542"
FWC26_SILVER = "#A8B8C8"
FWC26_TEXT = "#2B1E16"
FWC26_BG = "#F6F1EB"
FWC26_POSITION_COLORS = ["#C8102E", "#7B00FF", "#00F0FF", "#00FF00", "#FF4D00"]

st.markdown(
    f"""
    <style>
    .wc-hero {{
        background-color: {FWC26_BG}; color: {FWC26_TEXT};
        padding: 20px 22px; border-radius: 12px; border-left: 6px solid {FWC26_RED};
        font-family: 'Noto Sans', sans-serif;
    }}
    </style>
    """,
    unsafe_allow_html=True
)

# ============================================================================
# LOAD DATA
# ============================================================================
with st.spinner("Loading real WC26 player stats from open Kaggle dataset..."):
    players = get_real_wc26_players()
    summary = get_real_wc26_player_summary()
    top_scorers = get_real_wc26_top_scorers(10)
    top_assists = get_real_wc26_top_assists(10)
    top_contrib = get_real_wc26_top_contributors(10)
    nation_contrib = get_real_wc26_nation_contributions()
    position_breakdown = get_real_wc26_position_breakdown()
    gk_leaders = get_real_wc26_gk_leaders(10)

if players.empty or summary.empty:
    st.error("Failed to load real WC26 player data from the Kaggle dataset.")
    st.stop()

s = summary.iloc[0]

# Friendly aliases for display are now applied inside the loader so all derived
# dataframes (top_scorers, top_assists, top_contrib, nation_contrib, gk_leaders)
# inherit them automatically.

# ============================================================================
# HERO METRICS
# ============================================================================
col1, col2, col3, col4, col5 = st.columns(5)
with col1:
    st.metric("Players Tracked", f"{int(s['players_tracked']):,}")
with col2:
    st.metric("Goals Scored", f"{int(s['wc26_goals'])}", help="Player-attributed goals. Match total is 308; the 11-goal gap is own goals (own_goals column in the dataset).")
with col3:
    st.metric("Assists", f"{int(s['wc26_assists'])}")
with col4:
    st.metric("G+A Involved", f"{int(s['goal_contributions'])}", help="Goals + assists recorded for these players. An assist is counted on the same play as a goal, so this is not an independent event count.")
with col5:
    st.metric("Active Nations", f"{int(s['active_nations'])}")

st.caption(
    "Source: open Kaggle dataset mominullptr/fifa-world-cup-2026-dataset (CC0 public domain). "
    "Stats verified against sofascore.com. All 1,248 WC26 squad players — no club-season data, "
    "no synthetic prediction-system entries. "
    f"Player-attributed goals sum to {int(s['wc26_goals'])}; the {308 - int(s['wc26_goals'])} own goals "
    "bring the tournament-wide match total to 308."
)
st.divider()

# Tournament hero banner
st.markdown(
    f"<div class='wc-hero'><b>🏆 World Cup 2026 Tournament Leaders</b><br/>"
    "Real match-by-match stats from the actual tournament — not club season data, "
    "not predictions.</div>",
    unsafe_allow_html=True
)
st.markdown("")

# ============================================================================
# AWARDS ROW: Golden Boot / Playmaker King / Golden Glove
# ============================================================================
d1, d2, d3 = st.columns(3)
with d1:
    st.metric("👟 Golden Boot",
              s["golden_boot"],
              f"{int(s['golden_boot_goals'])} goals")
with d2:
    st.metric("🎯 Playmaker King",
              s["playmaker"],
              f"{int(s['playmaker_assists'])} assists")
with d3:
    top_gk = gk_leaders.iloc[0] if not gk_leaders.empty else None
    if top_gk is not None:
        st.metric("🧤 Golden Glove",
                  top_gk["player_name"],
                  f"{int(top_gk['clean_sheets'])} clean sheets")
    else:
        st.metric("🧤 Golden Glove", "—", "")
st.divider()

# ============================================================================
# TOP SCORERS & ASSISTS
# ============================================================================
c1, c2 = st.columns(2)
with c1:
    st.markdown("<h3 style='color: #C8102E; font-family: Bebas Neue; margin-top:15px;'>⚽ Top Scorers</h3>", unsafe_allow_html=True)
    fig_g = px.bar(
        top_scorers.sort_values("wc26_goals", ascending=True),
        x="wc26_goals", y="spotlight_name",
        orientation="h",
        color_discrete_sequence=[FWC26_RED],
        labels={"wc26_goals": "Goals", "spotlight_name": "Player"},
        text="wc26_goals",
    )
    fig_g.update_layout(
        title=dict(text="Top WC26 Scorers", font=dict(family="Bebas Neue", size=20, color=FWC26_RED)),
        paper_bgcolor=FWC26_WHITE, plot_bgcolor=FWC26_WHITE,
        font=dict(color=FWC26_TEXT, family="Noto Sans"),
        xaxis=dict(title="", showgrid=True, gridcolor=FWC26_SILVER),
        yaxis=dict(title=""),
        showlegend=False, height=420, margin=dict(l=120, r=20, t=30, b=40)
    )
    fig_g.update_traces(textposition="outside", marker_line_color=FWC26_WHITE, marker_line_width=1)
    st.plotly_chart(fig_g, width="stretch")

with c2:
    st.markdown("<h3 style='color: #C8102E; font-family: Bebas Neue; margin-top:15px;'>🅰️ Top Assist Providers</h3>", unsafe_allow_html=True)
    if not top_assists.empty:
        fig_a = px.bar(
            top_assists.sort_values("wc26_assists", ascending=True),
            x="wc26_assists", y="spotlight_name",
            orientation="h",
            color_discrete_sequence=[FWC26_SILVER],
            labels={"wc26_assists": "Assists", "spotlight_name": "Player"},
            text="wc26_assists",
        )
        fig_a.update_layout(
            title=dict(text="Top WC26 Assist Providers", font=dict(family="Bebas Neue", size=20, color=FWC26_RED)),
            paper_bgcolor=FWC26_WHITE, plot_bgcolor=FWC26_WHITE,
            font=dict(color=FWC26_TEXT, family="Noto Sans"),
            xaxis=dict(title="", showgrid=True, gridcolor=FWC26_SILVER),
            yaxis=dict(title=""),
            showlegend=False, height=420, margin=dict(l=120, r=20, t=30, b=40)
        )
        fig_a.update_traces(textposition="outside", marker_line_color=FWC26_WHITE, marker_line_width=1)
        st.plotly_chart(fig_a, width="stretch")
    else:
        st.info("No assist data yet for tournament leaders.")

# ============================================================================
# COMBINED GOAL CONTRIBUTIONS
# ============================================================================
st.markdown(
    "<h3 style='color: #C8102E; font-family: Bebas Neue; margin-top:15px;'>🎯 Combined Goal Contributions: Goals + Assists</h3>",
    unsafe_allow_html=True
)
fig_top = go.Figure()
fig_top.add_trace(go.Bar(
    name="Goals", x=top_contrib["spotlight_name"], y=top_contrib["wc26_goals"],
    marker_color=FWC26_RED, text=top_contrib["wc26_goals"], textposition="inside"
))
fig_top.add_trace(go.Bar(
    name="Assists", x=top_contrib["spotlight_name"], y=top_contrib["wc26_assists"],
    marker_color=FWC26_SILVER, text=top_contrib["wc26_assists"], textposition="inside"
))
fig_top.update_layout(
    barmode="stack",
    paper_bgcolor=FWC26_WHITE, plot_bgcolor=FWC26_WHITE,
    font=dict(color=FWC26_TEXT, family="Noto Sans"),
    title=dict(text="Top 10 Tournament Contributors", font=dict(family="Bebas Neue", size=20, color=FWC26_RED)),
    xaxis_tickangle=-35, xaxis=dict(title="", showgrid=False),
    yaxis=dict(title="Goal Contributions", showgrid=True, gridcolor=FWC26_SILVER),
    legend=dict(orientation="h", yanchor="bottom", y=1.04, xanchor="center", x=0.5),
    height=420, margin=dict(t=80, b=80)
)
st.plotly_chart(fig_top, width="stretch")
st.divider()

# ============================================================================
# PLAYER SPOTLIGHT INSIGHT
# ============================================================================
if not top_contrib.empty:
    star = top_contrib.iloc[0]
    st.info(
        f"**Tournament MVP Signal:** {star.get('spotlight_name', star['player_name'])} "
        f"({star.get('team_name', 'N/A')}) contributed **{int(star['goal_contribution'])}** "
        f"with **{int(star['wc26_goals'])} goal(s)** and **{int(star['wc26_assists'])} assist(s)** "
        f"across {int(star.get('matches_played', 0))} matches ({int(star.get('minutes_played', 0))} min). "
        f"Position: **{star.get('position', 'N/A')}** · Club: **{star.get('club_team', 'N/A')}**"
    )
    st.divider()

# ============================================================================
# NATION CONTRIBUTION MAP: GOALS & ASSISTS
# ============================================================================
if not nation_contrib.empty:
    st.markdown(
        "<h3 style='color: #C8102E; font-family: Bebas Neue; margin-top:15px;'>🏳️ Nation Contribution Map: Goals & Assists</h3>",
        unsafe_allow_html=True
    )
    col_n1, col_n2 = st.columns(2)

    with col_n1:
        fig_ng = px.bar(
            nation_contrib.sort_values("tgoals", ascending=True).head(15),
            x="tgoals", y="team_name",
            orientation="h",
            color="tgoals",
            color_continuous_scale=[FWC26_WHITE, FWC26_RED],
            labels={"tgoals": "Goals", "team_name": "Nation"},
            text="tgoals",
        )
        fig_ng.update_layout(
            title=dict(text="Top 15 Nations by WC26 Goals",
                       font=dict(family="Bebas Neue", size=18, color=FWC26_RED)),
            paper_bgcolor=FWC26_WHITE, plot_bgcolor=FWC26_WHITE,
            font=dict(color=FWC26_TEXT, family="Noto Sans"),
            xaxis=dict(title="", showgrid=True, gridcolor=FWC26_SILVER),
            yaxis=dict(title=""),
            coloraxis_showscale=False,
            height=380, margin=dict(l=80, r=20, t=30, b=40)
        )
        fig_ng.update_traces(textposition="outside")
        st.plotly_chart(fig_ng, width="stretch")

    with col_n2:
        fig_na = px.bar(
            nation_contrib.sort_values("tassists", ascending=True).head(15),
            x="tassists", y="team_name",
            orientation="h",
            color="tassists",
            color_continuous_scale=[FWC26_WHITE, FWC26_SILVER],
            labels={"tassists": "Assists", "team_name": "Nation"},
            text="tassists",
        )
        fig_na.update_layout(
            title=dict(text="Top 15 Nations by WC26 Assists",
                       font=dict(family="Bebas Neue", size=18, color=FWC26_RED)),
            paper_bgcolor=FWC26_WHITE, plot_bgcolor=FWC26_WHITE,
            font=dict(color=FWC26_TEXT, family="Noto Sans"),
            xaxis=dict(title="", showgrid=True, gridcolor=FWC26_SILVER),
            yaxis=dict(title=""),
            coloraxis_showscale=False,
            height=380, margin=dict(l=80, r=20, t=30, b=40)
        )
        fig_na.update_traces(textposition="outside")
        st.plotly_chart(fig_na, width="stretch")

    st.divider()

# ============================================================================
# POSITION BREAKDOWN
# ============================================================================
if not position_breakdown.empty:
    st.markdown(
        "<h3 style='color: #C8102E; font-family: Bebas Neue; margin-top:15px;'>📍 Goals & Assists by Position</h3>",
        unsafe_allow_html=True
    )
    pbreakdown = position_breakdown.copy()
    fig_pos = go.Figure()
    fig_pos.add_trace(go.Bar(
        name="Goals", x=pbreakdown["position"], y=pbreakdown["goals"],
        marker_color=FWC26_RED, text=pbreakdown["goals"], textposition="inside"
    ))
    fig_pos.add_trace(go.Bar(
        name="Assists", x=pbreakdown["position"], y=pbreakdown["assists"],
        marker_color=FWC26_SILVER, text=pbreakdown["assists"], textposition="inside"
    ))
    fig_pos.update_layout(
        barmode="group",
        paper_bgcolor=FWC26_WHITE, plot_bgcolor=FWC26_WHITE,
        font=dict(color=FWC26_TEXT, family="Noto Sans"),
        title=dict(text="Tournament Production by Position",
                   font=dict(family="Bebas Neue", size=20, color=FWC26_RED)),
        xaxis=dict(title="", showgrid=False),
        yaxis=dict(title="Count", showgrid=True, gridcolor=FWC26_SILVER),
        legend=dict(orientation="h", yanchor="bottom", y=1.04, xanchor="center", x=0.5),
        height=360, margin=dict(t=80, b=40)
    )
    st.plotly_chart(fig_pos, width="stretch")
    st.divider()

# ============================================================================
# GOALKEEPER LEADERS (Golden Glove race)
# ============================================================================
if not gk_leaders.empty:
    st.markdown(
        "<h3 style='color: #C8102E; font-family: Bebas Neue; margin-top:15px;'>🧤 Goalkeeper Leaders — Clean Sheets & Shootout</h3>",
        unsafe_allow_html=True
    )
    gk_show = gk_leaders[["player_name", "team_name", "matches_played",
                           "clean_sheets", "saves", "goals_conceded"]].copy()
    gk_show.columns = ["Goalkeeper", "Nation", "Matches", "Clean Sheets", "Saves", "Goals Conceded"]
    st.dataframe(
        gk_show,
        column_config={
            "Matches": st.column_config.NumberColumn(format="%d"),
            "Clean Sheets": st.column_config.NumberColumn(format="%d"),
            "Saves": st.column_config.NumberColumn(format="%d"),
            "Goals Conceded": st.column_config.NumberColumn(format="%d"),
        },
        hide_index=True, width="stretch"
    )
    st.divider()

# ============================================================================
# RADAR PROFILE: TOP 8 PLAYERS (Real per-90 metrics)
# ============================================================================
top8 = top_contrib.head(8).copy()
fig_radar = go.Figure()
for _, row in top8.iterrows():
    fig_radar.add_trace(go.Scatterpolar(
        r=[
            row["wc26_goals"],
            row["wc26_assists"],
            row["goal_contribution"],
            row.get("ninety_goals", 0),
            row.get("ninety_assists", 0),
            row.get("ninety_contributions", 0),
        ],
        theta=["Goals", "Assists", "Contributions (G+A)", "Per-90 Goals", "Per-90 Assists", "Per-90 Contrib."],
        fill="toself",
        name=f"{row['player_name']} ({row['team_name']})"
    ))

fig_radar.update_layout(
    polar=dict(radialaxis=dict(visible=True, gridcolor=FWC26_SILVER)),
    paper_bgcolor=FWC26_WHITE,
    font=dict(color=FWC26_TEXT, family="Noto Sans"),
    title=dict(text="Top 8 Contributor Profiles (Real WC26 stats, per-90 normalised)",
               font=dict(family="Bebas Neue", size=20, color=FWC26_RED)),
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5),
    height=520,
    margin=dict(t=70, b=40)
)
st.plotly_chart(fig_radar, width="stretch")
st.caption("Real per-90 figures derived from minutes_played in WC26 matches only.")
st.divider()

# ============================================================================
# FULL TOURNAMENT PLAYER RANKINGS (filterable)
# ============================================================================
st.markdown(
    "<h3 style='color: #C8102E; font-family: Bebas Neue; margin-top:15px;'>📊 Full Tournament Player Rankings</h3>",
    unsafe_allow_html=True
)

# Nation filter
all_nations = sorted(players["team_name"].dropna().unique().tolist())
pos_filter = st.selectbox("Filter by nation", ["All"] + all_nations, key="nat_filter")
display_df = players if pos_filter == "All" else players[players["team_name"] == pos_filter]

rank_cols = ["spotlight_name", "team_name", "nation_code", "position",
             "matches_played", "wc26_goals", "wc26_assists", "goal_contribution",
             "minutes_played", "ninety_contributions"]
avail = [c for c in rank_cols if c in display_df.columns]
ranked = display_df[avail].copy()
ranked.insert(0, "rank", range(1, len(ranked) + 1))
ranked = ranked.sort_values(["goal_contribution", "wc26_goals", "wc26_assists"],
                            ascending=[False, False, False]).reset_index(drop=True)
ranked["rank"] = range(1, len(ranked) + 1)

st.dataframe(
    ranked.head(50),
    column_config={
        "rank": st.column_config.NumberColumn("#", format="%d"),
        "spotlight_name": st.column_config.TextColumn("Player"),
        "team_name": st.column_config.TextColumn("Nation"),
        "nation_code": st.column_config.TextColumn("Code"),
        "position": st.column_config.TextColumn("Pos"),
        "matches_played": st.column_config.NumberColumn("MP", format="%d"),
        "wc26_goals": st.column_config.NumberColumn("Goals", format="%d"),
        "wc26_assists": st.column_config.NumberColumn("Assists", format="%d"),
        "goal_contribution": st.column_config.NumberColumn("G+A", format="%d"),
        "minutes_played": st.column_config.NumberColumn("Min", format="%d"),
        "ninety_contributions": st.column_config.NumberColumn("G+A/90", format="%.2f"),
    },
    hide_index=True,
    width="stretch"
)
info_card("Tournament Scope",
    "Includes only **World Cup 2026** match statistics. All 1,248 players across 48 nations "
    "are in the underlying table — no club-season data, no synthetic prediction-system entries. "
    "Players who did not play a single WC26 minute appear with 0 goals/assists and MP=0.")
st.divider()

# ============================================================================
# PLAYER SPOTLIGHT
# ============================================================================
spotlights = players[players["goal_contribution"] > 0]["spotlight_name"].tolist()
sel = st.selectbox("🔎 Spotlight a Tournament Player", ["None"] + spotlights)
if sel != "None":
    pstat = players.loc[players["spotlight_name"] == sel]
    if not pstat.empty:
        p = pstat.iloc[0]
        x, y, z, w = st.columns(4)
        with x:
            st.metric("Goals", f"{int(p['wc26_goals'])}")
        with y:
            st.metric("Assists", f"{int(p['wc26_assists'])}")
        with z:
            st.metric("G+A", f"{int(p['goal_contribution'])}")
        with w:
            st.metric("Minutes", f"{int(p['minutes_played'])}")
        info_card("Squad Context",
            f"Player: **{p['player_name']}** · Nation: **{p.get('team_name', 'N/A')}** ({p.get('fifa_code', '')}) · "
            f"Position: **{p.get('position', 'N/A')}** · Club: **{p.get('club_team', 'N/A')}** · "
            f"Matches played: **{int(p.get('matches_played', 0))}** · "
            f"Market value: **€{int(p.get('market_value_eur', 0)):,}** · Caps: **{int(p.get('caps', 0))}**")
    else:
        st.info("No WC26 tournament stats available for the selected player.")

st.divider()

# ============================================================================
# APPROACH NOTE
# ============================================================================
info_card(
    "WC 2026 Player Analytics",
    "All player numbers above are **real World Cup 2026 tournament stats**, derived from the open "
    "Kaggle dataset `mominullptr/fifa-world-cup-2026-dataset` (CC0 public domain, verified against "
    "sofascore.com). 1,248 players across 48 nations are covered. Club season statistics are excluded "
    "to avoid mixing 2024–25 historical data with the actual tournament."
)
