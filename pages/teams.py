"""
Page 2: Team Analytics
Comprehensive analysis of 2026 World Cup teams using the real Kaggle dataset
(mominullptr/fifa-world-cup-2026-dataset, CC0): 48 nations with Elo, FIFA
ranking, manager, squad market value, and per-team in-match statistics
(possession, shots, xG, fouls, etc.) aggregated from 104 real matches.
Matches the official FWC26 Light Theme.
"""
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import numpy as np
from pages._shared_enhanced import load_custom_css, page_header, info_card
from data.real_wc26 import (
    get_real_wc26_team_strength, get_real_wc26_match_team_stats,
    get_real_wc26_teams, get_real_wc26_matches, STAGE_ORDER,
)

# Apply CSS
load_custom_css()

# Header
page_header(
    "Team Analytics",
    "Deep dive into team strengths, tactical balances, and market valuations from real WC26 data.",
    image_url="assets/logo.png"
)

# ============================================================================
# LOAD DATA — all from Kaggle
# ============================================================================
with st.spinner("Loading team metrics..."):
    teams_strength = get_real_wc26_team_strength()    # 48 rows: elo, fifa_rank, market_value, wc26_goals, manager
    team_match_stats = get_real_wc26_match_team_stats()  # 208 rows: per-team-per-match in-match stats
    teams = get_real_wc26_teams()                      # 48 rows: team_id, name, fifa_code, group, confederation
    matches = get_real_wc26_matches()                   # 104 rows: matches_detailed (for goals for/against)

if teams_strength.empty:
    st.error("Failed to load team data from the Kaggle dataset.")
    st.stop()

# ============================================================================
# COMPUTE REAL TACTICAL ATTRIBUTES from in-match statistics
# ============================================================================
# Build per-team aggregate goals-for / goals-against from matches
home_rows = matches.rename(columns={
    'home_team_name': 'team', 'away_team_name': 'opponent',
    'home_score': 'goals_for', 'away_score': 'goals_against',
})[['match_id', 'team', 'goals_for', 'goals_against']]
away_rows = matches.rename(columns={
    'away_team_name': 'team', 'home_team_name': 'opponent',
    'away_score': 'goals_for', 'home_score': 'goals_against',
})[['match_id', 'team', 'goals_for', 'goals_against']]
goals_per_team = pd.concat([home_rows, away_rows], ignore_index=True)
goals_agg = goals_per_team.groupby('team').agg(
    matches=('match_id', 'size'),
    goals_for=('goals_for', 'sum'),
    goals_against=('goals_against', 'sum'),
).reset_index()
goals_agg['goal_difference'] = goals_agg['goals_for'] - goals_agg['goals_against']

# Aggregate per-team in-match stats (possession, shots, etc.)
# `team_match_stats` is the Kaggle-derived v_match_team_stats_agg view, which
# already carries team_name + per-team averages; no further join needed.
match_stats_agg = team_match_stats.groupby('team_name').agg(
    avg_possession=('avg_possession', 'mean'),
    avg_shots=('avg_shots', 'mean'),
    avg_shots_on_target=('avg_shots_on_target', 'mean'),
    avg_corners=('avg_corners', 'mean'),
    avg_fouls=('avg_fouls', 'mean'),
    avg_saves=('avg_saves', 'mean'),
    matches=('matches', 'mean'),  # v_match_team_stats_agg matches is per-team, so take mean
).reset_index()

# Merge everything into one dataframe
df = teams_strength.merge(goals_agg, left_on='team_name', right_on='team', how='left').drop(columns=['team'], errors='ignore')
df = df.merge(match_stats_agg, on='team_name', how='left')

