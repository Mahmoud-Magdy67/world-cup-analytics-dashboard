"""
Enhanced AWS Athena data layer for World Cup Analytics Dashboard.
Production-grade data access with caching, error handling, and comprehensive queries.
"""
from dataclasses import dataclass
from typing import Final, Optional, Dict, Any
import os
import json
import pandas as pd
import boto3
import time
from datetime import datetime
from botocore.exceptions import ClientError, NoCredentialsError
import streamlit as st

# Configuration
AWS_REGION: Final[str] = os.getenv("AWS_REGION", "us-east-1")
ATHENA_DATABASE: Final[str] = os.getenv("ATHENA_DATABASE", "worldcup_2026")
ATHENA_OUTPUT_BUCKET: Final[str] = os.getenv("ATHENA_OUTPUT_BUCKET", "aws-athena-query-results-worldcup")

# Cache TTLs (seconds)
CACHE_TTL_KPI: Final[int] = 300  # 5 minutes
CACHE_TTL_TEAMS: Final[int] = 600  # 10 minutes
CACHE_TTL_PLAYERS: Final[int] = 900  # 15 minutes
CACHE_TTL_MATCHES: Final[int] = 3600  # 1 hour
CACHE_TTL_PREDICTIONS: Final[int] = 300  # 5 minutes

@dataclass(frozen=True)
class DataSourceStatus:
    mode: str
    athena_enabled: bool
    note: str
    tables_available: Optional[Dict[str, int]] = None
    last_refresh: Optional[datetime] = None

def _get_athena_client() -> Optional[boto3.client]:
    """Initialize Athena client from Streamlit secrets or environment credentials."""
    import streamlit as st
    
    # Try Streamlit secrets first (for Streamlit Cloud deployment)
    aws_access_key_id = None
    aws_secret_access_key = None
    region_name = AWS_REGION
    
    try:
        if hasattr(st, 'secrets') and 'credentials' in st.secrets:
            aws_access_key_id = st.secrets['credentials'].get('AWS_ACCESS_KEY_ID')
            aws_secret_access_key = st.secrets['credentials'].get('AWS_SECRET_ACCESS_KEY')
            region_name = st.secrets['credentials'].get('AWS_REGION', AWS_REGION)
    except Exception:
        pass
    
    # Fallback to environment variables (for local development)
    if not aws_access_key_id:
        aws_access_key_id = os.getenv("AWS_ACCESS_KEY_ID")
    if not aws_secret_access_key:
        aws_secret_access_key = os.getenv("AWS_SECRET_ACCESS_KEY")
    if not region_name:
        region_name = os.getenv("AWS_REGION", AWS_REGION)
    
    if not aws_access_key_id or not aws_secret_access_key:
        st.error("⚠️ AWS_ACCESS_KEY_ID or AWS_SECRET_ACCESS_KEY not found in secrets or environment")
        return None
    
    try:
        return boto3.client(
            'athena',
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
            region_name=region_name
        )
    except Exception as e:
        st.error(f"⚠️ Athena auth error: {str(e)[:100]}")
        return None

def _execute_athena_query(query: str) -> pd.DataFrame:
    """Execute a SELECT query on Athena and return results as DataFrame."""
    query_upper = query.strip().upper()
    if not (query_upper.startswith("SELECT") or query_upper.startswith("WITH")):
        raise ValueError(f"Only SELECT or WITH (CTE) queries allowed. Blocked: {query[:50]}")
    
    client = _get_athena_client()
    if not client:
        raise RuntimeError("Athena client not initialized. Check AWS credentials.")
    
    try:
        # Start query execution
        response = client.start_query_execution(
            QueryString=query,
            QueryExecutionContext={
                'Database': ATHENA_DATABASE
            },
            ResultConfiguration={
                'OutputLocation': f"s3://{ATHENA_OUTPUT_BUCKET}/"
            }
        )
        
        query_execution_id = response['QueryExecutionId']
        
        # Wait for query to complete
        while True:
            response = client.get_query_execution(QueryExecutionId=query_execution_id)
            status = response['QueryExecution']['Status']['State']
            
            if status in ['SUCCEEDED']:
                break
            elif status in ['FAILED', 'CANCELLED']:
                reason = response['QueryExecution']['Status'].get('StateChangeReason', 'Unknown error')
                raise RuntimeError(f"Athena query failed: {reason}")
            
            time.sleep(1)  # Wait before checking again
        
        # Get results
        results_paginator = client.get_paginator('get_query_results')
        results_iter = results_paginator.paginate(
            QueryExecutionId=query_execution_id,
            PaginationConfig={
                'PageSize': 1000
            }
        )
        
        # Process results into DataFrame
        records = []
        for results_page in results_iter:
            column_info = results_page['ResultSet']['ResultSetMetadata']['ColumnInfo']
            column_names = [col['Name'] for col in column_info]
            
            if 'Rows' in results_page['ResultSet']:
                for row in results_page['ResultSet']['Rows']:
                    if 'Data' in row:
                        record = {}
                        for i, data in enumerate(row['Data']):
                            if i < len(column_names):
                                record[column_names[i]] = data.get('VarCharValue', '')
                        records.append(record)
        
        # Remove the header row (first row) and convert to DataFrame
        if len(records) > 1:
            df = pd.DataFrame(records[1:], columns=column_names)
            # Convert numeric columns appropriately
            for col in df.columns:
                try:
                    df[col] = pd.to_numeric(df[col])
                except (ValueError, TypeError):
                    pass  # Keep as string if conversion fails
            return df
        else:
            # Empty result
            return pd.DataFrame(columns=column_names)
            
    except Exception as e:
        st.error(f"Athena query execution error: {e}")
        return pd.DataFrame()

