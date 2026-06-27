# smoke test intentionally avoids external calls
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
def test_mock_data_helpers_are_local_only():
    from data.bigquery import get_data_source_status,get_mock_matches,get_mock_players,get_mock_predictions,get_mock_teams
    s=get_data_source_status()
    assert s.mode=="mock" and s.bigquery_enabled is False
    assert not get_mock_teams().empty
    assert not get_mock_players().empty
    assert not get_mock_matches().empty
    assert not get_mock_predictions().empty
