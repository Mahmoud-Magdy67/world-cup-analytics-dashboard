import os
import sys
import streamlit as st

# Add the data directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'data'))

def test_streamlit_integration():
    """Test how Streamlit integrates with the Athena data layer"""
    print("Testing Streamlit integration with Athena data layer...")
    
    try:
        from data.athena import get_data_source_status, get_teams
        
        # Test the status detection
        print("\n1. Testing data source status detection...")
        status = get_data_source_status()
        print(f"   Status object: {status}")
        print(f"   Athena enabled: {status.athena_enabled}")
        print(f"   Mode: {status.mode}")
        print(f"   Note: {status.note}")
        
        if status.tables_available:
            print("   Tables available:")
            for table, count in status.tables_available.items():
                print(f"     {table}: {count} rows")
        
        # Test data loading with explicit error handling like in the real app
        print("\n2. Testing data loading with error handling...")
        try:
            teams_df = get_teams()
            print(f"   Teams loaded: {len(teams_df)} rows")
            if len(teams_df) > 0:
                print(f"   Columns: {list(teams_df.columns)}")
                print("   Sample data:")
                print(teams_df.head(3))
            else:
                print("   No teams data loaded (this might be expected if tables are empty)")
        except Exception as e:
            print(f"   Error in get_teams(): {e}")
            # This is how the real app handles errors
            print("   This is how the real app would handle this...")
            import pandas as pd
            print("   Falling back to mock data")
            mock_teams = pd.DataFrame([
                {"team_name":"Spain","group_name":"H","winner_rank":1,"championship_probability":0.154},
                {"team_name":"France","group_name":"I","winner_rank":2,"championship_probability":0.091},
            ])
            print(f"   Mock teams loaded: {len(mock_teams)} rows")
        
        # Test what the Streamlit app would show
        print("\n3. Simulating Streamlit app behavior...")
        if status.athena_enabled:
            print("   Streamlit sidebar would show: ✅ Live data from Athena")
        else:
            print(f"   Streamlit sidebar would show: ℹ️ Mock data mode: {status.note[:50]}")
            
        print("\n4. Summary:")
        if status.athena_enabled and any(count > 0 for count in status.tables_available.values()):
            print("   ✅ App should show live data")
        elif status.athena_enabled:
            print("   ⚠️ App is connected to Athena but tables are empty")
            print("   This suggests data migration from BigQuery to Athena is needed")
        else:
            print("   ℹ️ App would fall back to mock data")
            
    except Exception as e:
        print(f"❌ Error in Streamlit integration test: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_streamlit_integration()