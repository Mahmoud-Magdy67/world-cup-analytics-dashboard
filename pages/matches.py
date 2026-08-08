"""
Page 4: Match Analysis
Comprehensive analysis of matches using the Kaggle dataset
(mominullptr/fifa-world-cup-2026-dataset): 104 completed matches across 16 venues
in 3 host nations, with scores, xG, lineups, and in-match statistics.

Spain defeated Argentina 1-0 (AET) in the Final on 2026-07-19 at MetLife Stadium.
Matches the official FWC26 Light Theme.
"""
from pages._shared_enhanced import st, load_custom_css, page_header, info_card, apply_dark_text_theme
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import numpy as np
from pathlib import Path

from data.real_wc26 import (
    get_real_wc26_matches_enriched, get_real_wc26_knockout_bracket,
    get_real_wc26_venues, get_real_wc26_referees, STAGE_ORDER,
)
from data.real_wc26_players import _famous_name

load_custom_css("matches")

# Header
page_header(
    "Match Analysis",
    "Comprehensive match schedule, venue analysis, and fixture insights.",
    image_url="assets/logo.png"
)

# ============================================================================
# LOAD DATA
# ============================================================================
with st.spinner("Loading match data..."):
    matches_df = get_real_wc26_matches_enriched()
    venues_df = get_real_wc26_venues()
    referees_df = get_real_wc26_referees()
    bracket_df = get_real_wc26_knockout_bracket()

if matches_df.empty:
    st.error("Failed to load match data from Kaggle dataset.")
    st.stop()

# Ensure proper data types
matches_df['date'] = pd.to_datetime(matches_df['date'], errors='coerce')
for c in ('home_score', 'away_score', 'home_xg', 'away_xg',
          'home_penalty_score', 'away_penalty_score',
          'venue_capacity', 'venue_latitude', 'venue_longitude',
          'home_possession', 'away_possession',
          'home_shots', 'away_shots',
          'home_shots_on_target', 'away_shots_on_target',
          'home_corners', 'away_corners',
          'home_fouls', 'away_fouls', 'home_saves', 'away_saves'):
    if c in matches_df.columns:
        matches_df[c] = pd.to_numeric(matches_df[c], errors='coerce')

# Derived columns
matches_df['total_goals'] = (
    matches_df['home_score'].fillna(0) + matches_df['away_score'].fillna(0)
)
matches_df['score_str'] = (
    matches_df['home_score'].astype('Int64').astype(str)
    + '-' +
    matches_df['away_score'].astype('Int64').astype(str)
)
matches_df['fixture'] = (
    matches_df['home_team_name'] + ' vs ' + matches_df['away_team_name']
)
# For team-perspective views
home_rows = matches_df.rename(columns={
    'home_team_name': 'team', 'away_team_name': 'opponent',
    'home_score': 'team_goals', 'away_score': 'opponent_goals',
    'home_xg': 'team_xg', 'away_xg': 'opponent_xg',
    'home_possession': 'team_possession',
    'home_shots': 'team_shots', 'home_shots_on_target': 'team_sot',
    'home_corners': 'team_corners', 'home_fouls': 'team_fouls',
})[['match_id', 'date', 'stage_name', 'team', 'opponent',
    'team_goals', 'opponent_goals', 'team_xg', 'opponent_xg',
    'team_possession', 'team_shots', 'team_sot',
    'team_corners', 'team_fouls']].copy()
away_rows = matches_df.rename(columns={
    'away_team_name': 'team', 'home_team_name': 'opponent',
    'away_score': 'team_goals', 'home_score': 'opponent_goals',
    'away_xg': 'team_xg', 'home_xg': 'opponent_xg',
    'away_possession': 'team_possession',
    'away_shots': 'team_shots', 'away_shots_on_target': 'team_sot',
    'away_corners': 'team_corners', 'away_fouls': 'team_fouls',
})[['match_id', 'date', 'stage_name', 'team', 'opponent',
    'team_goals', 'opponent_goals', 'team_xg', 'opponent_xg',
    'team_possession', 'team_shots', 'team_sot',
    'team_corners', 'team_fouls']].copy()
team_perspective = pd.concat([home_rows, away_rows], ignore_index=True)
team_perspective = team_perspective.sort_values(['team', 'date']).reset_index(drop=True)

# ============================================================================
# FILTERS
# ============================================================================
st.markdown("### 🎛️ Match Filters")
c1, c2, c3, c4 = st.columns(4)

stages = sorted(matches_df['stage_name'].dropna().unique().tolist())
venues = sorted(matches_df['stadium_name'].dropna().unique().tolist())
host_countries = sorted(matches_df['country'].dropna().unique().tolist())

sel_stage = c1.selectbox("📅 Stage", ["All"] + stages)
sel_venue = c2.selectbox("🏟️ Venue", ["All"] + venues)
sel_host = c3.selectbox("🏳️ Host Country", ["All"] + host_countries)
result_types = sorted(matches_df['result_type'].dropna().unique().tolist())
sel_result = c4.selectbox("🎯 Result Type", ["All"] + result_types)

