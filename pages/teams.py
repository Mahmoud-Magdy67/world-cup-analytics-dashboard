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
        
        strongest_idx = np.argmax(team_vals[:-1])
        weakest_idx = np.argmin(team_vals[:-1])
        strongest = cats[strongest_idx]
        weakest = cats[weakest_idx]
        strongest_diff = team_vals[strongest_idx] - avg_vals[strongest_idx]
        
        insight_text = f"Based on ML-hybrid FIFA attributes, {sel_team}'s strongest distinct tactical attribute is **{strongest}** "
        if strongest_diff > 0:
            insight_text += f"(+{strongest_diff:.1f} above tournament average). "
        else:
            insight_text += f"({strongest_diff:.1f} compared to average). "
            
        insight_text += f"Conversely, their most vulnerable area is **{weakest}**, which opponents may look to exploit in knockout stages."
        
        info_card("Tactical Insight", insight_text)
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
# Calculate how many teams are in the elite quadrant for the current view
elite_teams = scatter_df[(scatter_df['attack_strength'] > avg_atk) & (scatter_df['defense_strength'] > avg_def)]
elite_count = len(elite_teams)

insight_text = f"Teams in the top-right quadrant possess both elite attacking and defensive capabilities—a hallmark of deep tournament runs. "
if elite_count > 0:
    elite_names = ", ".join(elite_teams['team_name'].head(3).tolist())
    insight_text += f"Currently, {elite_count} team{'s' if elite_count > 1 else ''} in this view fall into this 'Elite Balance' category (e.g., {elite_names}). "
else:
    insight_text += "No teams in the current filter view meet the 'Elite Balance' threshold. "

insight_text += "Teams in the top-left rely heavily on outscoring opponents to compensate for defensive frailties."

info_card("Matrix Insight", insight_text)

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


# Add Financial Disparity Insight
if len(filtered) > 1 and 'total_market_value_eur' in filtered.columns:
    highest_val_team = filtered.loc[filtered['total_market_value_eur'].idxmax()]
    lowest_val_team = filtered.loc[filtered['total_market_value_eur'].idxmin()]
    
    # Avoid division by zero
    lowest_val = max(lowest_val_team['total_market_value_eur'], 100000)
    multiplier = highest_val_team['total_market_value_eur'] / lowest_val
    
    info_card(
        "Financial Disparity Insight", 
        f"The financial gap between teams is massive. **{highest_val_team['team_name']}** has a squad value of €{highest_val_team['total_market_value_eur']/1e9:.2f}B, which is roughly **{multiplier:.1f}x** greater than the squad value of **{lowest_val_team['team_name']}**. Despite this, ELO ratings often demonstrate a much closer competitive reality on the pitch."
    )

st.divider()

# ============================================================================
# ELO vs SQUAD VALUE (VALUE-FOR-MONEY ANALYSIS)
# ============================================================================
st.subheader("💰 ELO vs Squad Value: Value-for-Money Analysis")

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
        'elo_rating': 'ELO Rating',
        confed_col: 'Confederation'
    },
    title="Trend line = Expected ELO for a Given Squad Investment"
)
fig_value.update_layout(
    paper_bgcolor='#ffffff',
    plot_bgcolor='#ffffff',
    font=dict(color='#000000', family='Noto Sans'),
    title=dict(font=dict(family='Bebas Neue', size=18))
)
st.plotly_chart(fig_value, width='stretch')

