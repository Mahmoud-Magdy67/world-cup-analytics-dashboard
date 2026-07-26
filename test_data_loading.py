import os
import sys
import pandas as pd

# Add the data directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'data'))

# Set environment variables for testing (these would normally come from Streamlit secrets or env)
os.environ.setdefault("AWS_REGION", "us-east-1")
os.environ.setdefault("ATHENA_DATABASE", "worldcup_2026")
os.environ.setdefault("ATHENA_OUTPUT_BUCKET", "aws-athena-query-results-worldcup")

def test_data_loading():
    """Test the actual data loading functions from athena.py"""
    print("Testing data loading from Athena...")
    
    try:
        from data.athena import get_data_source_status, get_teams, get_players, get_matches, get_predictions
        
        # Test connection status
        print("\n1. Testing connection status...")
        status = get_data_source_status()
        print(f"   Status: {status}")
        print(f"   Athena Enabled: {status.athena_enabled}")
        print(f"   Mode: {status.mode}")
        print(f"   Note: {status.note}")
        
        if status.tables_available:
            print("   Tables Available:")
            for table, count in status.tables_available.items():
                print(f"     {table}: {count} rows")
        
        if not status.athena_enabled:
            print("❌ Athena is not enabled. Cannot proceed with data loading tests.")
            return False
            
        # Test teams data
        print("\n2. Testing teams data loading...")
        teams_df = get_teams()
        print(f"   Teams loaded: {len(teams_df)} rows")
        if len(teams_df) > 0:
            print(f"   Columns: {list(teams_df.columns)}")
            print("   Sample data:")
            print(teams_df.head(3))
        else:
            print("   ⚠️ No teams data loaded")
            
        # Test players data
        print("\n3. Testing players data loading...")
        players_df = get_players()
        print(f"   Players loaded: {len(players_df)} rows")
        if len(players_df) > 0:
            print(f"   Columns: {list(players_df.columns)}")
            print("   Sample data:")
            print(players_df.head(3))
        else:
            print("   ⚠️ No players data loaded")
            
        # Test matches data
        print("\n4. Testing matches data loading...")
        matches_df = get_matches()
        print(f"   Matches loaded: {len(matches_df)} rows")
        if len(matches_df) > 0:
            print(f"   Columns: {list(matches_df.columns)}")
            print("   Sample data:")
            print(matches_df.head(3))
        else:
            print("   ⚠️ No matches data loaded")
            
        # Test predictions data
        print("\n5. Testing predictions data loading...")
        predictions_df = get_predictions()
        print(f"   Predictions loaded: {len(predictions_df)} rows")
        if len(predictions_df) > 0:
            print(f"   Columns: {list(predictions_df.columns)}")
            print("   Sample data:")
            print(predictions_df.head(3))
        else:
            print("   ⚠️ No predictions data loaded")
            
        print("\n🎉 All data loading tests completed!")
        return True
        
    except Exception as e:
        print(f"❌ Data loading test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("=== Athena Data Loading Test ===")
    test_data_loading()