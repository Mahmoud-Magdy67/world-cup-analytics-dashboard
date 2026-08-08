"""
data/athena.py — World Cup 2026 Analytics

Reads the dashboard's analytical views from AWS Athena, which queries the
Kaggle dataset uploaded to S3 and materialized as external tables + views.

The migration is done by `migrate_kaggle_to_aws.py` (run once, idempotent).

"""
from dataclasses import dataclass
from typing import Final, Optional, Dict
import os
import time
import pandas as pd
import boto3
from botocore.exceptions import ClientError, NoCredentialsError
import streamlit as st

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
AWS_REGION: Final[str] = os.getenv("AWS_REGION", "eu-west-3")
ATHENA_DATABASE: Final[str] = os.getenv("ATHENA_DATABASE", "worldcup_2026")
# NOTE: the result bucket must be in the same AWS region as the Athena endpoint
# (eu-west-3). The `aws-athena-query-results-worldcup` bucket is in us-east-1 and
# will be rejected by start_query_execution.
ATHENA_OUTPUT_BUCKET: Final[str] = os.getenv(
    "ATHENA_OUTPUT_BUCKET",
    "aws-athena-query-results-986420598705-eu-west-3",
)

# Allowed datasets (read-only)
ALLOWED_ATHENA_DATASET_PLACEHOLDERS: Final[list[str]] = ["worldcup_2026"]
READ_ONLY_RULE: Final[str] = "Only SELECT queries are allowed for Athena access."

# ---------------------------------------------------------------------------
# Athena client + query execution
# ---------------------------------------------------------------------------
def _get_athena_client() -> Optional[boto3.client]:
    """Initialize Athena client from Streamlit secrets or environment credentials."""
    import streamlit as st
    aws_access_key_id = None
    aws_secret_access_key = None
    region_name = AWS_REGION

    try:
        if hasattr(st, "secrets") and "credentials" in st.secrets:
            aws_access_key_id = st.secrets["credentials"].get("AWS_ACCESS_KEY_ID")
            aws_secret_access_key = st.secrets["credentials"].get("AWS_SECRET_ACCESS_KEY")
            region_name = st.secrets["credentials"].get("AWS_REGION", AWS_REGION)
    except Exception:
        pass

    if not aws_access_key_id:
        aws_access_key_id = os.getenv("AWS_ACCESS_KEY_ID")
    if not aws_secret_access_key:
        aws_secret_access_key = os.getenv("AWS_SECRET_ACCESS_KEY")
    if not region_name:
        region_name = os.getenv("AWS_REGION", AWS_REGION)

    if not aws_access_key_id or not aws_secret_access_key:
        return None

    try:
        return boto3.client(
            "athena",
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
            region_name=region_name,
        )
    except Exception as e:
        st.error(f"Athena auth error: {e}")
        return None


def _execute_athena_query(query: str) -> pd.DataFrame:
    """Execute a SELECT / WITH query on Athena and return the results as a DataFrame."""
    query_upper = query.strip().upper()
    if not (query_upper.startswith("SELECT") or query_upper.startswith("WITH")):
        raise ValueError(f"Only SELECT or WITH (CTE) queries allowed. Blocked: {query[:50]}")

    client = _get_athena_client()
    if not client:
        raise RuntimeError("Athena client not initialized. Check AWS credentials.")

    try:
        response = client.start_query_execution(
            QueryString=query,
            QueryExecutionContext={"Database": ATHENA_DATABASE},
            ResultConfiguration={"OutputLocation": f"s3://{ATHENA_OUTPUT_BUCKET}/"},
        )
        qid = response["QueryExecutionId"]

        # Wait for completion
        while True:
            r = client.get_query_execution(QueryExecutionId=qid)
            status = r["QueryExecution"]["Status"]["State"]
            if status == "SUCCEEDED":
                break
            if status in ("FAILED", "CANCELLED"):
                reason = r["QueryExecution"]["Status"].get("StateChangeReason", "Unknown")
                raise RuntimeError(f"Athena query failed: {reason}")
            time.sleep(1)

        # Paginate results
        paginator = client.get_paginator("get_query_results")
        pages = paginator.paginate(QueryExecutionId=qid, PaginationConfig={"PageSize": 1000})

        records, column_names = [], None
        for page in pages:
            col_info = page["ResultSet"]["ResultSetMetadata"]["ColumnInfo"]
            column_names = [c["Name"] for c in col_info]
            if "Rows" in page["ResultSet"]:
                for row in page["ResultSet"]["Rows"]:
                    if "Data" in row:
                        rec = {}
                        for i, d in enumerate(row["Data"]):
                            if i < len(column_names):
                                rec[column_names[i]] = d.get("VarCharValue", "")
                        records.append(rec)

        # Athena's first row in get_query_results is the header — drop it
        # (the paginator DOES include the header row, so skip if first row ==
        # column_names)
        if records and [str(v) for v in records[0].values()] == column_names:
            records = records[1:]

        if records:
            df = pd.DataFrame(records, columns=column_names)
            for col in df.columns:
                try:
                    df[col] = pd.to_numeric(df[col])
                except (ValueError, TypeError):
                    pass
            return df
        return pd.DataFrame(columns=column_names or [])

    except Exception as e:
        st.error(f"Athena query execution error: {e}")
        return pd.DataFrame()