# Compute over/underperformers
trend_df = filtered.dropna(subset=['elo_rating', 'total_market_value_eur']).copy()
if len(trend_df) > 2:
    # Simple linear regression for residuals
    from numpy.polynomial import polynomial as P
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
            st.markdown("#### 📈 Overperformers (High ELO Relative to Spend)")
            for _, r in over.iterrows():
                st.markdown(f"- **{r['team_name']}** — ELO {r['elo_rating']:.0f} (+{r['elo_residual']:.0f} above expected)")
        with oc2:
            st.markdown("#### 📉 Underperformers (Low ELO Relative to Spend)")
            for _, r in under.iterrows():
                st.markdown(f"- **{r['team_name']}** — ELO {r['elo_rating']:.0f} ({r['elo_residual']:.0f} below expected)")

    info_card(
        "Value-for-Money Insight",
        f"The trend line shows the expected ELO rating for a given squad investment. Teams above the line are **overperforming** — they extract more competitive quality from their financial resources than the tournament average. Teams below the line may be **underperforming** relative to their financial firepower, which could point to inefficiencies in talent identification or tactical utilization."
    )

st.divider()

# ============================================================================
# CONFEDERATION STRENGTH COMPARISON
# ============================================================================
if confed_col in filtered.columns and filtered[confed_col].nunique() > 1:
    st.subheader("🌐 Confederation Strength Comparison")

    confed_stats = filtered.groupby(confed_col).agg(
        avg_elo=('elo_rating', 'mean'),
        avg_attack=('attack_strength', 'mean'),
        avg_defense=('defense_strength', 'mean'),
        avg_midfield=('midfield_strength', 'mean'),
        avg_value=('total_market_value_eur', 'mean'),
        team_count=('team_name', 'count')
    ).reset_index()

    metrics = ['avg_elo', 'avg_attack', 'avg_defense', 'avg_midfield']
    metric_labels = ['Avg ELO', 'Avg Attack', 'Avg Defense', 'Avg Midfield']

    cc1, cc2 = st.columns(2)
    for idx, (col, cc) in enumerate(zip(metrics[:2], [cc1, cc2])):
        fig_confed = px.bar(
            confed_stats, x=confed_col, y=col,
            color=confed_col,
            color_discrete_sequence=['#FF004D', '#7B00FF', '#00F0FF', '#00FF00', '#FF4D00'],
            text_auto='.1f',
            labels={col: metric_labels[idx], confed_col: 'Confederation'},
        )
        fig_confed.update_layout(
            showlegend=False,
            paper_bgcolor='#ffffff',
            plot_bgcolor='#ffffff',
            font=dict(color='#000000', family='Noto Sans'),
            title=dict(text=metric_labels[idx], font=dict(family='Bebas Neue', size=16))
        )
        cc.plotly_chart(fig_confed, width='stretch')

    cc3, cc4 = st.columns(2)
    for idx, (col, cc) in enumerate(zip(metrics[2:], [cc3, cc4])):
        fig_confed = px.bar(
            confed_stats, x=confed_col, y=col,
            color=confed_col,
            color_discrete_sequence=['#FF004D', '#7B00FF', '#00F0FF', '#00FF00', '#FF4D00'],
            text_auto='.1f',
            labels={col: metric_labels[idx + 2], confed_col: 'Confederation'},
        )
        fig_confed.update_layout(
            showlegend=False,
            paper_bgcolor='#ffffff',
            plot_bgcolor='#ffffff',
            font=dict(color='#000000', family='Noto Sans'),
            title=dict(text=metric_labels[idx + 2], font=dict(family='Bebas Neue', size=16))
        )
        cc.plotly_chart(fig_confed, width='stretch')

    # Identify strongest confederation
    strongest_confed = confed_stats.loc[confed_stats['avg_elo'].idxmax()]
    weakest_confed = confed_stats.loc[confed_stats['avg_elo'].idxmin()]
    elo_gap = strongest_confed['avg_elo'] - weakest_confed['avg_elo']

    info_card(
        "Confederation Power Rankings",
        f"**{strongest_confed[confed_col]}** leads with the highest average ELO ({strongest_confed['avg_elo']:.0f}), "
        f"while **{weakest_confed[confed_col]}** trails ({weakest_confed['avg_elo']:.0f}). "
        f"The ELO gap of {elo_gap:.0f} points between the strongest and weakest confederations reflects the competitive "
        f"hierarchy in world football. In World Cup tournaments, teams from stronger confederations typically advance "
        f"deeper into the knockout stages, though tactical discipline can bridge the gap."
    )
    st.divider()