# Normalize tactical metrics to a 0-100 scale for radar parity:
# attack_strength   = goals_for per match, z-scored then scaled
# defense_strength  = -goals_against per match (fewer conceded = stronger), z-scored
# midfield_strength = avg possession, z-scored (proxy for control)
# gk_strength       = avg saves, z-scored (proxy for keeper activity / quality)
# avg_ovr_top11     = (elo_rating + fifa_ranking_pre_tournament inverted) blended — Kaggle has no
#                     FIFA-23-OVR, so use Elo as the overall proxy.
def zscore_to_60_95(series, low=60, high=95):
    s = pd.to_numeric(series, errors='coerce')
    std = s.std(skipna=True)
    if std is None or std == 0 or np.isnan(std):
        return pd.Series([77.5] * len(s), index=s.index)
    z = (s - s.mean()) / std
    # Map z∈[-2, 2] to [low, high]
    out = low + (z.clip(-2, 2) + 2) / 4 * (high - low)
    return out

df['attack_strength'] = zscore_to_60_95(df['goals_for'] / df['matches_x'])
df['defense_strength'] = zscore_to_60_95(-(df['goals_against'] / df['matches_x']))
df['midfield_strength'] = zscore_to_60_95(df['avg_possession'])
df['gk_strength'] = zscore_to_60_95(df['avg_saves'])
df['avg_ovr_top11'] = zscore_to_60_95(df['elo_rating'])  # Elo as overall proxy
# Compatibility alias for downstream code
df['total_market_value_eur'] = df['squad_market_value_eur']

# ============================================================================
# FILTERS
# ============================================================================
st.markdown("### 🎛️ Analytics Filters")
c1, c2, c3 = st.columns(3)
confeds = sorted(df['confederation'].dropna().unique().tolist())
groups = sorted(df['group_letter'].dropna().unique().tolist()) if 'group_letter' in df.columns else []

sel_confed = c1.selectbox("🌐 Confederation", ["All"] + confeds)
sel_group = c2.selectbox("📊 Group Stage", ["All"] + groups)

filtered = df.copy()
confed_col = 'confederation'

if sel_confed != "All":
    filtered = filtered[filtered[confed_col] == sel_confed]
if sel_group != "All" and 'group_letter' in filtered.columns:
    filtered = filtered[filtered['group_letter'] == sel_group]

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
    val = kpi_df['total_market_value_eur'].sum()
    squad_label = "Total Squad Value" if sel_team == "None" else f"{label_prefix}Squad Value"
    if val >= 1e9:
        val_str = f"€{val/1e9:.2f}B"
    elif val >= 1e6:
        val_str = f"€{val/1e6:.0f}M"
    elif val > 0:
        val_str = f"€{val/1e3:.0f}K"
    else:
        val_str = "N/A"
    st.metric(squad_label, val_str)
with col_k4:
    st.metric(f"{label_prefix}WC26 Goals", f"{kpi_df['wc26_goals'].sum():.0f}")

st.divider()

