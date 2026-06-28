# smoke test - works with mock fallback
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
    assert not get_teams().empty
    assert not get_players().empty
    assert not get_matches().empty
    assert not get_predictions().empty
    assert status.mode in ["bigquery", "mock", "bigquery_error"]
