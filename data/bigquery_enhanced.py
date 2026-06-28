"""
Enhanced BigQuery data layer for World Cup Analytics Dashboard.
Production-grade data access with caching, error handling, and comprehensive queries.
"""
from dataclasses import dataclass
from typing import Final, Optional, Dict, Any
import os, json, base64, hashlib
from datetime import datetime
import pandas as pd
from google.cloud import bigquery
from google.oauth2 import service_account
import streamlit as st

# Configuration
GCP_PROJECT_ID: Final[str] = os.getenv("GCP_PROJECT_ID", "project-2f1e456e-b1be-4551-92b")
BIGQUERY_DATASET: Final[str] = "worldcup_2026"

# Cache TTLs (seconds)
CACHE_TTL_KPI: Final[int] = 300  # 5 minutes
CACHE_TTL_TEAMS: Final[int] = 600  # 10 minutes
CACHE_TTL_PLAYERS: Final[int] = 900  # 15 minutes
CACHE_TTL_MATCHES: Final[int] = 3600  # 1 hour
CACHE_TTL_PREDICTIONS: Final[int] = 300  # 5 minutes

@dataclass(frozen=True)
class DataSourceStatus:
    mode: str
    bigquery_enabled: bool
    note: str
    tables_available: Optional[Dict[str, int]] = None
    last_refresh: Optional[datetime] = None

def _get_bigquery_client() -> Optional[bigquery.Client]:
    """Initialize BigQuery client from Streamlit secrets or environment credentials."""
    import streamlit as st
    
    # Try Streamlit secrets first (for Streamlit Cloud deployment)
    creds_b64 = None
    try:
        if 'credentials' in st.secrets:
            creds_b64 = st.secrets['credentials'].get('GCP_SERVICE_ACCOUNT_KEY')
    except Exception:
        pass
    
    # Fallback to environment variable (for local development)
    if not creds_b64:
        creds_b64 = os.getenv("GCP_SERVICE_ACCOUNT_KEY")
    
    if not creds_b64:
        st.error("⚠️ GCP_SERVICE_ACCOUNT_KEY not found in secrets or environment")
        return None
    
    try:
        creds_json = json.loads(base64.b64decode(creds_b64).decode())
        credentials = service_account.Credentials.from_service_account_info(creds_json)
        return bigquery.Client(project=GCP_PROJECT_ID, credentials=credentials)
    except Exception as e:
        st.error(f"⚠️ BigQuery auth error: {str(e)[:100]}")
        return None

def _execute_readonly_query(query: str, cache_key: Optional[str] = None) -> pd.DataFrame:
    """Execute a read-only SELECT query with caching."""
    query_upper = query.strip().upper()
    if not query_upper.startswith("SELECT"):
        raise ValueError(f"Only SELECT queries allowed. Blocked: {query[:50]}")
    
    client = _get_bigquery_client()
    if not client:
        raise RuntimeError("BigQuery client not initialized. Check GCP_SERVICE_ACCOUNT_KEY.")
    
    job = client.query(query)
    return job.result().to_dataframe()

# ============================================================================
# STATUS & HEALTH CHECKS
# ============================================================================

