from dataclasses import dataclass
from typing import Final, Optional
import os, json, base64
import pandas as pd
from google.cloud import bigquery
from google.oauth2 import service_account

# Allowed datasets (read-only)
ALLOWED_BIGQUERY_DATASET_PLACEHOLDERS: Final[list[str]] = [
    "project-2f1e456e-b1be-4551-92b.worldcup_2026"
]
READ_ONLY_RULE: Final[str] = "Only SELECT queries are allowed for BigQuery access."

# GCP Configuration
GCP_PROJECT_ID: Final[str] = os.getenv("GCP_PROJECT_ID", "project-2f1e456e-b1be-4551-92b")
BIGQUERY_DATASET: Final[str] = "worldcup_2026"

def _get_bigquery_client() -> Optional[bigquery.Client]:
    """Initialize BigQuery client from Streamlit secrets or environment credentials."""
    import streamlit as st
    
    # Try Streamlit secrets first (for Streamlit Cloud deployment)
    creds_b64 = None
    project_id = GCP_PROJECT_ID
    
    try:
        if hasattr(st, 'secrets') and 'credentials' in st.secrets:
            creds_b64 = st.secrets['credentials'].get('GCP_SERVICE_ACCOUNT_KEY')
            project_id = st.secrets['credentials'].get('GCP_PROJECT_ID', GCP_PROJECT_ID)
    except Exception:
        pass
    
    # Fallback to environment variables (for local development)
    if not creds_b64:
        creds_b64 = os.getenv("GCP_SERVICE_ACCOUNT_KEY")
    
    if not creds_b64:
        return None
    
    try:
        creds_json = json.loads(base64.b64decode(creds_b64).decode())
        credentials = service_account.Credentials.from_service_account_info(creds_json)
        return bigquery.Client(project=project_id, credentials=credentials)
    except Exception as e:
        st.error(f"BigQuery auth error: {e}")
        return None

@dataclass(frozen=True)
class DataSourceStatus:
    mode: str
    bigquery_enabled: bool
    note: str
    tables_available: Optional[dict] = None

def get_data_source_status() -> DataSourceStatus:
    """Check if BigQuery is connected and list available tables."""
    client = _get_bigquery_client()
    if client:
        try:
            # Verify connection with simple query
            client.query("SELECT 1").result()
            
            # Get table metadata
            tables_info = {}
            table_queries = {
                'wc26_dashboard_comprehensive_v15_live': f'SELECT COUNT(*) as cnt FROM `{GCP_PROJECT_ID}.{BIGQUERY_DATASET}.wc26_dashboard_comprehensive_v15_live`',
                'v_winner_prediction_dashboard_v15_live_10m': f'SELECT COUNT(*) as cnt FROM `{GCP_PROJECT_ID}.{BIGQUERY_DATASET}.v_winner_prediction_dashboard_v15_live_10m`',
                'v_real_player_rows_enriched_v8': f'SELECT COUNT(*) as cnt FROM `{GCP_PROJECT_ID}.{BIGQUERY_DATASET}.v_real_player_rows_enriched_v8`',
                'v_team_schedule': f'SELECT COUNT(*) as cnt FROM `{GCP_PROJECT_ID}.{BIGQUERY_DATASET}.v_team_schedule`',
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
                tables_info
            )
        except Exception as e:
            return DataSourceStatus("bigquery_error", False, f"BigQuery connection failed: {str(e)[:100]}", None)
    return DataSourceStatus("mock", False, "BigQuery credentials not configured; using mock data", None)

def _execute_readonly_query(query: str) -> pd.DataFrame:
    """Execute a read-only SELECT query. Raises ValueError for non-SELECT statements."""
    query_upper = query.strip().upper()
    if not query_upper.startswith("SELECT"):
        raise ValueError(f"Only SELECT queries allowed. Blocked: {query[:50]}")
    client = _get_bigquery_client()
    if not client:
        raise RuntimeError("BigQuery client not initialized. Check GCP_SERVICE_ACCOUNT_KEY environment variable.")
    job = client.query(query)
    return job.result().to_dataframe()

