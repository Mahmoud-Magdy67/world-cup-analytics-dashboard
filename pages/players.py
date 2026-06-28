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
from data.bigquery_enhanced import get_players, get_player_percentiles

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

if df.empty:
    st.error("Failed to load player data from BigQuery.")
    st.stop()

# Ensure numeric columns
numeric_cols = ['goals', 'assists', 'xg', 'xa', 'npxg', 'shots', 'shots_on_target',
                'tackles', 'interceptions', 'tackles_interceptions', 'blocks', 'clearances',
                'age', 'matches_played', 'starts', 'minutes', 'nineties_played']
for col in numeric_cols:
    if col in df.columns:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

# GK stats
gk_cols = ['gk_minutes', 'gk_goals_against', 'gk_save_pct', 'gk_clean_sheets']
for col in gk_cols:
    if col in df.columns:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

# Compute per-90 metrics
if 'minutes' in df.columns and (df['minutes'] > 0).any():
    df['goals_per90'] = np.where(df['minutes'] > 0, df['goals'] / (df['minutes'] / 90), 0)
    df['assists_per90'] = np.where(df['minutes'] > 0, df['assists'] / (df['minutes'] / 90), 0)
    df['xg_per90'] = np.where(df['minutes'] > 0, df['xg'] / (df['minutes'] / 90), 0)
    df['xa_per90'] = np.where(df['minutes'] > 0, df['xa'] / (df['minutes'] / 90), 0)
else:
    df['goals_per90'] = 0
    df['assists_per90'] = 0
    df['xg_per90'] = 0
    df['xa_per90'] = 0

df['goal_contribution'] = df['goals'] + df['assists']
df['xg_overperformance'] = df['goals'] - df['xg']

# ============================================================================
# FILTERS
# ============================================================================
st.markdown("### 🎛️ Analytics Filters")
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
# KPIs
# ============================================================================
if sel_player != "None":
    kpi_df = filtered[filtered['player_name'] == sel_player]
    label_prefix = f"{sel_player} "
else:
    kpi_df = filtered
    label_prefix = "Total "

k1, k2, k3, k4, k5 = st.columns(5)
with k1:
    st.metric("Players", len(kpi_df))
with k2:
    st.metric(f"{label_prefix}Goals", f"{kpi_df['goals'].sum():.0f}")
with k3:
    st.metric(f"{label_prefix}Assists", f"{kpi_df['assists'].sum():.0f}")
with k4:
    st.metric(f"{label_prefix}xG", f"{kpi_df['xg'].sum():.1f}")
with k5:
    st.metric(f"{label_prefix}Minutes", f"{kpi_df['minutes'].sum():,.0f}")

st.divider()

# ============================================================================
# PLAYER SPOTLIGHT (PERCENTILE RADAR)
# ============================================================================
if sel_player != "None" and not percentiles.empty:
    st.subheader(f"🔍 Player Profile: {sel_player}")
    player_pct = percentiles[percentiles['player_name'] == sel_player]

    if not player_pct.empty:
        pct_row = player_pct.iloc[0]
        radar_cats = ['Goals', 'Assists', 'xG', 'xA', 'Tackles', 'Interceptions']
        radar_vals = [
            pct_row.get('goals_pct', 0) * 100,
            pct_row.get('assists_pct', 0) * 100,
            pct_row.get('xg_pct', 0) * 100,
            pct_row.get('xa_pct', 0) * 100,
            pct_row.get('tackles_pct', 0) * 100,
            pct_row.get('interceptions_pct', 0) * 100,
        ]

        fig_radar = go.Figure()
        fig_radar.add_trace(go.Scatterpolar(
            r=radar_vals + [radar_vals[0]],
            theta=radar_cats + [radar_cats[0]],
            fill='toself',
            name=sel_player,
            line_color='#FF004D',
            fillcolor='rgba(255, 0, 77, 0.4)'
        ))
        fig_radar.add_trace(go.Scatterpolar(
            r=[50] * 7,
            theta=radar_cats + [radar_cats[0]],
            fill='toself',
            name='50th Percentile',
            line_color='#000000',
            fillcolor='rgba(0, 0, 0, 0.05)'
        ))
        fig_radar.update_layout(
            polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
            showlegend=True,
            paper_bgcolor='#ffffff',
            font=dict(color='#000000', family='Noto Sans'),
            title=dict(text=f"{sel_player} — Percentile Profile vs World Cup Pool", font=dict(family='Bebas Neue', size=20))
        )

        r1, r2 = st.columns([2, 1])
        with r1:
            st.plotly_chart(fig_radar, width='stretch')
        with r2:
            player_data = filtered[filtered['player_name'] == sel_player].iloc[0]
            st.markdown(f"### Quick Profile")
            st.markdown(f"**Position:** {player_data.get('position', 'N/A')}")
            st.markdown(f"**Nation:** {player_data.get('nation_code', 'N/A')}")
            st.markdown(f"**Club:** {player_data.get('club_team', 'N/A')}")
            st.markdown(f"**League:** {player_data.get('league', 'N/A')}")
            st.markdown(f"**Age:** {player_data.get('age', 0):.0f}")
            st.markdown(f"**Goals / Assists:** {player_data['goals']:.0f} / {player_data['assists']:.0f}")
            st.markdown(f"**xG / xA:** {player_data['xg']:.1f} / {player_data['xa']:.1f}")

            top_attr = radar_cats[np.argmax(radar_vals)]
            info_card("Player Insight",
                f"{sel_player}'s standout attribute is **{top_attr}** (P{np.argmax(radar_vals)+1} percentile). "
                f"The radar compares the player against all World Cup squad members with 500+ minutes played."
            )
    else:
        st.info(f"No percentile data available for {sel_player} (requires 500+ minutes played).")
    st.divider()