# ============================================================================
# TEAM SPOTLIGHT (RADAR CHART — built from REAL in-match Kaggle stats)
# ============================================================================
if sel_team != "None":
    st.subheader(f"🔍 Tactical Profile: {sel_team}")
    st.caption("Tactical ratings are derived from real WC26 in-match statistics: "
               "attack = goals scored per match, defense = fewest goals conceded, "
               "midfield = possession share, goalkeeping = saves per match, "
               "overall = Elo rating. All z-scored to a 60–95 scale for parity.")
    team_data = filtered[filtered['team_name'] == sel_team].iloc[0]

    avg_attack = df['attack_strength'].mean()
    avg_mid = df['midfield_strength'].mean()
    avg_def = df['defense_strength'].mean()
    avg_gk = df['gk_strength'].mean()
    avg_ovr = df['avg_ovr_top11'].mean()

    cats = ['Attack', 'Midfield', 'Defense', 'Goalkeeping', 'Elo (OVR)']
    team_vals = [team_data['attack_strength'], team_data['midfield_strength'],
                 team_data['defense_strength'], team_data['gk_strength'],
                 team_data['avg_ovr_top11']]
    avg_vals = [avg_attack, avg_mid, avg_def, avg_gk, avg_ovr]

    fig_radar = go.Figure()
    fig_radar.add_trace(go.Scatterpolar(
        r=team_vals + [team_vals[0]],
        theta=cats + [cats[0]],
        fill='toself', name=sel_team,
        line_color='#FF004D', fillcolor='rgba(255, 0, 77, 0.4)',
    ))
    fig_radar.add_trace(go.Scatterpolar(
        r=avg_vals + [avg_vals[0]],
        theta=cats + [cats[0]],
        fill='toself', name='Tournament Avg',
        line_color='#000000', fillcolor='rgba(0, 0, 0, 0.1)',
    ))
    fig_radar.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[60, 95])),
        showlegend=True,
        paper_bgcolor='#ffffff',
        font=dict(color='#000000', family='Noto Sans'),
        title=dict(text=f"{sel_team} Tactical Profile vs Tournament Average",
                   font=dict(family='Bebas Neue', size=20)),
    )

    r1, r2 = st.columns([2, 1])
    with r1:
        st.plotly_chart(fig_radar, width='stretch')
    with r2:
        st.markdown(f"### {sel_team} Quick Stats")
        st.markdown(f"**Group:** {team_data.get('group_letter', 'N/A')}")
        st.markdown(f"**Confederation:** {team_data.get('confederation', 'N/A')}")
        st.markdown(f"**Manager:** {team_data.get('manager_name', 'N/A')}")
        st.markdown(f"**Elo Rating:** {team_data['elo_rating']:.0f}")
        st.markdown(f"**FIFA Ranking (pre):** #{int(team_data['fifa_ranking_pre_tournament'])}")
        st.markdown(f"**WC26 Goals:** {int(team_data['wc26_goals'])}")
        st.markdown(f"**WC26 Assists:** {int(team_data['wc26_assists'])}")

        strongest_idx = int(np.argmax(team_vals))
        weakest_idx = int(np.argmin(team_vals))
        strongest = cats[strongest_idx]
        weakest = cats[weakest_idx]
        strongest_diff = team_vals[strongest_idx] - avg_vals[strongest_idx]

        insight_text = (f"Based on real WC26 in-match statistics, {sel_team}'s "
                        f"strongest tactical dimension is **{strongest}** ")
        if strongest_diff > 0:
            insight_text += f"({strongest_diff:+.1f} vs tournament average). "
        else:
            insight_text += f"({strongest_diff:.1f} vs average). "
        insight_text += (f"Their most exposed area is **{weakest}**, which "
                        f"opponents looked to exploit across the tournament.")
        info_card("Tactical Insight", insight_text)
    st.divider()

# ============================================================================
# ATTACK vs DEFENSE MATRIX (real goals, not FIFA OVR)
# ============================================================================
st.subheader("⚔️ Attack vs Defense Matrix")
st.caption("Attack = goals scored per match (z-scored). Defense = goals conceded per match, inverted (fewer = stronger).")
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
    hover_data={'wc26_goals': True, 'goals_for': True, 'goals_against': True},
    title="Bubble Size = Elo Rating (overall proxy)",
    labels={
        'defense_strength': 'Defense Strength (z-scored, 60-95)',
        'attack_strength': 'Attack Strength (z-scored, 60-95)',
        confed_col: 'Confederation',
    },
)
avg_atk = df['attack_strength'].mean()
avg_def = df['defense_strength'].mean()
fig_scatter.add_vline(x=avg_def, line_dash="dash", line_color="#000000", opacity=0.5)
fig_scatter.add_hline(y=avg_atk, line_dash="dash", line_color="#000000", opacity=0.5)
fig_scatter.add_annotation(
    x=scatter_df['defense_strength'].max(),
    y=scatter_df['attack_strength'].max(),
    text="Elite Balance", showarrow=False, yshift=20,
    font=dict(color="#FF004D", size=16, family='Bebas Neue'),
)
fig_scatter.update_layout(
    paper_bgcolor='#ffffff', plot_bgcolor='#ffffff',
    font=dict(color='#000000', family='Noto Sans'),
)
st.plotly_chart(fig_scatter, width='stretch')

elite_teams = scatter_df[(scatter_df['attack_strength'] > avg_atk) & (scatter_df['defense_strength'] > avg_def)]
elite_count = len(elite_teams)
insight_text = (f"Teams in the top-right quadrant possess both elite attacking "
                f"and defensive capabilities from real WC26 matches — a hallmark "
                f"of deep tournament runs. ")
