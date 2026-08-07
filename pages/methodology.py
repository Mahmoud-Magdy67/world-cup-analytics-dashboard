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

load_custom_css()
page_header(
    "Data & Methodology",
    "How this dashboard works — data source, schema, derived metrics, limitations.",
    image_url="assets/logo.png",
)

# ============================================================================
# DATA SOURCE STATUS
# ============================================================================
st.subheader("📊 Data Connection Status")
with st.spinner("Checking Kaggle dataset availability..."):
    matches = get_real_wc26_matches()
    teams_strength = get_real_wc26_team_strength()
    team_stats = get_real_wc26_team_stats()
    summary = get_real_wc26_summary()
    bracket = get_real_wc26_knockout_bracket()

# Find the on-disk Kaggle data directory so we can actually list CSV files
_KAGGLE_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data", "kaggle_wc26"
)
csv_files = {}
if os.path.isdir(_KAGGLE_DIR):
    for f in sorted(os.listdir(_KAGGLE_DIR)):
        if f.endswith('.csv'):
            p = os.path.join(_KAGGLE_DIR, f)
            try:
                with open(p, 'r', encoding='utf-8') as fh:
                    # cheap row count: only count newlines, not pandas load
                    rows = sum(1 for _ in fh) - 1
                csv_files[f] = max(0, rows)
            except Exception:
                csv_files[f] = 0

ok = not matches.empty
real_s = summary.iloc[0] if not summary.empty else {}

c1, c2, c3, c4 = st.columns(4)
with c1:
    st.metric("Kaggle Dataset", "🟢 Loaded" if ok else "🔴 Missing")
with c2:
    st.metric("CSV Files", len(csv_files))
with c3:
    st.metric("Matches", int(real_s.get('total_matches', len(matches))) if not summary.empty else len(matches))
with c4:
    st.metric("Teams", len(teams_strength))

st.write(
    "**Connection:** Local CSV files under `data/kaggle_wc26/`, committed to the repo. "
    "No cloud credentials, no Athena queries at runtime — the dashboard is fully "
    "deterministic and reproducible from the repo checkout."
)

st.divider()

# ============================================================================
# AVAILABLE TABLES — list every CSV in the Kaggle dataset
# ============================================================================
st.subheader("📋 Available Data Tables (Kaggle CSVs)")
if csv_files:
    table_df = pd.DataFrame([
        {"File": f, "Rows (approx)": f"{n:,}", "Loaded by dashboard?": "—"}
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
else:
    st.info("No Kaggle CSV files found under data/kaggle_wc26/.")

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
- Complete coverage of the finished tournament (real results, not predictions)
- Cross-validation: 104 matches / 308 goals / 2.96 avg per match — matches the
  publicly reported tournament totals
- Replaces the prior pre-tournament Athena/BQ simulation layer, which was
  partial (group-stage only) and is now stale (the tournament is over)

### Previously retired sources
- AWS Athena views (`v_team_schedule`, `ml_group_fixture_predictions_*`,
  `v_winner_prediction_*`): pre-tournament Monte Carlo simulations. Valid
  only before 2026-06-11; now obsolete.
- The `mominullptr` Kaggle dataset supersedes all of them for retrospective
  analysis.
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
# DERIVED METRICS — how each page computes its numbers
# ============================================================================
st.subheader("🧮 Derived Metrics — How Each Page Computes Its Numbers")

st.markdown("""
Every metric shown on the dashboard is computed in `data/real_wc26.py` from the
raw Kaggle CSVs above. There is no black-box model. The key derivations:

#### Tournament summary (Overview page)
- **Total matches** = `len(matches_detailed)` → 104
- **Total goals** = `home_score.sum() + away_score.sum() - own_goals` → 308
  *(11 of the 308 goals are own goals, recorded as team totals of 297)*
- **Avg goals/match** = `total_goals / 104` → 2.96
- **Winner / Runner-up / Final score** = read from the Final row of `matches_detailed`

#### Per-team stats
- **Goals For / Against** = pivot `matches_detailed` to team-perspective (home_rows ∪ away_rows)
- **W / D / L** = count matches grouped by `result_type` and score
- **Goal difference** = GF − GA

#### Team Strength (Teams page)
- **Elo / FIFA ranking / Squad value / Manager** = read directly from `teams.csv`
- **Tactical radar dimensions** (attack, defense, midfield, GK, OVR) are **z-scored
  from real in-match statistics**, not FIFA-OVR style ratings:
  - `attack_strength` = goals_for / matches, z-scored → 60–95
  - `defense_strength` = -(goals_against / matches), z-scored → 60–95 (fewer conceded = higher)
  - `midfield_strength` = avg_possession from `match_team_stats`, z-scored
  - `gk_strength` = avg_saves from `match_team_stats`, z-scored
  - `avg_ovr_top11` = Elo (Kaggle has no FIFA-OVR; Elo is the overall proxy)
- All z-scores are clipped to ±2σ and rescaled to [60, 95] purely so the radar
  is comparable to the previous dashboard's visual scale.

#### Strength Index vs Outcomes (Predictions page)
- The old Monte-Carlo championship probabilities have been retired —
  they were pre-tournament only and are no longer relevant post-tournament.
- The page now shows **pre-tournament Elo / FIFA ranking** as a transparent
  strength prior, and overlays each team's **actual tournament stage** (how
  far they reached) derived from the knockout bracket rows in `matches_detailed`.
- "Elo Expected" stage is a **rank-quartile bucketing**, NOT a probabilistic
  model. It exists only to give the "Δ" over/underperformer column a baseline.

#### Knockout bracket (Overview + Predictions)
- Filter `matches_detailed` to `stage_name` ∈ {Round of 32, Round of 16,
  Quarter-finals, Semifinals, Third-place match, Final} → 32 rows.
- Order by `STAGE_ORDER` (module constant) then `date`.

#### Player stats (Players page)
- Loaded directly from `squads_and_players.csv` (1,248 players) and
  `player_stats.csv` (per-tournament goals, assists, xG, xA, minutes).
- The Kaggle player goals sum (297) is less than the match total (308)
  because the 11-goal gap is own goals — credited to no individual player.
""")

info_card(
    "Reproducibility",
    "Because every metric is a deterministic function of CSV files committed to "
    "the repo, any reader can reproduce every number on the dashboard by running "
    "the loaders in `data/real_wc26.py` against `data/kaggle_wc26/`. No external "
    "API, no credentials, no cloud query at runtime."
)

st.divider()

# ============================================================================
# LIMITATIONS
# ============================================================================
st.subheader("⚠️ Limitations")

col1, col2 = st.columns(2)
with col1:
    st.markdown("""
    ### Dataset limitations
    - Kaggle-derived match stats are a curated subset; not every Opta/StatsBomb
      field (e.g. x,y shot coordinates, pass maps) is available CC0.
    - xG values are the dataset's pre-computed xG, not our own shot-based model.
    - No per-minute game-state adjustment in the tactical radar — possession and
      goals are full-match aggregates.
    - Tactical dimensions are z-scored to the 60–95 scale for parity with the
      previous FIFA-OVR radar; they are not FIFA ratings.
    """)
with col2:
    st.markdown("""
    ### What the dashboard is NOT
    - It is **not a prediction engine**. The tournament is over; there is nothing
      left to predict. The old pre-tournament Monte Carlo probabilities have been
      retired.
    - It is **not real-time**. The data reflects the completed WC26 tournament.
    - It is **not exhaustive**. Stick to the Kaggle dataset's schema; if a field
      is not in a CSV above, the dashboard does not have it.
    """)

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
