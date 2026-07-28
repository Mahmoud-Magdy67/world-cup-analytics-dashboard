#!/usr/bin/env python3
"""
Migrate the real Kaggle WC26 dataset → S3 + Athena.

Pipeline:
  1. Upload the 12 Kaggle CSVs from data/kaggle_wc26/ to
     s3://<S3_DATA_BUCKET>/kaggle_wc26/<filename>
  2. DROP TABLE IF EXISTS + CREATE EXTERNAL TABLE for each CSV in
     the worldcup_2026 Athena database (Hive LazySimpleSerDe, CSV with header).
  3. CREATE OR REPLACE VIEW for the derived analytical views the dashboard
     reads from (replacing the pandas-side aggregations):
        v_tournament_summary   — 1 row of tournament KPIs
        v_team_stats           — per-team goals/W/D/L from real matches
        v_team_strength        — teams.csv + wc26 goals/assists aggregated
        v_match_team_stats_agg — per-team avg possession/shots/etc.
        v_knockout_bracket     — 32 knockout-stage matches with winner
        v_outcome_counts       — per-stage home/away/draw/goal counts

Idempotent: safe to re-run. DROPs everything it's about to create.
Requires:
  - boto3
  - AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_REGION in env
  - S3_DATA_BUCKET, ATHENA_DATABASE in env (with sane defaults)
"""
from __future__ import annotations
import os
import sys
import time
import itertools
from pathlib import Path

import boto3

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
# Credentials are required — no defaults. Set via environment variables:
#   AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_REGION (eu-west-3),
#   ATHENA_OUTPUT_BUCKET (must be in the same region as AWS_REGION).
# In CI / Streamlit Cloud these are wired via st.secrets['credentials'] /
# .streamlit/secrets.toml — for the one-shot migrator, env vars are simplest.
AWS_REGION = os.getenv("AWS_REGION", "eu-west-3")

S3_DATA_BUCKET = os.getenv("S3_DATA_BUCKET", "wc2026-simulation-data")
ATHENA_DATABASE = os.getenv("ATHENA_DATABASE", "worldcup_2026")
ATHENA_OUTPUT_BUCKET = os.getenv("ATHENA_OUTPUT_BUCKET",
                                 "aws-athena-query-results-986420598705-eu-west-3")  # eu-west-3 result bucket

KAGGLE_DIR = Path(__file__).resolve().parent / "data" / "kaggle_wc26"
S3_PREFIX = "kaggle_wc26"

# Validate credentials are present (fail loud instead of letting boto3 auth-fail
# mid-migration with a confusing traceback).
if not os.getenv("AWS_ACCESS_KEY_ID") or not os.getenv("AWS_SECRET_ACCESS_KEY"):
    print("❌ AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY not set in environment.")
    print("   Set them before running: e.g.")
    print("     export AWS_ACCESS_KEY_ID=... AWS_SECRET_ACCESS_KEY=... AWS_REGION=eu-west-3")
    print("   Or prefix the run:  AWS_ACCESS_KEY_ID=... AWS_SECRET_ACCESS_KEY=... python migrate_kaggle_to_aws.py")
    sys.exit(1)

