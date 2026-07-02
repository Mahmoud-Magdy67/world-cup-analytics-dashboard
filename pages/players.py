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
from data.bigquery_enhanced import get_players, get_player_tournament_stats

# Apply CSS
load_custom_css()

# Header
page_header(
    "Player Analytics",
    "Individual performance intelligence across the 48 World Cup 2026 final squads.",
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
with st.spinner("Loading player metrics..."):
    df = get_players()
    tournament_stats = get_player_tournament_stats()

if df.empty:
    st.error("Failed to load player data from BigQuery.")
    st.stop()

if tournament_stats.empty:
    st.error("No World Cup 2026 tournament player stats available yet.")
    st.stop()

# Merge club context, keeping tournament stats as source of truth
merged_tournament = tournament_stats.merge(
    df[['player_name', 'nation_code', 'position', 'club_team', 'league', 'minutes']].drop_duplicates('player_name'),
    on='player_name',
    how='left'
)

# Ensure metadata is never missing for display
for col in ['nation_code', 'position', 'club_team', 'league']:
    if col not in merged_tournament.columns:
        merged_tournament[col] = ''
    merged_tournament[col] = merged_tournament[col].fillna('').replace('nan', '', regex=False)
if 'minutes' not in merged_tournament.columns:
    merged_tournament['minutes'] = 0
merged_tournament['minutes'] = pd.to_numeric(merged_tournament['minutes'], errors='coerce').fillna(0).astype(int)

merged_tournament['goal_contribution'] = merged_tournament['wc26_goals'] + merged_tournament['wc26_assists']
merged_tournament['rank'] = range(1, len(merged_tournament) + 1)
merged_tournament = merged_tournament.sort_values(['wc26_goals', 'wc26_assists'], ascending=[False, False]).reset_index(drop=True)

top10 = merged_tournament.head(10).copy()

# ============================================================================
# HERO METRICS
# ============================================================================
col1, col2, col3, col4, col5 = st.columns(5)
with col1:
    st.metric("Players Tracked", f"{len(tournament_stats)}")
with col2:
    st.metric("WC26 Goals", f"{int(tournament_stats['wc26_goals'].sum())}")
with col3:
    st.metric("WC26 Assists", f"{int(tournament_stats['wc26_assists'].sum())}")
with col4:
    st.metric("Goal Contributions", f"{int(merged_tournament['goal_contribution'].sum())}")
with col5:
    st.metric("Active Nations", f"{merged_tournament['nation_code'].replace('', pd.NA).dropna().nunique()}")

# ============================================================================
# WORLD CUP THEME HERO BANNER
# ============================================================================
st.markdown(
    f"<div class='wc-hero'><b>🏆 World Cup 2026 Tournament Leaders</b><br/>"
    "Actual match statistics from the tournament — not club season data.</div>",
    unsafe_allow_html=True
)
st.markdown("")

# ============================================================================
# TOP SCORERS & ASSISTS
# ============================================================================
c1, c2 = st.columns(2)
with c1:
    st.markdown("<h3 style='color: #C8102E; font-family: Bebas Neue; margin-top:15px;'>⚽ Top Scorers</h3>", unsafe_allow_html=True)
    fig_g = px.bar(
        top10.sort_values('wc26_goals', ascending=True),
        x='wc26_goals', y='player_name',
        orientation='h',
        color='position' if 'position' in top10.columns else None,
        color_discrete_sequence=FWC26_POSITION_COLORS,
        labels={'wc26_goals': 'Goals', 'player_name': 'Player'},
        text='wc26_goals'
    )
    fig_g.update_layout(
        paper_bgcolor=FWC26_WHITE, plot_bgcolor=FWC26_WHITE,
        font=dict(color=FWC26_TEXT, family='Noto Sans'),
        xaxis=dict(title="", showgrid=True, gridcolor=FWC26_SILVER),
        yaxis=dict(title=""),
        showlegend=False, height=420, margin=dict(l=120, r=20, t=30, b=40)
    )
    fig_g.update_traces(textposition='outside', marker_line_color=FWC26_WHITE, marker_line_width=1)
    st.plotly_chart(fig_g, width='stretch')

with c2:
    st.markdown("<h3 style='color: #C8102E; font-family: Bebas Neue; margin-top:15px;'>🅰️ Top Assist Providers</h3>", unsafe_allow_html=True)
    top10a = top10[top10['wc26_assists'] > 0].sort_values('wc26_assists', ascending=False).head(10)
    if hasattr(top10a, 'empty') and not top10a.empty:
        fig_a = px.bar(
            top10a.sort_values('wc26_assists', ascending=True),
            x='wc26_assists', y='player_name',
            orientation='h',
            color='position' if 'position' in top10a.columns else None,
            color_discrete_sequence=FWC26_POSITION_COLORS,
            labels={'wc26_assists': 'Assists', 'player_name': 'Player'},
            text='wc26_assists'
        )
        fig_a.update_layout(
            paper_bgcolor=FWC26_WHITE, plot_bgcolor=FWC26_WHITE,
            font=dict(color=FWC26_TEXT, family='Noto Sans'),
            xaxis=dict(title="", showgrid=True, gridcolor=FWC26_SILVER),
            yaxis=dict(title=""),
            showlegend=False, height=420, margin=dict(l=120, r=20, t=30, b=40)
        )
        fig_a.update_traces(textposition='outside', marker_line_color=FWC26_WHITE, marker_line_width=1)
        st.plotly_chart(fig_a, width='stretch')
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
    name='Goals', x=top10['player_name'], y=top10['wc26_goals'],
    marker_color=FWC26_RED, text=top10['wc26_goals'], textposition='inside'
))
fig_top.add_trace(go.Bar(
    name='Assists', x=top10['player_name'], y=top10['wc26_assists'],
    marker_color=FWC26_SILVER, text=top10['wc26_assists'], textposition='inside'
))
fig_top.update_layout(
    barmode='stack',
    paper_bgcolor=FWC26_WHITE, plot_bgcolor=FWC26_WHITE,
    font=dict(color=FWC26_TEXT, family='Noto Sans'),
    title=dict(text="Top 10 Tournament Contributors", font=dict(family='Bebas Neue', size=20, color=FWC26_RED)),
    xaxis_tickangle=-35, xaxis=dict(title="", showgrid=False),
    yaxis=dict(title="Goal Contributions", showgrid=True, gridcolor=FWC26_SILVER),
    legend=dict(orientation="h", yanchor="bottom", y=1.04, xanchor="center", x=0.5),
    height=420, margin=dict(t=80, b=80)
)
st.plotly_chart(fig_top, width='stretch')
st.divider()

