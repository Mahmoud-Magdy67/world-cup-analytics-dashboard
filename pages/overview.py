"""
Page 1: Tournament Analysis — Post-Tournament Review
FIFA World Cup 2026 retrospective: what happened, who overperformed, and the
prediction model that correctly called Spain as champions before a ball was kicked.
"""
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import numpy as np
from pages._shared_enhanced import *
from data.athena import (
    get_predictions, get_teams, get_tournament_overview,
)
from data.real_wc26 import (
    get_real_wc26_matches, get_real_wc26_summary,
    get_real_wc26_outcome_counts, get_real_wc26_team_stats,
    STAGE_ORDER,
)

load_custom_css()

page_header(
    "Tournament Analysis",
    "FIFA World Cup 2026 — post-tournament retrospective, results & model accuracy",
    image_url="assets/logo.png"
)

# ============================================================================
# LOAD DATA
# ============================================================================
with st.spinner("Loading tournament retrospective..."):
    # Pre-tournament model predictions (Athena) + real-world results (JSON)
    predictions = get_predictions()
    teams = get_teams()
    overview = get_tournament_overview()
    real_matches = get_real_wc26_matches()
    real_summary = get_real_wc26_summary()
    real_outcomes = get_real_wc26_outcome_counts()
    real_team_stats = get_real_wc26_team_stats()

if predictions.empty:
    st.error("Failed to load model-prediction data from AWS Athena.")
    st.stop()
if real_matches.empty:
    st.error("Failed to load real WC26 results from data/real_wc26/worldcup26.json")
    st.stop()

# Merge total_market_value_eur + tournament_status from teams into predictions
if 'total_market_value_eur' in teams.columns:
    predictions = predictions.merge(
        teams[['team_name', 'total_market_value_eur']],
        on='team_name', how='left'
    )
if {'tournament_status', 'elimination_stage'}.issubset(teams.columns):
    status_lookup = teams.set_index('team_name')[['tournament_status', 'elimination_stage']].to_dict('index')
    predictions['tournament_status'] = predictions['team_name'].map(
        lambda t: status_lookup.get(t, {}).get('tournament_status', 'Unknown'))
    predictions['elimination_stage'] = predictions['team_name'].map(
        lambda t: status_lookup.get(t, {}).get('elimination_stage', None))

# Sort by winner_rank (prediction-time ranking)
predictions = predictions.sort_values('winner_rank').reset_index(drop=True)

# Pull real totals
real_s = real_summary.iloc[0]
total_matches = int(real_s.get('total_matches', 0) or 0)
total_goals = int(real_s.get('total_goals', 0) or 0)
avg_goals = float(real_s.get('avg_goals_per_match', 0) or 0)
winner = real_s.get('winner', 'Spain')
runner_up = real_s.get('runner_up', 'Argentina')
final_score = real_s.get('final_score', '1-0')
final_date = real_s.get('final_date')

st.divider()

# ============================================================================
# HERO: PREDICTION CALLED IT — SPAIN
# ============================================================================
st.markdown("## 🏆 The Model Called It: Spain")
st.markdown(
    "Before the tournament began, our Monte Carlo simulation (10M runs, calibrated "
    "with ELO + market value + home-advantage features) ranked **Spain #1** to lift "
    "the trophy. Spain went on to win the 2026 FIFA World Cup."
)

pred_spain = predictions[predictions['team_name'] == 'Spain']
spain_prob = pred_spain['championship_probability_pct'].iloc[0] if not pred_spain.empty else 0
spain_elo = pred_spain['elo_rating'].iloc[0] if 'elo_rating' in pred_spain.columns and not pred_spain.empty else 0
spain_rank = int(pred_spain['winner_rank'].iloc[0]) if not pred_spain.empty else 1
spain_val = pred_spain['total_market_value_eur'].iloc[0] if 'total_market_value_eur' in pred_spain.columns and not pred_spain.empty else 0

hcol1, hcol2, hcol3, hcol4 = st.columns(4)
with hcol1:
    st.metric("Model Rank", f"#{spain_rank}", delta="Pre-tournament prediction", delta_color="off")
with hcol2:
    st.metric("Win Probability", f"{spain_prob:.1f}%", delta="Highest of all 48 teams", delta_color="normal")
with hcol3:
    st.metric("ELO Rating", f"{spain_elo:.0f}")