# ---------------------------------------------------------------------------
# Schemas — names match the CSV header columns exactly (case sensitive in Athena)
# ---------------------------------------------------------------------------
# Each entry: csv_filename -> list of (column_name, athena_type)
SCHEMAS: dict[str, list[tuple[str, str]]] = {
    "teams.csv": [
        ("team_id", "int"),
        ("team_name", "string"),
        ("fifa_code", "string"),
        ("group_letter", "string"),
        ("confederation", "string"),
        ("fifa_ranking_pre_tournament", "int"),
        ("elo_rating", "int"),
        ("manager_name", "string"),
    ],
    "venues.csv": [
        ("venue_id", "int"),
        ("stadium_name", "string"),
        ("city", "string"),
        ("country", "string"),
        ("capacity", "int"),
        ("latitude", "double"),
        ("longitude", "double"),
        ("elevation_meters", "int"),
    ],
    "referees.csv": [
        ("referee_id", "int"),
        ("name", "string"),
        ("country", "string"),
        ("avg_cards_per_game", "double"),
    ],
    "tournament_stages.csv": [
        ("stage_id", "int"),
        ("stage_name", "string"),
        ("is_knockout", "string"),  # "True"/"False" strings in source
    ],
    "matches.csv": [
        ("match_id", "int"),
        ("date", "string"),
        ("kickoff_time_utc", "string"),
        ("stage_id", "int"),
        ("venue_id", "int"),
        ("home_team_id", "int"),
        ("away_team_id", "int"),
        ("home_score", "int"),
        ("away_score", "int"),
        ("home_penalty_score", "int"),
        ("away_penalty_score", "int"),
        ("status", "string"),
        ("result_type", "string"),
        ("home_xg", "double"),
        ("away_xg", "double"),
        ("referee_id", "int"),
        ("player_of_the_match_id", "int"),
    ],
    "matches_detailed.csv": [
        ("match_id", "int"),
        ("date", "string"),
        ("kickoff_time_utc", "string"),
        ("stage_name", "string"),
        ("stadium_name", "string"),
        ("city", "string"),
        ("country", "string"),
        ("home_team_name", "string"),
        ("home_fifa_code", "string"),
        ("away_team_name", "string"),
        ("away_fifa_code", "string"),
        ("home_score", "int"),
        ("away_score", "int"),
        ("home_penalty_score", "int"),
        ("away_penalty_score", "int"),
        ("status", "string"),
        ("result_type", "string"),
        ("home_xg", "double"),
        ("away_xg", "double"),
        ("home_goalkeeper", "string"),
        ("away_goalkeeper", "string"),
        ("player_of_the_match_name", "string"),
        ("referee_name", "string"),
    ],
    "match_team_stats.csv": [
        ("match_id", "int"),
        ("team_id", "int"),
        ("possession_pct", "int"),
        ("total_shots", "int"),
        ("shots_on_target", "int"),
        ("corners", "int"),
        ("fouls", "int"),
        ("offsides", "int"),
        ("saves", "int"),
        ("player_of_the_match", "string"),
        ("data_source", "string"),
        ("last_updated", "string"),
    ],
    "match_events.csv": [
        ("event_id", "int"),
        ("match_id", "int"),
        ("minute", "int"),
        ("event_type", "string"),
        ("team_id", "int"),
        ("player_id", "int"),
    ],
    "match_lineups.csv": [
        ("lineup_id", "int"),
        ("match_id", "int"),
        ("player_id", "int"),
        ("team_id", "int"),
        ("is_starting_xi", "int"),
        ("tactical_position", "string"),
        ("minutes_played", "int"),
    ],
    "match_prediction_features.csv": [
        ("match_id", "int"),
        ("date", "string"),
        ("kickoff_time_utc", "string"),
        ("stage_id", "int"),
        ("is_knockout", "int"),
        ("home_team_id", "int"),
        ("home_team_name", "string"),
        ("home_fifa_code", "string"),
        ("home_confederation", "string"),
        ("away_team_id", "int"),
        ("away_team_name", "string"),
        ("away_fifa_code", "string"),
        ("away_confederation", "string"),
        ("venue_id", "int"),
        ("stadium_name", "string"),
        ("venue_city", "string"),
        ("venue_country", "string"),
        ("venue_capacity", "int"),
        ("venue_elevation_meters", "double"),
        ("referee_id", "int"),
        ("referee_name", "string"),
        ("referee_avg_cards", "double"),
        ("home_fifa_rank", "int"),
        ("away_fifa_rank", "int"),
        ("home_elo", "double"),
        ("away_elo", "double"),
        ("home_is_host", "int"),
        ("away_is_host", "int"),
        ("home_squad_avg_age", "double"),
        ("away_squad_avg_age", "double"),
        ("home_squad_total_caps", "int"),
        ("away_squad_total_caps", "int"),
        ("home_squad_total_value_eur", "double"),
        ("away_squad_total_value_eur", "double"),
        ("home_squad_avg_value_eur", "double"),
        ("away_squad_avg_value_eur", "double"),
        ("home_rest_days", "double"),
        ("away_rest_days", "double"),
        ("home_prev_avg_goals_scored", "double"),
        ("away_prev_avg_goals_scored", "double"),
        ("home_prev_avg_goals_conceded", "double"),
        ("away_prev_avg_goals_conceded", "double"),
        ("home_prev_avg_possession", "double"),
        ("away_prev_avg_possession", "double"),
        ("home_prev_avg_shots", "double"),
        ("away_prev_avg_shots", "double"),
        ("home_prev_avg_shots_on_target", "double"),
        ("away_prev_avg_shots_on_target", "double"),
        ("home_prev_avg_saves", "double"),
        ("away_prev_avg_saves", "double"),
        ("home_prev_avg_corners", "double"),
        ("away_prev_avg_corners", "double"),
        ("home_prev_avg_fouls", "double"),
        ("away_prev_avg_fouls", "double"),
        ("home_prev_avg_offsides", "double"),
        ("away_prev_avg_offsides", "double"),
        ("home_prev_avg_xg_scored", "double"),
        ("home_prev_avg_xg_conceded", "double"),
        ("away_prev_avg_xg_scored", "double"),
        ("away_prev_avg_xg_conceded", "double"),
        ("home_score", "int"),
        ("away_score", "int"),
        ("result_type", "string"),
        ("home_xg", "double"),
        ("away_xg", "double"),
        ("match_result", "string"),
    ],
    "squads_and_players.csv": [
        ("player_id", "int"),
        ("team_id", "int"),
        ("player_name", "string"),
        ("position", "string"),
        ("club_team", "string"),
        ("market_value_eur", "int"),
        ("caps", "int"),
        ("date_of_birth", "string"),
        ("height_cm", "int"),
        ("goals", "int"),
    ],
    "player_stats.csv": [
        ("player_id", "int"),
        ("player_name", "string"),
        ("team_id", "int"),
        ("position", "string"),
        ("matches_played", "int"),
        ("matches_started", "int"),
        ("minutes_played", "int"),
        ("goals", "int"),
        ("assists", "int"),
        ("shots", "string"),          # CSV contains non-numeric placeholders — kept string, parsed in views
        ("shots_on_target", "string"),
        ("yellow_cards", "int"),
        ("red_cards", "int"),
        ("penalty_goals", "int"),
        ("own_goals", "int"),
        ("clean_sheets", "int"),
        ("saves", "int"),
        ("goals_conceded", "int"),
        ("average_rating", "string"),
        ("data_source", "string"),
        ("last_verified", "string"),
    ],
}