# ============================================================================
# GOALS vs xG (FINISHING EFFICIENCY)
# ============================================================================
st.subheader("⚽ Goals vs xG: Finishing Efficiency")
eff_df = filtered[filtered['minutes'] >= 300].copy()

if not eff_df.empty and 'xg' in eff_df.columns:
    fig_eff = px.scatter(
        eff_df,
        x='xg',
        y='goals',
        size='minutes',
        color='position' if 'position' in eff_df.columns else None,
        color_discrete_sequence=['#FF004D', '#7B00FF', '#00F0FF', '#00FF00', '#FF4D00'],
        hover_name='player_name',
        trendline='ols',
        trendline_color_override='#000000',
        labels={
            'xg': 'Expected Goals (xG)',
            'goals': 'Actual Goals',
            'position': 'Position'
        },
        title="Above the line = Clinical Finisher | Below = Underperforming"
    )
    fig_eff.update_layout(
        paper_bgcolor='#ffffff',
        plot_bgcolor='#ffffff',
        font=dict(color='#000000', family='Noto Sans'),
        title=dict(font=dict(family='Bebas Neue', size=18))
    )
    st.plotly_chart(fig_eff, width='stretch')

    # Identify clinical finishers and underperformers
    if len(eff_df) > 2:
        x_min = eff_df['xg'].min()
        x_max = eff_df['xg'].max()
        if x_max > x_min and x_max > 0:  # Ensure we have variance and meaningful xG data
            try:
                coeffs = np.polyfit(eff_df['xg'], eff_df['goals'], 1)
                eff_df['expected_goals'] = np.polyval(coeffs, eff_df['xg'])
                eff_df['finishing_delta'] = eff_df['goals'] - eff_df['expected_goals']

                clinical = eff_df.nlargest(5, 'finishing_delta')
                wasteful = eff_df.nsmallest(5, 'finishing_delta')

                ec1, ec2 = st.columns(2)
                with ec1:
                    st.markdown("#### 🎯 Most Clinical Finishers")
                    for _, r in clinical.iterrows():
                        st.markdown(f"- **{r['player_name']}** — {r['goals']:.0f} goals from {r['xg']:.1f} xG (+{r['finishing_delta']:.1f})")
                with ec2:
                    st.markdown("#### 😬 Underperforming xG")
                    for _, r in wasteful.iterrows():
                        st.markdown(f"- **{r['player_name']}** — {r['goals']:.0f} goals from {r['xg']:.1f} xG ({r['finishing_delta']:.1f})")

                info_card("Finishing Efficiency Insight",
                    "Players above the trend line are **outperforming their xG** — converting chances at a higher rate than expected. "
                    "This can indicate elite finishing ability or a hot streak. Players below the line may be experiencing bad luck "
                    "or struggling with composure. In tournament football, clinical finishing is often the difference in tight knockout matches.")
            except Exception as e:
                # Fallback to simple difference if OLS fails
                eff_df['finishing_delta'] = eff_df['goals'] - eff_df['xg']
                clinical = eff_df.nlargest(5, 'finishing_delta')
                wasteful = eff_df.nsmallest(5, 'finishing_delta')

                ec1, ec2 = st.columns(2)
                with ec1:
                    st.markdown("#### 🎯 Most Clinical Finishers")
                    for _, r in clinical.iterrows():
                        xg_display = f"{r['xg']:.1f}" if pd.notnull(r['xg']) and r['xg'] > 0 else "data unavailable"
                        st.markdown(f"- **{r['player_name']}** — {r['goals']:.0f} goals from {xg_display} xG (+{r['finishing_delta']:.1f})")
                with ec2:
                    st.markdown("#### 😬 Underperforming xG")
                    for _, r in wasteful.iterrows():
                        xg_display = f"{r['xg']:.1f}" if pd.notnull(r['xg']) and r['xg'] > 0 else "data unavailable"
                        st.markdown(f"- **{r['player_name']}** — {r['goals']:.0f} goals from {xg_display} xG ({r['finishing_delta']:.1f})")

                info_card("Finishing Efficiency Insight",
                    "Expected goals (xG) data is incomplete for some leagues, so we're showing the raw difference between goals and xG. "
                    "Players with positive values outperformed their expected goals, while those with negative values underperformed. "
                    "Note: xG data may be missing or unreliable for certain leagues.")
        else:
            # Handle case where xg is all zeros or no variance (common for leagues without xG data)
            eff_df['finishing_delta'] = eff_df['goals'] - eff_df['xg']
            clinical = eff_df.nlargest(5, 'finishing_delta')
            wasteful = eff_df.nsmallest(5, 'finishing_delta')

            ec1, ec2 = st.columns(2)
            with ec1:
                st.markdown("#### 🎯 Most Clinical Finishers")
                for _, r in clinical.iterrows():
                    xg_display = f"{r['xg']:.1f}" if pd.notnull(r['xg']) and r['xg'] > 0 else "data unavailable"
                    st.markdown(f"- **{r['player_name']}** — {r['goals']:.0f} goals from {xg_display} xG (+{r['finishing_delta']:.1f})")
            with ec2:
                st.markdown("#### 😬 Underperforming xG")
                for _, r in wasteful.iterrows():
                    xg_display = f"{r['xg']:.1f}" if pd.notnull(r['xg']) and r['xg'] > 0 else "data unavailable"
                    st.markdown(f"- **{r['player_name']}** — {r['goals']:.0f} goals from {xg_display} xG ({r['finishing_delta']:.1f})")

            info_card("Finishing Efficiency Insight",
                "Expected goals (xG) data is not available for the selected filters/league, so we're showing goals minus xG. "
                "When xG data is missing (shows as 0.0), this simplifies to just the goal total. "
                "For leagues like the Eredivisie where xG isn't tracked in this dataset, consider this a raw goal count comparison.")
    st.divider()