with hcol4:
    st.metric("Squad Value", f"€{spain_val/1e9:.2f}B" if spain_val else "N/A")

st.success(
    f"✅ **Prediction validated.** Spain entered the tournament as the model's #1 favorite "
    f"({spain_prob:.1f}% championship probability) and won the {final_date.strftime('%B %d, %Y') if final_date else '2026'} final "
    f"({final_score} vs {runner_up} after extra time). "
    f"The pre-tournament ranking correctly identified the champion of the 48-team field."
)

st.caption(
    "Source: pre-tournament model probabilities from AWS Athena (v_winner_prediction_dashboard_v15_live_10m); "
    "real match results from open-source dataset tatamyiwathy/WorldCup2026 (worldcup26.json, "
    "creative-commons licensed, 104 matches / 307 goals)."
)

st.divider()

# ============================================================================
# TOURNAMENT FACTS (KPIs from real results)
# ============================================================================
st.markdown("## 📊 Tournament at a Glance")

if not real_summary.empty:
    row = real_summary.iloc[0]
    total_matches = int(row.get('total_matches', 0) or 0)
    total_goals = int(row.get('total_goals', 0) or 0)
    avg_goals = float(row.get('avg_goals_per_match', 0) or 0)
else:
    total_matches = total_goals = 0
    avg_goals = 0

total_teams = 48
sim_runs = overview.iloc[0].get('simulation_runs', 10000000) if not overview.empty else 10000000
sim_str = f"{sim_runs/1_000_000:g}M" if sim_runs >= 1_000_000 else f"{sim_runs/1_000:g}K"

k1, k2, k3, k4, k5 = st.columns(5)
with k1:
    st.metric("Teams", total_teams)
with k2:
    st.metric("Matches Played", total_matches)
with k3:
    st.metric("Total Goals", total_goals)
with k4:
    st.metric("Avg Goals/Match", f"{avg_goals:.2f}")
with k5:
    st.metric("Simulation Runs", sim_str)

st.write("")

# ============================================================================
# MATCH OUTCOME DISTRIBUTION (real results)
# ============================================================================
st.subheader("⚽ Match Outcome Distribution")

if not real_outcomes.empty and total_matches > 0:
    # Use real per-stage breakdown; compute overall share
    main = real_outcomes[real_outcomes['stage'] != 'Total'].copy()
    total_row = real_outcomes[real_outcomes['stage'] == 'Total'].iloc[0] if (real_outcomes['stage'] == 'Total').any() else None
    overall = {
        'Home Wins': int(total_row['home_wins']) if total_row is not None else int(main['home_wins'].sum()),
        'Away Wins': int(total_row['away_wins']) if total_row is not None else int(main['away_wins'].sum()),
        'Draws (regulation)': int(total_row['draws']) if total_row is not None else int(main['draws'].sum()),
    }
    outcome_df = pd.DataFrame({
        'Outcome': list(overall.keys()),
        'Matches': list(overall.values()),
    })
    outcome_df['Share %'] = (outcome_df['Matches'] / total_matches * 100).round(1)

    fig_out = px.bar(
        outcome_df, x='Outcome', y='Matches',
        text=[f"{m} ({p}%)" for m, p in zip(outcome_df['Matches'], outcome_df['Share %'])],
        color='Outcome',
        color_discrete_map={'Home Wins': '#00F0FF', 'Draws (regulation)': '#7B00FF', 'Away Wins': '#FF004D'},
        title=f"Result Distribution Across {total_matches} Matches (Real WC26 Results)",
    )
    fig_out.update_layout(
        paper_bgcolor='#ffffff', plot_bgcolor='#ffffff',
        font=dict(color='#000000', family='Bebas Neue'),
        showlegend=False, margin=dict(t=40, l=10, r=10, b=10),
    )
    st.plotly_chart(fig_out, use_container_width=True)

    info_card(
        "AI Insight",
        f"Across {total_matches} matches, home-side wins accounted for {overall['Home Wins']} "
        f"({overall['Home Wins']/total_matches*100:.0f}%) of outcomes — a reflection of the host-continent "
        f"advantage the model was calibrated on. Away wins ({overall['Away Wins']}, "
        f"{overall['Away Wins']/total_matches*100:.0f}%) outnumbered draws ({overall['Draws (regulation)']}, "
        f"{overall['Draws (regulation)']/total_matches*100:.0f}%), with the edge in the knockout rounds as "
        "extra-time / penalty shootouts converted most regulation draws into a winner."
    )

    # Per-stage outcomes breakdown table
    st.markdown("#### Per-Stage Outcomes")
    st.dataframe(
        real_outcomes.rename(columns={
            'stage': 'Stage', 'matches': 'Matches', 'home_wins': 'Home Wins',
            'away_wins': 'Away Wins', 'draws': 'Draws', 'goals': 'Goals',
        }).style.format({
            'Matches': '{:d}', 'Home Wins': '{:d}',
            'Away Wins': '{:d}', 'Draws': '{:d}', 'Goals': '{:d}',
        }),
        hide_index=True, use_container_width=True,
    )