# Map CSV filename → Athena table name
TABLE_NAMES = {csv: csv.replace(".csv", "") for csv in SCHEMAS}

# ---------------------------------------------------------------------------
# AWS clients
# ---------------------------------------------------------------------------
def make_clients():
    s3 = boto3.client(
        "s3",
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
        region_name=AWS_REGION,
    )
    athena = boto3.client(
        "athena",
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
        region_name=AWS_REGION,
    )
    glue = boto3.client(
        "glue",
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
        region_name=AWS_REGION,
    )
    return s3, athena, glue

# ---------------------------------------------------------------------------
# Step 1: Upload CSVs to S3
# ---------------------------------------------------------------------------
def upload_csvs(s3):
    print(f"\n[1/3] Uploading Kaggle CSVs to s3://{S3_DATA_BUCKET}/{S3_PREFIX}/ ...")
    if not KAGGLE_DIR.is_dir():
        print(f"  ❌ Missing Kaggle data directory: {KAGGLE_DIR}")
        sys.exit(1)
    csv_files = sorted([f for f in os.listdir(KAGGLE_DIR) if f.endswith(".csv")])
    missing = [f for f in SCHEMAS if f not in csv_files]
    if missing:
        print(f"  ❌ Expected CSVs missing from {KAGGLE_DIR}: {missing}")
        sys.exit(1)
    # Clear the target S3 prefix so old files don't linger (idempotent re-runs)
    print(f"  Clearing stale S3 prefix '{S3_PREFIX}/' ...")
    paginator = s3.get_paginator("list_objects_v2")
    deleted = 0
    for page in paginator.paginate(Bucket=S3_DATA_BUCKET, Prefix=f"{S3_PREFIX}/"):
        objs = [{"Key": o["Key"]} for o in page.get("Contents", [])]
        if objs:
            s3.delete_objects(Bucket=S3_DATA_BUCKET, Delete={"Objects": objs})
            deleted += len(objs)
    print(f"  Deleted {deleted} existing objects under {S3_PREFIX}/.")
    for csv in csv_files:
        local = KAGGLE_DIR / csv
        # Upload into a per-table folder so Athena's LOCATION scan sees exactly one file:
        # s3://.../kaggle_wc26/teams/teams.csv — LOCATION 's3://.../kaggle_wc26/teams/'
        table_name = csv.replace(".csv", "")
        key = f"{S3_PREFIX}/{table_name}/{csv}"
        size = local.stat().st_size
        s3.upload_file(str(local), S3_DATA_BUCKET, key)
        print(f"  ✅ {csv:35} → s3://{S3_DATA_BUCKET}/{key}  ({size:,} bytes)")
    print(f"  Uploaded {len(csv_files)} files.")