def _execute_readonly_query(query: str, cache_key: Optional[str] = None) -> pd.DataFrame:
    """Execute a read-only SELECT query with caching."""
    query_upper = query.strip().upper()
    if not (query_upper.startswith("SELECT") or query_upper.startswith("WITH")):
        raise ValueError(f"Only SELECT or WITH (CTE) queries allowed. Blocked: {query[:50]}")
    return _execute_athena_query(query)

# ============================================================================
# STATUS & HEALTH CHECKS
# ============================================================================

@st.cache_data(ttl=60)
def get_data_source_status() -> DataSourceStatus:
    """Check if Athena is connected and list available tables."""
    client = _get_athena_client()
    if client:
        try:
            # Verify connection with simple query
            test_query = f"SELECT 1 FROM \"{ATHENA_DATABASE}\".\"wc26_dashboard_v16_live_july4\" LIMIT 1"
            _execute_athena_query(test_query)
            
            # Get table metadata for key tables
            tables_info = {}
            table_queries = {
                'wc26_dashboard_v16_live_july4': f'SELECT COUNT(*) as cnt FROM "{ATHENA_DATABASE}"."wc26_dashboard_v16_live_july4"',
                'v_winner_prediction_dashboard_v15_live_10m': f'SELECT COUNT(*) as cnt FROM "{ATHENA_DATABASE}"."v_winner_prediction_dashboard_v15_live_10m"',
                'v_real_player_rows_enriched_v8': f'SELECT COUNT(*) as cnt FROM "{ATHENA_DATABASE}"."v_real_player_rows_enriched_v8"',
                'v_team_schedule': f'SELECT COUNT(*) as cnt FROM "{ATHENA_DATABASE}"."v_team_schedule"',
                'looker_wc26_overview_kpis_v15_live_10m': f'SELECT COUNT(*) as cnt FROM "{ATHENA_DATABASE}"."looker_wc26_overview_kpis_v15_live_10m"',
                'ml_group_fixture_predictions_v15_live_match_calibrated': f'SELECT COUNT(*) as cnt FROM "{ATHENA_DATABASE}"."ml_group_fixture_predictions_v15_live_match_calibrated"',
            }
            for name, query in table_queries.items():
                try:
                    result = _execute_athena_query(query)
                    tables_info[name] = int(result['cnt'].iloc[0]) if not result.empty else 0
                except:
                    tables_info[name] = 0
            
            return DataSourceStatus(
                "athena", 
                True, 
                f"Connected to Athena database {ATHENA_DATABASE}",
                tables_info,
                datetime.now()
            )
        except Exception as e:
            return DataSourceStatus("athena_error", False, f"Athena connection failed: {str(e)[:100]}", None, datetime.now())
    return DataSourceStatus("mock", False, "Athena credentials not configured; using mock data", None, datetime.now())

# ============================================================================
# TOURNAMENT OVERVIEW - KPIs and Executive Dashboard
# ============================================================================

