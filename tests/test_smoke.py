# smoke test - works with BigQuery or mock fallback
import importlib.util
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
def test_application_structure_imports_without_external_calls():
    spec=importlib.util.spec_from_file_location("app", ROOT/"app.py")
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert len(module.PAGES)==6
    assert module.PAGE_TITLES==["Tournament Overview","Team Performance","Player Analysis","Match Analysis","Predictions / Model Results","Data & Methodology"]
def test_data_functions_return_dataframes():
    from data.bigquery import get_teams, get_players, get_matches, get_predictions, get_data_source_status
    status = get_data_source_status()
    teams = get_teams()
    players = get_players()
    matches = get_matches()
    predictions = get_predictions()
    assert not teams.empty
    assert not players.empty
    assert not matches.empty
    assert not predictions.empty
    # Verify expected columns exist
    assert "team_name" in teams.columns or "team" in teams.columns
    assert "player_name" in players.columns or "player" in players.columns
    assert "championship_probability" in teams.columns or "championship_probability_pct" in predictions.columns
    # Status should be either bigquery or mock
    assert status.mode in ["bigquery", "mock", "bigquery_error"]
    # If BigQuery connected, verify table counts
    if status.bigquery_enabled and status.tables_available:
        assert status.tables_available.get("wc26_dashboard_comprehensive_v15_live", 0) == 48
        assert status.tables_available.get("v_winner_prediction_dashboard_v15_live_10m", 0) == 48