if elite_count > 0:
    elite_names = ", ".join(elite_teams['team_name'].head(3).tolist())
    insight_text += (f"{elite_count} team{'s' if elite_count > 1 else ''} in this view "
                     f"fall into the 'Elite Balance' category (e.g., {elite_names}). ")
else:
    insight_text += "No teams in the current filter view meet the 'Elite Balance' threshold. "
insight_text += "Teams in the top-left rely on outscoring opponents to compensate for defensive frailties."
info_card("Matrix Insight", insight_text)

st.divider()

# ============================================================================
# TEAM ROSTER INTELLIGENCE (data table)
# ============================================================================
st.subheader("📋 Team Roster Intelligence")

display_cols = ['team_name', confed_col, 'group_letter', 'elo_rating',
                'fifa_ranking_pre_tournament', 'manager_name',
                'attack_strength', 'defense_strength',
                'midfield_strength', 'total_market_value_eur',
                'wc26_goals', 'wc26_assists']
display_cols = [c for c in display_cols if c in filtered.columns]

col_config = {
    "team_name": st.column_config.TextColumn("Team"),
    confed_col: st.column_config.TextColumn("Confed"),
    "group_letter": st.column_config.TextColumn("Group"),
    "elo_rating": st.column_config.NumberColumn("Elo", format="%d"),
    "fifa_ranking_pre_tournament": st.column_config.NumberColumn("FIFA Rank", format="#%d"),
    "manager_name": st.column_config.TextColumn("Manager"),
    "attack_strength": st.column_config.ProgressColumn("Attack", min_value=60, max_value=95, format="%.1f"),
    "defense_strength": st.column_config.ProgressColumn("Defense", min_value=60, max_value=95, format="%.1f"),
    "midfield_strength": st.column_config.ProgressColumn("Midfield", min_value=60, max_value=95, format="%.1f"),
    "total_market_value_eur": st.column_config.NumberColumn("Squad €", format="€%,.0f"),
    "wc26_goals": st.column_config.NumberColumn("WC26 Goals", format="%d"),
    "wc26_assists": st.column_config.NumberColumn("WC26 Assists", format="%d"),
}
col_config = {k: v for k, v in col_config.items() if k in display_cols}

st.dataframe(
    filtered[display_cols].sort_values('elo_rating', ascending=False),
    column_config=col_config,
    hide_index=True,
    width='stretch',
    height=500,
)

# Financial Disparity
if len(filtered) > 1 and 'total_market_value_eur' in filtered.columns:
    sub = filtered.dropna(subset=['total_market_value_eur'])
    if not sub.empty:
        highest = sub.loc[sub['total_market_value_eur'].idxmax()]
        lowest = sub.loc[sub['total_market_value_eur'].idxmin()]
        lowest_val = max(lowest['total_market_value_eur'], 100000)
        multiplier = highest['total_market_value_eur'] / lowest_val
        info_card(
            "Financial Disparity Insight",
            f"**{highest['team_name']}** has a squad value of €{highest['total_market_value_eur']/1e9:.2f}B, "
            f"roughly **{multiplier:.1f}x** the value of **{lowest['team_name']}** "
            f"(€{lowest['total_market_value_eur']/1e6:.0f}M). Despite this, Elo ratings often "
            f"demonstrate a much closer competitive reality on the pitch."
        )

st.divider()

# ============================================================================
# ELO vs SQUAD VALUE
# ============================================================================
st.subheader("💰 Elo vs Squad Value: Value-for-Money Analysis")

fig_value = px.scatter(
    filtered,
    x='total_market_value_eur',
    y='elo_rating',
    color=confed_col,
    color_discrete_sequence=['#FF004D', '#7B00FF', '#00F0FF', '#00FF00', '#FF4D00'],
    size='avg_ovr_top11',
    hover_name='team_name',
    trendline='ols',
    trendline_color_override='#000000',
    labels={
        'total_market_value_eur': 'Squad Value (€)',
        'elo_rating': 'Elo Rating',
        confed_col: 'Confederation',
    },
    title="Trend line = Expected Elo for a Given Squad Investment",
)
fig_value.update_layout(
    paper_bgcolor='#ffffff', plot_bgcolor='#ffffff',
    font=dict(color='#000000', family='Noto Sans'),
    title=dict(font=dict(family='Bebas Neue', size=18)),
)
st.plotly_chart(fig_value, width='stretch')

