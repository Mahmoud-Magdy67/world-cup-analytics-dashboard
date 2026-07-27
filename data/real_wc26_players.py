"""
Real FIFA World Cup 2026 player-performance loader (Kaggle / mominullptr dataset).

Source: https://www.kaggle.com/datasets/mominullptr/fifa-world-cup-2026-dataset
        CC0-1.0 (public domain). Verified stats from sofascore.com.
        1,248 WC26 squad players, 48 nations. Cross-check: player goals sum
        (297) + own goals (11) = 308 match goals, matching matches_detailed.csv.

Exposes per-player stats (goals/assists/minutes/cards/ratings), enriched with
team name, confederation, club, market value, and position group.

This REPLACES the prior data/athena.py get_players() / get_player_tournament_stats()
data layer for the player analysis page. Only real WC26 squad members appear.
"""
import os
import pandas as pd

_DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "kaggle_wc26")
_PLAYERS_FILE = os.path.join(_DATA_DIR, "player_stats.csv")
_TEAMS_FILE = os.path.join(_DATA_DIR, "teams.csv")
_SQUADS_FILE = os.path.join(_DATA_DIR, "squads_and_players.csv")


def _load_raw() -> pd.DataFrame:
    """Load player_stats merged with team + squad context."""
    ps = pd.read_csv(_PLAYERS_FILE)
    teams = pd.read_csv(_TEAMS_FILE)[["team_id", "team_name", "fifa_code", "confederation"]]
    squads = pd.read_csv(_SQUADS_FILE)[["player_id", "club_team", "market_value_eur",
                                         "caps", "date_of_birth", "height_cm"]]
    df = ps.merge(teams, on="team_id", how="left").merge(squads, on="player_id", how="left")
    return df


def get_real_wc26_players() -> pd.DataFrame:
    """All 1,248 WC26 squad players with tournament stats + context.

    Returns columns (all English):
      player_id, player_name, team_id, position, matches_played, matches_started,
      minutes_played, goals, assists, shots, shots_on_target,
      yellow_cards, red_cards, penalty_goals, own_goals,
      clean_sheets, saves, goals_conceded, average_rating,
      team_name, fifa_code (nation code), confederation,
      club_team, market_value_eur, caps, date_of_birth, height_cm,
      goal_contribution (goals + assists),
      ninety_goals (goals per 90), ninety_assists (assists per 90),
      ninety_contributions (contributions per 90)
    """
    df = _load_raw()

    # Derived fields
    df["goal_contribution"] = df["goals"] + df["assists"]
    mp = df["minutes_played"].clip(lower=1)  # avoid div-by-zero
    df["ninety_goals"] = (df["goals"] / mp * 90).round(2)
    df["ninety_assists"] = (df["assists"] / mp * 90).round(2)
    df["ninety_contributions"] = (df["goal_contribution"] / mp * 90).round(2)

    # Rename for display compatibility with prior page schema
    df = df.rename(columns={
        "goals": "wc26_goals",
        "assists": "wc26_assists",
    })

    # Display aliases (added here so all derived dataframes inherit them)
    df["spotlight_name"] = df["player_name"]
    df["nation_code"] = df["fifa_code"]
    df["wc26_minutes"] = df["minutes_played"]

    # Sort by goal contribution (goals first, then assists)
    df = df.sort_values(["goal_contribution", "wc26_goals", "wc26_assists"],
                        ascending=[False, False, False]).reset_index(drop=True)
    return df


def get_real_wc26_top_scorers(limit: int = 25) -> pd.DataFrame:
    """Tournament top scorers (sorted by goals, then assists)."""
    df = get_real_wc26_players()
    df = df[df["wc26_goals"] > 0].sort_values(["wc26_goals", "wc26_assists"], ascending=[False, False])
    return df.head(limit).reset_index(drop=True)


def get_real_wc26_top_assists(limit: int = 25) -> pd.DataFrame:
    """Tournament top assist providers (sorted by assists, then goals)."""
    df = get_real_wc26_players()
    df = df[df["wc26_assists"] > 0].sort_values(["wc26_assists", "wc26_goals"], ascending=[False, False])
    return df.head(limit).reset_index(drop=True)


def get_real_wc26_top_contributors(limit: int = 25) -> pd.DataFrame:
    """Tournament top goal contributors (goals + assists)."""
    df = get_real_wc26_players()
    df = df[df["goal_contribution"] > 0].sort_values(
        ["goal_contribution", "wc26_goals", "wc26_assists"], ascending=[False, False, False])
    return df.head(limit).reset_index(drop=True)


def get_real_wc26_player_summary() -> pd.DataFrame:
    """Tournament-level summary metrics (one row)."""
    df = get_real_wc26_players()
    return pd.DataFrame([{
        "players_tracked": len(df),
        "wc26_goals": int(df["wc26_goals"].sum()),
        "wc26_assists": int(df["wc26_assists"].sum()),
        "goal_contributions": int(df["goal_contribution"].sum()),
        "active_nations": int(df["team_name"].nunique()),
        "players_with_goals": int((df["wc26_goals"] > 0).sum()),
        "players_with_assists": int((df["wc26_assists"] > 0).sum()),
        "players_with_contributions": int((df["goal_contribution"] > 0).sum()),
        "golden_boot": df.sort_values(["wc26_goals", "wc26_assists"], ascending=[False, False]).iloc[0]["player_name"],
        "golden_boot_goals": int(df["wc26_goals"].max()),
        "playmaker": df.sort_values(["wc26_assists", "wc26_goals"], ascending=[False, False]).iloc[0]["player_name"],
        "playmaker_assists": int(df["wc26_assists"].max()),
    }])


def get_real_wc26_nation_contributions() -> pd.DataFrame:
    """Per-team aggregate goals + assists (for nation-level contribution charts)."""
    df = get_real_wc26_players()
    agg = df.groupby(["team_name", "fifa_code", "confederation"]).agg(
        tgoals=("wc26_goals", "sum"),
        tassists=("wc26_assists", "sum"),
        tcontributions=("goal_contribution", "sum"),
        nplayers=("player_id", "size"),
    ).reset_index()
    return agg.sort_values(["tcontributions", "tgoals"], ascending=[False, False]).reset_index(drop=True)


def get_real_wc26_position_breakdown() -> pd.DataFrame:
    """Per-position aggregates (GK/DEF/MID/FWD)."""
    df = get_real_wc26_players()
    return df.groupby("position").agg(
        players=("player_id", "size"),
        goals=("wc26_goals", "sum"),
        assists=("wc26_assists", "sum"),
        clean_sheets=("clean_sheets", "sum"),
        yellow_cards=("yellow_cards", "sum"),
        red_cards=("red_cards", "sum"),
    ).reset_index().sort_values("goals", ascending=False).reset_index(drop=True)


def get_real_wc26_gk_leaders(limit: int = 10) -> pd.DataFrame:
    """Top goalkeepers by clean sheets, with saves/goals_conceded context."""
    df = get_real_wc26_players()
    gk = df[df["position"] == "GK"].copy()
    gk = gk.sort_values(["clean_sheets", "saves"], ascending=[False, False])
    return gk.head(limit).reset_index(drop=True)
