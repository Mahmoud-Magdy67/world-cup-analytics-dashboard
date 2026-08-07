"""Shared Kaggle CSV loader helpers for data/real_wc26.py and real_wc26_players.py.

All WC26 source CSVs live under data/kaggle_wc26/. Twelve files, 9,369 rows total,
all from the mominullptr/fifa-world-cup-2026-dataset (CC0-1.0, sofascore.com
verified). See data/kaggle_wc26/SOURCE.txt for the full citation.

S3 mode: If AWS credentials are available (env vars, Streamlit secrets, or IAM
role), CSVs are read from s3://wc26-kaggle-data/kaggle_wc26/ instead of local
files. This enables Athena/Glue/other AWS operations on the data. Local files
are used as fallback.

This module exposes:
  - path constants (DATA_DIR, _CSVS)
  - _read(name) -> DataFrame  (cached via streamlit.cache_data where applicable)
  - id->name resolution helpers (player_id, team_id, referee_id, venue_id, match_id)
"""
import os
import io
import pandas as pd

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "kaggle_wc26")

# S3 configuration (fallback to local files if not set)
S3_BUCKET = os.getenv("WC26_S3_BUCKET", "wc26-kaggle-data")
S3_PREFIX = os.getenv("WC26_S3_PREFIX", "kaggle_wc26")

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

# Track whether we're reading from S3 (for UI display)
S3_ACTIVE = False

# --- Credential resolution (env vars → Streamlit secrets → IAM role) ---
def _get_aws_credentials():
    """Resolve AWS credentials from env vars, Streamlit secrets, or IAM role."""
    key_id = os.getenv("AWS_ACCESS_KEY_ID")
    secret = os.getenv("AWS_SECRET_ACCESS_KEY")
    region = os.getenv("AWS_DEFAULT_REGION", "us-east-1")

    # Try Streamlit secrets if env vars not set
    if not key_id or not secret:
        try:
            import streamlit as st
            if hasattr(st, 'secrets') and 'AWS_ACCESS_KEY_ID' in st.secrets:
                key_id = st.secrets['AWS_ACCESS_KEY_ID']
                secret = st.secrets['AWS_SECRET_ACCESS_KEY']
                region = st.secrets.get('AWS_DEFAULT_REGION', region)
        except Exception:
            pass

    return key_id, secret, region


# --- S3 client (lazy init) ---
_s3_client = None

def _get_s3_client():
    """Return an S3 client if AWS credentials are available, else None."""
    global _s3_client, S3_ACTIVE
    if _s3_client is not None:
        return _s3_client
    try:
        import boto3
        key_id, secret, region = _get_aws_credentials()
        if key_id and secret:
            _s3_client = boto3.client("s3",
                aws_access_key_id=key_id,
                aws_secret_access_key=secret,
                region_name=region)
            S3_ACTIVE = True
        else:
            # Try IAM role / default credential chain
            _s3_client = boto3.client("s3", region_name=region)
            S3_ACTIVE = True
    except Exception:
        _s3_client = None
    return _s3_client


def _read(name: str) -> pd.DataFrame:
    """Read one of the Kaggle CSVs by short name. Returns a fresh DataFrame.

    Reads from S3 if AWS credentials are available, else falls back to local files.
    """
    fname = FILES[name]
    s3 = _get_s3_client()
    if s3 is not None:
        try:
            s3_key = f"{S3_PREFIX}/{fname}"
            obj = s3.get_object(Bucket=S3_BUCKET, Key=s3_key)
            return pd.read_csv(io.BytesIO(obj["Body"].read()))
        except Exception:
            pass  # fall through to local
    # Local fallback
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