# ---------------------------------------------------------------------------
# Step 2: Create Athena external tables
# ---------------------------------------------------------------------------
def build_create_table_ddl(table_name: str, columns: list[tuple[str, str]], s3_location: str) -> str:
    cols_sql = ",\n    ".join(f"{name} {typ}" for name, typ in columns)
    return f"""CREATE EXTERNAL TABLE IF NOT EXISTS {table_name} (
    {cols_sql}
)
ROW FORMAT SERDE 'org.apache.hadoop.hive.serde2.lazy.LazySimpleSerDe'
WITH SERDEPROPERTIES (
    'serialization.format' = ',',
    'field.delim' = ',',
    'quoteChar' = '"',
    'skip.header.line.count' = '1'
)
STORED AS TEXTFILE
LOCATION '{s3_location}'
TBLPROPERTIES ('has_encrypted_data' = 'false')"""

def run_query(athena, query: str, label: str, poll_seconds: float = 0.7, max_wait: int = 60) -> str:
    """Run an Athena query and wait for completion. Returns the final state."""
    try:
        qid = athena.start_query_execution(
            QueryString=query,
            QueryExecutionContext={"Database": ATHENA_DATABASE},
            ResultConfiguration={"OutputLocation": f"s3://{ATHENA_OUTPUT_BUCKET}/"},
        )["QueryExecutionId"]
    except Exception as e:
        print(f"  ❌ [{label}] start_query_execution: {str(e)[:200]}")
        return "FAILED"
    waited = 0.0
    while waited < max_wait:
        st = athena.get_query_execution(QueryExecutionId=qid)["QueryExecution"]["Status"]
        state = st["State"]
        if state in ("SUCCEEDED", "FAILED", "CANCELLED"):
            if state != "SUCCEEDED":
                reason = (st.get("StateChangeReason") or "")[:200]
                print(f"  ❌ [{label}] {state}: {reason}")
            return state
        time.sleep(poll_seconds)
        waited += poll_seconds
    print(f"  ⏱ [{label}] timed out after {max_wait}s (state was {state})")
    return "TIMEOUT"

def create_tables(athena, glue):
    print(f"\n[2/3] Creating Athena external tables in database '{ATHENA_DATABASE}' ...")
    # Ensure database exists
    try:
        glue.get_database(Name=ATHENA_DATABASE)
    except glue.exceptions.EntityNotFoundException:
        print(f"  Database {ATHENA_DATABASE} not found — creating.")
        run_query(athena, f"CREATE DATABASE {ATHENA_DATABASE}", "create_database", max_wait=30)

    for csv, columns in SCHEMAS.items():
        table_name = TABLE_NAMES[csv]
        s3_loc = f"s3://{S3_DATA_BUCKET}/{S3_PREFIX}/{csv.rsplit('.', 1)[0]}/"
        # Drop if exists (Athena DDL DROP doesn't accept IF EXISTS in all engines — use Glue API)
        try:
            glue.delete_table(DatabaseName=ATHENA_DATABASE, Name=table_name)
            print(f"  ♻️  Dropped stale table {table_name}")
        except glue.exceptions.EntityNotFoundException:
            pass
        ddl = build_create_table_ddl(table_name, columns, s3_loc)
        state = run_query(athena, ddl, f"CREATE {table_name}", max_wait=30)
        if state == "SUCCEEDED":
            print(f"  ✅ Created table {table_name} ({len(columns)} columns)")
        else:
            print(f"  ❌ Failed to create {table_name} (state={state})")
            return False
    return True

