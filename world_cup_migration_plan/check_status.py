#!/usr/bin/env python3
"""
World Cup Analytics Dashboard - Export Status Checker

This script helps monitor the progress of export operations by:
1. Listing all tables in specified BigQuery datasets
2. Checking which tables already exist in S3
3. Identifying missing tables that still need to be exported
4. Generating reports on export progress
"""

import os
import boto3
import pandas as pd
from google.cloud import bigquery
from botocore.exceptions import ClientError
import argparse
import json
from typing import List, Dict

def setup_authentication(gcp_credentials_path):
    """Set up GCP authentication"""
    if os.path.exists(gcp_credentials_path):
        os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = gcp_credentials_path
        print("GCP authentication configured")
    else:
        print(f"Warning: GCP credentials file not found: {gcp_credentials_path}")

def initialize_clients(gcp_project_id, aws_region):
    """Initialize BigQuery and S3 clients"""
    bq_client = bigquery.Client(project=gcp_project_id)
    s3_client = boto3.client('s3', region_name=aws_region)
    return bq_client, s3_client

def list_bigquery_tables(bq_client, datasets):
    """
    List all tables in specified BigQuery datasets
    
    Args:
        bq_client: BigQuery client
        datasets: List of dataset names
        
    Returns:
        List of table names in format "dataset.table_name"
    """
    all_tables = []
    
    for dataset_id in datasets:
        try:
            dataset_ref = bq_client.dataset(dataset_id)
            tables = list(bq_client.list_tables(dataset_ref))
            for table in tables:
                all_tables.append(f"{dataset_id}.{table.table_id}")
        except Exception as e:
            print(f"Error accessing dataset '{dataset_id}': {e}")
    
    return all_tables

def list_s3_parquet_files(s3_client, bucket_name, prefix=""):
    """
    List all parquet files in an S3 bucket
    
    Args:
        s3_client: S3 client
        bucket_name: Name of the S3 bucket
        prefix: Optional prefix to filter files
        
    Returns:
        List of parquet file names (without extension and prefix)
    """
    s3_parquet_files = []
    
    try:
        paginator = s3_client.get_paginator('list_objects_v2')
        pages = paginator.paginate(Bucket=bucket_name, Prefix=prefix)
        
        for page in pages:
            if 'Contents' in page:
                for obj in page['Contents']:
                    if obj['Key'].endswith('.parquet'):
                        # Extract table name from file path
                        table_name = obj['Key'].replace(prefix, '').replace('.parquet', '')
                        s3_parquet_files.append(table_name)
                        
    except ClientError as e:
        print(f"Error accessing S3 bucket: {e}")
    
    return s3_parquet_files

def identify_missing_tables(bq_tables, s3_tables):
    """
    Identify which BigQuery tables are missing from S3
    
    Args:
        bq_tables: List of BigQuery tables in format "dataset.table_name"
        s3_tables: List of table names already in S3
        
    Returns:
        List of missing tables in format "dataset.table_name"
    """
    # Extract just the table names from BigQuery tables (without dataset prefix)
    bq_table_names = [table.split('.')[-1] for table in bq_tables]
    
    # Identify missing tables
    missing_tables = []
    for i, table_name in enumerate(bq_table_names):
        if table_name not in s3_tables:
            missing_tables.append(bq_tables[i])  # Store full name with dataset
    
    return missing_tables

def generate_detailed_report(bq_tables, s3_tables, missing_tables, bucket_name, datasets):
    """
    Generate a detailed report on export status
    """
    print("=" * 80)
    print("WORLD CUP ANALYTICS DASHBOARD - BIGQUERY TO S3 EXPORT STATUS REPORT")
    print("=" * 80)
    print(f"Project Datasets: {', '.join(datasets)}")
    print(f"Total BigQuery tables: {len(bq_tables)}")
    print(f"Tables already in S3: {len(s3_tables)}")
    print(f"Missing tables to export: {len(missing_tables)}")
    print(f"S3 Bucket: {bucket_name}")
    print()
    
    # Calculate completion percentage
    if bq_tables:
        completed = len(bq_tables) - len(missing_tables)
        completion_pct = (completed / len(bq_tables)) * 100
        print(f"Completion: {completion_pct:.1f}% ({completed}/{len(bq_tables)})")
    
    print()
    if missing_tables:
        print("Missing tables:")
        # Group by dataset for better readability
        dataset_groups = {}
        for table in missing_tables:
            dataset = table.split('.')[0]
            if dataset not in dataset_groups:
                dataset_groups[dataset] = []
            dataset_groups[dataset].append(table.split('.')[1])
        
        for dataset, tables in dataset_groups.items():
            print(f"  {dataset}: {len(tables)} tables")
            # Show first 10 tables in each dataset
            for table in tables[:10]:
                print(f"    - {table}")
            if len(tables) > 10:
                print(f"    ... and {len(tables) - 10} more")
    else:
        print("✓ All tables have been successfully exported!")
    
    print()
    print("Sample S3 tables:")
    for table in s3_tables[:15]:
        print(f"  - {table}")
    
    if len(s3_tables) > 15:
        print(f"  ... and {len(s3_tables) - 15} more")
    
    return {
        'total_bq_tables': len(bq_tables),
        'tables_in_s3': len(s3_tables),
        'missing_tables': len(missing_tables),
        'completion_percentage': completion_pct if bq_tables else 0,
        'datasets': datasets,
        's3_bucket': bucket_name
    }