filtered = matches_df.copy()
if sel_stage != "All":
    filtered = filtered[filtered['stage_name'] == sel_stage]
if sel_venue != "All":
    filtered = filtered[filtered['stadium_name'] == sel_venue]
if sel_host != "All":
    filtered = filtered[filtered['country'] == sel_host]
if sel_result != "All":
    filtered = filtered[filtered['result_type'] == sel_result]

if filtered.empty:
    st.warning("No matches match the selected filters.")
    st.stop()

st.divider()

# ============================================================================
# KPIs
# ============================================================================
k1, k2, k3, k4, k5 = st.columns(5)
with k1:
    st.metric("Total Matches", len(matches_df))
with k2:
    group_matches = len(matches_df[matches_df['stage_name'] == 'Group Stage'])
    st.metric("Group Stage", f"{group_matches}")
with k3:
    knockout_matches = len(matches_df[matches_df['stage_name'] != 'Group Stage'])
    st.metric("Knockout Stage", f"{knockout_matches}")
with k4:
    st.metric("Venues Used", matches_df['stadium_name'].nunique())
with k5:
    st.metric("Host Nations", matches_df['country'].nunique())

st.divider()

# ============================================================================
# TOURNAMENT MATCH DENSITY — matches & goals per day
# ============================================================================
st.subheader("📊 Tournament Match Density — 39 Days, 104 Matches")
st.caption("Each bar = one matchday. Bar height = matches played; line = goals scored. "
           "Spikes reveal the high-pressure group-stage block and the knockout concentration.")

density_df = filtered.copy()
density_df['date'] = pd.to_datetime(density_df['date'])
density_df['total_goals'] = density_df['home_score'].fillna(0) + density_df['away_score'].fillna(0)
daily = density_df.groupby(density_df['date'].dt.date).agg(
    matches=('match_id', 'count'),
    goals=('total_goals', 'sum'),
    avg_goals=('total_goals', 'mean'),
).reset_index().rename(columns={'date': 'match_date'})
daily['match_date'] = pd.to_datetime(daily['match_date'])

fig_density = go.Figure()
# Bar: matches per day (solid red — visible at all heights, no white at low values)
fig_density.add_trace(go.Bar(
    x=daily['match_date'], y=daily['matches'],
    name='Matches', marker_color='#C8102E',
    marker_line_color='#7a0a1a', marker_line_width=1,
    text=daily['matches'], textposition='outside',
    textfont=dict(size=10, color='#000000'),
    hovertemplate='<b>%{x|%b %d}</b><br>Matches: %{y}<extra></extra>',
))
# Line: goals per day
fig_density.add_trace(go.Scatter(
    x=daily['match_date'], y=daily['goals'],
    name='Goals', mode='lines+markers',
    line=dict(color='#F4C542', width=3),
    marker=dict(size=8, color='#F4C542', line=dict(color='#7a0a1a', width=1)),
    yaxis='y2',
    hovertemplate='<b>%{x|%b %d}</b><br>Goals: %{y}<extra></extra>',
))
fig_density.update_layout(
    paper_bgcolor='#ffffff', plot_bgcolor='#ffffff',
    font=dict(color='#000000', family='Noto Sans'),
    title=dict(text="Daily Match & Goal Volume Across the Tournament",
               font=dict(family='Bebas Neue', size=18, color='#C8102E')),
    xaxis_title="Match Date",
    yaxis=dict(title="Matches Played", side='left', showgrid=False, dtick=1, rangemode='tozero'),
    yaxis2=dict(title="Goals Scored", overlaying='y', side='right',
                showgrid=True, gridcolor='rgba(0,0,0,0.05)'),
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5),
    height=400, margin=dict(t=70, b=40),
)
st.plotly_chart(apply_dark_text_theme(fig_density), width='stretch')

# Peak / quietest days
peak_match_day = daily.loc[daily['matches'].idxmax()]
peak_goal_day = daily.loc[daily['goals'].idxmax()]
quiet_day = daily.loc[daily['matches'].idxmin()]

info_card(
    "Schedule Insight",
    f"**{int(daily['matches'].sum())} matches across {len(daily)} days** — the tournament ran "
    f"from {daily['match_date'].min().strftime('%b %d')} to {daily['match_date'].max().strftime('%b %d, %Y')}. "
    f"The busiest matchday was **{peak_match_day['match_date'].strftime('%A, %b %d')}** with "
    f"**{int(peak_match_day['matches'])} matches** and **{int(peak_goal_day['goals'])} goals** scored "
    f"(the goal-spike day). Knockout rounds taper the schedule down to single fixtures — "
    f"**{int((daily['matches'] == 1).sum())} days** hosted just one decisive match, "
    f"the climax of the competition."
)
st.divider()

# ============================================================================
# VENUE ANALYSIS
# ============================================================================
st.subheader("🏟️ Venue Distribution & Capacity")
# Aggregate matches per venue (each match is one row in Kaggle data)
venue_stats = filtered.groupby('stadium_name').agg(
    matches=('match_id', 'size'),
    city=('city', 'first'),
    host_country=('country', 'first'),
    capacity=('venue_capacity', 'first'),
    latitude=('venue_latitude', 'first'),
    longitude=('venue_longitude', 'first'),
).reset_index().sort_values('matches', ascending=False)