# ============================================================================
# PLAYER SPOTLIGHT INSIGHT
# ============================================================================
if not top10.empty:
    star = top10.iloc[0]
    nation = star.get('nation_code', 'N/A')
    position = star.get('position', 'N/A')
    st.info(
        f"**Tournament MVP Signal:** {star['player_name']} leads in **{int(star['wc26_goals'])} goal(s)** "
        f"and **{int(star['wc26_assists'])} assist(s)** for a **{int(star['goal_contribution'])}-contribution** tournament tally. "
        f"Nation: **{nation}** · Position: **{position}**."
    )
    st.divider()

# ============================================================================
# FULL TOURNAMENT PLAYER RANKINGS
# ============================================================================
st.markdown(
    "<h3 style='color: #C8102E; font-family: Bebas Neue; margin-top:15px;'>📊 Full Tournament Player Rankings</h3>",
    unsafe_allow_html=True
)

rank_cols = ['player_name', 'nation_code', 'position', 'wc26_goals', 'wc26_assists']
avail = [c for c in rank_cols if c in merged_tournament.columns]
ranked = merged_tournament[avail].copy().fillna('—').replace('', '—', regex=False)

# Ensure required columns exist with safe display values
for required in ['nation_code', 'position']:
    if required not in ranked.columns:
        ranked[required] = '—'
    else:
        ranked[required] = ranked[required].fillna('—').replace('', '—', regex=False)

ranked['rank'] = range(1, len(ranked) + 1)
ranked = ranked[['rank'] + rank_cols]

