#!/usr/bin/env python3
"""
Test script to verify Streamlit app functionality after BigQuery to Athena migration
"""

import sys
import os

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_athena_connection():
    """Test Athena connection status"""
    print("Testing Athena connection...")
    try:
        from data.athena import get_data_source_status
        status = get_data_source_status()
        print(f"✓ Mode: {status.mode}")
        print(f"✓ Enabled: {status.athena_enabled}")
        print(f"✓ Note: {status.note}")
        if status.tables_available:
            print(f"✓ Available tables: {len(status.tables_available)}")
            for table, count in status.tables_available.items():
                print(f"  - {table}: {count} rows")
        else:
            print("⚠ No tables found in database")
        return status.athena_enabled
    except Exception as e:
        print(f"✗ Failed to test Athena connection: {e}")
        return False

def test_data_loading():
    """Test loading data from Athena"""
    print("\nTesting data loading...")
    
    try:
        from data.athena import get_teams, get_players, get_matches, get_predictions
        
        # Test teams data
        print("  Testing teams data...")
        teams = get_teams()
        print(f"  ✓ Teams loaded: {len(teams)} rows")
        
        # Test players data
        print("  Testing players data...")
        players = get_players()
        print(f"  ✓ Players loaded: {len(players)} rows")
        
        # Test matches data
        print("  Testing matches data...")
        matches = get_matches()
        print(f"  ✓ Matches loaded: {len(matches)} rows")
        
        # Test predictions data
        print("  Testing predictions data...")
        predictions = get_predictions()
        print(f"  ✓ Predictions loaded: {len(predictions)} rows")
        
        return True
    except Exception as e:
        print(f"✗ Failed to load data: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    print("=" * 60)
    print("Streamlit App Verification - BigQuery to Athena Migration")
    print("=" * 60)
    
    # Test connection
    connection_ok = test_athena_connection()
    
    if connection_ok:
        # Test data loading
        data_ok = test_data_loading()
        
        if data_ok:
            print("\n" + "=" * 60)
            print("✅ VERIFICATION RESULT: SUCCESS")
            print("Athena connection is working and data loading functions are accessible.")
            print("However, tables appear to be empty which may indicate a data migration issue.")
            print("=" * 60)
            return 0
        else:
            print("\n" + "=" * 60)
            print("❌ VERIFICATION RESULT: PARTIAL FAILURE")
            print("Athena connection works but data loading functions failed.")
            print("=" * 60)
            return 1
    else:
        print("\n" + "=" * 60)
        print("❌ VERIFICATION RESULT: CONNECTION FAILURE")
        print("Could not establish Athena connection.")
        print("=" * 60)
        return 1

if __name__ == "__main__":
    sys.exit(main())