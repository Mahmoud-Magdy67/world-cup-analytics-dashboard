"""
Real FIFA World Cup 2026 match-results loader (Kaggle / mominullptr dataset).

Source: https://www.kaggle.com/datasets/mominullptr/fifa-world-cup-2026-dataset
        CC0-1.0 (public domain).
        Cross-checked totals: 104 matches / 308 goals / 2.96 avg per match.
        Spain def. Argentina 1-0 (AET) in the 2026-07-19 Final at MetLife Stadium.

This module loads the English Kaggle CSVs (no translation needed) and exposes
clean DataFrames to the dashboard pages. Replaces the prior JP-JSON loader.
"""
import os
import pandas as pd

_DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "kaggle_wc26")
_MATCHES_FILE = os.path.join(_DATA_DIR, "matches_detailed.csv")
_TEAMS_FILE = os.path.join(_DATA_DIR, "teams.csv")
_STAGES_FILE = os.path.join(_DATA_DIR, "tournament_stages.csv")
_VENUES_FILE = os.path.join(_DATA_DIR, "venues.csv")

# Stable stage ordering for charts (low → high)
STAGE_ORDER = [
    "Group Stage", "Round of 32", "Round of 16",
    "Quarter-finals", "Semi-finals", "Third-place match", "Final",
]


def _read_matches() -> pd.DataFrame:
    """Load and lightly clean matches_detailed.csv."""
    df = pd.read_csv(_MATCHES_FILE)
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    # Numeric coercion for the score & xG cols
    for c in ("home_score", "away_score", "home_xg", "away_xg",
              "home_penalty_score", "away_penalty_score"):
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    return df


def _read_teams() -> pd.DataFrame:
    df = pd.read_csv(_TEAMS_FILE)
    return df


def get_real_wc26_matches() -> pd.DataFrame:
    """Full 104-match WC26 schedule & results.

    Returns columns (all English):
        match_id, date, kickoff_time_utc, stage_name, stadium_name, city, country,
        home_team_name, home_fifa_code, away_team_name, away_fifa_code,
        home_score, away_score, home_penalty_score, away_penalty_score,
        status, result_type, home_xg, away_xg,
        home_goalkeeper, away_goalkeeper,
        player_of_the_match_name, referee_name
    """
    df = _read_matches()
    # Sort chronologically; stable for NaN dates
    df = df.sort_values(["date", "match_id"], kind="stable").reset_index(drop=True)
    return df


def get_real_wc26_summary() -> pd.DataFrame:
    """Tournament totals: matches, goals, avg, winner, runner-up, final details."""
    df = _read_matches()
    df = df[df["status"] == "Completed"].copy()
    total_matches = len(df)
    total_goals = int(df["home_score"].sum() + df["away_score"].sum())
    avg_goals = round(total_goals / total_matches, 2) if total_matches else 0.0

    final_row = df[df["stage_name"] == "Final"].iloc[0] if (df["stage_name"] == "Final").any() else None
    winner = runner_up = None
    final_score = None
    final_date = None
    final_venue = None
    final_city = None
    result_type = None
    if final_row is not None:
        if final_row["home_score"] > final_row["away_score"]:
            winner = final_row["home_team_name"]
            runner_up = final_row["away_team_name"]
        elif final_row["away_score"] > final_row["home_score"]:
            winner = final_row["away_team_name"]
            runner_up = final_row["home_team_name"]
        else:
            # penalties
            if final_row.get("home_penalty_score", 0) and final_row.get("away_penalty_score", 0):
                if final_row["home_penalty_score"] > final_row["away_penalty_score"]:
                    winner = final_row["home_team_name"]; runner_up = final_row["away_team_name"]
                else:
                    winner = final_row["away_team_name"]; runner_up = final_row["home_team_name"]
        final_score = f"{int(final_row['home_score'])}-{int(final_row['away_score'])}"
        final_date = final_row["date"]
        final_venue = final_row.get("stadium_name")
        final_city = final_row.get("city")
        result_type = final_row.get("result_type")  # 'AET' etc.

    return pd.DataFrame([{
        "total_matches": total_matches,
        "total_goals": total_goals,
        "avg_goals_per_match": avg_goals,
        "final_date": final_date,
        "final_venue": final_venue,
        "final_city": final_city,
        "winner": winner,
        "runner_up": runner_up,
        "final_score": final_score,
        "result_type": result_type,  # 'AET' = after extra time, 'PENS' = penalties
    }])