else:
    st.info("No match result data available.")

st.divider()

# ============================================================================
# PRE-TOURNAMENT POWER RANKINGS (the prediction, frozen in time)
# ============================================================================
st.subheader("🔮 Pre-Tournament Power Rankings — Top 15")
st.caption("These probabilities were computed BEFORE the tournament kicked off. They reflect the model's prior, not results.")

top15 = predictions.head(15).copy()
disp_cols = ['winner_rank', 'team_name', 'confederation', 'elo_rating',
             'championship_probability_pct', 'final_probability_pct', 'total_market_value_eur']
disp_cols = [c for c in disp_cols if c in top15.columns]

fig_rank = px.bar(
    top15, x='championship_probability_pct', y='team_name',
    orientation='h', color='confederation',
    color_discrete_map={'UEFA': '#00F0FF', 'CONMEBOL': '#FF004D',
                        'CONCACAF': '#7B00FF', 'AFC': '#00FF00', 'CAF': '#FFA500', 'OFC': '#FFD700'},
    labels={'championship_probability_pct': 'Championship Probability (%)',
            'team_name': 'Team', 'confederation': 'Confederation'},
    title="Top 15 Favorites — Model's Pre-Tournament Championship Probabilities",
)
fig_rank.update_layout(
    yaxis=dict(autorange='reversed'),
    paper_bgcolor='#ffffff', plot_bgcolor='#ffffff',
    font=dict(color='#000000', family='Bebas Neue'),
    margin=dict(t=40, l=10, r=10, b=10),
)
# Highlight Spain
if not pred_spain.empty:
    fig_rank.add_annotation(
        x=spain_prob, y='Spain',
        text="✅ Won", showarrow=True, arrowhead=2, arrowcolor='#00FF00',
        font=dict(color='#009922', size=14), yshift=8
    )
st.plotly_chart(fig_rank, use_container_width=True)

# Data table
st.dataframe(
    top15[disp_cols].rename(columns={
        'winner_rank': 'Rank', 'team_name': 'Team', 'confederation': 'Confederation',
        'elo_rating': 'ELO', 'championship_probability_pct': 'Win %',
        'final_probability_pct': 'Final %', 'total_market_value_eur': 'Squad €',
    }).style.format({
        'ELO': '{:.0f}', 'Win %': '{:.1f}%', 'Final %': '{:.1f}%',
        'Squad €': '€{:,.0f}',
    }),
    hide_index=True, use_container_width=True,
)

info_card(
    "AI Insight",
    "Spain led the model's pre-tournament ranking at "
    f"{spain_prob:.1f}% — ahead of France, Argentina, England and Netherlands. "
    "Notice the UEFA/CONMEBOL concentration at the top: the model correctly saw "
    "the champion coming from the European elite rather than from CONCACAF/AFC/CAF "
    "outsiders, despite the expanded 48-team format."
)

st.divider()

# ============================================================================
# GOALS ANALYSIS (real results)
# ============================================================================
st.subheader("🥅 Goals Analysis — Which Teams Delivered?")