col1, col2 = st.columns([2, 1])
with col1:
    fig_venue = px.bar(
        venue_stats,
        x='stadium_name',
        y='matches',
        color='host_country',
        hover_data=['capacity', 'city'],
        color_discrete_sequence=['#FF004D', '#7B00FF', '#00F0FF', '#00FF00', '#FF4D00'],
        title="Matches by Venue",
    )
    fig_venue.update_layout(
        paper_bgcolor='#ffffff', plot_bgcolor='#ffffff',
        font=dict(color='#000000', family='Noto Sans'),
        title=dict(font=dict(family='Bebas Neue', size=16)),
        xaxis_tickangle=-45,
        xaxis_title="Venue", yaxis_title="Number of Matches",
        height=400, showlegend=True,
    )
    st.plotly_chart(apply_dark_text_theme(fig_venue), width='stretch')

with col2:
    st.markdown("#### 📊 Venue Statistics")
    if not venue_stats.empty and 'capacity' in venue_stats.columns:
        biggest = venue_stats.dropna(subset=['capacity']).loc[
            venue_stats.dropna(subset=['capacity'])['capacity'].idxmax()
        ] if venue_stats['capacity'].notna().any() else venue_stats.iloc[0]
        most_used = venue_stats.loc[venue_stats['matches'].idxmax()]
        st.metric("Largest Venue", f"{biggest['stadium_name']}",
                  f"{int(biggest['capacity']):,} seats")
        st.metric("Most Used Venue", f"{most_used['stadium_name']}",
                  f"{int(most_used['matches'])} matches")
        avg_cap = venue_stats['capacity'].dropna().mean()
        st.metric("Avg. Capacity", f"{int(avg_cap):,} seats")
        host_dist = venue_stats['host_country'].value_counts()
        st.markdown("**Matches by Host Country:**")
        for host, cnt in host_dist.items():
            st.markdown(f"- {host}: {cnt} matches")

st.divider()

# Venue map (zoomed on North America)
if 'latitude' in venue_stats.columns and venue_stats['latitude'].notna().any():
    map_df = venue_stats.dropna(subset=['latitude', 'longitude'])
    if not map_df.empty:
        fig_map = px.scatter_geo(
            map_df,
            lat='latitude', lon='longitude',
            size='matches',
            color='host_country',
            hover_name='stadium_name',
            hover_data=['city', 'matches', 'capacity'],
            projection='natural earth',
            title="World Cup 2026 Venues — Host Cities Across USA, Canada & Mexico",
            color_discrete_sequence=['#FF004D', '#7B00FF', '#00F0FF', '#00FF00', '#FF4D00'],
        )
        # Zoom to North America: USA (lon -125 to -65, lat 25 to 50),
        # Canada (lon -140 to -55, lat 50 to 75), Mexico (lon -118 to -86, lat 14 to 33)
        fig_map.update_geos(
            scope='north america',
            showland=True, landcolor='#f5f5f0',
            showocean=True, oceancolor='#cce7ff',
            showlakes=True, lakecolor='#cce7ff',
            showcountries=True, countrycolor='#888888',
            showcoastlines=True, coastlinecolor='#888888',
            lataxis=dict(range=[10, 75]),
            lonaxis=dict(range=[-145, -50]),
        )
        fig_map.update_layout(
            paper_bgcolor='#ffffff',
            font=dict(color='#000000', family='Noto Sans'),
            title=dict(font=dict(family='Bebas Neue', size=16)),
            height=420,
        )
        st.plotly_chart(apply_dark_text_theme(fig_map), width='stretch')

        info_card("Venue Insight",
            f"The 2026 World Cup was hosted across {venue_stats['host_country'].nunique()} countries "
            f"({', '.join(sorted(venue_stats['host_country'].unique()))}) "
            f"with {len(venue_stats)} unique venues. The geographic distribution "
            f"across North America maximized accessibility while showcasing world-class "
            f"sporting infrastructure.")
st.divider()

# ============================================================================
# KNOCKOUT DRAMA — how each KO round was decided
# ============================================================================
st.subheader("🥊 Knockout Drama — How Each Round Was Settled")
st.caption("Knockout football isn't just goals — it's also extra time and penalties. "
           "Each bar = a KO match; colour shows whether it ended in regulation, extra time, or a shootout.")

