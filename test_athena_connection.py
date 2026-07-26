import os
import sys
import pandas as pd
import boto3
from botocore.exceptions import ClientError, NoCredentialsError

# Add the data directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), 'data'))

from athena import get_data_source_status, get_teams, get_players, get_matches, get_predictions

def test_athena_connection():
    """Test Athena connection and data loading"""
    print("Testing Athena connection...")
    
    # Test connection status
    status = get_data_source_status()
    print(f"Connection Status: {status}")
    print(f"Athena Enabled: {status.athena_enabled}")
    print(f"Mode: {status.mode}")
    print(f"Note: {status.note}")
    
    if status.tables_available:
        print("Tables Available:")
        for table, count in status.tables_available.items():
            print(f"  {table}: {count} rows")
    
    if status.athena_enabled:
        print("\n--- Testing Data Loading ---")
        
        # Test teams data
        print("Loading teams data...")
        teams_df = get_teams()
        print(f"Teams loaded: {len(teams_df)} rows")
        if len(teams_df) > 0:
            print(f"Columns: {list(teams_df.columns)}")
            print("Sample data:")
            print(teams_df.head(3))
        
        # Test players data
        print("\nLoading players data...")
        players_df = get_players()
        print(f"Players loaded: {len(players_df)} rows")
        if len(players_df) > 0:
            print(f"Columns: {list(players_df.columns)}")
            print("Sample data:")
            print(players_df.head(3))
            
        # Test matches data
        print("\nLoading matches data...")
        matches_df = get_matches()
        print(f"Matches loaded: {len(matches_df)} rows")
        if len(matches_df) > 0:
            print(f"Columns: {list(matches_df.columns)}")
            print("Sample data:")
            print(matches_df.head(3))
            
        # Test predictions data
        print("\nLoading predictions data...")
        predictions_df = get_predictions()
        print(f"Predictions loaded: {len(predictions_df)} rows")
        if len(predictions_df) > 0:
            print(f"Columns: {list(predictions_df.columns)}")
            print("Sample data:")
            print(predictions_df.head(3))
    else:
        print("Athena is not enabled. Using mock data.")
        print("\n--- Testing Mock Data ---")
        
        # Test mock data
        teams_df = get_teams()
        print(f"Mock teams loaded: {len(teams_df)} rows")
        
        players_df = get_players()
        print(f"Mock players loaded: {len(players_df)} rows")
        
        matches_df = get_matches()
        print(f"Mock matches loaded: {len(matches_df)} rows")
        
        predictions_df = get_predictions()
        print(f"Mock predictions loaded: {len(predictions_df)} rows")

if __name__ == "__main__":
    test_athena_connection()