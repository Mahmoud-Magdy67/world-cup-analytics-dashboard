"""
Page 5: Pre-Tournament Strength vs Actual Outcomes
Built from the Kaggle dataset (mominullptr/fifa-world-cup-2026-dataset):
  - teams.csv pre-tournament Elo + FIFA ranking
  - matches_detailed.csv real knockout bracket → actual stage each team reached

There is no championship-probability model in the Kaggle data, so this page
reframes what used to be "Model Predictions" as a transparent Elo / FIFA-rank
based strength index with tournament outcome overlaid.
"""
from pages._shared_enhanced import st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import numpy as np
from pages._shared_enhanced import load_custom_css, page_header, info_card, apply_dark_text_theme
from data.real_wc26 import (
    get_real_wc26_team_strength, get_real_wc26_matches, STAGE_ORDER,
)

load_custom_css("predictions")
page_header(
    "Strength Index vs Outcomes",
    "Pre-tournament Elo / FIFA ranking strength, compared to how far each team actually went.",
    image_url="assets/logo.png",
)

with st.spinner("Loading team strength and knockout bracket..."):
    strength = get_real_wc26_team_strength()       # 48 teams: elo, fifa_rank, confederation, ...
    matches = get_real_wc26_matches()               # 104 matches

if strength.empty or matches.empty:
    st.error("Failed to load Kaggle data.")
    st.stop()

# ============================================================================
# Derive the deepest stage each team reached
# ============================================================================
# Only true knockout rounds (exclude Group Stage)
KO_STAGES = ['Round of 32', 'Round of 16', 'Quarter-finals', 'Semi-finals', 'Third-place match', 'Final']
# Depth reflects tournament progression: R32 earlist exit, Final is deepest.
# Semi-finals and Third-place match share the same depth (both are top-4),
# so a semifinal loser who then played the 3rd-place match doesn't appear
# to have progressed "deeper" than a team that only reached the semis.
KO_DEPTH = {'Round of 32': 0, 'Round of 16': 1, 'Quarter-finals': 2,
            'Semi-finals': 3, 'Third-place match': 3, 'Final': 4}

knockouts = matches[matches['stage_name'].isin(KO_STAGES)].copy()

# Derive the winner of each match (no 'winner' column in the Kaggle data)
def _match_winner(row):
    h, a = row['home_score'], row['away_score']
    if h > a:
        return row['home_team_name']
    if a > h:
        return row['away_team_name']
    # Penalty shootout
    hp, ap = row.get('home_penalty_score'), row.get('away_penalty_score')
    if pd.notna(hp) and pd.notna(ap):
        return row['home_team_name'] if hp > ap else row['away_team_name']
    return None

knockouts['winner'] = knockouts.apply(_match_winner, axis=1)

# A team "reached" the deepest stage where they appear in a knockout match.
home_reached = knockouts[['home_team_name', 'stage_name']].rename(columns={'home_team_name': 'team_name'})
away_reached = knockouts[['away_team_name', 'stage_name']].rename(columns={'away_team_name': 'team_name'})
reached = pd.concat([home_reached, away_reached], ignore_index=True)
reached['depth'] = reached['stage_name'].map(KO_DEPTH)
deepest = reached.groupby('team_name')['depth'].max().reset_index().rename(columns={'depth': 'deepest_depth'})

# Teams not in any knockout match exited at Group Stage
all_teams = strength[['team_name']].copy()
all_teams = all_teams.merge(deepest, on='team_name', how='left')
all_teams['deepest_depth'] = all_teams['deepest_depth'].fillna(-1)  # -1 = Group Stage exit

# Determine champion and runner-up from the Final
final_row = knockouts[knockouts['stage_name'] == 'Final']
if not final_row.empty:
    fr = final_row.iloc[0]
    champion = _match_winner(fr)
    runner_up = fr['away_team_name'] if fr['home_team_name'] == champion else fr['home_team_name']
else:
    champion = runner_up = None

# Map deepest_depth → human label
def outcome_label(row):
    if row['team_name'] == champion:
        return 'Champion'
    if row['team_name'] == runner_up:
        return 'Finalist'
    d = int(row['deepest_depth'])
    if d == -1:
        return 'Group Stage'
    return KO_STAGES[d]

all_teams['actual_outcome'] = all_teams.apply(outcome_label, axis=1)
# Order outcomes for chart axes (Champion → Group Stage)
outcome_order = ['Champion', 'Finalist', 'Third-place match', 'Semi-finals',
                 'Quarter-finals', 'Round of 16', 'Round of 32', 'Group Stage']