# ---------------------------------------------------------------------------
# Step 3: Create derived views (the dashbaord's actual data sources)
# ---------------------------------------------------------------------------
DERIVED_VIEWS = {
    "v_team_stats": """
        WITH home AS (
            SELECT home_team_name AS team, home_score AS goals_for, away_score AS goals_against,
                   match_id, stage_name, result_type
            FROM matches_detailed
        ),
        away AS (
            SELECT away_team_name AS team, away_score AS goals_for, home_score AS goals_against,
                   match_id, stage_name, result_type
            FROM matches_detailed
        ),
        both AS (
            SELECT * FROM home
            UNION ALL
            SELECT * FROM away
        )
        SELECT
            team,
            COUNT(*) AS matches,
            SUM(goals_for) AS goals_for,
            SUM(goals_against) AS goals_against,
            SUM(CASE WHEN goals_for > goals_against THEN 1 ELSE 0 END) AS W,
            SUM(CASE WHEN goals_for = goals_against AND result_type IN ('Regular','AET') THEN 1 ELSE 0 END) AS D,
            SUM(CASE WHEN goals_for < goals_against THEN 1 ELSE 0 END) AS L,
            SUM(goals_for) - SUM(goals_against) AS goal_difference
        FROM both
        GROUP BY team
    """,

    "v_tournament_summary": """
        WITH m AS (SELECT * FROM matches_detailed),
        final_row AS (
            SELECT * FROM m WHERE stage_name = 'Final' LIMIT 1
        )
        SELECT
            (SELECT COUNT(*) FROM m) AS total_matches,
            (SELECT COALESCE(SUM(home_score), 0) + COALESCE(SUM(away_score), 0) FROM m) AS total_goals,
            (SELECT COALESCE(SUM(home_score),0)+COALESCE(SUM(away_score),0) FROM m) * 1.0
             / NULLIF((SELECT COUNT(*) FROM m), 0) AS avg_goals_per_match,
            (SELECT home_team_name FROM final_row) AS finalist_home,
            (SELECT away_team_name FROM final_row) AS finalist_away,
            (SELECT CASE WHEN home_score > away_score THEN home_team_name
                         WHEN away_score > home_score THEN away_team_name
                         WHEN home_penalty_score > away_penalty_score THEN home_team_name
                         ELSE away_team_name END FROM final_row) AS winner,
            (SELECT CASE WHEN home_score > away_score THEN away_team_name
                         WHEN away_score > home_score THEN home_team_name
                         WHEN home_penalty_score > away_penalty_score THEN away_team_name
                         ELSE home_team_name END FROM final_row) AS runner_up,
            (SELECT CAST(home_score AS VARCHAR) || '-' || CAST(away_score AS VARCHAR) FROM final_row) AS final_score,
            (SELECT result_type FROM final_row) AS result_type,
            (SELECT date FROM final_row) AS final_date,
            (SELECT stadium_name FROM final_row) AS final_venue,
            (SELECT city FROM final_row) AS final_city
    """,

    "v_team_strength": """
        WITH home AS (
            SELECT home_team_name AS team, home_score AS goals_for, away_score AS goals_against, match_id
            FROM matches_detailed
        ),
        away AS (
            SELECT away_team_name AS team, away_score AS goals_for, home_score AS goals_against, match_id
            FROM matches_detailed
        ),
        goals AS (
            SELECT team, SUM(goals_for) AS wc26_goals FROM (
                SELECT team, goals_for FROM home
                UNION ALL
                SELECT team, goals_for FROM away
            ) GROUP BY team
        ),
        -- assists come from player_stats (per-team sum)
        assists AS (
            SELECT t.team_name, COALESCE(SUM(ps.assists), 0) AS wc26_assists
            FROM teams t
            LEFT JOIN player_stats ps ON ps.team_id = t.team_id
            GROUP BY t.team_name
        )
        SELECT
            t.team_id,
            t.team_name,
            t.fifa_code,
            t.group_letter,
            t.confederation,
            t.fifa_ranking_pre_tournament,
            t.elo_rating,
            t.manager_name,
            COALESCE(s.market_value_eur, 0) AS squad_market_value_eur,
            COALESCE(g.wc26_goals, 0) AS wc26_goals,
            COALESCE(a.wc26_assists, 0) AS wc26_assists
        FROM teams t
        LEFT JOIN (
            SELECT team_id, SUM(market_value_eur) AS market_value_eur
            FROM squads_and_players
            GROUP BY team_id
        ) s ON s.team_id = t.team_id
        LEFT JOIN goals g ON g.team = t.team_name
        LEFT JOIN assists a ON a.team_name = t.team_name
    """,

    "v_match_team_stats_agg": """
        SELECT
            t.team_id,
            t.team_name,
            COUNT(*) AS matches,
            AVG(mts.possession_pct) AS avg_possession,
            AVG(mts.total_shots) AS avg_shots,
            AVG(mts.shots_on_target) AS avg_shots_on_target,
            AVG(mts.corners) AS avg_corners,
            AVG(mts.fouls) AS avg_fouls,
            AVG(mts.offsides) AS avg_offsides,
            AVG(mts.saves) AS avg_saves
        FROM match_team_stats mts
        JOIN teams t ON t.team_id = mts.team_id
        GROUP BY t.team_id, t.team_name
        ORDER BY t.team_name
    """,

    "v_knockout_bracket": """
        SELECT
            match_id,
            CAST(date AS DATE) AS date,
            stage_name,
            home_team_name,
            away_team_name,
            home_score,
            away_score,
            home_penalty_score,
            away_penalty_score,
            result_type,
            stadium_name,
            city,
            country,
            CASE
                WHEN home_score > away_score THEN home_team_name
                WHEN away_score > home_score THEN away_team_name
                WHEN home_penalty_score > away_penalty_score THEN home_team_name
                WHEN away_penalty_score > home_penalty_score THEN away_team_name
                ELSE NULL
            END AS winner
        FROM matches_detailed
        WHERE stage_name IN (
            'Round of 32', 'Round of 16', 'Quarter-finals',
            'Semi-finals', 'Third-place match', 'Final'
        )
        ORDER BY
            CASE stage_name
                WHEN 'Round of 32' THEN 0
                WHEN 'Round of 16' THEN 1
                WHEN 'Quarter-finals' THEN 2
                WHEN 'Semifinals' THEN 3
                WHEN 'Third-place match' THEN 4
                WHEN 'Final' THEN 5
                ELSE 99
            END,
            date
    """,

    "v_outcome_counts": """
        WITH m AS (SELECT * FROM matches_detailed)
        SELECT
            'Total' AS stage_name,
            COUNT(*) AS matches,
            SUM(CASE WHEN home_score > away_score THEN 1 ELSE 0 END) AS home_wins,
            SUM(CASE WHEN away_score > home_score THEN 1 ELSE 0 END) AS away_wins,
            SUM(CASE WHEN home_score = away_score THEN 1 ELSE 0 END) AS draws,
            SUM(home_score + away_score) AS goals
        FROM m
        UNION ALL
        SELECT
            stage_name,
            COUNT(*) AS matches,
            SUM(CASE WHEN home_score > away_score THEN 1 ELSE 0 END) AS home_wins,
            SUM(CASE WHEN away_score > home_score THEN 1 ELSE 0 END) AS away_wins,
            SUM(CASE WHEN home_score = away_score THEN 1 ELSE 0 END) AS draws,
            SUM(home_score + away_score) AS goals
        FROM m
        GROUP BY stage_name
    """,

    "v_player_stats_full": """
        SELECT
            ps.player_id,
            ps.player_name,
            t.team_name,
            t.confederation,
            ps.position,
            ps.matches_played,
            ps.matches_started,
            ps.minutes_played,
            ps.goals,
            ps.assists,
            ps.yellow_cards,
            ps.red_cards,
            ps.penalty_goals,
            ps.own_goals,
            ps.clean_sheets,
            ps.saves,
            ps.goals_conceded,
            TRY_CAST(ps.shots AS double) AS shots,
            TRY_CAST(ps.shots_on_target AS double) AS shots_on_target,
            TRY_CAST(ps.average_rating AS double) AS average_rating
        FROM player_stats ps
        JOIN teams t ON t.team_id = ps.team_id
    """,

    # Wide-form matches joined to per-team in-match stats (matches.py expects
    # this shape — home_possession / away_possession / home_shots / away_shots
    # / home_corners / away_corners / home_fouls / away_fouls / home_saves /
    # away_saves / venue_capacity / venue_latitude / venue_longitude).
    # NOTE: matches_detailed has no team_id column, so we derive it from
    # teams via home_team_name / away_team_name before joining match_team_stats.
    "v_matches_enriched": """
        WITH
        m AS (
            SELECT
                md.match_id,
                md.date,
                md.kickoff_time_utc,
                md.stage_name,
                md.home_team_name,
                md.home_fifa_code,
                th.team_id AS home_team_id,
                md.away_team_name,
                md.away_fifa_code,
                ta.team_id AS away_team_id,
                md.home_score,
                md.away_score,
                md.home_penalty_score,
                md.away_penalty_score,
                md.status,
                md.result_type,
                md.home_xg,
                md.away_xg,
                md.home_goalkeeper,
                md.away_goalkeeper,
                md.player_of_the_match_name,
                md.referee_name,
                md.stadium_name,
                md.city,
                md.country
            FROM matches_detailed md
            LEFT JOIN teams th ON th.team_name = md.home_team_name
            LEFT JOIN teams ta ON ta.team_name = md.away_team_name
        ),
        home_stats AS (
            SELECT m.match_id, m.home_team_id, mts.possession_pct AS home_possession,
                   mts.total_shots AS home_shots,
                   mts.shots_on_target AS home_shots_on_target,
                   mts.corners AS home_corners,
                   mts.fouls AS home_fouls,
                   mts.saves AS home_saves,
                   mts.player_of_the_match AS home_potm
            FROM m
            JOIN match_team_stats mts
                ON mts.match_id = m.match_id
                AND mts.team_id = m.home_team_id
        ),
        away_stats AS (
            SELECT m.match_id, m.away_team_id, mts.possession_pct AS away_possession,
                   mts.total_shots AS away_shots,
                   mts.shots_on_target AS away_shots_on_target,
                   mts.corners AS away_corners,
                   mts.fouls AS away_fouls,
                   mts.saves AS away_saves,
                   mts.player_of_the_match AS away_potm
            FROM m
            JOIN match_team_stats mts
                ON mts.match_id = m.match_id
                AND mts.team_id = m.away_team_id
        )
        SELECT
            m.match_id, m.date, m.kickoff_time_utc, m.stage_name,
            m.home_team_name, m.home_fifa_code, m.home_team_id,
            m.away_team_name, m.away_fifa_code, m.away_team_id,
            m.home_score, m.away_score,
            m.home_penalty_score, m.away_penalty_score,
            m.status, m.result_type, m.home_xg, m.away_xg,
            m.home_goalkeeper, m.away_goalkeeper,
            m.player_of_the_match_name, m.referee_name,
            m.stadium_name, m.city, m.country,
            v.capacity         AS venue_capacity,
            v.latitude         AS venue_latitude,
            v.longitude        AS venue_longitude,
            v.elevation_meters AS venue_elevation,
            hs.home_possession, hs.home_shots, hs.home_shots_on_target,
            hs.home_corners, hs.home_fouls, hs.home_saves, hs.home_potm,
            aus.away_possession, aus.away_shots, aus.away_shots_on_target,
            aus.away_corners, aus.away_fouls, aus.away_saves, aus.away_potm
        FROM m
        LEFT JOIN venues     v   ON v.stadium_name = m.stadium_name
        LEFT JOIN home_stats hs  ON hs.match_id  = m.match_id AND hs.home_team_id = m.home_team_id
        LEFT JOIN away_stats aus ON aus.match_id = m.match_id AND aus.away_team_id = m.away_team_id
        ORDER BY m.date, m.match_id
    """,
}