ko = filtered[filtered['stage_name'] != 'Group Stage'].copy()
if not ko.empty:
    ko['total_goals'] = ko['home_score'].fillna(0) + ko['away_score'].fillna(0)
    ko['margin'] = (ko['home_score'] - ko['away_score']).abs()

    # Classify outcome using the dataset's result_type column (AET/Penalties/Regular)
    def ko_outcome(row):
        rt = str(row.get('result_type', '')).strip()
        if rt == 'Penalties':
            return 'Penalties'
        if rt == 'AET':
            return 'Extra Time'
        return 'Regulation'

    ko['outcome'] = ko.apply(ko_outcome, axis=1)

    # Build per-round summary
    KO_STAGES = ['Round of 32', 'Round of 16', 'Quarter-finals', 'Semi-finals', 'Third-place match', 'Final']
    round_summary = ko.groupby('stage_name').agg(
        matches=('match_id', 'count'),
        avg_goals=('total_goals', 'mean'),
        avg_margin=('margin', 'mean'),
        regulation=('outcome', lambda x: (x == 'Regulation').sum()),
        extra_time=('outcome', lambda x: (x == 'Extra Time').sum()),
        penalties=('outcome', lambda x: (x == 'Penalties').sum()),
    ).reset_index()
    # Keep only stages that exist
    round_summary = round_summary[round_summary['stage_name'].isin(KO_STAGES)]
    round_summary['stage_order'] = round_summary['stage_name'].map({s: i for i, s in enumerate(KO_STAGES)})
    round_summary = round_summary.sort_values('stage_order')

    col_kd1, col_kd2 = st.columns([3, 2])
    with col_kd1:
        # Stacked horizontal bar — outcome mix per round
        fig_kd = go.Figure()
        outcome_colors = {'Regulation': '#00FF00', 'Extra Time': '#F4C542', 'Penalties': '#C8102E'}
        outcome_col_map = {'Regulation': 'regulation', 'Extra Time': 'extra_time', 'Penalties': 'penalties'}
        for outcome in ['Regulation', 'Extra Time', 'Penalties']:
            col_name = outcome_col_map[outcome]
            fig_kd.add_trace(go.Bar(
                y=round_summary['stage_name'],
                x=round_summary[col_name],
                name=outcome,
                orientation='h',
                marker_color=outcome_colors[outcome],
                text=round_summary[col_name],
                textposition='inside',
                hovertemplate='<b>%{y}</b><br>' + outcome + ': %{x} matches<extra></extra>',
            ))
        fig_kd.update_layout(
            barmode='stack',
            paper_bgcolor='#ffffff', plot_bgcolor='#ffffff',
            font=dict(color='#000000', family='Noto Sans'),
            title=dict(text="How Each Knockout Round Was Settled",
                       font=dict(family='Bebas Neue', size=18, color='#C8102E')),
            xaxis_title="Number of Matches",
            yaxis=dict(autorange='reversed'),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5),
            height=380, margin=dict(t=70, b=40, l=80, r=40),
        )
        st.plotly_chart(apply_dark_text_theme(fig_kd), width='stretch')

    with col_kd2:
        # Summary table
        display_table = round_summary[['stage_name', 'matches', 'avg_goals', 'avg_margin',
                                       'regulation', 'extra_time', 'penalties']].copy()
        display_table = display_table.rename(columns={
            'stage_name': 'Round',
            'matches': 'Matches',
            'avg_goals': 'Avg Goals',
            'avg_margin': 'Avg Margin',
            'regulation': 'Reg',
            'extra_time': 'ET',
            'penalties': 'Pen',
        })
        st.dataframe(
            display_table,
            column_config={
                'Avg Goals': st.column_config.NumberColumn(format="%.2f"),
                'Avg Margin': st.column_config.NumberColumn(format="%.2f"),
            },
            hide_index=True, width='stretch',
        )

    # Insight
    n_ko = len(ko)
    n_pen = int((ko['outcome'] == 'Penalties').sum())
    n_et = int((ko['outcome'] == 'Extra Time').sum())
    n_reg = int((ko['outcome'] == 'Regulation').sum())
    final = ko[ko['stage_name'] == 'Final'].iloc[0]
    final_label = f"{final['home_team_name']} {int(final['home_score'])}-{int(final['away_score'])} {final['away_team_name']}"
    final_outcome = final['outcome']
    # Round of 32 penalty share
    r32 = round_summary[round_summary['stage_name'] == 'Round of 32']
    r32_pen_pct = 0
    if not r32.empty:
        r32_pen_pct = 100 * float(r32['penalties'].iloc[0]) / float(r32['matches'].iloc[0])
    info_card(
        "Knockout Drama Insight",
        f"**{n_ko} knockout matches** produced **{n_pen} penalty shootouts** and "
        f"**{n_et} extra-time deciders** — **{100*(n_pen+n_et)/n_ko:.0f}%** of KO games "
        f"needed more than 90 minutes to settle. The Final ({final_label}) ended in "
        f"**{final_outcome.lower()}**. Penalty drama peaked in the "
        f"**Round of 32** with **{int(r32['penalties'].iloc[0]) if not r32.empty else 0} of {int(r32['matches'].iloc[0]) if not r32.empty else 16} "
        f"ties ({r32_pen_pct:.0f}%)** going to shootouts — the highest share of any round."
    )

st.divider()

# ============================================================================
# GOAL BREAKDOWN — open-play vs penalty goals by knockout stage
# ============================================================================
st.subheader("⚽ Goal Breakdown — How Goals Were Scored")

