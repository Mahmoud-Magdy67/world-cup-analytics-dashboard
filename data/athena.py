from dataclasses import dataclass
from typing import Final, Optional, Dict, Any
import os
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

# Allowed datasets (read-only)
ALLOWED_ATHENA_DATASET_PLACEHOLDERS: Final[list[str]] = [
    "worldcup_2026"
]
READ_ONLY_RULE: Final[str] = "Only SELECT queries are allowed for Athena access."

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
        return None
    
    try:
        return boto3.client(
            'athena',
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
            region_name=region_name
        )
    except Exception as e:
        st.error(f"Athena auth error: {e}")
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

@dataclass(frozen=True)
class DataSourceStatus:
    mode: str
    athena_enabled: bool
    note: str
    tables_available: Optional[Dict[str, int]] = None

def get_data_source_status() -> DataSourceStatus:
    """Check if Athena is connected and list available tables."""
    client = _get_athena_client()
    if client:
        try:
            # Verify connection with simple query
            test_query = f"SELECT 1 FROM \"{ATHENA_DATABASE}\".\"wc26_dashboard_v16_live_july4\" LIMIT 1"
            _execute_athena_query(test_query)
            
            # Get table metadata
            tables_info = {}
            table_queries = {
                'wc26_dashboard_v16_live_july4': f'SELECT COUNT(*) as cnt FROM "{ATHENA_DATABASE}"."wc26_dashboard_v16_live_july4"',
                'v_winner_prediction_dashboard_v15_live_10m': f'SELECT COUNT(*) as cnt FROM "{ATHENA_DATABASE}"."v_winner_prediction_dashboard_v15_live_10m"',
                'v_real_player_rows_enriched_v8': f'SELECT COUNT(*) as cnt FROM "{ATHENA_DATABASE}"."v_real_player_rows_enriched_v8"',
                'v_team_schedule': f'SELECT COUNT(*) as cnt FROM "{ATHENA_DATABASE}"."v_team_schedule"',
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
                tables_info
            )
        except Exception as e:
            return DataSourceStatus("athena_error", False, f"Athena connection failed: {str(e)[:100]}", None)
    return DataSourceStatus("mock", False, "Athena credentials not configured; using mock data", None)

def _execute_readonly_query(query: str) -> pd.DataFrame:
    """Execute a read-only SELECT query. Raises ValueError for non-SELECT statements."""
    query_upper = query.strip().upper()
    if not (query_upper.startswith("SELECT") or query_upper.startswith("WITH")):
        raise ValueError(f"Only SELECT or WITH (CTE) queries allowed. Blocked: {query[:50]}")
    return _execute_athena_query(query)

# ============================================================================
# REAL ATHENA QUERIES - World Cup 2026 Dataset
# ============================================================================

def get_teams() -> pd.DataFrame:
    """
    Fetch teams data from wc26_dashboard_v16_live_july4.
    
    SQL Query:
    SELECT 
        team_name, group_name, winner_rank, championship_probability,
        elo_rating, total_market_value_eur, contender_tier,
        round32_probability, round16_probability, quarterfinal_probability,
        semifinal_probability, final_probability,
        elimination_stage, tournament_status
    FROM "worldcup_2026"."wc26_dashboard_v16_live_july4"
    ORDER BY winner_rank
    
    Returns columns: team_name, group_name, winner_rank, championship_probability, elo_rating,
                     total_market_value_eur, contender_tier, round32_probability, round16_probability,
                     quarterfinal_probability, semifinal_probability, final_probability,
                     elimination_stage, tournament_status
    
    Expected rows: 48 teams
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
        result = _execute_readonly_query(query)
        # Log success to Streamlit
        import streamlit as st
        st.cache_data.clear()  # Clear cache to ensure fresh data
        return result
    except Exception as e:
        import streamlit as st
        error_msg = f"Athena error in get_teams(): {str(e)[:200]}"
        st.error(f"⚠️ Athena query failed: {str(e)[:100]}")
        st.warning(f"Using mock data (6 teams) instead of 48 teams")
        print(error_msg)
        return _get_mock_teams()

def get_players() -> pd.DataFrame:
    """
    Fetch players data from v_real_player_rows_enriched_v8.
    
    SQL Query:
    SELECT 
        player_name, nation_code, position, club_team, league,
        goals, assists, goals_assists, xg, xa,
        minutes, matches_played, age
    FROM "worldcup_2026"."v_real_player_rows_enriched_v8"
    WHERE nation_code IN (SELECT DISTINCT fifa_code FROM "worldcup_2026"."v_teams_clean")
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
    FROM "{ATHENA_DATABASE}"."v_real_player_rows_enriched_v8"
    WHERE nation_code IN (SELECT DISTINCT fifa_code FROM "{ATHENA_DATABASE}"."v_teams_clean")
    ORDER BY goals DESC, assists DESC
    LIMIT 500
    """
    try:
        result = _execute_readonly_query(query)
        import streamlit as st
        st.cache_data.clear()
        return result
    except Exception as e:
        import streamlit as st
        error_msg = f"Athena error in get_players(): {str(e)[:200]}"
        st.error(f"⚠️ Athena query failed: {str(e)[:100]}")
        st.warning(f"Using mock data (6 players) instead of 500 players")
        print(error_msg)
        return _get_mock_players()

def get_matches() -> pd.DataFrame:
    """
    Fetch match schedule from v_team_schedule.
    
    SQL Query:
    SELECT 
        match_number, match_date, stage, group_name,
        team, opponent, venue, city, status
    FROM "worldcup_2026"."v_team_schedule"
    ORDER BY match_date, match_number
    
    Returns columns: match_number, match_date, stage, group_name,
                     team, opponent, venue, city, status
    
    Expected rows: 208 matches (group stage + knockout)
    """
    query = f"""
    SELECT 
        match_number, match_date, stage, group_name,
        team, opponent, venue, city, status
    FROM "{ATHENA_DATABASE}"."v_team_schedule"
    ORDER BY match_date, match_number
    """
    try:
        return _execute_readonly_query(query)
    except Exception as e:
        print(f"Athena error in get_matches(): {e}")
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
    FROM "worldcup_2026"."v_winner_prediction_dashboard_v15_live_10m"
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
    FROM "{ATHENA_DATABASE}"."v_winner_prediction_dashboard_v15_live_10m"
    ORDER BY winner_rank
    """
    try:
        return _execute_readonly_query(query)
    except Exception as e:
        print(f"Athena error in get_predictions(): {e}")
        return _get_mock_predictions()

# Backward compatibility aliases
get_mock_teams = get_teams
get_mock_players = get_players
get_mock_matches = get_matches
get_mock_predictions = get_predictions

# ============================================================================
# MOCK DATA FALLBACK (when Athena unavailable)
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