def create_views(athena, glue):
    print(f"\n[3/3] Creating derived views in database '{ATHENA_DATABASE}' ...")
    for view_name, query in DERIVED_VIEWS.items():
        # Drop existing view via Glue API (Athena's DROP VIEW is sometimes finicky with CTAS-replaced objects)
        try:
            glue.delete_table(DatabaseName=ATHENA_DATABASE, Name=view_name)
            print(f"  ♻️  Dropped stale view {view_name}")
        except glue.exceptions.EntityNotFoundException:
            pass
        # Athena view DDL: CREATE OR REPLACE VIEW (Presto syntax)
        ddl = f"CREATE OR REPLACE VIEW {view_name} AS\n{query}"
        state = run_query(athena, ddl, f"VIEW {view_name}", max_wait=60)
        if state == "SUCCEEDED":
            print(f"  ✅ Created view {view_name}")
        else:
            print(f"  ⚠️  Failed view {view_name} (state={state}) — continuing")
    return True

# ---------------------------------------------------------------------------
# Verification
# ---------------------------------------------------------------------------
def verify(athena):
    print(f"\n[Verify] Sampling each table / view ...")
    objects = list(TABLE_NAMES.values()) + list(DERIVED_VIEWS.keys())
    for name in objects:
        qid = athena.start_query_execution(
            QueryString=f"SELECT COUNT(*) AS n FROM {name}",
            QueryExecutionContext={"Database": ATHENA_DATABASE},
            ResultConfiguration={"OutputLocation": f"s3://{ATHENA_OUTPUT_BUCKET}/"},
        )["QueryExecutionId"]
        for _ in range(40):
            st = athena.get_query_execution(QueryExecutionId=qid)["QueryExecution"]["Status"]
            if st["State"] in ("SUCCEEDED", "FAILED", "CANCELLED"):
                break
            time.sleep(0.7)
        if st["State"] != "SUCCEEDED":
            print(f"  ❌ {name}: {st['State']} — {(st.get('StateChangeReason') or '')[:120]}")
            continue
        # fetch the count value
        try:
            res = athena.get_query_results(QueryExecutionId=qid)["ResultSet"]
            row = res.get("Rows", [{}])[1] if len(res.get("Rows", [])) > 1 else res.get("Rows", [{}])[0]
            n = row.get("Data", [{}])[0].get("VarCharValue", "?")
        except Exception:
            n = "?"
        print(f"  ✅ {name:35} {n} rows")

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    print("=" * 78)
    print("  World Cup 2026 — Kaggle → S3 + Athena Migration")
    print("=" * 78)
    print(f"  S3 bucket     : {S3_DATA_BUCKET}")
    print(f"  S3 prefix     : {S3_PREFIX}/")
    print(f"  Athena DB     : {ATHENA_DATABASE}")
    print(f"  Athena output : s3://{ATHENA_OUTPUT_BUCKET}/")
    print(f"  Region        : {AWS_REGION}")
    print(f"  Kaggle dir    : {KAGGLE_DIR}")

    s3, athena, glue = make_clients()
    upload_csvs(s3)
    ok = create_tables(athena, glue)
    if not ok:
        print("\n❌ Table creation failed — aborting before views.")
        sys.exit(1)
    create_views(athena, glue)
    verify(athena)
    print("\n" + "=" * 78)
    print("  ✅ Migration complete.")
    print("=" * 78)

if __name__ == "__main__":
    main()