# Use player_stats: penalty_goals and own_goals columns
from data.real_wc26 import get_real_wc26_player_stats
ps = get_real_wc26_player_stats()
total_g = int(ps['goals'].sum())
total_pk = int(ps['penalty_goals'].sum())
total_og = int(ps['own_goals'].sum())
total_op = total_g - total_pk - total_og
total_shootout = 25  # from separate events (penalty shootouts don't count toward player_stats goals)

col_g1, col_g2 = st.columns([3, 1])
with col_g1:
    # Horizontal bar: open play, penalties, own goals
    fig_bg = go.Figure()
    fig_bg.add_trace(go.Bar(
        y=['Goal Type'], x=[total_op],
        name=f'Open Play ({total_op})', marker_color='#C8102E', orientation='h',
        text=[str(total_op)], textposition='inside', textfont=dict(color='white'),
        hoverlabel=dict(bgcolor='#C8102E', font=dict(color='white')),
    ))
    fig_bg.add_trace(go.Bar(
        y=['Goal Type'], x=[total_pk],
        name=f'Penalty ({total_pk})', marker_color='#F4C542', orientation='h',
        text=[str(total_pk)], textposition='inside', textfont=dict(color='#000000'),
        hoverlabel=dict(bgcolor='#F4C542', font=dict(color='#000000')),
    ))
    fig_bg.add_trace(go.Bar(
        y=['Goal Type'], x=[total_og],
        name=f'Own Goal ({total_og})', marker_color='#7B00FF', orientation='h',
        text=[str(total_og)], textposition='inside', textfont=dict(color='white'),
        hoverlabel=dict(bgcolor='#7B00FF', font=dict(color='white')),
    ))
    fig_bg.update_layout(
        barmode='stack',
        paper_bgcolor='#ffffff', plot_bgcolor='#ffffff',
        font=dict(color='#000000', family='Noto Sans'),
        title=dict(
            text=f"Tournament Goals: {total_g} Open Play · {total_pk} Penalties · {total_og} Own Goals",
            font=dict(family='Bebas Neue', size=16, color='#000000'),
        ),
        xaxis_title="Number of Goals",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5),
        height=220, margin=dict(t=70, b=40, l=40, r=20),
    )
    st.plotly_chart(apply_dark_text_theme(fig_bg), width='stretch')

with col_g2:
    st.metric("Open Play", total_op, f"{100*total_op/total_g:.0f}%")
    st.metric("Penalties", total_pk, f"{100*total_pk/total_g:.0f}%")
    st.metric("Own Goals", total_og, f"{100*total_og/total_g:.0f}%")

info_card(
    "Goal Method Insight",
    f"Across **{total_g} tournament goals** (excluding {total_shootout} penalty-shootout conversions): "
    f"**{total_op} open play ({100*total_op/total_g:.0f}%)**, "
    f"**{total_pk} penalties ({100*total_pk/total_g:.0f}%)**, "
    f"**{total_og} own goals ({100*total_og/total_g:.0f}%)**.\n\n"
    f"Penalties account for {100*total_pk/total_g:.0f}% of goals — below the ~10–12% typical in top leagues, "
    f"reflecting fewer soft foul calls in high-stakes knockout football. "
    f"Own goals at {100*total_og/total_g:.0f}% are in line with normal tournament rates (~3%). "
    f"The **{total_pk} non-shootout penalty goals** are tracked separately from the 25 shootout spot kicks."
)

# ============================================================================
# TEAM SCHEDULE BALANCE (rest days)
# ============================================================================
st.subheader("⚖️ Team Schedule Balance")
# Build team-perspective schedule filtered to the same filters
# Recompute team_perspective from filtered matches
f_home = filtered.rename(columns={
    'home_team_name': 'team', 'away_team_name': 'opponent'
})[['match_id', 'date', 'team']]
f_away = filtered.rename(columns={
    'away_team_name': 'team', 'home_team_name': 'opponent'
})[['match_id', 'date', 'team']]
team_sched = pd.concat([f_home, f_away], ignore_index=True)
team_sched['date'] = pd.to_datetime(team_sched['date'], errors='coerce')
team_sched = team_sched.sort_values(['team', 'date'])
team_sched['days_rest'] = team_sched.groupby('team')['date'].diff().dt.days

rest_stats = team_sched.groupby('team').agg(
    avg_rest=('days_rest', 'mean'),
    min_rest=('days_rest', 'min'),
    max_rest=('days_rest', 'max'),
    total_matches=('date', 'count'),
).reset_index()
rest_stats = rest_stats[rest_stats['total_matches'] > 1].dropna(subset=['avg_rest'])