# ============================================================================
# TOP CONTRIBUTORS (GOALS + ASSISTS)
# ============================================================================
st.subheader("🏆 Top Goal Contributors")
top_contrib = filtered.nlargest(15, 'goal_contribution')

if not top_contrib.empty:
    fig_top = go.Figure()
    fig_top.add_trace(go.Bar(
        name='Goals', x=top_contrib['player_name'], y=top_contrib['goals'],
        marker_color='#FF004D'
    ))
    fig_top.add_trace(go.Bar(
        name='Assists', x=top_contrib['player_name'], y=top_contrib['assists'],
        marker_color='#00F0FF'
    ))
    fig_top.update_layout(
        barmode='stack',
        paper_bgcolor='#ffffff',
        plot_bgcolor='#ffffff',
        font=dict(color='#000000', family='Noto Sans'),
        title=dict(text="Top 15: Goals (Pink) + Assists (Cyan)", font=dict(family='Bebas Neue', size=18)),
        xaxis_tickangle=-45,
        yaxis_title="Goal Contributions"
    )
    st.plotly_chart(fig_top, width='stretch')

    top_player = top_contrib.iloc[0]
    info_card("Top Contributor Insight",
        f"**{top_player['player_name']}** ({top_player.get('nation_code', 'N/A')}) leads with "
        f"{top_player['goals']:.0f} goals and {top_player['assists']:.0f} assists "
        f"({top_player['goal_contribution']:.0f} total contributions). "
        f"Their xG of {top_player['xg']:.1f} suggests {'clinical finishing above expected output' if top_player['goals'] > top_player['xg'] else 'output in line with chance quality'}.")
    st.divider()