# ============================================================================
# TOURNAMENT PROGRESSION FUNNEL
# ============================================================================
st.subheader("🏅 Tournament Progression Funnel")

# Load predictions for stage probabilities
try:
    from data.bigquery_enhanced import get_predictions
    preds = get_predictions()
    if not preds.empty:
        funnel_stages = [
            ('championship_probability_pct', 'Champion'),
            ('final_probability_pct', 'Final'),
            ('semifinal_probability_pct', 'Semifinal'),
            ('quarterfinal_probability_pct', 'Quarterfinal'),
            ('round16_probability_pct', 'Round of 16'),
        ]
        # Filter to selected teams
        funnel_df = preds[preds['team_name'].isin(filtered['team_name'])].copy()
        if not funnel_df.empty:
            # Show top 10 by championship probability
            top_funnel = funnel_df.nlargest(10, 'championship_probability_pct')

            fig_funnel = go.Figure()
            for _, row in top_funnel.iterrows():
                fig_funnel.add_trace(go.Bar(
                    name=row['team_name'],
                    x=[s[1] for s in funnel_stages],
                    y=[row.get(s[0], 0) for s in funnel_stages],
                ))
            fig_funnel.update_layout(
                barmode='group',
                paper_bgcolor='#ffffff',
                plot_bgcolor='#ffffff',
                font=dict(color='#000000', family='Noto Sans'),
                title=dict(text="Top 10 Teams: Stage-by-Stage Probability (%)", font=dict(family='Bebas Neue', size=18)),
                yaxis_title="Probability (%)",
                xaxis_title="Tournament Stage",
                legend=dict(font=dict(family='Noto Sans'))
            )
            st.plotly_chart(fig_funnel, width='stretch')

            # Identify biggest droppers
            if 'championship_probability_pct' in top_funnel.columns and 'round16_probability_pct' in top_funnel.columns:
                top_funnel_copy = top_funnel.copy()
                top_funnel_copy['drop_off'] = top_funnel_copy['round16_probability_pct'] - top_funnel_copy['championship_probability_pct']
                biggest_dropper = top_funnel_copy.nlargest(1, 'drop_off')

                if not biggest_dropper.empty:
                    bd = biggest_dropper.iloc[0]
                    info_card(
                        "Progression Insight",
                        f"**{bd['team_name']}** has a {bd['round16_probability_pct']:.1f}% chance of reaching the Round of 16, "
                        f"but their championship probability drops to just {bd['championship_probability_pct']:.1f}% — "
                        f"a {bd['drop_off']:.1f} percentage point drop-off. This suggests they are likely to reach the "
                        f"knockout rounds but face a significant competitive cliff in the deeper stages."
                    )
    else:
        st.info("No prediction data available for the current filter.")
except Exception as e:
    st.warning(f"Could not load tournament progression data: {e}")

st.divider()

# ============================================================================
# GROUP OF DEATH ANALYSIS
# ============================================================================
st.subheader("💀 Group of Death Analysis")