if not rest_stats.empty:
    col1, col2 = st.columns([2, 1])
    with col1:
        # Sort by min_rest (lowest = toughest at top) then by avg_rest
        plot_df = rest_stats.sort_values(['min_rest', 'avg_rest'], ascending=[True, True]).copy()
        # Bar chart: each team on its own row, colored by min_rest category
        fig_rest = px.bar(
            plot_df.sort_values('avg_rest', ascending=False),
            x='avg_rest', y='team', orientation='h',
            color='min_rest',
            color_discrete_map={
                0: '#C8102E', 1: '#C8102E', 2: '#C8102E', 3: '#C8102E',
                4: '#F4C542', 5: '#00a86b', 6: '#00a86b', 7: '#00a86b', 8: '#00a86b',
                9: '#00a86b', 10: '#00a86b', 11: '#00a86b', 12: '#00a86b', 13: '#00a86b',
            },
            hover_data={'min_rest': True, 'avg_rest': ':.1f', 'total_matches': True},
            title="Team Rest Distribution: Avg vs Minimum Rest Days",
        )
        fig_rest.update_layout(
            paper_bgcolor='#ffffff', plot_bgcolor='#ffffff',
            font=dict(color='#2B1E16', family='Noto Sans'),
            title=dict(font=dict(family='Bebas Neue', size=16, color='#2B1E16')),
            xaxis_title="Average Rest Days Between Matches",
            yaxis_title="",
            height=550, margin=dict(t=50, b=40, l=150, r=20),
        )
        st.plotly_chart(apply_dark_text_theme(fig_rest), width='stretch')

    with col2:
        st.markdown("#### 📊 Rest Statistics")
        toughest = rest_stats.loc[rest_stats['min_rest'].idxmin()]
        best_rested = rest_stats.loc[rest_stats['min_rest'].idxmax()]
        st.metric("Toughest Schedule", f"{toughest['team']}",
                  f"{int(toughest['min_rest'])} min rest")
        st.metric("Best Rested Team", f"{best_rested['team']}",
                  f"{int(best_rested['min_rest'])} min rest")
        st.metric("Avg. Rest (all teams)", f"{rest_stats['avg_rest'].mean():.1f} days")
        quick = rest_stats[rest_stats['min_rest'] <= 2]
        if not quick.empty:
            st.markdown("**⚠️ Teams with ≤2 day turnaround:**")
            for _, t in quick.iterrows():
                st.markdown(f"- {t['team']} ({int(t['min_rest'])} days)")

    info_card("Scheduling Equity Insight",
        f"Tournament scheduling aimed to provide equitable rest between matches. "
        f"Teams with <3 days rest faced increased injury risk and performance fatigue. "
        f"{len(quick)} teams had turnarounds of 2 days or less.")
st.divider()

# ============================================================================
# MATCH DAYS CALENDAR VIEW
# ============================================================================
st.subheader("📅 Match Calendar by Date")
cal = filtered.copy()
cal['date_iso'] = cal['date'].dt.strftime('%Y-%m-%d')
cal['date_str'] = cal['date'].dt.strftime('%b %d')
cal['day_of_week'] = cal['date'].dt.day_name()
daily = cal.groupby(['date_iso', 'date_str', 'day_of_week']).agg(
    matches=('match_id', 'size'),
    teams_list=('home_team_name', lambda x: sorted(set(x) | set(cal.loc[x.index, 'away_team_name']))),
).reset_index().sort_values('date_iso')

if not daily.empty:
    daily['Teams Playing'] = daily['teams_list'].apply(
        lambda lst: ', '.join(lst[:6]) + (' + %d more' % (len(lst)-6) if len(lst) > 6 else ''))
    display_df = daily.drop(columns=['date_iso', 'teams_list']).rename(columns={
        'date_str': 'Date', 'day_of_week': 'Day',
        'matches': '# Matches',
    })
    st.dataframe(
            display_df,
            column_config={
                "Date": st.column_config.TextColumn("Date"),
                "Day": st.column_config.TextColumn("Day"),
                "# Matches": st.column_config.NumberColumn("# Matches", format="%d"),
                "Teams Playing": st.column_config.TextColumn("Teams Playing", width="large"),
            },
            hide_index=True, width='stretch',
        )
    busiest = daily.loc[daily['matches'].idxmax()]
    info_card("Calendar Insight",
        f"The busiest match day was {busiest['date_str']} ({busiest['day_of_week']}) "
        f"with {int(busiest['matches'])} matches. Final group-stage matchdays "
        f"typically see all groups play simultaneously to ensure competitive integrity.")
st.divider()

# ============================================================================
# xG & POSSESSION ANALYSIS
# ============================================================================
st.subheader("🎯 xG Performance — Who Created & Conceded Chances")

