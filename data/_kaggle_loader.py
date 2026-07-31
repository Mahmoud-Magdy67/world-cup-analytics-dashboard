"""Shared Kaggle CSV loader helpers for data/real_wc26.py and real_wc26_players.py.

All WC26 source CSVs live under data/kaggle_wc26/. Twelve files, 9,369 rows total,
all from the mominullptr/fifa-world-cup-2026-dataset (CC0-1.0, sofascore.com
verified). See data/kaggle_wc26/SOURCE.txt for the full citation.

This module exposes:
  - path constants (DATA_DIR, _CSVS)
  - _read(name) -> DataFrame  (cached via streamlit.cache_data where applicable)
  - id->name resolution helpers (player_id, team_id, referee_id, venue_id, match_id)
"""
import os
import pandas as pd

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "kaggle_wc26")

# File map: <public_name> -> <csv filename>
FILES = {
    "teams":          "teams.csv",                    # 48 teams
    "matches":        "matches.csv",                  # 104 matches (raw ids)
    "matches_detailed": "matches_detailed.csv",        # 104 matches (with names)
    "match_events":   "match_events.csv",             # 834 events (goals/cards/assists)
    "match_lineups":  "match_lineups.csv",            # 5408 lineup rows (XI + bench)
    "match_team_stats": "match_team_stats.csv",       # 208 per-team-per-match in-match stats
    "match_prediction_features": "match_prediction_features.csv",  # 104 rows, 66 pre-match cols
    "player_stats":   "player_stats.csv",             # 1248 players (in-tournament stats)
    "squads_and_players": "squads_and_players.csv",   # 1248 players (squad metadata)
    "venues":         "venues.csv",                   # 16 venues
    "referees":       "referees.csv",                 # 28 referees
    "tournament_stages": "tournament_stages.csv",     # 7 stages
}


def _read(name: str) -> pd.DataFrame:
    """Read one of the Kaggle CSVs by short name. Returns a fresh DataFrame."""
    fname = FILES[name]
    path = os.path.join(DATA_DIR, fname)
    return pd.read_csv(path)


# ---------------------------------------------------------------------------
# ID -> name resolution caches (built lazily on first access)
# ---------------------------------------------------------------------------
_TEAMS_CACHE = None
_PLAYERS_CACHE = None
_REFEREE_CACHE = None
_VENUES_CACHE = None
_MATCHES_CACHE = None


def _teams() -> pd.DataFrame:
    global _TEAMS_CACHE
    if _TEAMS_CACHE is None:
        _TEAMS_CACHE = _read("teams")
    return _TEAMS_CACHE


def _players() -> pd.DataFrame:
    global _PLAYERS_CACHE
    if _PLAYERS_CACHE is None:
        _PLAYERS_CACHE = _read("player_stats")[["player_id", "player_name", "team_id", "position"]]
    return _PLAYERS_CACHE


def _referees_df() -> pd.DataFrame:
    global _REFEREE_CACHE
    if _REFEREE_CACHE is None:
        _REFEREE_CACHE = _read("referees")
    return _REFEREE_CACHE


def _venues() -> pd.DataFrame:
    global _VENUES_CACHE
    if _VENUES_CACHE is None:
        _VENUES_CACHE = _read("venues")
    return _VENUES_CACHE


def _matches() -> pd.DataFrame:
    global _MATCHES_CACHE
    if _MATCHES_CACHE is None:
        _MATCHES_CACHE = _read("matches_detailed")
    return _MATCHES_CACHE


def team_name(team_id: int) -> str:
    df = _teams()
    row = df[df["team_id"] == team_id]
    return str(row["team_name"].iloc[0]) if not row.empty else f"team#{team_id}"


def team_code(team_id: int) -> str:
    df = _teams()
    row = df[df["team_id"] == team_id]
    return str(row["fifa_code"].iloc[0]) if not row.empty else ""


def player_name(player_id: int) -> str:
    df = _players()
    row = df[df["player_id"] == player_id]
    return str(row["player_name"].iloc[0]) if not row.empty else f"player#{player_id}"


def referee_name(referee_id: int) -> str:
    df = _referees_df()
    row = df[df["referee_id"] == referee_id]
    return str(row["name"].iloc[0]) if not row.empty else f"referee#{referee_id}"


def stage_name(stage_id: int) -> str:
    s = _read("tournament_stages")
    row = s[s["stage_id"] == stage_id]
    return str(row["stage_name"].iloc[0]) if not row.empty else f"stage#{stage_id}"