# ============================================================================
# PER-90 EFFICIENCY ANALYSIS
# ============================================================================
st.subheader("⚡ Per-90 Efficiency: Goals vs Assists")
per90_df = filtered[filtered['minutes'] >= 500].copy()

if not per90_df.empty:
    fig_90 = px.scatter(
        per90_df,
        x='xa_per90',
        y='goals_per90',
        size='minutes',
        color='position' if 'position' in per90_df.columns else None,
        color_discrete_sequence=['#FF004D', '#7B00FF', '#00F0FF', '#00FF00', '#FF4D00'],
        hover_name='player_name',
        labels={
            'xa_per90': 'Expected Assists per 90',
            'goals_per90': 'Goals per 90',
            'position': 'Position'
        },
        title="Only players with 500+ minutes | Bubble size = total minutes"
    )
    avg_g90 = per90_df['goals_per90'].mean()
    xa90_avg = per90_df['xa_per90'].mean()
    fig_90.add_vline(x=xa90_avg, line_dash="dash", line_color="#000000", opacity=0.4)
    fig_90.add_hline(y=avg_g90, line_dash="dash", line_color="#000000", opacity=0.4)
    fig_90.update_layout(
        paper_bgcolor='#ffffff',
        plot_bgcolor='#ffffff',
        font=dict(color='#000000', family='Noto Sans'),
        title=dict(font=dict(family='Bebas Neue', size=18))
    )
    st.plotly_chart(fig_90, width='stretch')

    # Dual-threat players
    per90_df['threat_score'] = per90_df['goals_per90'] + per90_df['xa_per90']
    dual_threat = per90_df.nlargest(5, 'threat_score')
    dc1, dc2 = st.columns(2)
    with dc1:
        st.markdown("#### 🌟 Dual-Threat Players (Goals + xA per 90)")
        for _, r in dual_threat.iterrows():
            st.markdown(f"- **{r['player_name']}** — {r['goals_per90']:.2f} G/90 + {r['xa_per90']:.2f} xA/90")
    with dc2:
        pure_scorers = per90_df.nlargest(5, 'goals_per90')
        st.markdown("#### 🔥 Pure Scorers (Goals per 90)")
        for _, r in pure_scorers.iterrows():
            st.markdown(f"- **{r['player_name']}** — {r['goals_per90']:.2f} G/90")

    info_card("Per-90 Insight",
        "Per-90 metrics normalize for playing time, revealing true efficiency. The top-right quadrant contains "
        "**dual-threat players** who both score and create — invaluable in tournament football where tactical "
        "flexibility against diverse opponents is essential. Pure scorers (high G/90, lower xA/90) provide "
        "finishing but may be easier for defenses to neutralize."
    )
    st.divider()

# ============================================================================
# POSITION BREAKDOWN
# ============================================================================
st.subheader("📋 Position-by-Position Breakdown")
if 'position' in filtered.columns:
    pos_list = sorted(filtered['position'].unique())
    tabs = st.tabs([f"{p} ({len(filtered[filtered['position']==p])})" for p in pos_list[:5]])

    for i, pos in enumerate(pos_list[:5]):
        with tabs[i]:
            pos_df = filtered[filtered['position'] == pos].nlargest(10, 'goal_contribution')
            display_cols = ['player_name', 'nation_code', 'club_team', 'goals', 'assists', 'xg', 'xa', 'minutes']
            avail = [c for c in display_cols if c in pos_df.columns]
            st.dataframe(
                pos_df[avail].sort_values('goals', ascending=False),
                column_config={
                    "player_name": st.column_config.TextColumn("Player"),
                    "nation_code": st.column_config.TextColumn("Nation"),
                    "club_team": st.column_config.TextColumn("Club"),
                    "goals": st.column_config.NumberColumn("Goals", format="%d"),
                    "assists": st.column_config.NumberColumn("Assists", format="%d"),
                    "xg": st.column_config.NumberColumn("xG", format="%.1f"),
                    "xa": st.column_config.NumberColumn("xA", format="%.1f"),
                    "minutes": st.column_config.NumberColumn("Minutes", format="%d"),
                },
                hide_index=True,
                width='stretch'
            )
    st.divider()

