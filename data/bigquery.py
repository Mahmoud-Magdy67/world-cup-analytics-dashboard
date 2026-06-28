from dataclasses import dataclass
from typing import Final, Optional
import os, json, base64
import pandas as pd
from google.cloud import bigquery

# Allowed datasets (read-only)
ALLOWED_BIGQUERY_DATASET_PLACEHOLDERS: Final[list[str]] = [
    "PROJECT_ID.worldcup_2026",
    "PROJECT_ID.worldcup_analytics", 
    "PROJECT_ID.worldcup_predictions"
]
READ_ONLY_RULE: Final[str] = "Only SELECT queries are allowed for BigQuery access."

# GCP Configuration
GCP_PROJECT_ID: Final[str] = os.getenv("GCP_PROJECT_ID", "project-2f1e456e-b1be-4551-92b")

def _get_bigquery_client() -> Optional[bigquery.Client]:
    """Initialize BigQuery client from environment credentials."""
    creds_b64 = os.getenv("GCP_SERVICE_ACCOUNT_KEY")
    if not creds_b64:
        return None
    try:
        creds_json = json.loads(base64.b64decode(creds_b64).decode())
        credentials = bigquery.Credentials.from_service_account_info(creds_json)
        return bigquery.Client(project=GCP_PROJECT_ID, credentials=credentials)
    except Exception:
        return None

@dataclass(frozen=True)
class DataSourceStatus:
    mode: str
    bigquery_enabled: bool
    note: str

def get_data_source_status() -> DataSourceStatus:
    """Check if BigQuery is connected and functional."""
    client = _get_bigquery_client()
    if client:
        try:
            client.query("SELECT 1").result()
            return DataSourceStatus("bigquery", True, f"Connected to BigQuery project {GCP_PROJECT_ID}")
        except Exception as e:
            return DataSourceStatus("bigquery_error", False, f"BigQuery connection failed: {str(e)[:100]}")
    return DataSourceStatus("mock", False, "BigQuery credentials not configured; using mock data")

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

# Public API functions
def get_teams() -> pd.DataFrame:
    """Fetch teams data from BigQuery or fallback to mock."""
    query = f"""
    SELECT team, confederation, "group" as group_letter, rating, goals_for, goals_against, xg, win_probability
    FROM `{GCP_PROJECT_ID}.worldcup_2026.teams`
    ORDER BY rating DESC
    """
    try:
        return _execute_readonly_query(query)
    except Exception:
        return _get_mock_teams()

def get_players() -> pd.DataFrame:
    """Fetch players data from BigQuery or fallback to mock."""
    query = f"""
    SELECT player, team, position, goals, assists, xg, xa, minutes
    FROM `{GCP_PROJECT_ID}.worldcup_2026.players`
    ORDER BY goals DESC
    """
    try:
        return _execute_readonly_query(query)
    except Exception:
        return _get_mock_players()

def get_matches() -> pd.DataFrame:
    """Fetch matches data from BigQuery or fallback to mock."""
    query = f"""
    SELECT CONCAT(home_team, ' vs ', away_team) as match, stage, home_goals, away_goals, total_xg, attendance
    FROM `{GCP_PROJECT_ID}.worldcup_2026.matches`
    ORDER BY stage DESC, attendance DESC
    """
    try:
        return _execute_readonly_query(query)
    except Exception:
        return _get_mock_matches()

def get_predictions() -> pd.DataFrame:
    """Fetch predictions data from BigQuery or fallback to mock."""
    query = f"""
    SELECT team, win_probability, rating, model_method
    FROM `{GCP_PROJECT_ID}.worldcup_predictions.tournament_winner`
    ORDER BY win_probability DESC
    """
    try:
        return _execute_readonly_query(query)
    except Exception:
        return _get_mock_predictions()

# Backward compatibility aliases
get_mock_teams = get_teams
get_mock_players = get_players
get_mock_matches = get_matches
get_mock_predictions = get_predictions

# Legacy mock data (fallback)
def _get_mock_teams():
    return pd.DataFrame([
        {"team":"Brazil","confederation":"CONMEBOL","group":"A","rating":91,"goals_for":14,"goals_against":5,"xg":12.8,"win_probability":0.18},
        {"team":"France","confederation":"UEFA","group":"B","rating":90,"goals_for":13,"goals_against":6,"xg":11.7,"win_probability":0.16},
        {"team":"Argentina","confederation":"CONMEBOL","group":"C","rating":89,"goals_for":12,"goals_against":6,"xg":10.9,"win_probability":0.14},
        {"team":"England","confederation":"UEFA","group":"D","rating":88,"goals_for":11,"goals_against":7,"xg":10.2,"win_probability":0.12},
        {"team":"Morocco","confederation":"CAF","group":"E","rating":84,"goals_for":8,"goals_against":5,"xg":8.4,"win_probability":0.07},
        {"team":"Japan","confederation":"AFC","group":"F","rating":82,"goals_for":7,"goals_against":6,"xg":7.2,"win_probability":0.05},
    ])

def _get_mock_players():
    return pd.DataFrame([
        {"player":"Vinicius Jr","team":"Brazil","position":"Forward","goals":5,"assists":3,"xg":4.6,"xa":2.1,"minutes":560},
        {"player":"Kylian Mbappe","team":"France","position":"Forward","goals":6,"assists":2,"xg":5.2,"xa":1.8,"minutes":590},
        {"player":"Lionel Messi","team":"Argentina","position":"Forward","goals":4,"assists":4,"xg":3.7,"xa":3.4,"minutes":540},
        {"player":"Jude Bellingham","team":"England","position":"Midfielder","goals":3,"assists":3,"xg":2.8,"xa":2.6,"minutes":610},
        {"player":"Achraf Hakimi","team":"Morocco","position":"Defender","goals":1,"assists":4,"xg":0.9,"xa":2.9,"minutes":620},
        {"player":"Takefusa Kubo","team":"Japan","position":"Midfielder","goals":2,"assists":2,"xg":1.7,"xa":2.3,"minutes":430},
    ])

def _get_mock_matches():
    return pd.DataFrame([
        {"match":"Brazil vs France","stage":"Semi-final","home_goals":2,"away_goals":1,"total_xg":3.4,"attendance":79000},
        {"match":"Argentina vs England","stage":"Semi-final","home_goals":1,"away_goals":1,"total_xg":2.7,"attendance":76000},
        {"match":"Morocco vs Japan","stage":"Quarter-final","home_goals":2,"away_goals":0,"total_xg":2.3,"attendance":61000},
        {"match":"Brazil vs Morocco","stage":"Quarter-final","home_goals":3,"away_goals":1,"total_xg":3.8,"attendance":71000},
        {"match":"France vs Japan","stage":"Round of 16","home_goals":2,"away_goals":1,"total_xg":2.9,"attendance":67000},
    ])

def _get_mock_predictions():
    t=_get_mock_teams()[["team","win_probability","rating"]].copy()
    t["final_probability"]=(t.win_probability*1.8).clip(upper=0.32)
    t["model_method"]=["elo_xg_blend","elo_xg_blend","monte_carlo","monte_carlo","baseline","baseline"]
    return t
