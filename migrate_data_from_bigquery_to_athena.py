#!/usr/bin/env python3
"""
Data migration script to transfer World Cup 2026 data from BigQuery to AWS Athena.
"""

import os
import pandas as pd
import boto3
from google.cloud import bigquery
from google.oauth2 import service_account
import json
import base64

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

def get_athena_client():
    """Initialize Athena client from environment credentials."""
    aws_access_key_id = os.getenv("AWS_ACCESS_KEY_ID")
    aws_secret_access_key = os.getenv("AWS_SECRET_ACCESS_KEY")
    region_name = os.getenv("AWS_REGION", "us-east-1")
    
    if not aws_access_key_id or not aws_secret_access_key:
        raise ValueError("AWS credentials not found in environment variables")
    
    return boto3.client(
        'athena',
        aws_access_key_id=aws_access_key_id,
        aws_secret_access_key=aws_secret_access_key,
        region_name=region_name
    )

def get_s3_client():
    """Initialize S3 client from environment credentials."""
    aws_access_key_id = os.getenv("AWS_ACCESS_KEY_ID")
    aws_secret_access_key = os.getenv("AWS_SECRET_ACCESS_KEY")
    region_name = os.getenv("AWS_REGION", "us-east-1")
    
    if not aws_access_key_id or not aws_secret_access_key:
        raise ValueError("AWS credentials not found in environment variables")
    
    return boto3.client(
        's3',
        aws_access_key_id=aws_access_key_id,
        aws_secret_access_key=aws_secret_access_key,
        region_name=region_name
    )

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

def upload_to_s3(s3_client, local_file_path, bucket_name, s3_key):
    """Upload a file to S3."""
    print(f"Uploading {local_file_path} to s3://{bucket_name}/{s3_key}")
    s3_client.upload_file(local_file_path, bucket_name, s3_key)
    print("Upload complete!")

def create_athena_table(athena_client, table_name, s3_location, database_name="worldcup_2026"):
    """Create an Athena table using CTAS from the uploaded CSV."""
    print(f"Creating Athena table {table_name}...")
    
    # Drop table if it exists
    drop_query = f"DROP TABLE IF EXISTS \"{database_name}\".\"{table_name}\""
    
    try:
        response = athena_client.start_query_execution(
            QueryString=drop_query,
            QueryExecutionContext={'Database': database_name},
            ResultConfiguration={'OutputLocation': f"s3://{os.getenv('ATHENA_OUTPUT_BUCKET', 'aws-athena-query-results-worldcup')}/"}
        )
        
        # Wait for query to complete
        import time
        query_execution_id = response['QueryExecutionId']
        while True:
            response = athena_client.get_query_execution(QueryExecutionId=query_execution_id)
            status = response['QueryExecution']['Status']['State']
            if status in ['SUCCEEDED']:
                break
            elif status in ['FAILED', 'CANCELLED']:
                reason = response['QueryExecution']['Status'].get('StateChangeReason', 'Unknown error')
                print(f"Drop table query failed: {reason}")
                break
            time.sleep(1)
    except Exception as e:
        print(f"Error dropping table: {e}")
    
    # Create table using CTAS
    ctas_query = f"""
    CREATE TABLE "{database_name}"."{table_name}"
    WITH (
        external_location = '{s3_location}',
        format = 'PARQUET',
        partitioned_by = ARRAY['partition_col']
    ) AS
    SELECT *, 'default_partition' as partition_col
    FROM (
        SELECT * 
        FROM UNNEST(SEQUENCE(1, 1)) as t(partition_col)
    ) dummy
    CROSS JOIN (
        SELECT *
        FROM "{database_name}"."temp_{table_name}"
    ) data
    """
    
    # For now, let's use a simpler approach - create external table from parquet
    print("Please manually create the table in Athena using the AWS console or CLI after uploading the data.")

def main():
    """Main migration function."""
    # Tables to migrate
    tables = [
        "wc26_dashboard_v16_live_july4",
        "v_winner_prediction_dashboard_v15_live_10m", 
        "v_real_player_rows_enriched_v8",
        "v_team_schedule",
        "v_teams_clean"
    ]
    
    # Initialize clients
    try:
        bq_client = get_bigquery_client()
        athena_client = get_athena_client()
        s3_client = get_s3_client()
    except Exception as e:
        print(f"Error initializing clients: {e}")
        return
    
    # Configuration
    s3_bucket = os.getenv("S3_DATA_BUCKET", "wc2026-simulation-data")
    s3_prefix = "migrated-from-bigquery"
    
    # Create local directory for temporary files
    os.makedirs("temp_migration", exist_ok=True)
    
    # Migrate each table
    for table_name in tables:
        try:
            print(f"\n=== Migrating {table_name} ===")
            
            # Step 1: Export from BigQuery
            local_csv_path = f"temp_migration/{table_name}.csv"
            df = export_table_from_bigquery(bq_client, table_name, local_csv_path)
            
            # Step 2: Convert to Parquet for better performance
            local_parquet_path = f"temp_migration/{table_name}.parquet"
            df.to_parquet(local_parquet_path, index=False)
            print(f"Converted to Parquet: {local_parquet_path}")
            
            # Step 3: Upload to S3
            s3_key = f"{s3_prefix}/{table_name}.parquet"
            upload_to_s3(s3_client, local_parquet_path, s3_bucket, s3_key)
            
            # Step 4: Create Athena table (commented out as it needs manual steps)
            s3_location = f"s3://{s3_bucket}/{s3_prefix}/{table_name}.parquet"
            # create_athena_table(athena_client, table_name, s3_location)
            
            print(f"Successfully migrated {table_name}")
            
        except Exception as e:
            print(f"Error migrating {table_name}: {e}")
            continue
    
    print("\nMigration process completed!")
    print("Next steps:")
    print("1. Create Athena tables using the AWS console or CLI")
    print("2. Point the tables to the Parquet files in S3")
    print("3. Test the Streamlit app to verify data is loading")

if __name__ == "__main__":
    main()