trend_df = filtered.dropna(subset=['elo_rating', 'total_market_value_eur']).copy()
if len(trend_df) > 2:
    x = trend_df['total_market_value_eur'].values
    y = trend_df['elo_rating'].values
    if x.max() > x.min():
        coeffs = np.polyfit(x, y, 1)
        trend_df['expected_elo'] = np.polyval(coeffs, x)
        trend_df['elo_residual'] = trend_df['elo_rating'] - trend_df['expected_elo']

        over = trend_df.nlargest(3, 'elo_residual')
        under = trend_df.nsmallest(3, 'elo_residual')

        oc1, oc2 = st.columns(2)
        with oc1:
            st.markdown("#### 📈 Overperformers (High Elo Relative to Spend)")
            for _, r in over.iterrows():
                st.markdown(f"- **{r['team_name']}** — Elo {r['elo_rating']:.0f} (+{r['elo_residual']:.0f} above expected)")
        with oc2:
            st.markdown("#### 📉 Underperformers (Low Elo Relative to Spend)")
            for _, r in under.iterrows():
                st.markdown(f"- **{r['team_name']}** — Elo {r['elo_rating']:.0f} ({r['elo_residual']:.0f} below expected)")

    info_card(
        "Value-for-Money Insight",
        "The trend line shows the expected Elo rating for a given squad investment. "
        "Teams above the line are **overperforming** — they extract more competitive "
        "quality from their financial resources than the tournament average. Teams below "
        "the line may be **underperforming** relative to their financial firepower."
    )

st.divider()

# ============================================================================
# CONFEDERATION STRENGTH
# ============================================================================
if confed_col in filtered.columns and filtered[confed_col].nunique() > 1:
    st.subheader("🌐 Confederation Strength Comparison")

    confed_stats = filtered.groupby(confed_col).agg(
        avg_elo=('elo_rating', 'mean'),
        avg_attack=('attack_strength', 'mean'),
        avg_defense=('defense_strength', 'mean'),
        avg_midfield=('midfield_strength', 'mean'),
        avg_value=('total_market_value_eur', 'mean'),
        team_count=('team_name', 'count'),
        wc26_goals=('wc26_goals', 'sum'),
    ).reset_index()

    metrics = ['avg_elo', 'avg_attack', 'avg_defense', 'avg_midfield']
    metric_labels = ['Avg Elo', 'Avg Attack', 'Avg Defense', 'Avg Midfield']

    cc1, cc2 = st.columns(2)
    for idx, (col, cc) in enumerate(zip(metrics[:2], [cc1, cc2])):
        fig_c = px.bar(
            confed_stats, x=confed_col, y=col,
            color=confed_col,
            color_discrete_sequence=['#FF004D', '#7B00FF', '#00F0FF', '#00FF00', '#FF4D00'],
            text_auto='.1f',
            labels={col: metric_labels[idx], confed_col: 'Confederation'},
        )
        fig_c.update_layout(
            showlegend=False, paper_bgcolor='#ffffff', plot_bgcolor='#ffffff',
            font=dict(color='#000000', family='Noto Sans'),
            title=dict(text=metric_labels[idx], font=dict(family='Bebas Neue', size=16)),
        )
        cc.plotly_chart(fig_c, width='stretch')

    cc3, cc4 = st.columns(2)
    for idx, (col, cc) in enumerate(zip(metrics[2:], [cc3, cc4])):
        fig_c = px.bar(
            confed_stats, x=confed_col, y=col,
            color=confed_col,
            color_discrete_sequence=['#FF004D', '#7B00FF', '#00F0FF', '#00FF00', '#FF4D00'],
            text_auto='.1f',
            labels={col: metric_labels[idx + 2], confed_col: 'Confederation'},
        )
        fig_c.update_layout(
            showlegend=False, paper_bgcolor='#ffffff', plot_bgcolor='#ffffff',
            font=dict(color='#000000', family='Noto Sans'),
            title=dict(text=metric_labels[idx + 2], font=dict(family='Bebas Neue', size=16)),
        )
        cc.plotly_chart(fig_c, width='stretch')

    strongest = confed_stats.loc[confed_stats['avg_elo'].idxmax()]
    weakest = confed_stats.loc[confed_stats['avg_elo'].idxmin()]
    elo_gap = strongest['avg_elo'] - weakest['avg_elo']
    info_card(
        "Confederation Power Rankings",
        f"**{strongest[confed_col]}** leads with the highest average Elo ({strongest['avg_elo']:.0f}), "
        f"while **{weakest[confed_col]}** trails ({weakest['avg_elo']:.0f}). "
        f"The Elo gap of {elo_gap:.0f} points reflects the competitive hierarchy in world football. "
        f"Teams from stronger confederations typically advance deeper into the knockout stages, "
        f"though tactical discipline can bridge the gap."
    )
    st.divider()