def save_tables_to_files(bq_tables, s3_tables, missing_tables):
    """
    Save table lists to files for further processing
    """
    # Save all BigQuery tables
    with open('all_bq_tables.txt', 'w') as f:
        for table in bq_tables:
            f.write(f"{table}\n")
    
    # Save S3 tables
    with open('s3_parquet_tables.txt', 'w') as f:
        for table in s3_tables:
            f.write(f"{table}\n")
    
    # Save missing tables
    with open('missing_tables.txt', 'w') as f:
        for table in missing_tables:
            f.write(f"{table}\n")
    
    # Save in JSON format for programmatic access
    report_data = {
        'all_bq_tables': bq_tables,
        's3_parquet_tables': s3_tables,
        'missing_tables': missing_tables
    }
    
    with open('migration_status.json', 'w') as f:
        json.dump(report_data, f, indent=2)
    
    print()
    print("Files saved:")
    print("  - all_bq_tables.txt: All BigQuery tables")
    print("  - s3_parquet_tables.txt: Tables already in S3")
    print("  - missing_tables.txt: Tables that still need to be exported")
    print("  - migration_status.json: Complete status report in JSON format")

def estimate_remaining_time(missing_count, avg_time_per_table=30):
    """
    Estimate remaining time based on average time per table
    
    Args:
        missing_count: Number of tables still to export
        avg_time_per_table: Average seconds per table (default 30 seconds)
        
    Returns:
        Estimated time in hours and minutes
    """
    total_seconds = missing_count * avg_time_per_table
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    
    if hours > 0:
        return f"{int(hours)} hours and {int(minutes)} minutes"
    else:
        return f"{int(minutes)} minutes"

def main(gcp_project_id, gcp_credentials_path, aws_bucket_name, datasets, s3_prefix, aws_region):
    """
    Main function to check export status
    
    Args:
        gcp_project_id: GCP project ID
        gcp_credentials_path: Path to GCP service account credentials
        aws_bucket_name: S3 bucket name
        datasets: List of BigQuery datasets to check
        s3_prefix: Prefix for parquet files in S3
        aws_region: AWS region
    """
    print("Checking World Cup Analytics Dashboard BigQuery to S3 export status...")
    
    # Set up authentication
    setup_authentication(gcp_credentials_path)
    
    # Initialize clients
    try:
        bq_client, s3_client = initialize_clients(gcp_project_id, aws_region)
    except Exception as e:
        print(f"Error initializing clients: {e}")
        return
    
    # List BigQuery tables
    print("Listing BigQuery tables...")
    bq_tables = list_bigquery_tables(bq_client, datasets)
    
    # List S3 parquet files
    print("Listing S3 parquet files...")
    s3_tables = list_s3_parquet_files(s3_client, aws_bucket_name, s3_prefix)
    
    # Identify missing tables
    print("Identifying missing tables...")
    missing_tables = identify_missing_tables(bq_tables, s3_tables)
    
    # Generate report
    report = generate_detailed_report(bq_tables, s3_tables, missing_tables, aws_bucket_name, datasets)
    
    # Estimate remaining time
    if missing_tables:
        estimated_time = estimate_remaining_time(len(missing_tables))
        print(f"\nEstimated time to complete: {estimated_time} (based on ~30 seconds per table)")
    
    # Save to files
    save_tables_to_files(bq_tables, s3_tables, missing_tables)
    
    return report

if __name__ == "__main__":
    # Configuration
    GCP_PROJECT_ID = "your-worldcup-project-id"
    GCP_CREDENTIALS_PATH = "/path/to/gcp-service-account.json"
    AWS_BUCKET_NAME = "world-cup-analytics-data"
    DATASETS = ["world_cup_2026", "world_cup_historical", "world_cup_player_stats", "world_cup_team_stats"]
    S3_PREFIX = "input/"
    AWS_REGION = "us-east-1"
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Check World Cup data export status from BigQuery to S3')
    parser.add_argument('--project-id', default=GCP_PROJECT_ID, help='GCP project ID')
    parser.add_argument('--credentials', default=GCP_CREDENTIALS_PATH, help='Path to GCP service account credentials')
    parser.add_argument('--bucket', default=AWS_BUCKET_NAME, help='S3 bucket name')
    parser.add_argument('--datasets', nargs='+', default=DATASETS, help='BigQuery datasets to check')
    parser.add_argument('--prefix', default=S3_PREFIX, help='S3 prefix for parquet files')
    parser.add_argument('--region', default=AWS_REGION, help='AWS region')
    
    args = parser.parse_args()
    
    # Run the status check
    report = main(
        args.project_id,
        args.credentials,
        args.bucket,
        args.datasets,
        args.prefix,
        args.region
    )