def _execute_readonly_query(query: str) -> pd.DataFrame:
    """Execute a read-only SELECT/WITH query. Raises ValueError for non-SELECT."""
    q = query.strip().upper()
    if not (q.startswith("SELECT") or q.startswith("WITH")):
        raise ValueError(f"Only SELECT/WITH queries allowed. Blocked: {query[:50]}")
    return _execute_athena_query(query)


# ---------------------------------------------------------------------------
# Data-source status
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class DataSourceStatus:
    mode: str
    athena_enabled: bool
    note: str
    tables_available: Optional[Dict[str, int]] = None


def get_data_source_status() -> DataSourceStatus:
    """Check Athena connectivity and report counts for the key tables/views."""
    client = _get_athena_client()
    if not client:
        return DataSourceStatus(
            "mock", False,
            "Athena credentials not configured; check .streamlit/secrets.toml",
            None,
        )

    tables = [
        "teams", "matches_detailed", "match_team_stats",
        "player_stats", "squads_and_players", "venues",
        "v_team_strength", "v_team_stats", "v_tournament_summary",
        "v_knockout_bracket", "v_outcome_counts",
    ]
    counts: Dict[str, int] = {}
    try:
        for t in tables:
            try:
                df = _execute_athena_query(f"SELECT COUNT(*) AS n FROM {t}")
                counts[t] = int(df["n"].iloc[0]) if not df.empty else 0
            except Exception:
                counts[t] = 0
        return DataSourceStatus(
            "athena", True,
            f"Connected to Athena database '{ATHENA_DATABASE}' "
            f"(region {AWS_REGION}). Kaggle WC26 dataset backed by S3 "
            f"at s3://wc2026-simulation-data/kaggle_wc26/.",
            counts,
        )
    except Exception as e:
        return DataSourceStatus("athena_error", False, f"Athena connection failed: {str(e)[:150]}", None)


# ===========================================================================
# Loads — every page calls these. Each one queries a Kaggle-backed Athena view.
# ===========================================================================

def get_real_wc26_data_source_status() -> DataSourceStatus:
    """Alias for get_data_source_status — the dashboard's health-check call."""
    return get_data_source_status()


# ----- Tournament (Overview page) -----------------------------------------

def get_tournament_overview() -> pd.DataFrame:
    """1 row of tournament KPIs (total_matches, total_goals, avg_goals_per_match,
    winner, runner_up, final_score, result_type, final_date, final_venue, final_city)."""
    return _execute_readonly_query("SELECT * FROM v_tournament_summary")


def get_match_outcome_summary() -> pd.DataFrame:
    """Per-stage outcome counts (matches, home_wins, away_wins, draws, goals),
    plus one Total row."""
    return _execute_readonly_query("SELECT * FROM v_outcome_counts")


def get_real_wc26_outcome_counts() -> pd.DataFrame:
    """Alias for get_match_outcome_summary — backward-compatible name."""
    return get_match_outcome_summary()


def get_real_wc26_summary() -> pd.DataFrame:
    """Alias for get_tournament_overview — backward-compatible name."""
    return get_tournament_overview()


def get_knockout_bracket_summary() -> pd.DataFrame:
    """32 knockout-stage matches with winner computed, ordered by stage depth."""
    df = _execute_readonly_query("""
        SELECT match_id, date, stage_name, home_team_name, away_team_name,
               home_score, away_score, home_penalty_score, away_penalty_score,
               result_type, stadium_name, city, country, winner
        FROM v_knockout_bracket
        ORDER BY
            CASE stage_name
                WHEN 'Round of 32' THEN 0
                WHEN 'Round of 16' THEN 1
                WHEN 'Quarter-finals' THEN 2
                WHEN 'Semi-finals' THEN 3
                WHEN 'Third-place match' THEN 4
                WHEN 'Final' THEN 5
                ELSE 99
            END, date
    """)
    if not df.empty and "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
    return df