def get_real_wc26_outcome_counts() -> pd.DataFrame:
    """Per-stage W/D/L counts (on regulation score, draws separated out)."""
    df = _read_matches()
    df = df[df["status"] == "Completed"].copy()
    df["total_goals"] = df["home_score"].fillna(0) + df["away_score"].fillna(0)

    def outcome(r):
        if r["home_score"] > r["away_score"]: return "Home Win"
        if r["away_score"] > r["home_score"]: return "Away Win"
        return "Draw"
    df["outcome"] = df.apply(outcome, axis=1)

    summary = df.groupby("stage_name").agg(
        matches=("outcome", "size"),
        home_wins=("outcome", lambda s: (s == "Home Win").sum()),
        away_wins=("outcome", lambda s: (s == "Away Win").sum()),
        draws=("outcome", lambda s: (s == "Draw").sum()),
        goals=("total_goals", "sum"),
    ).reset_index()

    summary["stage_order"] = summary["stage_name"].apply(
        lambda s: STAGE_ORDER.index(s) if s in STAGE_ORDER else 99
    )
    summary = summary.sort_values("stage_order").drop(columns=["stage_order"]).reset_index(drop=True)

    total = pd.DataFrame([{
        "stage_name": "Total",
        "matches": summary["matches"].sum(),
        "home_wins": summary["home_wins"].sum(),
        "away_wins": summary["away_wins"].sum(),
        "draws": summary["draws"].sum(),
        "goals": summary["goals"].sum(),
    }])
    return pd.concat([summary, total], ignore_index=True)


def get_real_wc26_team_stats() -> pd.DataFrame:
    """Per-team goals for/against, W/D/L (regulation score), matches."""
    df = _read_matches()
    df = df[df["status"] == "Completed"].copy()

    rows = []
    for _, m in df.iterrows():
        rows.append({"team": m["home_team_name"], "goals_for": m["home_score"],
                     "goals_against": m["away_score"], "stage": m["stage_name"],
                     "home_venue_country": m.get("country")})
        rows.append({"team": m["away_team_name"], "goals_for": m["away_score"],
                     "goals_against": m["home_score"], "stage": m["stage_name"],
                     "home_venue_country": m.get("country")})
    team_df = pd.DataFrame(rows)

    team_df["result"] = team_df.apply(
        lambda r: "W" if r["goals_for"] > r["goals_against"]
        else ("D" if r["goals_for"] == r["goals_against"] else "L"),
        axis=1,
    )
    wdl = team_df.groupby(["team", "result"]).size().unstack(fill_value=0)
    for col in ("W", "D", "L"):
        if col not in wdl.columns: wdl[col] = 0
    wdl = wdl.reset_index()[["team", "W", "D", "L"]]

    agg = team_df.groupby("team").agg(
        matches=("goals_for", "size"),
        goals_for=("goals_for", "sum"),
        goals_against=("goals_against", "sum"),
    ).reset_index()
    agg = agg.merge(wdl, on="team", how="left")
    agg["goal_difference"] = agg["goals_for"] - agg["goals_against"]
    return agg.sort_values(["goals_for", "goal_difference"], ascending=[False, False]).reset_index(drop=True)


def get_real_wc26_xg_by_team() -> pd.DataFrame:
    """Per-team xG for/against (from matches_detailed.csv)."""
    df = _read_matches()
    df = df[df["status"] == "Completed"].copy()
    rows = []
    for _, m in df.iterrows():
        if pd.notna(m.get("home_xg")):
            rows.append({"team": m["home_team_name"], "xg_for": m["home_xg"], "xg_against": m["away_xg"]})
        if pd.notna(m.get("away_xg")):
            rows.append({"team": m["away_team_name"], "xg_for": m["away_xg"], "xg_against": m["home_xg"]})
    xg_df = pd.DataFrame(rows)
    return xg_df.groupby("team").agg(
        matches=("xg_for", "size"),
        xg_for=("xg_for", "sum"),
        xg_against=("xg_against", "sum"),
    ).reset_index().sort_values("xg_for", ascending=False).reset_index(drop=True)