st.dataframe(
    ranked.head(50),
    column_config={
        "rank": st.column_config.NumberColumn("#", format="%d"),
        "player_name": st.column_config.TextColumn("Player"),
        "nation_code": st.column_config.TextColumn("Nation"),
        "position": st.column_config.TextColumn("Position"),
        "wc26_goals": st.column_config.NumberColumn("WC26 Goals", format="%d"),
        "wc26_assists": st.column_config.NumberColumn("WC26 Assists", format="%d"),
    },
    hide_index=True,
    width='stretch'
)

info_card("Tournament Scope",
    "This table includes only **World Cup 2026** match statistics. "
    "Club season data is intentionally excluded to avoid mixing seasons/tournaments.")
st.divider()

# ============================================================================
# TOURNAMENT INSIGHTS
# ============================================================================
st.markdown("<h3 style='color: #C8102E; font-family: Bebas Neue; margin-top:15px;'>🧠 Tournament Insights</h3>", unsafe_allow_html=True)

only_goals = merged_tournament[merged_tournament['wc26_goals'] > 0]
only_assists = merged_tournament[merged_tournament['wc26_assists'] > 0]

max_g = only_goals['wc26_goals'].max() if not only_goals.empty else 0
max_a = only_assists['wc26_assists'].max() if not only_assists.empty else 0

if not only_goals.empty:
    golden_boot = only_goals[only_goals['wc26_goals'] == max_g].iloc[0]
else:
    golden_boot = merged_tournament.iloc[0]

if not only_assists.empty:
    playmaker = only_assists[only_assists['wc26_assists'] == max_a].iloc[0]
else:
    playmaker = merged_tournament.iloc[0]

dual = merged_tournament[(merged_tournament['wc26_goals'] >= 3) & (merged_tournament['wc26_assists'] >= 2)]

d1, d2, d3 = st.columns(3)
with d1:
    st.metric("Golden Boot", golden_boot['player_name'], f"{int(max_g)} goals")
with d2:
    st.metric("Playmaker King", playmaker['player_name'], f"{int(max_a)} assists")
with d3:
    st.metric("Dual Threats", f"{len(dual)} players", "3G+ / 2A+")

insight_parts = []
if len(dual) > 0:
    insight_parts.append(
        f"Dual threats in this tournament are rare: **{len(dual)}** players recorded both 3+ goals and 2+ assists, "
        f"including {', '.join(dual['player_name'].head(3).tolist())}."
    )

nation_by_nation = merged_tournament[merged_tournament['nation_code'].ne('')].groupby('nation_code').agg(
    tgoals=('wc26_goals', 'sum'),
    tassists=('wc26_assists', 'sum')
).reset_index().sort_values('tgoals', ascending=False)

if not nation_by_nation.empty:
    top_nation = nation_by_nation.iloc[0]['nation_code']
    top_n_g = int(nation_by_nation.iloc[0]['tgoals'])
    top_n_a = int(nation_by_nation.iloc[0]['tassists'])
    insight_parts.append(
        f"Nation-level attack leader is **{top_nation}** with **{top_n_g} goal(s)** and **{top_n_a} assists** in the tournament."
    )

info_card("Tournament Insight", " ".join(insight_parts) if insight_parts else "Tournament data is still building.")

st.divider()