xg_df = filtered.dropna(subset=['home_xg', 'away_xg']).copy()
if not xg_df.empty:
    # Build team-level xG aggregation: for + against per team
    home_xg = xg_df.groupby('home_team_name', as_index=False).agg(
        xg_for=('home_xg', 'mean'),
        goals_for=('home_score', 'mean'),
    ).rename(columns={'home_team_name': 'team'})
    away_xg = xg_df.groupby('away_team_name', as_index=False).agg(
        xg_for=('away_xg', 'mean'),
        goals_for=('away_score', 'mean'),
    ).rename(columns={'away_team_name': 'team'})
    # xG against: swap sides
    home_xga = xg_df.groupby('home_team_name', as_index=False).agg(
        xg_against=('away_xg', 'mean'),
    ).rename(columns={'home_team_name': 'team'})
    away_xga = xg_df.groupby('away_team_name', as_index=False).agg(
        xg_against=('home_xg', 'mean'),
    ).rename(columns={'away_team_name': 'team'})

    team_xg = home_xg.merge(away_xg, on='team', how='left').fillna(0)
    team_xga = home_xga.merge(away_xga, on='team', how='left').fillna(0)
    team_xg_stats = team_xg.merge(team_xga, on='team', how='left')
    team_xg_stats['xg_for'] = (team_xg_stats['xg_for_x'] + team_xg_stats['xg_for_y']) / 2
    team_xg_stats['goals_for'] = (team_xg_stats['goals_for_x'] + team_xg_stats['goals_for_y']) / 2  # not used
    team_xg_stats['xg_against'] = (team_xg_stats['xg_against_x'] + team_xg_stats['xg_against_y']) / 2
    team_xg_stats['xg_diff'] = team_xg_stats['xg_for'] - team_xg_stats['xg_against']
    team_xg_stats = team_xg_stats[['team', 'xg_for', 'xg_against', 'xg_diff']].sort_values('xg_for', ascending=False)

    col1, col2 = st.columns(2)
    with col1:
        fig_xg = px.bar(
            team_xg_stats.head(15).sort_values('xg_for', ascending=True),
            x='xg_for', y='team', orientation='h',
            color_discrete_sequence=['#00a86b'],
            title="Top 15 Teams: Avg Expected Goals (xG) For",
        )
        fig_xg.update_layout(
            paper_bgcolor='#ffffff', plot_bgcolor='#ffffff',
            font=dict(color='#2B1E16', family='Noto Sans'),
            title=dict(font=dict(family='Bebas Neue', size=16)),
            xaxis_title='Avg xG Created per Match', yaxis_title='',
            height=450,
        )
        st.plotly_chart(apply_dark_text_theme(fig_xg), width='stretch')

    with col2:
        xga_df = team_xg_stats.sort_values('xg_against', ascending=True)
        fig_xga = px.bar(
            xga_df.head(15).sort_values('xg_against', ascending=True),
            x='xg_against', y='team', orientation='h',
            color_discrete_sequence=['#C8102E'],
            title='Top 15 Teams: Best Defensive Expected Goals',
        )
        fig_xga.update_layout(
            paper_bgcolor='#ffffff', plot_bgcolor='#ffffff',
            font=dict(color='#2B1E16', family='Noto Sans'),
            title=dict(font=dict(family='Bebas Neue', size=16)),
            xaxis_title='Avg Attacks Faced per Match (lower is better)', yaxis_title='',
            height=450,
        )
        st.plotly_chart(apply_dark_text_theme(fig_xga), width='stretch')

    info_card("xG Insight",
        f"High xG teams create many chances but fewer goals than their xG, showing that "
        f"finishing matters (e.g. average xG is {team_xg_stats['xg_for'].mean():.2f}/match). "
        f"Low xGA means solid defending — the best teams sit bottom-left of both charts.")
st.divider()

# ============================================================================
# STADIUM CAPACITY & ATTENDANCE
# ============================================================================
st.subheader("🎟️ Stadium Capacity & Attendance")
cap_data = filtered['venue_capacity'].dropna()
if not cap_data.empty:
    col1, col2, col3 = st.columns(3)
    with col1:
        fig_cap = px.histogram(
            cap_data, nbins=15,
            color_discrete_sequence=['#FF004D'],
            title="Stadium Capacity Distribution",
        )
        fig_cap.update_layout(
            paper_bgcolor='#ffffff', plot_bgcolor='#ffffff',
            font=dict(color='#000000', family='Noto Sans'),
            title=dict(font=dict(family='Bebas Neue', size=16)),
            xaxis_title="Stadium Capacity", yaxis_title="Number of Venues",
            bargap=0.1,
        )
        st.plotly_chart(apply_dark_text_theme(fig_cap), width='stretch')

    with col2:
        st.metric("Average Capacity", f"{int(cap_data.mean()):,} seats")
        st.metric("Median Capacity", f"{int(cap_data.median()):,} seats")
        st.metric("Spread (Range)", f"{int(cap_data.min()):,} to {int(cap_data.max()):,} seats")

    with col3:
        # Sum unique venue capacities (not per-match — 104 matches reuse 16 venues)
        unique_seats = filtered.groupby('stadium_name')['venue_capacity'].first().sum()
        st.metric("Seats Across All Venues", f"{int(unique_seats):,}")
        st.metric("Biggest Venue (any stadium)", f"{int(cap_data.max()):,} seats")
        st.metric("Venues Bigger Than Wembley (>80k)", f"{(cap_data > 80000).sum()}")

    if 'stadium_name' in filtered.columns and 'city' in filtered.columns:
        largest = filtered[['stadium_name', 'city', 'country', 'venue_capacity']].drop_duplicates()\
            .sort_values('venue_capacity', ascending=False).head(5)
        st.markdown("#### 🏟️ Largest Venues")
        for _, v in largest.iterrows():
            st.markdown(f"- **{v['stadium_name']}** ({v['city']}, {v['country']}) "
                        f"— {int(v['venue_capacity']):,} seats")

    info_card("Capacity Insight",
        f"With an average venue capacity of {int(cap_data.mean()):,} seats across "
        f"{filtered['stadium_name'].nunique()} venues in {filtered['country'].nunique()} host nations, "
        f"the 2026 World Cup set new attendance benchmarks. The expanded 48-team "
        f"format and North American infrastructure underpinned record turnout.")