# ----- Teams / Team Analytics page ---------------------------------------

def get_teams() -> pd.DataFrame:
    """48 teams with Elo, FIFA ranking, confederation, manager, market value,
    and aggregated WC26 goals/assists — ready for the Teams page."""
    return _execute_readonly_query("""
        SELECT team_id, team_name, fifa_code, group_letter, confederation,
               fifa_ranking_pre_tournament, elo_rating, manager_name,
               squad_market_value_eur, wc26_goals, wc26_assists
        FROM v_team_strength
        ORDER BY elo_rating DESC
    """)


def get_team_strength() -> pd.DataFrame:
    """Alias for get_teams — explicit name for the page that used to call
    get_real_wc26_team_strength via the pandas layer."""
    return get_teams()


def get_real_wc26_team_strength() -> pd.DataFrame:
    """Alias — backward-compatible name."""
    return get_teams()


def get_team_stats() -> pd.DataFrame:
    """Per-team goals-for/against/W/D/L/GD from the real 104 matches."""
    return _execute_readonly_query("""
        SELECT team, matches, goals_for, goals_against,
               W, D, L, goal_difference
        FROM v_team_stats
        ORDER BY goals_for DESC, goal_difference DESC
    """)


def get_real_wc26_team_stats() -> pd.DataFrame:
    """Alias for get_team_stats — backward-compatible name."""
    return get_team_stats()


def get_match_team_stats_agg() -> pd.DataFrame:
    """Per-team avg in-match stats (possession, shots, corners, etc.) aggregated
    across the WC26 tournament — used by the Teams page tactical radar."""
    return _execute_readonly_query("""
        SELECT team_id, team_name, matches,
               avg_possession, avg_shots, avg_shots_on_target,
               avg_corners, avg_fouls, avg_offsides, avg_saves
        FROM v_match_team_stats_agg
        ORDER BY team_name
    """)


def get_real_wc26_match_team_stats() -> pd.DataFrame:
    """Alias for get_match_team_stats_agg — backward-compatible name."""
    return get_match_team_stats_agg()


# ----- Matches page ------------------------------------------------------

def get_matches() -> pd.DataFrame:
    """All 104 matches from matches_detailed with stage, scores, xG, venue,
    referee, POTM."""
    return _execute_readonly_query("""
        SELECT match_id, date, kickoff_time_utc, stage_name, stadium_name,
               city, country, home_team_name, home_fifa_code,
               away_team_name, away_fifa_code,
               home_score, away_score, home_penalty_score, away_penalty_score,
               status, result_type, home_xg, away_xg,
               home_goalkeeper, away_goalkeeper,
               player_of_the_match_name, referee_name
        FROM matches_detailed
        ORDER BY date, match_id
    """)


def get_real_wc26_matches() -> pd.DataFrame:
    """Alias for get_matches — backward-compatible name."""
    return get_matches()


def get_venues() -> pd.DataFrame:
    """16 venues with capacity, lat/lon, elevation."""
    return _execute_readonly_query("""
        SELECT venue_id, stadium_name, city, country,
               capacity, latitude, longitude, elevation_meters
        FROM venues
        ORDER BY capacity DESC
    """)


def get_real_wc26_venues() -> pd.DataFrame:
    """Alias for get_venues — backward-compatible name."""
    return get_venues()


def get_knockout_bracket() -> pd.DataFrame:
    """Knockout-stage matches with computed winner (alias of get_knockout_bracket_summary)."""
    return get_knockout_bracket_summary()


def get_real_wc26_knockout_bracket() -> pd.DataFrame:
    """Alias — backward-compatible name."""
    return get_knockout_bracket_summary()


# ----- Players page -------------------------------------------------------

def get_players() -> pd.DataFrame:
    """1,248 players with squad info (position, club, market value, caps, height)."""
    return _execute_readonly_query("""
        SELECT p.player_id, p.team_id, t.team_name, p.player_name,
               p.position, p.club_team, p.market_value_eur, p.caps,
               p.date_of_birth, p.height_cm, p.goals
        FROM squads_and_players p
        JOIN teams t ON t.team_id = p.team_id
        ORDER BY p.market_value_eur DESC
    """)


def get_player_tournament_stats() -> pd.DataFrame:
    """Per-player WC26 in-tournament stats (goals, assists, cards, minutes, xG)."""
    return _execute_readonly_query("""
        SELECT player_id, player_name, team_name, confederation, position,
               matches_played, matches_started, minutes_played,
               goals, assists, yellow_cards, red_cards,
               penalty_goals, own_goals, clean_sheets, saves,
               goals_conceded, shots, shots_on_target, average_rating
        FROM v_player_stats_full
        ORDER BY goals DESC, assists DESC
    """)