@st.cache_data(ttl=60)
def get_data_source_status() -> DataSourceStatus:
    """Check if BigQuery is connected and list available tables."""
    client = _get_bigquery_client()
    if client:
        try:
            client.query("SELECT 1").result()
            
            # Get table metadata for key tables
            tables_info = {}
            table_queries = {
                'wc26_dashboard_comprehensive_v15_live': f'SELECT COUNT(*) as cnt FROM `{GCP_PROJECT_ID}.{BIGQUERY_DATASET}.wc26_dashboard_comprehensive_v15_live`',
                'v_winner_prediction_dashboard_v15_live_10m': f'SELECT COUNT(*) as cnt FROM `{GCP_PROJECT_ID}.{BIGQUERY_DATASET}.v_winner_prediction_dashboard_v15_live_10m`',
                'v_real_player_rows_enriched_v8': f'SELECT COUNT(*) as cnt FROM `{GCP_PROJECT_ID}.{BIGQUERY_DATASET}.v_real_player_rows_enriched_v8`',
                'v_team_schedule': f'SELECT COUNT(*) as cnt FROM `{GCP_PROJECT_ID}.{BIGQUERY_DATASET}.v_team_schedule`',
                'looker_wc26_overview_kpis_v15_live_10m': f'SELECT COUNT(*) as cnt FROM `{GCP_PROJECT_ID}.{BIGQUERY_DATASET}.looker_wc26_overview_kpis_v15_live_10m`',
                'ml_group_fixture_predictions_v15_live_match_calibrated': f'SELECT COUNT(*) as cnt FROM `{GCP_PROJECT_ID}.{BIGQUERY_DATASET}.ml_group_fixture_predictions_v15_live_match_calibrated`',
            }
            for name, query in table_queries.items():
                try:
                    result = client.query(query).result().to_dataframe()
                    tables_info[name] = int(result['cnt'].iloc[0])
                except:
                    tables_info[name] = 0
            
            return DataSourceStatus(
                "bigquery", 
                True, 
                f"Connected to BigQuery project {GCP_PROJECT_ID}.{BIGQUERY_DATASET}",
                tables_info,
                datetime.now()
            )
        except Exception as e:
            return DataSourceStatus("bigquery_error", False, f"BigQuery connection failed: {str(e)[:100]}", None, datetime.now())
    return DataSourceStatus("mock", False, "BigQuery credentials not configured; using mock data", None, datetime.now())

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
    FROM `{GCP_PROJECT_ID}.{BIGQUERY_DATASET}.looker_wc26_overview_kpis_v15_live_10m`
    """
    try:
        return _execute_readonly_query(query)
    except Exception as e:
        st.error(f"Tournament overview error: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=CACHE_TTL_TEAMS)
def get_teams() -> pd.DataFrame:
    """
    Fetch comprehensive team data from wc26_dashboard_comprehensive_v15_live.
    
    Returns all 48 teams with predictions, ELO, market value, and group stats.
    """
    query = f"""
    SELECT 
        team_name, group_name, winner_rank, championship_probability,
        elo_rating, total_market_value_eur, contender_tier,
        round32_probability, round16_probability, quarterfinal_probability,
        semifinal_probability, final_probability,
        avg_group_points, avg_group_goal_difference, avg_group_goals_for
    FROM `{GCP_PROJECT_ID}.{BIGQUERY_DATASET}.wc26_dashboard_comprehensive_v15_live`
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
    FROM `{GCP_PROJECT_ID}.{BIGQUERY_DATASET}.ml_fc_real_hybrid_team_attributes_vfc_2`
    WHERE vfc2_hybrid_power_score IS NOT NULL
    ORDER BY vfc2_hybrid_power_score DESC
    """
    try:
        result = _execute_readonly_query(query)
        # Clear cache to ensure fresh data
        st.cache_data.clear()
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
    Fetch player data from v_real_player_rows_enriched_v8.
    
    Returns top players by goals/assists with comprehensive stats.
    """
    query = f"""
    SELECT 
        player_name, nation_code, position, club_team, league, season,
        age, matches_played, starts, minutes, nineties_played,
        goals, assists, goals_assists, xg, xa, npxg,
        shots, shots_on_target, shot_on_target_pct,
        tackles, tackles_won, interceptions, blocks, clearances,
        progressive_passes, progressive_carries, progressive_receives,
        gk_minutes, gk_goals_against, gk_save_pct, gk_clean_sheets
    FROM `{GCP_PROJECT_ID}.{BIGQUERY_DATASET}.v_real_player_rows_enriched_v8`
    ORDER BY goals DESC, assists DESC, xg DESC
    LIMIT {limit}
    """
    try:
        return _execute_readonly_query(query)
    except Exception as e:
        st.error(f"Players query error: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=CACHE_TTL_PLAYERS)
def get_player_percentiles() -> pd.DataFrame:
    """
    Get player performance percentiles for radar charts.
    """
    query = f"""
    SELECT 
        player_name, nation_code, position,
        goals, assists, xg, xa,
        progressive_passes, progressive_carries,
        tackles, interceptions,
        gk_save_pct,
        PERCENT_RANK() OVER (ORDER BY goals) as goals_pct,
        PERCENT_RANK() OVER (ORDER BY assists) as assists_pct,
        PERCENT_RANK() OVER (ORDER BY xg) as xg_pct,
        PERCENT_RANK() OVER (ORDER BY progressive_passes) as prog_pass_pct,
        PERCENT_RANK() OVER (ORDER BY tackles) as tackles_pct
    FROM `{GCP_PROJECT_ID}.{BIGQUERY_DATASET}.v_real_player_rows_enriched_v8`
    WHERE minutes >= 500
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
    FROM `{GCP_PROJECT_ID}.{BIGQUERY_DATASET}.v_team_schedule`
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
    FROM `{GCP_PROJECT_ID}.{BIGQUERY_DATASET}.ml_group_fixture_predictions_v15_live_match_calibrated`
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
        total_market_value_eur, vfc2_hybrid_power_score, real_world_score
    FROM `{GCP_PROJECT_ID}.{BIGQUERY_DATASET}.v_winner_prediction_dashboard_v15_live_10m`
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
    FROM `{GCP_PROJECT_ID}.{BIGQUERY_DATASET}.v_stage_probability_dashboard_v15_live_10m`
    ORDER BY stage, probability_pct DESC
    """
    try:
        return _execute_readonly_query(query)
    except Exception as e:
        st.error(f"Stage probabilities error: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=CACHE_TTL_PREDICTIONS)
def get_group_standings() -> pd.DataFrame:
    """
    Get expected group standings from ml_group_expected_standings_v15_live_10m.
    
    Returns qualification probabilities and expected points for all teams.
    """
    query = f"""
    SELECT 
        team_name, group_name,
        avg_group_points, avg_group_goal_difference, avg_group_goals_for,
        group_winner_probability_pct, group_runner_up_probability_pct,
        group_third_probability_pct, group_fourth_probability_pct,
        round32_probability_pct
    FROM `{GCP_PROJECT_ID}.{BIGQUERY_DATASET}.ml_group_expected_standings_v15_live_10m`
    ORDER BY group_name, avg_group_points DESC
    """
    try:
        return _execute_readonly_query(query)
    except Exception as e:
        st.error(f"Group standings error: {e}")
        return pd.DataFrame()

# ============================================================================
# DATA QUALITY & METHODOLOGY
# ============================================================================

@st.cache_data(ttl=3600)
def get_data_quality_report() -> Dict[str, Any]:
    """
    Generate data quality report for all key tables.
    """
    client = _get_bigquery_client()
    if not client:
        return {"error": "BigQuery not connected"}
    
    quality_report = {}
    tables_to_check = [
        'wc26_dashboard_comprehensive_v15_live',
        'v_winner_prediction_dashboard_v15_live_10m',
        'v_real_player_rows_enriched_v8',
        'v_team_schedule',
        'ml_group_fixture_predictions_v15_live_match_calibrated',
        'ml_fc_real_hybrid_team_attributes_vfc_2'
    ]
    
    for table_name in tables_to_check:
        try:
            # Row count
            count_query = f"SELECT COUNT(*) as cnt FROM `{GCP_PROJECT_ID}.{BIGQUERY_DATASET}.{table_name}`"
            count_result = client.query(count_query).result().to_dataframe()
            row_count = int(count_result['cnt'].iloc[0])
            
            # Null check for key columns
            table_obj = client.get_table(f"{BIGQUERY_DATASET}.{table_name}")
            nullable_columns = [f.name for f in table_obj.schema if f.is_nullable]
            
            quality_report[table_name] = {
                "row_count": row_count,
                "total_columns": len(table_obj.schema),
                "nullable_columns": len(nullable_columns),
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