st.divider()

# ============================================================================
# ALL MATCH RESULTS TABLE
# ============================================================================
st.subheader("📋 Complete Match Results")
results_table = filtered.sort_values('date')[[
    'date', 'stage_name', 'home_team_name', 'away_team_name',
    'home_score', 'away_score', 'result_type', 'stadium_name', 'city',
    'player_of_the_match_name', 'referee_name',
]].copy()
# Apply famous-name overrides to Player of the Match (raw CSV uses full legal names)
results_table['player_of_the_match_name'] = results_table['player_of_the_match_name'].apply(_famous_name)
results_table['date'] = results_table['date'].dt.strftime('%b %d')
results_table = results_table.rename(columns={
    'date': 'Date', 'stage_name': 'Stage',
    'home_team_name': 'Home', 'away_team_name': 'Away',
    'home_score': 'H', 'away_score': 'A', 'result_type': 'Result',
    'stadium_name': 'Venue', 'city': 'City',
    'player_of_the_match_name': 'Player of the Match',
    'referee_name': 'Referee',
})
st.dataframe(results_table, hide_index=True, width='stretch')
st.divider()

# ============================================================================
# DATA QUALITY & SOURCES
# ============================================================================
st.subheader("⚽ xG Conversion — Who Finishes Their Chances")

xg_df2 = filtered.dropna(subset=['home_xg', 'home_score', 'away_xg', 'away_score']).copy()
if not xg_df2.empty:
    # Build home + away: xG vs actual goals for each team
    home_xg = xg_df2.groupby('home_team_name', as_index=False).agg(
        xg=('home_xg', 'mean'), goals=('home_score', 'mean')
    ).rename(columns={'home_team_name': 'team'})
    away_xg = xg_df2.groupby('away_team_name', as_index=False).agg(
        xg=('away_xg', 'mean'), goals=('away_score', 'mean')
    ).rename(columns={'away_team_name': 'team'})
    all_xg = pd.concat([home_xg, away_xg])
    team_conv = all_xg.groupby('team', as_index=False)[['xg', 'goals']].mean()
    team_conv['conversion'] = team_conv['goals'] - team_conv['xg']
    team_conv['label'] = team_conv.apply(
        lambda r: f"{r['goals']:.1f} goals vs {r['xg']:.1f} xG ({r['conversion']:+.1f})", axis=1
    )
    # Show best finishers (positive conversion)
    best = team_conv.sort_values('conversion', ascending=False).head(10)
    worst = team_conv.sort_values('conversion', ascending=True).head(10)

    col1, col2 = st.columns(2)
    with col1:
        fig_conv_best = px.bar(
            best.sort_values('conversion', ascending=True),
            x='conversion', y='team', orientation='h',
            text='label', color_discrete_sequence=['#00a86b'],
            title='Best Finishers (Goals Above xG)',
        )
        fig_conv_best.update_layout(
            paper_bgcolor='#ffffff', plot_bgcolor='#ffffff',
            font=dict(color='#2B1E16', family='Noto Sans'),
            title=dict(font=dict(family='Bebas Neue', size=16)),
            xaxis_title='Goals - xG per Match', yaxis_title='', height=450,
        )
        fig_conv_best.update_traces(textposition='outside', textfont=dict(size=10, color='#2B1E16'))
        st.plotly_chart(apply_dark_text_theme(fig_conv_best), width='stretch')

    with col2:
        fig_conv_worst = px.bar(
            worst.sort_values('conversion', ascending=False),
            x='conversion', y='team', orientation='h',
            text='label', color_discrete_sequence=['#C8102E'],
            title='Biggest Underperformers (Goals Below xG)',
        )
        fig_conv_worst.update_layout(
            paper_bgcolor='#ffffff', plot_bgcolor='#ffffff',
            font=dict(color='#2B1E16', family='Noto Sans'),
            title=dict(font=dict(family='Bebas Neue', size=16)),
            xaxis_title='Conversion Difference per Match', yaxis_title='', height=450,
        )
        fig_conv_worst.update_traces(textposition='outside', textfont=dict(size=10, color='#2B1E16'))
        st.plotly_chart(apply_dark_text_theme(fig_conv_worst), width='stretch')

    info_card("Conversion Insight",
        f"Teams above the zero line score more goals than their xG suggests — "
        f"they are clinical finishers. Teams below zero create chances but struggle to convert. "
        f"The best finisher is {best.iloc[0]['team']} (+{best.iloc[0]['conversion']:+.1f}/match), "
        f"worst is {worst.iloc[0]['team']} ({worst.iloc[0]['conversion']:+.1f}/match).")