if 'group_name' in filtered.columns and 'elo_rating' in filtered.columns:
    group_analysis = filtered.groupby('group_name').agg(
        avg_elo=('elo_rating', 'mean'),
        std_elo=('elo_rating', 'std'),
        min_elo=('elo_rating', 'min'),
        max_elo=('elo_rating', 'max'),
        team_count=('team_name', 'count'),
        total_value=('total_market_value_eur', 'sum')
    ).reset_index().sort_values('avg_elo', ascending=False)

    # Group of Death = highest average ELO + lowest std (most competitive)
    group_analysis['competitiveness'] = group_analysis['avg_elo'] / (group_analysis['std_elo'] + 1)

    fig_group = px.bar(
        group_analysis,
        x='group_name',
        y='avg_elo',
        color='avg_elo',
        color_continuous_scale=['#00F0FF', '#7B00FF', '#FF004D'],
        text_auto='.0f',
        labels={'avg_elo': 'Average ELO', 'group_name': 'Group'},
        title="Average ELO by Group (Higher = Harder Group)"
    )
    fig_group.update_layout(
        paper_bgcolor='#ffffff',
        plot_bgcolor='#ffffff',
        font=dict(color='#000000', family='Noto Sans'),
        title=dict(font=dict(family='Bebas Neue', size=18))
    )
    st.plotly_chart(fig_group, width='stretch')

    # Hardest and easiest groups
    hardest = group_analysis.iloc[0]
    easiest = group_analysis.iloc[-1]

    gc1, gc2 = st.columns(2)
    with gc1:
        st.markdown(f"#### 🔴 Hardest Group: {hardest['group_name']}")
        st.markdown(f"- Avg ELO: **{hardest['avg_elo']:.0f}**")
        st.markdown(f"- ELO Range: {hardest['min_elo']:.0f} – {hardest['max_elo']:.0f}")
        st.markdown(f"- Total Squad Value: €{hardest['total_value']/1e9:.2f}B")
    with gc2:
        st.markdown(f"#### 🟢 Easiest Group: {easiest['group_name']}")
        st.markdown(f"- Avg ELO: **{easiest['avg_elo']:.0f}**")
        st.markdown(f"- ELO Range: {easiest['min_elo']:.0f} – {easiest['max_elo']:.0f}")
        st.markdown(f"- Total Squad Value: €{easiest['total_value']/1e9:.2f}B")

    elo_diff = hardest['avg_elo'] - easiest['avg_elo']
    info_card(
        "Group of Death Insight",
        f"**Group {hardest['group_name']}** is statistically the hardest group with an average ELO of {hardest['avg_elo']:.0f}. "
        f"In contrast, **Group {easiest['group_name']}** is the easiest with an average ELO of {easiest['avg_elo']:.0f}. "
        f"The {elo_diff:.0f}-point ELO gap between the hardest and easiest groups means that teams drawn into "
        f"Group {hardest['group_name']} face a significantly steeper path to the knockout rounds. Historically, "
        f"teams emerging from 'Groups of Death' either galvanize into deep-tournament contenders or suffer "
        f"from early fatigue and injury accumulation."
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
    x='overall_strength',
    y='balance_score',
    size='avg_ovr_top11',
    color=confed_col,
    color_discrete_sequence=['#FF004D', '#7B00FF', '#00F0FF', '#00FF00', '#FF4D00'],
    hover_name='team_name',
    labels={
        'overall_strength': 'Overall Tactical Strength (Avg of Atk/Def/Mid)',
        'balance_score': 'Tactical Imbalance (Std Dev — Lower = More Balanced)',
        confed_col: 'Confederation'
    },
    title="Lower Y = More Balanced | Higher X = Stronger Overall"
)
fig_balance.update_layout(
    paper_bgcolor='#ffffff',
    plot_bgcolor='#ffffff',
    font=dict(color='#000000', family='Noto Sans'),
    title=dict(font=dict(family='Bebas Neue', size=18))
)

# Add quadrant lines
avg_strength = balance_df['overall_strength'].mean()
avg_balance = balance_df['balance_score'].mean()
fig_balance.add_vline(x=avg_strength, line_dash="dash", line_color="#000000", opacity=0.4)
fig_balance.add_hline(y=avg_balance, line_dash="dash", line_color="#000000", opacity=0.4)

st.plotly_chart(fig_balance, width='stretch')

# Most balanced and most imbalanced teams
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

info_card(
    "Tactical Balance Insight",
    "The **Tactical Balance Index** measures the standard deviation between a team's Attack, Defense, and Midfield ratings. "
    "Teams with low imbalance scores have well-rounded squads — a critical factor in tournament football where opponents "
    "vary in style across 7 matches. Highly imbalanced teams (high std dev) may dominate in one phase but struggle when "
    "the game forces them into their weak zone. Historically, World Cup winners tend to have both high overall strength "
    "AND low tactical imbalance."
)