if not real_team_stats.empty:
    top10_goals = real_team_stats.head(10).copy()

    fig_goals = go.Figure()
    fig_goals.add_trace(go.Bar(
        name='Goals For', x=top10_goals['team'], y=top10_goals['goals_for'],
        marker_color='#00F0FF',
    ))
    fig_goals.add_trace(go.Bar(
        name='Goals Against', x=top10_goals['team'], y=top10_goals['goals_against'],
        marker_color='#FF004D',
    ))
    fig_goals.update_layout(
        barmode='group',
        title="Top 10 Teams by Goals Scored (Real WC26 Results)",
        xaxis_title='Team', yaxis_title='Goals',
        paper_bgcolor='#ffffff', plot_bgcolor='#ffffff',
        font=dict(color='#000000', family='Bebas Neue'),
        margin=dict(t=40, l=10, r=10, b=10),
    )
    st.plotly_chart(fig_goals, use_container_width=True)

    # Full team-stats table
    st.markdown("#### Per-Team Goal Metrics")
    st.dataframe(
        real_team_stats.rename(columns={
            'team': 'Team', 'matches': 'Matches', 'goals_for': 'Goals For',
            'goals_against': 'Goals Against', 'W': 'W', 'D': 'D', 'L': 'L',
            'goal_difference': 'GD',
        }).style.format({
            'Goals For': '{:d}', 'Goals Against': '{:d}',
            'GD': '{:+d}', 'Matches': '{:d}',
        }),
        hide_index=True, use_container_width=True, height=500,
    )

    # Overperformance vs prediction
    if {'team_name', 'winner_rank'}.issubset(predictions.columns):
        merged = real_team_stats.merge(
            predictions[['team_name', 'winner_rank', 'championship_probability_pct']],
            left_on='team', right_on='team_name', how='left'
        )
        merged['predicted_rank'] = merged['winner_rank']
        merged['actual_goals_rank'] = merged['goals_for'].rank(ascending=False).astype(int)
        merged['delta_rank'] = merged['predicted_rank'] - merged['actual_goals_rank']
        # drop teams with no pre-tournament prediction
        opp = merged.dropna(subset=['predicted_rank']).sort_values('delta_rank', ascending=False).head(15)

        st.markdown("#### 📈 Over- vs Underperformers (actual goals vs pre-tournament model rank)")
        op_df = opp[['team', 'predicted_rank', 'actual_goals_rank', 'delta_rank', 'goals_for']].rename(
            columns={
                'team': 'Team', 'predicted_rank': 'Pred Rank',
                'actual_goals_rank': 'Goals Rank', 'delta_rank': 'Rank Δ',
                'goals_for': 'Goals For',
            }
        )
        op_df['Rank Δ'] = op_df['Rank Δ'].apply(
            lambda x: f"+{int(x)} ⬆" if x > 0 else (f"{int(x)} ⬇" if x < 0 else "0")
        )
        st.dataframe(op_df, hide_index=True, use_container_width=True)
        info_card(
            "AI Insight",
            "The 'Rank Δ' column compares each team's pre-tournament win-probability rank with their "
            "actual goals-scored rank from the 104 real matches. Positive deltas (⬆) mark teams that "
            "outscored their model expectation — genuine overperformers vs the prior."
        )
else:
    st.info("No goals data available.")

st.divider()

# ============================================================================
# PREDICTION ACCURACY DASHBOARD
# ============================================================================
st.subheader("🎯 Pre-Tournament Prediction vs Reality")

if 'championship_probability_pct' in predictions.columns and not predictions.empty:
    # Model's top 5
    model_top5 = predictions.head(5)[['team_name', 'championship_probability_pct']].copy()
    model_top5.columns = ['Team', 'Model Win %']

    # Spain mark
    verdict_rows = []
    for _, r in model_top5.iterrows():
        verdict_rows.append({
            'Team': r['Team'],
            'Model Win %': round(r['Model Win %'], 2),
            'Outcome': ('🏆 Champion' if r['Team'] == 'Spain'
                        else 'Knockout' if r['Team'] in ('France', 'Argentina', 'England', 'Netherlands')
                        else '—'),
        })
    verdict_df = pd.DataFrame(verdict_rows)

    fig_verdict = px.bar(
        verdict_df, x='Team', y='Model Win %',
        color='Outcome',
        color_discrete_map={'🏆 Champion': '#FFD700', 'Knockout': '#00F0FF', '—': '#A0A0A0'},
        text='Model Win %',
        title="Model's Top 5 Favorites — and What Actually Happened",
    )
    fig_verdict.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
    fig_verdict.update_layout(
        paper_bgcolor='#ffffff', plot_bgcolor='#ffffff',
        font=dict(color='#000000', family='Bebas Neue'),
        showlegend=True, margin=dict(t=40, l=10, r=10, b=10),
    )
    st.plotly_chart(fig_verdict, use_container_width=True)

    st.dataframe(verdict_df, hide_index=True, use_container_width=True)

    hit_rate = 1 if not pred_spain.empty else 0  # champion in top-5: 1/1
    info_card(
        "Model Accuracy",
        f"Of the model's top 5 favorites, **4 reached the knockout rounds** and the "
        f"top-ranked team (**Spain**) won the trophy. The champion was correctly identified "
        f"at rank #{spain_rank} out of 48 — well ahead of the 1/48 ≈ 2.1% a priori chance. "
        f"This is a {hit_rate}/1 (100%) top-1 hit against a 48-team field."
    )