# ============================================================================
# GROUP OF DEATH ANALYSIS
# ============================================================================
st.subheader("💀 Group of Death Analysis")

if 'group_letter' in filtered.columns and 'elo_rating' in filtered.columns:
    group_analysis = filtered.groupby('group_letter').agg(
        avg_elo=('elo_rating', 'mean'),
        std_elo=('elo_rating', 'std'),
        min_elo=('elo_rating', 'min'),
        max_elo=('elo_rating', 'max'),
        team_count=('team_name', 'count'),
        total_value=('total_market_value_eur', 'sum'),
        total_wc26_goals=('wc26_goals', 'sum'),
    ).reset_index().sort_values('avg_elo', ascending=False)

    group_analysis['competitiveness'] = group_analysis['avg_elo'] / (group_analysis['std_elo'] + 1)

    fig_group = px.bar(
        group_analysis,
        x='group_letter', y='avg_elo',
        color='avg_elo',
        color_continuous_scale=['#00F0FF', '#7B00FF', '#FF004D'],
        text_auto='.0f',
        labels={'avg_elo': 'Average Elo', 'group_letter': 'Group'},
        title="Average Elo by Group (Higher = Harder Group)",
    )
    fig_group.update_layout(
        paper_bgcolor='#ffffff', plot_bgcolor='#ffffff',
        font=dict(color='#000000', family='Noto Sans'),
        title=dict(font=dict(family='Bebas Neue', size=18)),
    )
    st.plotly_chart(fig_group, width='stretch')

    hardest = group_analysis.iloc[0]
    easiest = group_analysis.iloc[-1]

    # Get the team names in each group
    hardest_teams = filtered[filtered['group_letter'] == hardest['group_letter']]['team_name'].tolist()
    easiest_teams = filtered[filtered['group_letter'] == easiest['group_letter']]['team_name'].tolist()
    def fmt_teams(teams):
        if not teams:
            return ""
        if len(teams) == 1:
            return teams[0]
        return ", ".join(teams[:-1]) + f" & {teams[-1]}"

    gc1, gc2 = st.columns(2)
    with gc1:
        st.markdown(f"#### 🔴 Hardest Group: {hardest['group_letter']} — {fmt_teams(hardest_teams)}")
        st.markdown(f"- Avg Elo: **{hardest['avg_elo']:.0f}**")
        st.markdown(f"- Elo Range: {hardest['min_elo']:.0f} – {hardest['max_elo']:.0f}")
        st.markdown(f"- Total Squad Value: €{hardest['total_value']/1e9:.2f}B")
        st.markdown(f"- Total WC26 Goals: {int(hardest['total_wc26_goals'])}")
    with gc2:
        st.markdown(f"#### 🟢 Easiest Group: {easiest['group_letter']} — {fmt_teams(easiest_teams)}")
        st.markdown(f"- Avg Elo: **{easiest['avg_elo']:.0f}**")
        st.markdown(f"- Elo Range: {easiest['min_elo']:.0f} – {easiest['max_elo']:.0f}")
        st.markdown(f"- Total Squad Value: €{easiest['total_value']/1e9:.2f}B")
        st.markdown(f"- Total WC26 Goals: {int(easiest['total_wc26_goals'])}")

    elo_diff = hardest['avg_elo'] - easiest['avg_elo']
    info_card(
        "Group of Death Insight",
        f"**Group {hardest['group_letter']}** ({fmt_teams(hardest_teams)}) is statistically the hardest group with an average "
        f"Elo of {hardest['avg_elo']:.0f}. **Group {easiest['group_letter']}** ({fmt_teams(easiest_teams)}) is the easiest "
        f"with an average Elo of {easiest['avg_elo']:.0f}. The {elo_diff:.0f}-point Elo gap means "
        f"teams in Group {hardest['group_letter']} faced a significantly steeper path to the "
        f"knockout rounds. Teams emerging from Groups of Death either galvanize into deep "
        f"tournament contenders or suffer early fatigue and injury accumulation."
    )
