#!/usr/bin/env python3
"""
Simple data export script to transfer World Cup 2026 data from BigQuery to CSV files.
These can then be manually uploaded to S3 and imported into Athena.
"""

import os
import pandas as pd
import json
import base64
from google.cloud import bigquery
from google.oauth2 import service_account

def get_bigquery_client():
    """Initialize BigQuery client from environment credentials."""
    # Try to get credentials from environment variable
    creds_b64 = os.getenv("GCP_SERVICE_ACCOUNT_KEY")
    if not creds_b64:
        raise ValueError("GCP_SERVICE_ACCOUNT_KEY environment variable not set")
    
    try:
        creds_json = json.loads(base64.b64decode(creds_b64).decode())
        credentials = service_account.Credentials.from_service_account_info(creds_json)
        project_id = creds_json.get('project_id', 'project-2f1e456e-b1be-4551-92b')
        return bigquery.Client(project=project_id, credentials=credentials)
    except Exception as e:
        raise RuntimeError(f"Failed to initialize BigQuery client: {e}")

def export_table_from_bigquery(bq_client, table_name, output_path):
    """Export a table from BigQuery to a local CSV file."""
    project_id = os.getenv("GCP_PROJECT_ID", "project-2f1e456e-b1be-4551-92b")
    dataset_id = "worldcup_2026"
    
    query = f"SELECT * FROM `{project_id}.{dataset_id}.{table_name}`"
    print(f"Exporting {table_name} from BigQuery...")
    
    df = bq_client.query(query).result().to_dataframe()
    df.to_csv(output_path, index=False)
    print(f"Exported {len(df)} rows to {output_path}")
    return df

def main():
    """Main export function."""
    # Tables to export
    tables = [
        "wc26_dashboard_v16_live_july4",
        "v_winner_prediction_dashboard_v15_live_10m", 
        "v_real_player_rows_enriched_v8",
        "v_team_schedule",
        "v_teams_clean"
    ]
    
    # Initialize BigQuery client
    try:
        bq_client = get_bigquery_client()
    except Exception as e:
        print(f"Error initializing BigQuery client: {e}")
        return
    
    # Create local directory for exported files
    os.makedirs("exported_data", exist_ok=True)
    
    # Export each table
    for table_name in tables:
        try:
            print(f"\n=== Exporting {table_name} ===")
            
            # Export from BigQuery to CSV
            local_csv_path = f"exported_data/{table_name}.csv"
            df = export_table_from_bigquery(bq_client, table_name, local_csv_path)
            
            # Also save as Parquet for better performance
            local_parquet_path = f"exported_data/{table_name}.parquet"
            df.to_parquet(local_parquet_path, index=False)
            print(f"Also saved as Parquet: {local_parquet_path}")
            
            print(f"Successfully exported {table_name}")
            
        except Exception as e:
            print(f"Error exporting {table_name}: {e}")
            continue
    
    print("\nExport process completed!")
    print("Next steps:")
    print("1. Upload the CSV/Parquet files to your S3 bucket")
    print("2. Create Athena tables pointing to these files")
    print("3. Test the Streamlit app to verify data is loading")

if __name__ == "__main__":
    main()