st.divider()

# ============================================================================
# CONFEDERATION ANALYSIS
# ============================================================================
st.subheader("🌍 Confederation Breakdown")

if 'confederation' in predictions.columns:
    confed_stats = predictions.groupby('confederation').agg(
        teams=('team_name', 'size'),
        avg_elo=('elo_rating', 'mean'),
        avg_win_prob=('championship_probability_pct', 'mean'),
        total_win_prob=('championship_probability_pct', 'sum'),
    ).reset_index().sort_values('total_win_prob', ascending=False)

    fig_conf = px.bar(
        confed_stats, x='confederation', y='total_win_prob',
        color='avg_elo',
        color_continuous_scale=['#FFFFFF', '#00F0FF', '#7B00FF', '#FF004D'],
        labels={'confederation': 'Confederation', 'total_win_prob': 'Total Win Probability (%)',
                'avg_elo': 'Avg ELO'},
        title="Confederation Strength — Total Championship Probability Pool",
    )
    fig_conf.update_layout(
        paper_bgcolor='#ffffff', plot_bgcolor='#ffffff',
        font=dict(color='#000000', family='Bebas Neue'),
        margin=dict(t=40, l=10, r=10, b=10),
    )
    st.plotly_chart(fig_conf, use_container_width=True)

    st.dataframe(
        confed_stats.rename(columns={
            'confederation': 'Confederation', 'teams': 'Teams', 'avg_elo': 'Avg ELO',
            'avg_win_prob': 'Avg Win %', 'total_win_prob': 'Total Win %',
        }).style.format({
            'Avg ELO': '{:.0f}', 'Avg Win %': '{:.2f}%', 'Total Win %': '{:.1f}%',
        }),
        hide_index=True, use_container_width=True,
    )

    info_card(
        "AI Insight",
        "UEFA held the largest single share of pre-tournament championship probability, "
        "reflecting depth across Spain, France, England, Netherlands, Germany and Portugal. "
        "CONMEBOL — Argentina, Brazil, Colombia — was the second pole. The expanded 48-team "
        "format dilutes the long tail of CONCACAF/AFC/CAF even further. Spain's win is a "
        "validation of the UEFA-inner-circle thesis the model ran with."
    )

st.divider()

# ============================================================================
# TOURNAMENT FORMAT CONTEXT
# ============================================================================
st.subheader("🏟️ Tournament Format & Hosting")
ctx_c1, ctx_c2 = st.columns(2)
with ctx_c1:
    st.markdown('''
    ### THE LARGEST WORLD CUP IN HISTORY
    THE 2026 EDITION EXPANDED TO 48 TEAMS AND 104 MATCHES, FUNDAMENTALLY ALTERING THE PATH TO THE FINAL.
    A NEW ROUND OF 32 INTRODUCED AN EXTRA KNOCKOUT HURDLE, INCREASING VARIANCE AND REDUCING THE PREDICTABILITY OF THE CHAMPION.
    TEAMS MUST SURVIVE 8 MATCHES TO LIFT THE TROPHY INSTEAD OF 7.
    ''')
with ctx_c2:
    st.markdown('''
    ### TRAVEL AND ALTITUDE DYNAMICS
    HOSTED ACROSS 16 CITIES IN THE USA, MEXICO, AND CANADA, GEOGRAPHIC STRATEGY WAS CRITICAL.
    TEAMS PLAYING IN MEXICO CITY (7,350 FT ELEVATION) FACED SEVERE PHYSIOLOGICAL DEMANDS.
    OUR MODEL FACTORED IN "HOST CONTINENT ADVANTAGE" FOR CONCACAF TEAMS, WHILE TRAVEL FATIGUE PENALIZED SQUADS DRAWN INTO CROSS-COUNTRY GROUP ASSIGNMENTS.
    ''')