outcome_order = [o for o in outcome_order if o in all_teams['actual_outcome'].unique().tolist()] or list(all_teams['actual_outcome'].unique())

# Merge strength + actual outcome
df = strength.merge(all_teams[['team_name', 'actual_outcome']], on='team_name', how='left')

# Compute a simple Elo-based "expected depth" — purely as a transparency aid.
# We rank teams by Elo (desc) and bucket into the 8 outcomes by rank quantiles.
# This is NOT a probabilistic model, just a rank-based prior.
df = df.sort_values('elo_rating', ascending=False).reset_index(drop=True)
df['elo_rank'] = df.index + 1
# Assign each team an "expected_outcome" bucket by Elo-rank quantile (purely illustrative)
def expected_bucket(rank, n_teams, outcome_list):
    # Equal-sized buckets aligned to outcome order (Champion first)
    bucket_size = max(1, n_teams // len(outcome_list))
    idx = min(len(outcome_list) - 1, (rank - 1) // bucket_size)
    return outcome_list[idx]
df['expected_outcome'] = df['elo_rank'].apply(lambda r: expected_bucket(r, len(df), outcome_order))

# Did the team outperform or underperform their Elo bucket?
out_depth = {o: i for i, o in enumerate(outcome_order)}  # Champion=0 (shallowest), Group=7
df['expected_depth_idx'] = df['expected_outcome'].map(out_depth)
df['actual_depth_idx'] = df['actual_outcome'].map(out_depth)
# Positive delta = team went further than Elo bucket predicted
df['delta'] = df['expected_depth_idx'] - df['actual_depth_idx']

# ============================================================================
# KPIs
# ============================================================================
top_seed = df.iloc[0]  # top Elo
k1, k2, k3, k4 = st.columns(4)
with k1:
    st.metric("Teams", len(df))
with k2:
    st.metric("Top Elo Seed", f"{top_seed['team_name']} ({top_seed['elo_rating']:.0f})")
with k3:
    st.metric("Champion (actual)", champion or "—")
with k4:
    hit = "✅ Yes" if champion == top_seed['team_name'] else "❌ No"
    st.metric("Top seed won?", hit)

st.divider()

# ============================================================================
# CHART 1: Elo ranking with actual outcome colored
# ============================================================================
st.subheader("🔮 Elo Power Ranking — Top 24 by Elo, Colored by Actual Outcome")
st.caption("Elo is a pre-tournament strength signal from the Kaggle dataset. "
           "The color shows how far the team actually went in the 2026 World Cup.")

top24 = df.head(24).copy()
# Order the actual_outcome categories so the legend reads Champion → Group Stage
top24['actual_outcome'] = pd.Categorical(top24['actual_outcome'], categories=outcome_order, ordered=True)
color_map = {
    'Champion': '#FFD700', 'Finalist': '#C0C0C0', 'Third-place match': '#CD7F32',
    'Semi-finals': '#FF004D', 'Quarter-finals': '#7B00FF',
    'Round of 16': '#00F0FF', 'Round of 32': '#00FF00', 'Group Stage': '#A0A0A0',
}

fig_elo = px.bar(
    top24, x='elo_rating', y='team_name', orientation='h',
    color='actual_outcome', color_discrete_map=color_map,
    labels={'elo_rating': 'Pre-tournament Elo', 'team_name': 'Team', 'actual_outcome': 'Actual Stage'},
    title="Top 24 Teams by Elo — tournament stage in color",
)
fig_elo.update_layout(
    yaxis=dict(autorange='reversed'),
    paper_bgcolor='#ffffff', plot_bgcolor='#ffffff',
    font=dict(color='#000000', family='Bebas Neue'),
    margin=dict(t=40, l=10, r=10, b=10),
)
st.plotly_chart(apply_dark_text_theme(fig_elo), width='stretch')

# ============================================================================
# CHART 2: Expected vs Actual delta — over/underperformers
# ============================================================================
st.subheader("📈 Over- vs Underperformers (vs Elo-based expectation)")
st.caption("Positive Δ = team went further than their Elo rank would predict. "
           "Negative Δ = team exited earlier than Elo rank would predict.")

delta_df = df.dropna(subset=['delta']).copy()
delta_df['delta_label'] = delta_df['delta'].apply(
    lambda x: f"+{int(x)}" if x > 0 else (str(int(x)) if x < 0 else "0"))

# Show top 12 overperformers AND top 12 underperformers (guaranteed both sides)
top_over = delta_df.sort_values('delta', ascending=False).head(12)
top_under = delta_df.sort_values('delta', ascending=True).head(12)
combined = pd.concat([top_over, top_under]).drop_duplicates('team_name').sort_values('delta', ascending=False)

fig_delta = px.bar(
    combined, x='delta', y='team_name', orientation='h',
    color='delta',
    color_continuous_scale=['#ef4444', '#fbbf24', '#10b981'],  # red → amber → green
    color_continuous_midpoint=0,  # center at 0
    text='delta_label',
    labels={'delta': 'Δ (stages further than Elo predicted)', 'team_name': 'Team'},
    title="Over- vs Underperformers vs Elo-based expectation",
)
fig_delta.update_layout(
    yaxis=dict(autorange='reversed'),
    paper_bgcolor='#ffffff', plot_bgcolor='#ffffff',
    font=dict(color='#1e293b', family='Inter'),
    margin=dict(t=40, l=10, r=10, b=10),
)
st.plotly_chart(apply_dark_text_theme(fig_delta), use_container_width=True)

info_card(
    "AI Insight",
    f"**{champion or 'The champion'}** entered the tournament with an Elo of "
    f"{top_seed['elo_rating']:.0f} " + (
        f"— the #1 Elo seed. The Elo ranking correctly identified the champion."
        if champion == top_seed['team_name'] else
        f", ranked #{int(top_seed['fifa_ranking_pre_tournament'])} by FIFA pre-tournament. "
        f"The actual champion, {champion}, was lower in the Elo seedings — "
        f"a reminder that tournament football introduces knockout-stage variance no rating system fully captures."
    ),
)

st.divider()

# ============================================================================
# CHART 3: FIFA ranking vs Elo — scatter with actual outcome
# ============================================================================
st.subheader("🌐 FIFA Ranking vs Elo — Scatter by Actual Outcome")
fig_scatter = px.scatter(
    df, x='fifa_ranking_pre_tournament', y='elo_rating',
    color='actual_outcome', color_discrete_map=color_map,
    hover_name='team_name',
    size='elo_rating', size_max=18,
    labels={
        'fifa_ranking_pre_tournament': 'FIFA Ranking (pre-tournament, lower = better)',
        'elo_rating': 'Elo Rating',
        'actual_outcome': 'Actual Stage',
    },
    title="FIFA Ranking vs Elo — tournament stage in color",
)
# Invert x-axis so rank 1 is on the LEFT (better)
fig_scatter.update_xaxes(autorange='reversed')
fig_scatter.update_layout(
    paper_bgcolor='#ffffff', plot_bgcolor='#ffffff',
    font=dict(color='#000000', family='Noto Sans'),
    margin=dict(t=40, l=10, r=10, b=10),
    height=520,
)
st.plotly_chart(apply_dark_text_theme(fig_scatter), width='stretch')

st.divider()

# ============================================================================
# DATA TABLE — full league table of Elo, FIFA rank, expected vs actual, Δ
# ============================================================================
st.subheader("📋 Full Strength vs Outcome Table")
table = df[['team_name', 'confederation', 'elo_rating', 'elo_rank',
            'fifa_ranking_pre_tournament', 'expected_outcome', 'actual_outcome', 'delta']].copy()
table = table.rename(columns={
    'team_name': 'Team', 'confederation': 'Confederation',
    'elo_rating': 'Elo', 'elo_rank': 'Elo Rank',
    'fifa_ranking_pre_tournament': 'FIFA Rank',
    'expected_outcome': 'Elo Expected', 'actual_outcome': 'Actual',
    'delta': 'Δ',
})
table['Δ'] = table['Δ'].apply(lambda x: f"+{int(x)}" if x > 0 else (str(int(x)) if x < 0 else "0"))
st.dataframe(
    table.sort_values('Elo Rank'),
    column_config={
        "Elo": st.column_config.NumberColumn(format="%.0f"),
    },
    hide_index=True, width='stretch', height=560,
)

st.caption(
    "'Elo Expected' is a simple rank-quartile bucketing, NOT a probabilistic model — "
    "championship probability models from Athena have been retired in favour of this "
    "transparent Elo / FIFA-rank strength view."
)