# ============================================================================
# NATION CONTRIBUTION MAP: GOALS & ASSISTS
# ============================================================================
if not nation_by_nation.empty:
    st.markdown(
        "<h3 style='color: #C8102E; font-family: Bebas Neue; margin-top:15px;'>🏳️ Nation Contribution Map: Goals & Assists</h3>",
        unsafe_allow_html=True
    )
    col_n1, col_n2 = st.columns(2)

    with col_n1:
        fig_ng = px.bar(
            nation_by_nation.sort_values('tgoals', ascending=True).head(15),
            x='tgoals', y='nation_code',
            orientation='h',
            color='tgoals',
            color_continuous_scale=[FWC26_WHITE, FWC26_RED],
            labels={'tgoals': 'Goals', 'nation_code': 'Nation'},
            text='tgoals'
        )
        fig_ng.update_layout(
            paper_bgcolor=FWC26_WHITE, plot_bgcolor=FWC26_WHITE,
            font=dict(color=FWC26_TEXT, family='Noto Sans'),
            xaxis=dict(title="", showgrid=True, gridcolor=FWC26_SILVER),
            yaxis=dict(title=""),
            coloraxis_showscale=False,
            height=380, margin=dict(l=60, r=20, t=30, b=40)
        )
        fig_ng.update_traces(textposition='outside')
        st.plotly_chart(fig_ng, width='stretch')

    with col_n2:
        fig_na = px.bar(
            nation_by_nation.sort_values('tassists', ascending=True).head(15),
            x='tassists', y='nation_code',
            orientation='h',
            color='tassists',
            color_continuous_scale=[FWC26_WHITE, FWC26_SILVER],
            labels={'tassists': 'Assists', 'nation_code': 'Nation'},
            text='tassists'
        )
        fig_na.update_layout(
            paper_bgcolor=FWC26_WHITE, plot_bgcolor=FWC26_WHITE,
            font=dict(color=FWC26_TEXT, family='Noto Sans'),
            xaxis=dict(title="", showgrid=True, gridcolor=FWC26_SILVER),
            yaxis=dict(title=""),
            coloraxis_showscale=False,
            height=380, margin=dict(l=60, r=20, t=30, b=40)
        )
        fig_na.update_traces(textposition='outside')
        st.plotly_chart(fig_na, width='stretch')

    st.divider()

# ============================================================================
# RADAR PROFILE: TOP 8 PLAYERS
# ============================================================================
top8 = merged_tournament.head(8).copy()
fig_radar = go.Figure()
for _, row in top8.iterrows():
    fig_radar.add_trace(go.Scatterpolar(
        r=[
            row['wc26_goals'],
            row['wc26_assists'],
            row['goal_contribution'],
            max(row.get('minutes', 0), 0) / 90,
            row.get('wc26_goals', 0) * 3,
            row.get('wc26_assists', 0) * 3,
        ],
        theta=['Goals', 'Assists', 'Contributions', 'Per-90 Goals*', 'Efficiency*', 'Create*'],
        fill='toself',
        name=f"{row['player_name']}"
    ))

fig_radar.update_layout(
    polar=dict(radialaxis=dict(visible=True, gridcolor=FWC26_SILVER)),
    paper_bgcolor=FWC26_WHITE,
    font=dict(color=FWC26_TEXT, family='Noto Sans'),
    title=dict(text="Top 8 Player Profiles", font=dict(family='Bebas Neue', size=20, color=FWC26_RED)),
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5),
    height=520,
    margin=dict(t=70, b=40)
)
st.plotly_chart(fig_radar, width='stretch')
st.caption("*Derived metrics from tournament goals/assists for profile visualization only.")

# ============================================================================
# PLAYER SPOTLIGHT
# ============================================================================
sel = st.selectbox("🔎 Spotlight a Tournament Player", ["None"] + merged_tournament['player_name'].tolist())
if sel != "None":
    pstat = merged_tournament[merged_tournament['player_name'] == sel]
    if not pstat.empty:
        p = pstat.iloc[0]
        x, y, z = st.columns(3)
        with x:
            st.metric("Goals", f"{int(p['wc26_goals'])}")
        with y:
            st.metric("Assists", f"{int(p['wc26_assists'])}")
        with z:
            st.metric("Contributions", f"{int(p['goal_contribution'])}")
        ctx_row = df[df['player_name'] == sel]
        if not ctx_row.empty:
            ctx = ctx_row.iloc[0]
            info_card("Squad Context",
                f"Position: **{ctx.get('position', 'N/A')}** · Nation: **{ctx.get('nation_code', 'N/A')}** · "
                f"Club: **{ctx.get('club_team', 'N/A')}**")
    else:
        st.info("No tournament stats available for the selected player yet.")

st.divider()

# ============================================================================
# APPROACH NOTE
# ============================================================================
info_card(
    "WC 2026 Player Analytics",
    "All player numbers above are **tournament-only** from FIFA World Cup 2026 matches. "
    "Club season statistics are excluded to avoid mixing 2024–25 historical data with the current tournament. "
    "Data source: ESPN FIFA World Cup statistics API + BigQuery cache (`raw_wc26_player_stats_espn`)."
)