# ============================================================================
# REAL BIGQUERY QUERIES - World Cup 2026 Dataset
# ============================================================================

def get_teams() -> pd.DataFrame:
    """
    Fetch teams data from wc26_dashboard_comprehensive_v15_live.
    
    SQL Query:
    SELECT 
        team_name, group_name, winner_rank, championship_probability,
        elo_rating, total_market_value_eur, contender_tier,
        round32_probability, round16_probability, quarterfinal_probability,
        semifinal_probability, final_probability,
        avg_group_points, avg_group_goal_difference, avg_group_goals_for
    FROM `project-2f1e456e-b1be-4551-92b.worldcup_2026.wc26_dashboard_comprehensive_v15_live`
    ORDER BY winner_rank
    
    Returns columns: team_name, group_name, winner_rank, championship_probability, elo_rating,
                     total_market_value_eur, contender_tier, round32_probability, round16_probability,
                     quarterfinal_probability, semifinal_probability, final_probability,
                     avg_group_points, avg_group_goal_difference, avg_group_goals_for
    
    Expected rows: 48 teams
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
        print(f"BigQuery error in get_teams(): {e}")
        return _get_mock_teams()

def get_players() -> pd.DataFrame:
    """
    Fetch players data from v_real_player_rows_enriched_v8.
    
    SQL Query:
    SELECT 
        player_name, nation_code, position, club_team, league,
        goals, assists, goals_assists, xg, xa,
        minutes, matches_played, age
    FROM `project-2f1e456e-b1be-4551-92b.worldcup_2026.v_real_player_rows_enriched_v8`
    WHERE nation_code IN (SELECT DISTINCT fifa_code FROM `project-2f1e456e-b1be-4551-92b.worldcup_2026.v_teams_clean`)
    ORDER BY goals DESC, assists DESC
    LIMIT 500
    
    Returns columns: player_name, nation_code, position, club_team, league,
                     goals, assists, goals_assists, xg, xa, minutes, matches_played, age
    
    Expected rows: ~500 players (top scorers from World Cup nations)
    """
    query = f"""
    SELECT 
        player_name, nation_code, position, club_team, league,
        goals, assists, goals_assists, xg, xa,
        minutes, matches_played, age
    FROM `{GCP_PROJECT_ID}.{BIGQUERY_DATASET}.v_real_player_rows_enriched_v8`
    WHERE nation_code IN (SELECT DISTINCT fifa_code FROM `{GCP_PROJECT_ID}.{BIGQUERY_DATASET}.v_teams_clean`)
    ORDER BY goals DESC, assists DESC
    LIMIT 500
    """
    try:
        return _execute_readonly_query(query)
    except Exception as e:
        print(f"BigQuery error in get_players(): {e}")
        return _get_mock_players()

def get_matches() -> pd.DataFrame:
    """
    Fetch match schedule from v_team_schedule.
    
    SQL Query:
    SELECT 
        match_number, match_date, stage, group_name,
        team, opponent, venue, city, status
    FROM `project-2f1e456e-b1be-4551-92b.worldcup_2026.v_team_schedule`
    ORDER BY match_date, match_number
    
    Returns columns: match_number, match_date, stage, group_name,
                     team, opponent, venue, city, status
    
    Expected rows: 208 matches (group stage + knockout)
    """
    query = f"""
    SELECT 
        match_number, match_date, stage, group_name,
        team, opponent, venue, city, status
    FROM `{GCP_PROJECT_ID}.{BIGQUERY_DATASET}.v_team_schedule`
    ORDER BY match_date, match_number
    """
    try:
        return _execute_readonly_query(query)
    except Exception as e:
        print(f"BigQuery error in get_matches(): {e}")
        return _get_mock_matches()

def get_predictions() -> pd.DataFrame:
    """
    Fetch championship predictions from v_winner_prediction_dashboard_v15_live_10m.
    
    SQL Query:
    SELECT 
        team_name, fifa_code, group_name, confederation,
        championship_probability_pct, final_probability_pct,
        semifinal_probability_pct, quarterfinal_probability_pct,
        round16_probability_pct, winner_rank, model_method,
        elo_rating, generated_at
    FROM `project-2f1e456e-b1be-4551-92b.worldcup_2026.v_winner_prediction_dashboard_v15_live_10m`
    ORDER BY winner_rank
    
    Returns columns: team_name, fifa_code, group_name, confederation,
                     championship_probability_pct, final_probability_pct,
                     semifinal_probability_pct, quarterfinal_probability_pct,
                     round16_probability_pct, winner_rank, model_method,
                     elo_rating, generated_at
    
    Expected rows: 48 teams
    """
    query = f"""
    SELECT 
        team_name, fifa_code, group_name, confederation,
        championship_probability_pct, final_probability_pct,
        semifinal_probability_pct, quarterfinal_probability_pct,
        round16_probability_pct, winner_rank, model_method,
        elo_rating, generated_at
    FROM `{GCP_PROJECT_ID}.{BIGQUERY_DATASET}.v_winner_prediction_dashboard_v15_live_10m`
    ORDER BY winner_rank
    """
    try:
        return _execute_readonly_query(query)
    except Exception as e:
        print(f"BigQuery error in get_predictions(): {e}")
        return _get_mock_predictions()

# Backward compatibility aliases
get_mock_teams = get_teams
get_mock_players = get_players
get_mock_matches = get_matches
get_mock_predictions = get_predictions

# ============================================================================
# MOCK DATA FALLBACK (when BigQuery unavailable)
# ============================================================================

def _get_mock_teams():
    return pd.DataFrame([
        {"team_name":"Spain","group_name":"H","winner_rank":1,"championship_probability":0.154,"elo_rating":2212,"total_market_value_eur":3427975000,"contender_tier":"Top 5"},
        {"team_name":"France","group_name":"I","winner_rank":2,"championship_probability":0.091,"elo_rating":2107,"total_market_value_eur":4083000000,"contender_tier":"Top 5"},
        {"team_name":"Argentina","group_name":"J","winner_rank":3,"championship_probability":0.083,"elo_rating":2158,"total_market_value_eur":1569025000,"contender_tier":"Top 5"},
        {"team_name":"England","group_name":"L","winner_rank":4,"championship_probability":0.079,"elo_rating":2081,"total_market_value_eur":4251575000,"contender_tier":"Top 5"},
        {"team_name":"Netherlands","group_name":"F","winner_rank":5,"championship_probability":0.068,"elo_rating":2024,"total_market_value_eur":2121375000,"contender_tier":"Top 5"},
        {"team_name":"Germany","group_name":"E","winner_rank":6,"championship_probability":0.053,"elo_rating":1975,"total_market_value_eur":2380800000,"contender_tier":"Top 10"},
    ])

def _get_mock_players():
    return pd.DataFrame([
        {"player_name":"Robert Lewandowski","nation_code":"POL","position":"FW","club_team":"Bayern Munich","league":"GER","goals":41,"assists":7,"xg":32.1,"xa":4.8,"minutes":2458,"matches_played":29,"age":31},
        {"player_name":"Luis Suárez","nation_code":"URU","position":"FW","club_team":"Barcelona","league":"ESP","goals":40,"assists":17,"xg":35.8,"xa":13.3,"minutes":3150,"matches_played":35,"age":28},
        {"player_name":"Lionel Messi","nation_code":"ARG","position":"FW","club_team":"Barcelona","league":"ESP","goals":37,"assists":9,"xg":26.9,"xa":14.0,"minutes":2830,"matches_played":34,"age":29},
        {"player_name":"Erling Haaland","nation_code":"NOR","position":"FW","club_team":"Manchester City","league":"EPL","goals":36,"assists":8,"xg":32.8,"xa":5.8,"minutes":2769,"matches_played":35,"age":22},
        {"player_name":"Harry Kane","nation_code":"ENG","position":"FW","club_team":"Bayern Munich","league":"GER","goals":36,"assists":8,"xg":33.1,"xa":6.8,"minutes":2839,"matches_played":32,"age":30},
        {"player_name":"Kylian Mbappé","nation_code":"FRA","position":"FW","club_team":"Paris Saint-Germain","league":"FRA","goals":33,"assists":7,"xg":None,"xa":None,"minutes":2343,"matches_played":29,"age":19},
    ])

def _get_mock_matches():
    return pd.DataFrame([
        {"match_number":1,"match_date":"2026-06-11","stage":"Group Stage","group_name":"A","team":"South Africa","opponent":"Mexico","venue":"Estadio Azteca","city":"Mexico City","status":"confirmed_group_fixture"},
        {"match_number":2,"match_date":"2026-06-11","stage":"Group Stage","group_name":"A","team":"Czechia","opponent":"Korea Republic","venue":"Estadio Akron","city":"Guadalajara","status":"confirmed_group_fixture"},
        {"match_number":3,"match_date":"2026-06-12","stage":"Group Stage","group_name":"B","team":"Bosnia and Herzegovina","opponent":"Canada","venue":"BMO Field","city":"Toronto","status":"confirmed_group_fixture"},
        {"match_number":4,"match_date":"2026-06-12","stage":"Group Stage","group_name":"D","team":"United States","opponent":"Paraguay","venue":"SoFi Stadium","city":"Los Angeles","status":"confirmed_group_fixture"},
        {"match_number":5,"match_date":"2026-06-13","stage":"Group Stage","group_name":"C","team":"Haiti","opponent":"Scotland","venue":"Gillette Stadium","city":"Boston","status":"confirmed_group_fixture"},
        {"match_number":6,"match_date":"2026-06-13","stage":"Group Stage","group_name":"D","team":"Türkiye","opponent":"Australia","venue":"BC Place","city":"Vancouver","status":"confirmed_group_fixture"},
    ])

def _get_mock_predictions():
    return pd.DataFrame([
        {"team_name":"Spain","fifa_code":"ESP","group_name":"H","confederation":"UEFA","championship_probability_pct":15.35,"final_probability_pct":23.25,"semifinal_probability_pct":36.77,"quarterfinal_probability_pct":52.18,"round16_probability_pct":80.37,"winner_rank":1,"model_method":"V15_LIVE_FULL_MONTE_CARLO","elo_rating":2212.23},
        {"team_name":"France","fifa_code":"FRA","group_name":"I","confederation":"UEFA","championship_probability_pct":9.09,"final_probability_pct":16.14,"semifinal_probability_pct":26.83,"quarterfinal_probability_pct":40.99,"round16_probability_pct":73.52,"winner_rank":2,"model_method":"V15_LIVE_FULL_MONTE_CARLO","elo_rating":2106.79},
        {"team_name":"Argentina","fifa_code":"ARG","group_name":"J","confederation":"CONMEBOL","championship_probability_pct":8.27,"final_probability_pct":17.02,"semifinal_probability_pct":31.54,"quarterfinal_probability_pct":47.82,"round16_probability_pct":64.48,"winner_rank":3,"model_method":"V15_LIVE_FULL_MONTE_CARLO","elo_rating":2157.70},
        {"team_name":"England","fifa_code":"ENG","group_name":"L","confederation":"UEFA","championship_probability_pct":7.87,"final_probability_pct":14.20,"semifinal_probability_pct":23.04,"quarterfinal_probability_pct":35.55,"round16_probability_pct":53.47,"winner_rank":4,"model_method":"V15_LIVE_FULL_MONTE_CARLO","elo_rating":2080.53},
        {"team_name":"Netherlands","fifa_code":"NED","group_name":"F","confederation":"UEFA","championship_probability_pct":6.83,"final_probability_pct":13.14,"semifinal_probability_pct":25.30,"quarterfinal_probability_pct":48.25,"round16_probability_pct":68.28,"winner_rank":5,"model_method":"V15_LIVE_FULL_MONTE_CARLO","elo_rating":2024.24},
        {"team_name":"Germany","fifa_code":"GER","group_name":"E","confederation":"UEFA","championship_probability_pct":5.27,"final_probability_pct":10.56,"semifinal_probability_pct":21.58,"quarterfinal_probability_pct":41.13,"round16_probability_pct":70.83,"winner_rank":6,"model_method":"V15_LIVE_FULL_MONTE_CARLO","elo_rating":1974.93},
    ])