# ============================================================================
# NATION CONTRIBUTION ANALYSIS
# ============================================================================
st.subheader("🏳️ Nation Contribution Heatmap")
if 'nation_code' in filtered.columns:
    nat_agg = filtered.groupby('nation_code').agg(
        total_goals=('goals', 'sum'),
        total_assists=('assists', 'sum'),
        total_xg=('xg', 'sum'),
        player_count=('player_name', 'count'),
        avg_age=('age', 'mean')
    ).reset_index().sort_values('total_goals', ascending=False)

    top_nations = nat_agg.head(15)

    fig_heat = go.Figure(data=go.Heatmap(
        z=top_nations[['total_goals', 'total_assists', 'total_xg']].values,
        x=['Goals', 'Assists', 'xG'],
        y=top_nations['nation_code'],
        colorscale=[[0, '#ffffff'], [0.5, '#7B00FF'], [1, '#FF004D']],
        text=top_nations[['total_goals', 'total_assists', 'total_xg']].round(1).values,
        texttemplate='%{text}',
        hovertemplate='%{y}: %{x} = %{z}<extra></extra>'
    ))
    fig_heat.update_layout(
        paper_bgcolor='#ffffff',
        plot_bgcolor='#ffffff',
        font=dict(color='#000000', family='Noto Sans'),
        title=dict(text="Top 15 Nations: Goal Contribution Heatmap", font=dict(family='Bebas Neue', size=18)),
        height=500
    )
    st.plotly_chart(fig_heat, width='stretch')

    top_nat = top_nations.iloc[0]
    info_card("Nation Insight",
        f"**{top_nat['nation_code']}** contributes the most goals ({top_nat['total_goals']:.0f}) from {top_nat['player_count']:.0f} players "
        f"with an average age of {top_nat['avg_age']:.1f}. "
        f"{'This squad blends youth and experience effectively.' if 25 <= top_nat['avg_age'] <= 29 else 'A younger squad may bring energy but lack tournament experience.' if top_nat['avg_age'] < 25 else 'A veteran-heavy squad brings experience but may face stamina concerns.'}"
    )
    st.divider()

# ============================================================================
# AGE DISTRIBUTION
# ============================================================================
st.subheader("📊 Age Distribution & Experience Profile")
if 'age' in filtered.columns and (filtered['age'] > 0).any():
    fig_age = px.histogram(
        filtered[filtered['age'] > 0],
        x='age',
        nbins=15,
        color='position' if 'position' in filtered.columns else None,
        color_discrete_sequence=['#FF004D', '#7B00FF', '#00F0FF', '#00FF00', '#FF4D00'],
        labels={'age': 'Player Age', 'position': 'Position'},
        title="Age Distribution Across World Cup Squad Players"
    )
    fig_age.update_layout(
        paper_bgcolor='#ffffff',
        plot_bgcolor='#ffffff',
        font=dict(color='#000000', family='Noto Sans'),
        title=dict(font=dict(family='Bebas Neue', size=18)),
        bargap=0.1
    )
    st.plotly_chart(fig_age, width='stretch')

    avg_age = filtered[filtered['age'] > 0]['age'].mean()
    youngest = filtered[filtered['age'] > 0].nsmallest(1, 'age').iloc[0]
    oldest = filtered[filtered['age'] > 0].nlargest(1, 'age').iloc[0]

    ac1, ac2, ac3 = st.columns(3)
    with ac1:
        st.metric("Average Age", f"{avg_age:.1f} yrs")
    with ac2:
        st.metric("Youngest", f"{youngest['player_name']}", f"{youngest['age']:.0f} yrs")
    with ac3:
        st.metric("Oldest", f"{oldest['player_name']}", f"{oldest['age']:.0f} yrs")