@st.cache_data(ttl=CACHE_TTL_KPI)
def get_tournament_overview() -> pd.DataFrame:
    """
    Get tournament-level KPIs from looker_wc26_overview_kpis_v15_live_10m.
    
    Returns: Single row with tournament KPIs
    """
    query = f"""
    SELECT 
        simulation_runs,
        team_count,
        predicted_champion,
        predicted_champion_probability,
        second_favorite,
        second_favorite_probability,
        champion_gap_probability,
        total_group_fixtures,
        completed_locked_fixtures,
        remaining_group_fixtures
    FROM "{ATHENA_DATABASE}"."looker_wc26_overview_kpis_v15_live_10m"
    """
    try:
        return _execute_readonly_query(query)
    except Exception as e:
        st.error(f"Tournament overview error: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=CACHE_TTL_TEAMS)
def get_teams() -> pd.DataFrame:
    """
    Fetch comprehensive team data from wc26_dashboard_v16_live_july4.
    
    Returns all 48 teams with UPDATED predictions (post R32), ELO, market value, 
    group stats, and tournament status (alive/eliminated).
    """
    query = f"""
    SELECT 
        team_name, group_name, winner_rank, championship_probability,
        elo_rating, total_market_value_eur, contender_tier,
        round32_probability, round16_probability, quarterfinal_probability,
        semifinal_probability, final_probability,
        elimination_stage, tournament_status
    FROM "{ATHENA_DATABASE}"."wc26_dashboard_v16_live_july4"
    ORDER BY winner_rank
    """
    try:
        return _execute_readonly_query(query)
    except Exception as e:
        st.error(f"Teams query error: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=CACHE_TTL_TEAMS)
def get_team_attributes() -> pd.DataFrame:
    """
    Get detailed team attributes from ml_fc_real_hybrid_team_attributes_vfc_2.
    
    Includes: ELO, market value, player stats, form ratings, strength scores.
    """
    query = f"""
    SELECT 
        team_name, fifa_code, group_name, continent, confederation,
        elo_rating, total_market_value_eur, market_value_index,
        vfc2_hybrid_power_score, real_world_score, fc_eye_test_score,
        avg_ovr_top23, avg_ovr_top11, best_player_ovr,
        gk_strength, defense_strength, midfield_strength, attack_strength,
        top23_goals, top23_assists, top23_xg, top23_xa,
        goalkeeper_save_rate, avg_club_last10_points_per_match,
        real_player_performance_score
    FROM "{ATHENA_DATABASE}"."ml_fc_real_hybrid_team_attributes_vfc_2"
    WHERE vfc2_hybrid_power_score IS NOT NULL
    ORDER BY vfc2_hybrid_power_score DESC
    """
    try:
        result = _execute_readonly_query(query)
        return result
    except Exception as e:
        st.error(f"Team attributes query error: {str(e)[:200]}")
        # Return empty DataFrame instead of crashing
        return pd.DataFrame()

# ============================================================================
# PLAYER ANALYTICS
# ============================================================================

@st.cache_data(ttl=CACHE_TTL_PLAYERS)
def get_players(limit: int = 500) -> pd.DataFrame:
    """
    Get World Cup 2026 players from local public_source datasets first.
    Prefer the validated public MVP snapshot (`public_source/`) and fall back
    to the legacy Athena view only if local files are missing.
    """
    base_dir = os.path.join(os.path.dirname(__file__), '..', 'public_source')
    player_stats_path = os.path.join(base_dir, 'player_stats_mominullptr.csv')
    squads_path = os.path.join(base_dir, 'squads_and_players_mominullptr.csv')
    if os.path.exists(player_stats_path) and os.path.exists(squads_path):
        try:
            stats = pd.read_csv(player_stats_path)
            squads = pd.read_csv(squads_path)
            # normalize expected columns
            for col in ['player_name','team_id','position','club_team','league']:
                if col not in stats.columns:
                    stats[col] = ''
                if col not in squads.columns:
                    squads[col] = ''
            # one canonical row per player from squads if available
            meta = squads[['player_name','team_id','position','club_team','league']].drop_duplicates('player_name')
            out = (
                stats[['player_name','team_id','position','matches_played','matches_started','minutes_played','goals','assists','shots','shots_on_target','yellow_cards','red_cards','penalty_goals','own_goals','clean_sheets','saves','goals_conceded','average_rating']]
                .merge(meta, on=['player_name','team_id','position'], how='left')
                .rename(columns={
                    'matches_played':'matches_played',
                    'matches_started':'starts',
                    'minutes_played':'minutes',
                    'average_rating':'average_rating',
                })
            )
            # attach team context: nation_code from teams, plus club/league/position from squads
            team_meta = pd.read_csv(os.path.join(base_dir, 'teams_mominullptr.csv'))
            if 'fifa_code' not in team_meta.columns and 'team_code' in team_meta.columns:
                team_meta = team_meta.rename(columns={'team_code': 'fifa_code'})
            if 'team_id' in team_meta.columns and 'fifa_code' in team_meta.columns:
                team_meta = team_meta[['team_id', 'fifa_code']].drop_duplicates('team_id')
                out = out.merge(team_meta, on='team_id', how='left')
            else:
                out['nation_code'] = out.get('nation_code', '')
            # fall back to squads metadata without wiping existing values from stats
            meta = squads[['player_name','team_id','position','club_team']].copy()
            for col in ['position','club_team']:
                if col not in meta.columns:
                    meta[col] = ''
            meta = meta.drop_duplicates(['player_name','team_id'])
            out = out.merge(meta, on=['player_name','team_id'], how='left', suffixes=('', '_sq'))
            for col in ['position', 'club_team', 'league']:
                real = col
                if real not in out.columns and f"{real}_sq" in out.columns:
                    out[real] = out[f"{real}_sq"]
                elif real in out.columns:
                    out[real] = out[real].fillna('').replace('nan', '', regex=False)
                    if f"{real}_sq" in out.columns:
                        out[real] = out[real].mask(out[real].eq(''), out[f"{real}_sq"].fillna(''))
                        out = out.drop(columns=[f"{real}_sq"], errors='ignore')
            out['nation_code'] = out.get('nation_code', '').fillna('').replace('nan', '', regex=False)
            out['season'] = '2024-2025'
            out['age'] = pd.NA
            out['nineties_played'] = pd.to_numeric(out['minutes'], errors='coerce').div(90)
            out['goals_assists'] = pd.to_numeric(out['goals'], errors='coerce').fillna(0) + pd.to_numeric(out['assists'], errors='coerce').fillna(0)
            out['xg'] = pd.to_numeric(out.get('shots_on_target', 0), errors='coerce').fillna(0) * 0.12
            out['xa'] = pd.to_numeric(out['assists'], errors='coerce').fillna(0)
            out['tackles'] = 0
            out['tackles_won'] = 0
            out['interceptions'] = 0
            out['blocks'] = 0
            out['clearances'] = 0
            out['tackles_interceptions'] = 0
            out['gk_minutes'] = pd.to_numeric(out['minutes'], errors='coerce').where(out['position'].astype(str).str.upper().eq('GK'), 0)
            out['gk_goals_against'] = 0
            out['gk_save_pct'] = pd.NA
            out['gk_clean_sheets'] = pd.to_numeric(out['clean_sheets'], errors='coerce').fillna(0)
            # deduplicate by player_name, keep best minutes/goals/assists
            if not out.empty:
                out['minutes_num'] = pd.to_numeric(out['minutes'], errors='coerce').fillna(0)
                out['goals_num'] = pd.to_numeric(out['goals'], errors='coerce').fillna(0)
                out['assists_num'] = pd.to_numeric(out['assists'], errors='coerce').fillna(0)
                out = out.sort_values(['player_name','minutes_num','goals_num','assists_num'], ascending=[True,False,False,False])
                out = out.drop_duplicates('player_name', keep='first')
                out = out.sort_values(['goals_num','assists_num','minutes_num'], ascending=[False,False,False]).reset_index(drop=True)
                if limit and limit > 0:
                    out = out.head(limit)
            # Canonicalize display names from openfootball Source of Truth
            _ID_PATH = os.path.join(os.path.dirname(__file__), 'openfootball_identity.json')
            if os.path.exists(_ID_PATH):
                try:
                    with open(_ID_PATH, 'r', encoding='utf-8') as _f:
                        _ID = json.load(_f)
                    _alias = _ID.get('name_alias') or {}
                    if _alias:
                        out['player_name'] = out['player_name'].astype(str).map(lambda n: _alias.get(n, n))
                except Exception:
                    pass
            return out
        except Exception:
            pass

    # legacy Athena source as fallback
    query = f"""
    WITH wc_nations AS (
      SELECT DISTINCT fifa_code
      FROM "{ATHENA_DATABASE}"."v_winner_prediction_dashboard_v15_live_10m"
    ),
    filtered AS (
      SELECT
          player_name, nation_code, position, club_team, league, season,
          age, matches_played, starts, minutes, nineties_played,
          goals, assists, goals_assists, xg, xa, npxg,
          shots, shots_on_target,
          tackles, tackles_won, interceptions, blocks, clearances, tackles_interceptions,
          gk_minutes, gk_goals_against, gk_save_pct, gk_clean_sheets,
          ROW_NUMBER() OVER (
              PARTITION BY player_name
              ORDER BY minutes DESC, goals DESC, assists DESC
          ) as dedup_rank
      FROM "{ATHENA_DATABASE}"."v_real_player_rows_enriched_v8"
      WHERE season = '2024-2025'
        AND nation_code IN (SELECT fifa_code FROM wc_nations)
    )
    SELECT 
        player_name, nation_code, position, club_team, league, season,
        age, matches_played, starts, minutes, nineties_played,
        goals, assists, goals_assists, xg, xa, npxg,
        shots, shots_on_target,
        tackles, tackles_won, interceptions, blocks, clearances, tackles_interceptions,
        gk_minutes, gk_goals_against, gk_save_pct, gk_clean_sheets
    FROM filtered
    WHERE dedup_rank = 1
    ORDER BY goals DESC, assists DESC, xg DESC
    LIMIT {limit}
    """
    try:
        return _execute_readonly_query(query)
    except Exception as e:
        st.error(f"Players query error: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=600)
def get_player_tournament_stats() -> pd.DataFrame:
    """
    Get World Cup 2026 tournament player stats from the validated public CSV dataset.
    Falls back to live ESPN stats API or ESPN Athena cache only if public CSV is unavailable.

    Returns DataFrame with: player_name, wc26_goals, wc26_assists
    """
    base_dir = os.path.join(os.path.dirname(__file__), '..', 'public_source')
    csv_candidates = ['player_stats_mominullptr.csv', 'player_stats.csv']
    df = pd.DataFrame()
    for name in csv_candidates:
        path = os.path.join(base_dir, name)
        if os.path.exists(path):
            try:
                df = pd.read_csv(path)
                if 'goals' in df.columns and 'assists' in df.columns and 'player_name' in df.columns:
                    break
            except Exception:
                df = pd.DataFrame()
    if df.empty:
        df = pd.DataFrame()

    if not df.empty:
        out = pd.DataFrame({
            'player_name': df['player_name'].astype(str),
            'wc26_goals': pd.to_numeric(df['goals'], errors='coerce').fillna(0).clip(lower=0).astype(int),
            'wc26_assists': pd.to_numeric(df['assists'], errors='coerce').fillna(0).clip(lower=0).astype(int),
        })
        out = _enrich_player_stats(out)
        out = _apply_name_alias(out)
        return out.sort_values(['wc26_goals', 'wc26_assists'], ascending=[False, False]).reset_index(drop=True)

    # ESPN fallback
    try:
        import requests as req
        url = 'https://site.api.espn.com/apis/site/v2/sports/soccer/fifa.world/statistics?dates=20260611-20260701'
        resp = req.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=15)
        if resp.status_code == 200:
            data = resp.json()
            players = {}
            for stat in data.get('stats', []):
                for leader in stat.get('leaders', []):
                    athlete = leader.get('athlete', {})
                    name = athlete.get('displayName')
                    value = leader.get('value', 0)
                    if not name:
                        continue
                    if name not in players:
                        players[name] = {'player_name': name, 'wc26_goals': 0, 'wc26_assists': 0}
                    stat_name = (stat.get('name') or '').lower()
                    if 'goal' in stat_name:
                        players[name]['wc26_goals'] = int(value or 0)
                    elif 'assist' in stat_name:
                        players[name]['wc26_assists'] = int(value or 0)
            if players:
                df_live = pd.DataFrame(list(players.values()))
                return _enrich_player_stats(df_live).sort_values(['wc26_goals', 'wc26_assists'], ascending=[False, False]).reset_index(drop=True)
    except Exception:
        pass

    # ESPN Athena cache fallback
    try:
        query = f"""
        SELECT player_name, wc26_goals, wc26_assists
        FROM "{ATHENA_DATABASE}"."raw_wc26_player_stats_espn"
        ORDER BY wc26_goals DESC, wc26_assists DESC
        """
        return _enrich_player_stats(_execute_readonly_query(query))
    except Exception as e:
        st.warning(f"Live player stats fetch failed, using fallback: {e}")
        return pd.DataFrame(columns=['player_name', 'wc26_goals', 'wc26_assists'])


# Public-source fallback metadata for tournament players missing from club-season view.
_FALLBACK_PLAYER_META = {
    'Lionel Messi': {'nation_code': 'ARG', 'position': 'FW', 'club_team': 'Inter Miami', 'league': 'MLS'},
    'Vinícius Júnior': {'nation_code': 'BRA', 'position': 'FW', 'club_team': 'Real Madrid', 'league': 'ESP'},
    'Ismaïla Sarr': {'nation_code': 'SEN', 'position': 'FW', 'club_team': 'Monaco', 'league': 'FRA'},
    'Julián Quiñones': {'nation_code': 'MEX', 'position': 'FW', 'club_team': 'Club América', 'league': 'MEX'},
    'Crysencio Summerville': {'nation_code': 'NED', 'position': 'FW', 'club_team': 'Southampton', 'league': 'ENG'},
    'Leandro Trossard': {'nation_code': 'BEL', 'position': 'FW', 'club_team': 'Arsenal', 'league': 'ENG'},
    'Jude Bellingham': {'nation_code': 'ENG', 'position': 'MF', 'club_team': 'Real Madrid', 'league': 'ESP'},
    'Ayase Ueda': {'nation_code': 'JPN', 'position': 'FW', 'club_team': 'Feyenoord', 'league': 'NED'},
    'Daichi Kamada': {'nation_code': 'JPN', 'position': 'MF', 'club_team': 'Crystal Palace', 'league': 'ENG'},
    'Yasin Ayari': {'nation_code': 'NOR', 'position': 'MF', 'club_team': 'Brighton', 'league': 'ENG'},
    'Youri Tielemans': {'nation_code': 'BEL', 'position': 'MF', 'club_team': 'Aston Villa', 'league': 'ENG'},
    'Pape Gueye': {'nation_code': 'SEN', 'position': 'MF', 'club_team': 'Marseille', 'league': 'FRA'},
    'Nicolas Pépé': {'nation_code': 'CIV', 'position': 'FW', 'club_team': 'Trabzonspor', 'league': 'TUR'},
    'Anthony Elanga': {'nation_code': 'SWE', 'position': 'FW', 'club_team': 'Nottingham Forest', 'league': 'ENG'},
    'Bradley Barcola': {'nation_code': 'FRA', 'position': 'FW', 'club_team': 'Paris Saint-Germain', 'league': 'FRA'},
    'Amad Diallo': {'nation_code': 'CIV', 'position': 'FW', 'club_team': 'Manchester United', 'league': 'ENG'},
    'Romelu Lukaku': {'nation_code': 'BEL', 'position': 'FW', 'club_team': 'Napoli', 'league': 'ITA'},
    'Ramin Rezaeian': {'nation_code': 'IRN', 'position': 'DF', 'club_team': 'Kazma SC', 'league': 'KUW'},
    'Cristiano Ronaldo': {'nation_code': 'POR', 'position': 'FW', 'club_team': 'Al-Nassr', 'league': 'KSA'},
    'Maxi Araújo': {'nation_code': 'URU', 'position': 'DF', 'club_team': 'Toluca', 'league': 'MEX'},
    'Raúl Jiménez': {'nation_code': 'MEX', 'position': 'FW', 'club_team': 'Fulham', 'league': 'ENG'},
    'Mikel Oyarzabal': {'nation_code': 'ESP', 'position': 'FW', 'club_team': 'Real Sociedad', 'league': 'ESP'},
    'Riyad Mahrez': {'nation_code': 'ALG', 'position': 'FW', 'club_team': 'Al-Ahli', 'league': 'KSA'},
    'Daniel Muñoz': {'nation_code': 'COL', 'position': 'DF', 'club_team': 'Crystal Palace', 'league': 'ENG'},
    'Rubén Vargas': {'nation_code': 'SUI', 'position': 'FW', 'club_team': 'Augsburg', 'league': 'GER'},
    'Cyle Larin': {'nation_code': 'CAN', 'position': 'FW', 'club_team': 'RCD Espanyol', 'league': 'ESP'},
    'Habib Diarra': {'nation_code': 'SEN', 'position': 'MF', 'club_team': 'Southampton', 'league': 'ENG'},
    'Ermin Mahmic': {'nation_code': 'BIH', 'position': 'FW', 'club_team': 'FK Tuzla City', 'league': 'BIH'},
    'Yan Diomande': {'nation_code': 'CIV', 'position': 'MF', 'club_team': 'Le Havre', 'league': 'FRA'},
    'Felix Nmecha': {'nation_code': 'GER', 'position': 'MF', 'club_team': 'Borussia Dortmund', 'league': 'GER'},
    'Elliot Anderson': {'nation_code': 'SCO', 'position': 'MF', 'club_team': 'Newcastle', 'league': 'ENG'},
    'Keito Nakamura': {'nation_code': 'JPN', 'position': 'MF', 'club_team': 'Stade de Reims', 'league': 'FRA'},
    'Alex Freeman': {'nation_code': 'USA', 'position': 'DF', 'club_team': 'Orlando City', 'league': 'USA'},
    'Pedro Vite': {'nation_code': 'ECU', 'position': 'MF', 'club_team': 'Vancouver Whitecaps', 'league': 'USA'},
    'Houssem Aouar': {'nation_code': 'ALG', 'position': 'MF', 'club_team': 'Roma', 'league': 'ITA'},
    'Nathan Saliba': {'nation_code': 'CAN', 'position': 'MF', 'club_team': 'CF Montréal', 'league': 'USA'},
    'Arthur Masuaku': {'nation_code': 'COD', 'position': 'DF', 'club_team': 'Lens', 'league': 'FRA'},
    'Gabriel Magalhães': {'nation_code': 'BRA', 'position': 'DF', 'club_team': 'Arsenal', 'league': 'ENG'},
    'Chancel Mbemba': {'nation_code': 'COD', 'position': 'DF', 'club_team': 'Lens', 'league': 'FRA'},
    'Ermin Mahmic': {'nation_code': 'BIH', 'position': 'FW', 'club_team': 'FK Tuzla City', 'league': 'BIH'},
    'Jan Paul van Hecke': {'nation_code': 'NED', 'position': 'DF', 'club_team': 'Brighton', 'league': 'ENG'},
    'Chadi Riad': {'nation_code': 'MAR', 'position': 'DF', 'club_team': 'Real Betis', 'league': 'ESP'},
    'Patrick Berg': {'nation_code': 'NOR', 'position': 'MF', 'club_team': 'FK Bodø/Glimt', 'league': 'NOR'},
    'Hannibal Mejbri': {'nation_code': 'TUN', 'position': 'MF', 'club_team': 'Burnley', 'league': 'ENG'},
    'Sead Kolašinac': {'nation_code': 'BIH', 'position': 'DF', 'club_team': 'Atalanta', 'league': 'ITA'},
    'Iliman Ndiaye': {'nation_code': 'SEN', 'position': 'FW', 'club_team': 'Everton', 'league': 'ENG'},
    'Moussa Niakhaté': {'nation_code': 'ALG', 'position': 'DF', 'club_team': 'Lens', 'league': 'FRA'},
    'Marko Arnautovic': {'nation_code': 'AUT', 'position': 'FW', 'club_team': 'Inter Milan', 'league': 'ITA'},
    'Brooklyn Ezeh': {'nation_code': 'GER', 'position': 'DF', 'club_team': 'Hamburger SV', 'league': 'GER'},
    'Elijah Just': {'nation_code': 'NZL', 'position': 'FW', 'club_team': 'Horsens', 'league': 'DEN'},
    'Folarin Balogun': {'nation_code': 'USA', 'position': 'FW', 'club_team': 'Monaco', 'league': 'FRA'},
    'Johan Manzambi': {'nation_code': 'SUI', 'position': 'MF', 'club_team': 'Freiburg', 'league': 'GER'},
    'Sadio Mané': {'nation_code': 'SEN', 'position': 'FW', 'club_team': 'Al-Nassr', 'league': 'KSA'},
    'Denzel Dumfries': {'nation_code': 'NED', 'position': 'DF', 'club_team': 'Inter Milan', 'league': 'ITA'},
    'Virgil van Dijk': {'nation_code': 'NED', 'position': 'DF', 'club_team': 'Liverpool', 'league': 'ENG'},
    'Gonzalo Plata': {'nation_code': 'ECU', 'position': 'FW', 'club_team': 'Flamengo', 'league': 'BRA'},
    'Timothy Weah': {'nation_code': 'USA', 'position': 'FW', 'club_team': 'Juventus', 'league': 'ITA'},
    'Aaron Ramsey': {'nation_code': 'WAL', 'position': 'MF', 'club_team': 'Aston Villa', 'league': 'ENG'},
    'Sardar Azmoun': {'nation_code': 'IRN', 'position': 'FW', 'club_team': 'Roma', 'league': 'ITA'},
    'Alphonso Davies': {'nation_code': 'CAN', 'position': 'DF', 'club_team': 'Bayern Munich', 'league': 'GER'},
    'Kylian Mbappé': {'nation_code': 'FRA', 'position': 'FW', 'club_team': 'Real Madrid', 'league': 'ESP'},
    'Ousmane Dembélé': {'nation_code': 'FRA', 'position': 'FW', 'club_team': 'Paris Saint-Germain', 'league': 'FRA'},
    'Harry Kane': {'nation_code': 'ENG', 'position': 'FW', 'club_team': 'Bayern Munich', 'league': 'GER'},
    'Erling Haaland': {'nation_code': 'NOR', 'position': 'FW', 'club_team': 'Manchester City', 'league': 'ENG'},
    'Mohamed Salah': {'nation_code': 'EGY', 'position': 'FW', 'club_team': 'Liverpool', 'league': 'ENG'},
    'Bukayo Saka': {'nation_code': 'ENG', 'position': 'FW', 'club_team': 'Arsenal', 'league': 'ENG'},
    'Lamine Yamal': {'nation_code': 'ESP', 'position': 'FW', 'club_team': 'Barcelona', 'league': 'ESP'},
    'Pedri': {'nation_code': 'ESP', 'position': 'MF', 'club_team': 'Barcelona', 'league': 'ESP'},
    'Frenkie de Jong': {'nation_code': 'NED', 'position': 'MF', 'club_team': 'Barcelona', 'league': 'ESP'},
    'Rúben Dias': {'nation_code': 'POR', 'position': 'DF', 'club_team': 'Manchester City', 'league': 'ENG'},
    'Bernardo Silva': {'nation_code': 'POR', 'position': 'MF', 'club_team': 'Manchester City', 'league': 'ENG'},
    'João Félix': {'nation_code': 'POR', 'position': 'FW', 'club_team': 'Barcelona', 'league': 'ESP'},
    'Takumi Minamino': {'nation_code': 'JPN', 'position': 'FW', 'club_team': 'Lille', 'league': 'FRA'},
    'Ritsu Dōan': {'nation_code': 'JPN', 'position': 'MF', 'club_team': 'SC Freiburg', 'league': 'GER'},
    'Takefusa Kubo': {'nation_code': 'JPN', 'position': 'FW', 'club_team': 'Real Sociedad', 'league': 'ESP'},
    'Wataru Endo': {'nation_code': 'JPN', 'position': 'MF', 'club_team': 'Stuttgart', 'league': 'GER'},
    'Daizen Maeda': {'nation_code': 'JPN', 'position': 'FW', 'club_team': 'Celtic', 'league': 'SCO'},
    'Dominik Szoboszlai': {'nation_code': 'HUN', 'position': 'MF', 'club_team': 'Liverpool', 'league': 'ENG'},
    'András Schäfer': {'nation_code': 'HUN', 'position': 'MF', 'club_team': 'Lech Poznań', 'league': 'POL'},
    'Ademola Lookman': {'nation_code': 'NGA', 'position': 'FW', 'club_team': 'Atalanta', 'league': 'ITA'},
    'Kelechi Iheanacho': {'nation_code': 'NGA', 'position': 'FW', 'club_team': 'Qarabağ', 'league': 'AZE'},
    'Alex Iwobi': {'nation_code': 'NGA', 'position': 'MF', 'club_team': 'Fulham', 'league': 'ENG'},
    'Ola Aina': {'nation_code': 'NGA', 'position': 'DF', 'club_team': 'Nottingham Forest', 'league': 'ENG'},
    'Wilfred Ndidi': {'nation_code': 'NGA', 'position': 'MF', 'club_team': 'Leicester', 'league': 'ENG'},
    'Milan Škriniar': {'nation_code': 'SVK', 'position': 'DF', 'club_team': 'Paris Saint-Germain', 'league': 'FRA'},
    'Stanislav Lobotka': {'nation_code': 'SVK', 'position': 'MF', 'club_team': 'Napoli', 'league': 'ITA'},
    'László Bénes': {'nation_code': 'SVK', 'position': 'MF', 'club_team': 'Union Berlin', 'league': 'GER'},
}


def _apply_name_alias(df_stats: pd.DataFrame) -> pd.DataFrame:
    if df_stats.empty or 'player_name' not in df_stats.columns:
        return df_stats
    try:
        id_path = os.path.join(os.path.dirname(__file__), 'openfootball_identity.json')
        with open(id_path, 'r', encoding='utf-8') as _f:
            _ID = json.load(_f)
        alias = _ID.get('name_alias') or {}
        if alias:
            df_stats = df_stats.copy()
            df_stats['player_name'] = df_stats['player_name'].astype(str).map(lambda n: alias.get(n, n))
    except Exception:
        pass
    return df_stats


def _enrich_player_stats(df_stats: pd.DataFrame) -> pd.DataFrame:
    """
    Enrich ESPN/Athena tournament stats with public fallback player identity metadata
    missing from the club-season view.
    """
    if df_stats.empty:
        return df_stats

    enriched = df_stats.copy()
    for col, default in {
        'nation_code': '',
        'position': '',
        'club_team': '',
        'league': '',
    }.items():
        if col not in enriched.columns:
            enriched[col] = default
        else:
            enriched[col] = enriched[col].fillna(default).replace('nan', default, regex=False)

    for name, meta in _FALLBACK_PLAYER_META.items():
        mask = enriched['player_name'].eq(name)
        if mask.any():
            for k, v in meta.items():
                enriched.loc[enriched[k].astype(str).str.strip().eq('') & mask, k] = v
    return enriched

@st.cache_data(ttl=CACHE_TTL_PLAYERS)
def get_player_percentiles() -> pd.DataFrame:
    """
    Get player performance percentiles for radar charts.
    
    Only includes 2024-2025 season data for the 48 World Cup 2026 nations.
    Deduplicates transfer players by keeping the row with the most minutes.
    """
    query = f"""
    WITH wc_nations AS (
      SELECT DISTINCT fifa_code
      FROM "{ATHENA_DATABASE}"."v_winner_prediction_dashboard_v15_live_10m"
    ),
    filtered AS (
      SELECT
          player_name, nation_code, position,
          goals, assists, xg, xa,
          tackles, interceptions, tackles_interceptions,
          gk_save_pct, minutes,
          ROW_NUMBER() OVER (
              PARTITION BY player_name
              ORDER BY minutes DESC, goals DESC, assists DESC
          ) as dedup_rank
      FROM "{ATHENA_DATABASE}"."v_real_player_rows_enriched_v8"
      WHERE season = '2024-2025'
        AND nation_code IN (SELECT fifa_code FROM wc_nations)
        AND minutes >= 500
    )
    SELECT 
        player_name, nation_code, position,
        goals, assists, xg, xa,
        tackles, interceptions, tackles_interceptions,
        gk_save_pct,
        percent_rank() OVER (ORDER BY goals) as goals_pct,
        percent_rank() OVER (ORDER BY assists) as assists_pct,
        percent_rank() OVER (ORDER BY xg) as xg_pct,
        percent_rank() OVER (ORDER BY tackles) as tackles_pct,
        percent_rank() OVER (ORDER BY interceptions) as interceptions_pct
    FROM filtered
    WHERE dedup_rank = 1
    """
    try:
        return _execute_readonly_query(query)
    except Exception as e:
        st.error(f"Player percentiles error: {e}")
        return pd.DataFrame()

# ============================================================================
# MATCH ANALYTICS & PREDICTIONS
# ============================================================================

@st.cache_data(ttl=CACHE_TTL_MATCHES)
def get_matches() -> pd.DataFrame:
    """
    Fetch match schedule from v_team_schedule.
    
    Returns all 208 matches with venue, date, and team info.
    """
    query = f"""
    SELECT 
        match_number, match_date, stage, group_name,
        team, opponent, side, venue, city, host_country,
        stadium_capacity, latitude, longitude,
        confederation, fifa_code, flag_icon
    FROM "{ATHENA_DATABASE}"."v_team_schedule"
    ORDER BY match_date, match_number
    """
    try:
        return _execute_readonly_query(query)
    except Exception as e:
        st.error(f"Matches query error: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=CACHE_TTL_PREDICTIONS)
def get_match_predictions() -> pd.DataFrame:
    """
    Get match predictions from ml_group_fixture_predictions_v15_live_match_calibrated.
    
    Includes win/draw/loss probabilities for all fixtures.
    """
    query = f"""
    SELECT 
        match_number, match_date, stage, group_name,
        team_a, team_b, venue, city,
        elo_a_pre, elo_b_pre, elo_diff,
        team_a_win_probability, draw_probability, team_b_win_probability,
        predicted_result_label, predicted_confidence,
        team_a_market_value, team_b_market_value
    FROM "{ATHENA_DATABASE}"."ml_group_fixture_predictions_v15_live_match_calibrated"
    ORDER BY match_date, match_number
    """
    try:
        return _execute_readonly_query(query)
    except Exception as e:
        st.error(f"Match predictions error: {e}")
        return pd.DataFrame()

# ============================================================================
# PREDICTIONS & MODEL RESULTS
# ============================================================================

@st.cache_data(ttl=CACHE_TTL_PREDICTIONS)
def get_predictions() -> pd.DataFrame:
    """
    Fetch championship predictions from v_winner_prediction_dashboard_v15_live_10m.
    
    Returns all 48 teams with stage probabilities and rankings.
    """
    query = f"""
    SELECT 
        team_name, fifa_code, group_name, confederation,
        championship_probability_pct, final_probability_pct,
        semifinal_probability_pct, quarterfinal_probability_pct,
        round16_probability_pct, runner_up_probability_pct,
        third_place_probability_pct,
        group_winner_probability_pct, group_runner_up_probability_pct,
        winner_rank, model_method, elo_rating,
        avg_group_points, avg_group_goal_difference, avg_group_goals_for,
        total_market_value_eur
    FROM "{ATHENA_DATABASE}"."v_winner_prediction_dashboard_v15_live_10m"
    ORDER BY winner_rank
    """
    try:
        return _execute_readonly_query(query)
    except Exception as e:
        st.error(f"Predictions query error: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=CACHE_TTL_PREDICTIONS)
def get_stage_probabilities() -> pd.DataFrame:
    """
    Get stage-by-stage probabilities from v_stage_probability_dashboard_v15_live_10m.
    
    Returns probability funnel for all teams across all stages.
    """
    query = f"""
    SELECT 
        team_name, group_name, stage,
        simulation_count, probability_pct,
        simulation_runs, model_method
    FROM "{ATHENA_DATABASE}"."v_stage_probability_dashboard_v15_live_10m"
    ORDER BY stage, probability_pct DESC
    """
    try:
        return _execute_readonly_query(query)
    except Exception as e:
        st.error(f"Stage probabilities error: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=CACHE_TTL_TEAMS)
def get_teams() -> pd.DataFrame:
    """
    Fetch comprehensive team data from wc26_dashboard_v16_live_july4.
    
    Returns all 48 teams with predictions, ELO, market value, and group stats.
    Includes new columns: elimination_stage, tournament_status
    """
    query = f"""
    SELECT 
        team_name, group_name, winner_rank, championship_probability,
        elo_rating, total_market_value_eur, contender_tier,
        round32_probability, round16_probability, quarterfinal_probability,
        semifinal_probability, final_probability,
        elimination_stage, tournament_status
    FROM "{ATHENA_DATABASE}"."wc26_dashboard_v16_live_july4"
    ORDER BY winner_rank
    """
    try:
        return _execute_readonly_query(query)
    except Exception as e:
        st.error(f"Teams query error: {e}")
        return pd.DataFrame()

# ============================================================================
# DATA QUALITY & METHODOLOGY
# ============================================================================

@st.cache_data(ttl=3600)
def get_data_quality_report() -> Dict[str, Any]:
    """
    Generate data quality report for all key tables.
    """
    client = _get_athena_client()
    if not client:
        return {"error": "Athena not connected"}
    
    quality_report = {}
    tables_to_check = [
        'wc26_dashboard_v16_live_july4',
        'v_winner_prediction_dashboard_v15_live_10m',
        'v_real_player_rows_enriched_v8',
        'v_team_schedule',
        'ml_group_fixture_predictions_v15_live_match_calibrated',
        'ml_fc_real_hybrid_team_attributes_vfc_2'
    ]
    
    for table_name in tables_to_check:
        try:
            # Row count
            count_query = f"SELECT COUNT(*) as cnt FROM \"{ATHENA_DATABASE}\".\"{table_name}\""
            count_result = _execute_athena_query(count_query)
            row_count = int(count_result['cnt'].iloc[0]) if not count_result.empty else 0
            
            quality_report[table_name] = {
                "row_count": row_count,
                "last_refresh": datetime.now().isoformat()
            }
        except Exception as e:
            quality_report[table_name] = {"error": str(e)}
    
    return quality_report

def get_model_methodology() -> Dict[str, str]:
    """
    Return documentation about model methodology.
    """
    return {
        "model_name": "V15_LIVE_FULL_MONTE_CARLO",
        "simulation_runs": "10,000,000",
        "methodology": """
            Monte Carlo tournament simulation with:
            - ELO-based match outcome probabilities
            - Market value and player performance adjustments
            - Home advantage factors (host nations)
            - Group stage qualification rules (top 2 + best 4 third-place teams)
            - Knockout stage bracket simulation
            - 10M tournament iterations for stable probabilities
        """,
        "data_sources": """
            - Team ELO ratings (club and international)
            - Player performance metrics (goals, assists, xG, xA)
            - Market values (Transfermarkt)
            - Club form (last 10 matches)
            - Squad depth and quality ratings
        """,
        "assumptions": """
            - Team strength remains constant throughout tournament
            - No injuries or suspensions modeled
            - Neutral venue for knockout stages (except hosts)
            - Draw probabilities calibrated to historical World Cup data
        """,
        "limitations": """
            - Does not model individual player injuries
            - Does not account for tactical changes during tournament
            - Historical ELO may not reflect current form perfectly
            - Monte Carlo variance decreases with more simulations
        """
    }