def get_real_wc26_players() -> pd.DataFrame:
    """Alias for get_players."""
    return get_players()


def get_real_wc26_player_stats() -> pd.DataFrame:
    """Alias for get_player_tournament_stats."""
    return get_player_tournament_stats()


# ----- Per-team xG aggregation (Overview page) ---------------------------

def get_xg_by_team() -> pd.DataFrame:
    """Per-team expected goals for/against aggregated across all WC26 matches.
    Computed from matches_detailed (which has home_xg, away_xg per match) by
    unfolding the home/away rows into a team-perspective view."""
    return _execute_readonly_query("""
        WITH home AS (
            SELECT home_team_name AS team, home_xg AS xg_for, away_xg AS xg_against
            FROM matches_detailed
        ),
        away AS (
            SELECT away_team_name AS team, away_xg AS xg_for, home_xg AS xg_against
            FROM matches_detailed
        )
        SELECT team,
               COUNT(*) AS matches,
               SUM(xg_for) AS xg_for,
               SUM(xg_against) AS xg_against
        FROM (SELECT * FROM home UNION ALL SELECT * FROM away)
        GROUP BY team
        ORDER BY xg_for DESC
    """)


def get_real_wc26_xg_by_team() -> pd.DataFrame:
    """Alias for get_xg_by_team."""
    return get_xg_by_team()


# ----- Referees (Matches page) -------------------------------------------

def get_referees() -> pd.DataFrame:
    """28 referees with country and avg cards per game."""
    return _execute_readonly_query("""
        SELECT referee_id, name, country, avg_cards_per_game
        FROM referees
        ORDER BY avg_cards_per_game DESC
    """)


def get_real_wc26_referees() -> pd.DataFrame:
    """Alias for get_referees."""
    return get_referees()


# ----- Convenience aliases used by the page files -------------------------

# teams.py historical alias: `get_real_wc26_teams` ≠ `get_real_wc26_team_strength`
get_real_wc26_teams = get_teams
# matches.py historical alias: `get_real_wc26_matches_enriched` was the
# pre-Athena pandas "matches_detailed + venue + ref + player_name" join —
# Athena's v_matches_enriched view does the same wide-form pivot, joining
# match_team_stats onto matches in home_/away_ columns.
def get_real_wc26_matches_enriched() -> pd.DataFrame:
    """Wide-form matches joined to per-team in-match stats (possession,
    shots, corners, fouls, saves, venue capacity/lat/lon, etc.).
    Columns expected by matches.py: home_possession, away_possession,
    home_shots, away_shots, home_shots_on_target, away_shots_on_target,
    home_corners, away_corners, home_fouls, away_fouls, home_saves,
    away_saves, venue_capacity, venue_latitude, venue_longitude."""
    return _execute_readonly_query("""
        SELECT match_id, date, kickoff_time_utc, stage_name,
               home_team_name, home_fifa_code, home_team_id,
               away_team_name, away_fifa_code, away_team_id,
               home_score, away_score,
               home_penalty_score, away_penalty_score,
               status, result_type, home_xg, away_xg,
               home_goalkeeper, away_goalkeeper,
               player_of_the_match_name, referee_name,
               stadium_name, city, country,
               venue_capacity, venue_latitude, venue_longitude, venue_elevation,
               home_possession, home_shots, home_shots_on_target,
               home_corners, home_fouls, home_saves, home_potm,
               away_possession, away_shots, away_shots_on_target,
               away_corners, away_fouls, away_saves, away_potm
        FROM v_matches_enriched
        ORDER BY date, match_id
    """)


# ---------------------------------------------------------------------------
# Retired loaders — kept as stubs that raise, to catch any stale callers.
# The pre-tournament Monte Carlo simulations are obsolete now that the
# tournament is over. Dataflow should go through the views above instead.
# ---------------------------------------------------------------------------
def _retired(name: str):
    def _stub(*a, **kw):
        raise NotImplementedError(
            f"{name}() is retired. The pre-tournament Monte Carlo simulation "
            f"loaded by this function is obsolete now that the WC26 tournament "
            f"is complete. Use the view-backed loaders above (get_team_strength, "
            f"get_tournament_overview, get_knockout_bracket, etc.) instead."
        )
    return _stub


get_predictions = _retired("get_predictions")
get_team_attributes = _retired("get_team_attributes")
get_stage_probabilities = _retired("get_stage_probabilities")
get_match_predictions = _retired("get_match_predictions")
get_team_match_results = _retired("get_team_match_results")