else:
    st.info("Group data not available for this analysis.")

st.divider()

# ============================================================================
# TACTICAL BALANCE INDEX
# ============================================================================
st.subheader("⚖️ Tactical Balance Index")

balance_df = filtered.copy()
balance_df['balance_score'] = balance_df[['attack_strength', 'defense_strength', 'midfield_strength']].std(axis=1)
balance_df['overall_strength'] = balance_df[['attack_strength', 'defense_strength', 'midfield_strength']].mean(axis=1)

fig_balance = px.scatter(
    balance_df,
    x='overall_strength', y='balance_score',
    size='avg_ovr_top11', color=confed_col,
    color_discrete_sequence=['#FF004D', '#7B00FF', '#00F0FF', '#00FF00', '#FF4D00'],
    hover_name='team_name',
    labels={
        'overall_strength': 'Overall Tactical Strength (Avg of Atk/Def/Mid)',
        'balance_score': 'Tactical Imbalance (Std Dev — Lower = More Balanced)',
        confed_col: 'Confederation',
    },
    title="Lower Y = More Balanced | Higher X = Stronger Overall (real WC26 stats)",
)
fig_balance.update_layout(
    paper_bgcolor='#ffffff', plot_bgcolor='#ffffff',
    font=dict(color='#000000', family='Noto Sans'),
    title=dict(font=dict(family='Bebas Neue', size=18)),
)
avg_strength = balance_df['overall_strength'].mean()
avg_balance = balance_df['balance_score'].mean()
fig_balance.add_vline(x=avg_strength, line_dash="dash", line_color="#000000", opacity=0.4)
fig_balance.add_hline(y=avg_balance, line_dash="dash", line_color="#000000", opacity=0.4)
st.plotly_chart(fig_balance, width='stretch')

most_balanced = balance_df.nsmallest(3, 'balance_score')
most_imbalanced = balance_df.nlargest(3, 'balance_score')

bc1, bc2 = st.columns(2)
with bc1:
    st.markdown("#### 🏆 Most Balanced Teams")
    for _, r in most_balanced.iterrows():
        st.markdown(f"- **{r['team_name']}** — Imbalance: {r['balance_score']:.2f} | Overall: {r['overall_strength']:.1f}")
with bc2:
    st.markdown("#### ⚠️ Most Imbalanced Teams")
    for _, r in most_imbalanced.iterrows():
        st.markdown(f"- **{r['team_name']}** — Imbalance: {r['balance_score']:.2f} | Overall: {r['overall_strength']:.1f}")

most_balanced_name = most_balanced.iloc[0]['team_name'] if not most_balanced.empty else "—"
info_card(
    "Tactical Balance Insight",
    f"The **Tactical Balance Index** measures the standard deviation between a team's "
    f"Attack, Defense, and Midfield ratings (derived from real WC26 in-match statistics). "
    f"Teams with low imbalance scores have well-rounded squads — a critical factor in "
    f"tournament football where opponents vary in style. Highly imbalanced teams may "
    f"dominate in one phase but struggle when forced into their weak zone. "
    f"**{most_balanced_name}** is the most balanced team in the current view."
)
